"""PDF / image ingestion: validate, store original, extract (text layer or OCR), chunk, embed,
persist canonical text in the relational DB, index vectors in ChromaDB.

A document is marked `processed` only when persistence AND indexing both succeeded."""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date

import pymupdf as fitz  # PyMuPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document, DocumentPage, DocumentStatus, ExtractionStatus
from app.services.chunking import chunk_pages
from app.services.embeddings import Embedder
from app.services.language import detect_language
from app.services.ocr import OcrProvider, OcrUnavailable
from app.services.storage import Storage, safe_filename
from app.services.text_clean import clean_text
from app.services.vectorstore import VectorStore

log = logging.getLogger("campusvoice.ingest")

MIN_TEXT_CHARS = 25  # a PDF page with less text than this is treated as scanned
OCR_DPI = 200
SIGNATURES = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
ALIASES = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}


class UploadRejected(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message, self.status_code = message, status_code


@dataclass
class IngestionDeps:
    storage: Storage
    ocr: OcrProvider
    embedder: Embedder
    vectors: VectorStore


@dataclass
class IngestionReport:
    document_id: str
    status: str
    extraction_status: str
    pages: int = 0
    ocr_pages: int = 0
    chunks: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0


def validate_upload(filename: str, declared_mime: str | None, data: bytes, max_bytes: int) -> str:
    """Return the verified MIME type. Checks size, declared type AND file signature."""
    if not data:
        raise UploadRejected("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise UploadRejected(f"File is larger than {max_bytes // (1024 * 1024)} MB.", 413)
    mime = ALIASES.get((declared_mime or "").lower(), (declared_mime or "").lower())
    if mime not in SIGNATURES:
        raise UploadRejected("Unsupported file type. Upload a PDF, JPG or PNG.", 415)
    if not any(data.startswith(sig) for sig in SIGNATURES[mime]):
        raise UploadRejected("The file content does not match its declared type.", 415)
    return mime


@dataclass
class _Page:
    number: int
    text: str
    method: str  # text | ocr
    ocr_status: str  # not_needed | ok | low_quality | failed
    warnings: list[str]


def _ocr_png(png: bytes, ocr: OcrProvider) -> tuple[str, str, list[str]]:
    try:
        res = ocr.ocr_image(png)
    except OcrUnavailable as exc:
        return "", "failed", [f"OCR unavailable: {exc}"]
    except Exception as exc:  # noqa: BLE001
        log.exception("OCR crashed")
        return "", "failed", [f"OCR failed: {type(exc).__name__}"]
    text = clean_text(res.text)
    if not text:
        return "", "failed", res.warnings or ["OCR found no readable text."]
    status = "low_quality" if any("Low OCR confidence" in w for w in res.warnings) else "ok"
    return text, status, res.warnings


def _extract_pdf(data: bytes, ocr: OcrProvider) -> list[_Page]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise UploadRejected("The PDF could not be opened. It may be corrupted or password-protected.") from exc
    if doc.needs_pass:
        raise UploadRejected("Password-protected PDFs are not supported.")
    pages: list[_Page] = []
    for i, page in enumerate(doc, start=1):
        text = clean_text(page.get_text("text"))
        if len(text) >= MIN_TEXT_CHARS:
            pages.append(_Page(i, text, "text", "not_needed", []))
            continue
        png = page.get_pixmap(dpi=OCR_DPI).tobytes("png")
        ocr_text, status, warns = _ocr_png(png, ocr)
        pages.append(_Page(i, ocr_text, "ocr", status, [f"Page {i}: {w}" for w in warns]))
    return pages


def _extract_image(data: bytes, ocr: OcrProvider) -> list[_Page]:
    try:
        pix = fitz.Pixmap(data)
        png = pix.tobytes("png")
    except Exception as exc:  # noqa: BLE001
        raise UploadRejected("The image could not be read.") from exc
    text, status, warns = _ocr_png(png, ocr)
    return [_Page(1, text, "ocr", status, warns)]


def ingest_document(
    db: Session,
    deps: IngestionDeps,
    *,
    data: bytes,
    filename: str,
    declared_mime: str | None,
    title: str,
    category: str,
    department: str,
    source_date: date,
    supersedes_id: str | None = None,
    max_bytes: int = 15 * 1024 * 1024,
) -> IngestionReport:
    import time

    started = time.perf_counter()
    mime = validate_upload(filename, declared_mime, data, max_bytes)
    content_hash = hashlib.sha256(data).hexdigest()

    existing = db.scalar(select(Document).where(Document.content_hash == content_hash))
    if existing is not None:
        if existing.processing_status != DocumentStatus.failed.value:
            raise UploadRejected(f"This file was already uploaded (document {existing.id}).", 409)
        deps.vectors.delete_document(existing.id)  # retry a failed upload from scratch
        db.delete(existing)
        db.commit()

    if supersedes_id is not None and db.get(Document, supersedes_id) is None:
        raise UploadRejected("The document to supersede does not exist.")

    doc_id = str(uuid.uuid4())
    clean_name = safe_filename(filename)
    storage_path = f"documents/{doc_id}/{clean_name}"
    doc = Document(
        id=doc_id, title=title.strip(), category=category.strip(), department=department.strip(), source_date=source_date,
        original_filename=clean_name, mime_type=mime, file_size_bytes=len(data), content_hash=content_hash,
        processing_status=DocumentStatus.processing.value, extraction_status=ExtractionStatus.pending.value,
        supersedes_id=supersedes_id,
    )
    db.add(doc)
    db.commit()
    report = IngestionReport(document_id=doc_id, status=DocumentStatus.processing.value, extraction_status="pending")

    def fail(message: str) -> IngestionReport:
        db.rollback()
        try:
            deps.vectors.delete_document(doc_id)
        except Exception:  # noqa: BLE001
            log.exception("Could not clean vectors after failure")
        d = db.get(Document, doc_id)
        if d is not None:
            d.processing_status = DocumentStatus.failed.value
            d.extraction_status = report.extraction_status if report.extraction_status != "pending" else ExtractionStatus.failed.value
            d.error_message = message[:1000]
            db.commit()
        report.status, report.error = DocumentStatus.failed.value, message
        report.duration_ms = round((time.perf_counter() - started) * 1000)
        return report

    try:
        deps.storage.save(storage_path, data, mime)
        doc.storage_path = storage_path
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("Storing original failed")
        return fail(f"Could not store the original file: {type(exc).__name__}")

    try:
        pages = _extract_pdf(data, deps.ocr) if mime == "application/pdf" else _extract_image(data, deps.ocr)
    except UploadRejected as exc:
        return fail(exc.message)

    report.pages = len(pages)
    report.ocr_pages = sum(1 for p in pages if p.method == "ocr")
    for p in pages:
        report.warnings += p.warnings
    readable = [p for p in pages if p.text.strip()]
    unreadable = len(pages) - len(readable)
    if not readable:
        report.extraction_status = ExtractionStatus.failed.value
        return fail("No readable text could be extracted from this file.")
    report.extraction_status = ExtractionStatus.partial.value if (unreadable or any(p.ocr_status == "low_quality" for p in pages)) else ExtractionStatus.ok.value
    if unreadable:
        report.warnings.append(f"{unreadable} of {len(pages)} pages had no readable text.")

    try:
        full_text = "\n".join(p.text for p in readable)
        doc.language = detect_language(full_text)
        for p in pages:
            db.add(DocumentPage(document_id=doc_id, page_number=p.number, extracted_text=p.text,
                                extraction_method=p.method, ocr_status=p.ocr_status, warnings=p.warnings or None))
        drafts = chunk_pages([(p.number, p.text) for p in readable])
        chunk_rows = [Chunk(id=str(uuid.uuid4()), document_id=doc_id, page_number=d.page_number,
                            chunk_index=d.chunk_index, content=d.content, token_count=d.token_count) for d in drafts]
        db.add_all(chunk_rows)
        db.flush()
        vectors = deps.embedder.embed_passages([c.content for c in chunk_rows])
        meta = {"document_id": doc_id, "title": doc.title, "department": doc.department, "category": doc.category,
                "source_date": source_date.isoformat()}
        deps.vectors.upsert(
            ids=[c.id for c in chunk_rows], embeddings=vectors, documents=[c.content for c in chunk_rows],
            metadatas=[{**meta, "page_number": c.page_number, "chunk_index": c.chunk_index} for c in chunk_rows],
        )
        for c in chunk_rows:
            c.vector_id = c.id
        if deps.vectors.count_document(doc_id) != len(chunk_rows):
            raise RuntimeError("Vector index count does not match stored chunks")
        doc.extraction_status = report.extraction_status
        doc.processing_status = DocumentStatus.processed.value
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("Persistence/indexing failed")
        return fail(f"Indexing failed: {type(exc).__name__}: {str(exc)[:200]}")

    report.status = DocumentStatus.processed.value
    report.chunks = len(chunk_rows)
    report.duration_ms = round((time.perf_counter() - started) * 1000)
    return report
