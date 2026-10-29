"""
Document Ingestion Pipeline
Handles file validation, hashing, storage, text extraction, OCR, chunking,
multilingual E5 embeddings, and dual persistence (Supabase/SQLite & ChromaDB).
"""
import hashlib
import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.db.models import Document, DocumentPage, Chunk
from app.services.storage import save_document_file
from app.services.ocr import extract_text_from_pdf_stream, extract_text_from_image_stream
from app.services.embeddings import generate_passage_embeddings

logger = logging.getLogger("campusvoice.ingestion")

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits text into approximately 500-token chunks with overlap.
    Uses whitespace word-boundary approximation (~0.75 tokens per word).
    """
    words = text.split()
    if not words:
        return []
    
    # Approx 375 words for 500 tokens
    target_words = int(chunk_size * 0.75)
    overlap_words = int(overlap * 0.75)
    
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + target_words]
        chunk_str = " ".join(chunk_words)
        chunks.append(chunk_str)
        i += (target_words - overlap_words)
        if i <= 0 or i >= len(words):
            break
            
    return chunks

def ingest_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    title: str,
    category: str,
    department: str,
    source_date: str,
    db: Session,
    replaces_doc_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the full ingestion pipeline.
    """
    # 1. Validation
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise ValueError(f"File size ({size_mb:.2f} MB) exceeds maximum limit of {settings.MAX_UPLOAD_MB} MB.")

    content_hash = compute_sha256(file_bytes)

    # 2. Duplicate detection
    existing = db.query(Document).filter(Document.content_hash == content_hash).first()
    if existing:
        logger.warning(f"[INGESTION] Duplicate file detected (hash: {content_hash}). Document ID: {existing.id}")
        return {
            "document_id": existing.id,
            "status": "duplicate",
            "message": f"This document has already been indexed as '{existing.title}'.",
            "chunks_indexed": len(existing.chunks)
        }

    # 3. Save File to Supabase Storage / Local
    file_url, storage_path = save_document_file(file_bytes, filename, content_type)

    # 4. Create Document Record
    doc = Document(
        title=title,
        category=category,
        department=department,
        source_date=source_date,
        file_url=file_url,
        content_hash=content_hash,
        processing_status="processing",
        extraction_status="none"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 5. Extract Text & OCR
    is_pdf = "pdf" in content_type.lower() or filename.lower().endswith(".pdf")
    is_txt = "text" in content_type.lower() or filename.lower().endswith(".txt")

    if is_pdf:
        pages = extract_text_from_pdf_stream(file_bytes)
        extraction_type = "ocr_fallback" if any(p["ocr_applied"] for p in pages) else "native_pdf"
    elif is_txt:
        p_text = file_bytes.decode("utf-8", errors="ignore").strip()
        pages = [{
            "page_number": 1,
            "text": p_text,
            "ocr_applied": False,
            "warnings": None
        }]
        extraction_type = "plain_text"
    else:
        # Image (JPG / PNG)
        img_page = extract_text_from_image_stream(file_bytes, content_type)
        pages = [img_page]
        extraction_type = "ocr_image"

    doc.extraction_status = extraction_type

    all_chunks_text = []
    chunk_meta_list = []

    # 6. Save Pages & Create Chunks
    for p in pages:
        page_record = DocumentPage(
            document_id=doc.id,
            page_number=p["page_number"],
            extracted_text=p["text"],
            ocr_status="ocr_applied" if p["ocr_applied"] else "none",
            warnings=p.get("warnings")
        )
        db.add(page_record)

        if p["text"]:
            text_chunks = chunk_text(p["text"], settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
            for idx, c_text in enumerate(text_chunks):
                all_chunks_text.append(c_text)
                chunk_meta_list.append({
                    "document_id": doc.id,
                    "page_number": p["page_number"],
                    "chunk_index": idx,
                    "title": title,
                    "department": department,
                    "source_date": source_date,
                    "replaces_doc_id": replaces_doc_id or ""
                })

    db.commit()

    # 7. Generate Multilingual E5 Embeddings & Index in ChromaDB
    indexed_count = 0
    if all_chunks_text:
        embeddings = generate_passage_embeddings(all_chunks_text)
        
        # Save canonical chunk records in DB
        for c_text, meta in zip(all_chunks_text, chunk_meta_list):
            chunk_rec = Chunk(
                document_id=doc.id,
                page_number=meta["page_number"],
                chunk_index=meta["chunk_index"],
                content=c_text,
                vector_metadata=meta
            )
            db.add(chunk_rec)
        db.commit()

        # Add to ChromaDB
        try:
            import chromadb
            if settings.CHROMA_SERVER_HOST:
                headers = {"x-chroma-token": settings.CHROMA_CLOUD_API_KEY} if settings.CHROMA_CLOUD_API_KEY else {}
                chroma_client = chromadb.HttpClient(
                    host=settings.CHROMA_SERVER_HOST,
                    port=settings.CHROMA_SERVER_HTTP_PORT or (443 if settings.CHROMA_SERVER_SSL_ENABLED else 8000),
                    ssl=settings.CHROMA_SERVER_SSL_ENABLED,
                    headers=headers
                )
            else:
                chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)

            collection = chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

            ids = [f"{doc.id}_p{m['page_number']}_c{m['chunk_index']}" for m in chunk_meta_list]
            chroma_client_metas = [
                {
                    "document_id": m["document_id"],
                    "page_number": m["page_number"],
                    "title": m["title"],
                    "department": m["department"],
                    "source_date": m["source_date"],
                    "replaces": m.get("replaces_doc_id", "")
                }
                for m in chunk_meta_list
            ]

            collection.add(
                ids=ids,
                documents=all_chunks_text,
                embeddings=embeddings,
                metadatas=chroma_client_metas
            )
            indexed_count = len(ids)
            logger.info(f"[INGESTION] Successfully indexed {indexed_count} chunks into ChromaDB for '{title}'.")
        except Exception as e:
            logger.error(f"[INGESTION] Failed to index chunks in ChromaDB: {e}")

    doc.processing_status = "completed"
    db.commit()

    return {
        "document_id": doc.id,
        "title": title,
        "status": "completed",
        "extraction_status": extraction_type,
        "pages_processed": len(pages),
        "chunks_indexed": indexed_count,
        "warnings": [p["warnings"] for p in pages if p.get("warnings")]
    }
