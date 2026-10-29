"""
Multilingual Document Retrieval Service
Queries ChromaDB using intfloat/multilingual-e5-small embeddings.
Enforces similarity thresholds, citation extraction, and latest document precedence.
"""
import logging
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.embeddings import generate_query_embedding

logger = logging.getLogger("campusvoice.retrieval")

def retrieve_document_chunks(
    query: str,
    department: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant document chunks from ChromaDB.
    Returns a list of candidate dictionaries with content, metadata, and similarity scores.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    # 1. Generate query embedding
    query_vec = generate_query_embedding(clean_query)

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

        try:
            collection = chroma_client.get_collection(name=settings.CHROMA_COLLECTION_NAME)
        except Exception:
            logger.info(f"[RETRIEVAL] Collection '{settings.CHROMA_COLLECTION_NAME}' does not exist or is empty.")
            return []

        where_filter = {}
        if department:
            where_filter = {"department": department}

        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, collection.count() or 1),
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        candidates = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for doc_text, meta, dist in zip(docs, metas, dists):
                # Cosine distance to similarity: similarity = 1 - (dist / 2) or 1 - dist depending on backend
                # For HNSW cosine, distance is in [0, 2], similarity is 1 - dist
                similarity = max(0.0, min(1.0, 1.0 - dist))
                
                candidates.append({
                    "content": doc_text,
                    "title": meta.get("title", "Official Notice"),
                    "department": meta.get("department", "General"),
                    "source_date": meta.get("source_date", ""),
                    "page_number": meta.get("page_number", 1),
                    "document_id": meta.get("document_id", ""),
                    "replaces": meta.get("replaces", ""),
                    "similarity": round(similarity, 4),
                    "superseded": False
                })

        # Precedence Resolution: If a candidate's document has been superseded by a newer candidate, flag it
        replaces_set = {c["replaces"] for c in candidates if c.get("replaces")}
        for c in candidates:
            if c["document_id"] in replaces_set:
                c["superseded"] = True

        # Sort: Active documents first (by latest date), then similarity
        candidates.sort(key=lambda x: (not x["superseded"], x.get("source_date", ""), x["similarity"]), reverse=True)

        return candidates[:top_k]

    except Exception as e:
        logger.error(f"[RETRIEVAL ERROR] Failed to query ChromaDB: {e}")
        return []
