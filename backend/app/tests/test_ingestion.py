from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.models import Chunk, Document, DocumentPage
from app.services.ingestion import UploadRejected, ingest_document, validate_upload
from app.services.ocr import TesseractOcr
from app.tests.conftest import BUS_TEXT, FEE_TEXT, FakeOcr, ingest, make_pdf, make_png


def test_text_pdf_is_processed_and_indexed(db, deps):
    r = ingest(db, deps, [FEE_TEXT, "Second page about scholarships."], title="Fee", department="Accounts")
    assert r.status == "processed" and r.extraction_status == "ok" and r.pages == 2 and r.ocr_pages == 0 and r.chunks == 2
    doc = db.get(Document, r.document_id)
    assert doc.processing_status == "processed" and doc.content_hash and doc.language == "en"
    assert db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)) == 2
    assert deps.vectors.count_document(doc.id) == 2
    assert deps.storage.read(doc.storage_path).startswith(b"%PDF")


def test_chunk_and_vector_metadata_link_back_to_document_and_page(db, deps):
    r = ingest(db, deps, ["Page one text about fees.", "Page two text about hostel."], title="T", department="Hostel")
    chunks = db.scalars(select(Chunk).where(Chunk.document_id == r.document_id).order_by(Chunk.chunk_index)).all()
    assert [c.page_number for c in chunks] == [1, 2] and all(c.vector_id == c.id for c in chunks)
    got = deps.vectors._col.get(where={"document_id": r.document_id}, include=["metadatas"])
    assert {m["page_number"] for m in got["metadatas"]} == {1, 2}
    assert all(m["department"] == "Hostel" and m["title"] == "T" and m["source_date"] == "2026-08-01" for m in got["metadatas"])


def test_scanned_pdf_page_uses_ocr(db, deps, ocr):
    ocr.text = "Scanned holiday list. 8 November 2026 is a holiday for the festival break."
    r = ingest(db, deps, ["", FEE_TEXT])  # page 1 has no text layer
    assert r.status == "processed" and r.ocr_pages == 1 and ocr.calls == 1
    pages = db.scalars(select(DocumentPage).where(DocumentPage.document_id == r.document_id).order_by(DocumentPage.page_number)).all()
    assert [(p.extraction_method, p.ocr_status) for p in pages] == [("ocr", "ok"), ("text", "not_needed")]


def test_image_upload_runs_ocr(db, deps, ocr):
    ocr.text = "Bus routes notice. Route R1 departs at 7:15 AM."
    r = ingest_document(db, deps, data=make_png(), filename="notice.png", declared_mime="image/png", title="Bus", category="Notice",
                        department="Transport", source_date=date(2026, 7, 20))
    assert r.status == "processed" and r.ocr_pages == 1 and r.chunks == 1


def test_unreadable_image_is_not_reported_as_processed(db, deps, ocr):
    ocr.text, ocr.warnings = "", ["OCR found no readable text."]
    r = ingest_document(db, deps, data=make_png(), filename="blur.png", declared_mime="image/png", title="Blur", category="Notice",
                        department="General", source_date=date(2026, 7, 20))
    doc = db.get(Document, r.document_id)
    assert r.status == "failed" and doc.processing_status == "failed" and doc.extraction_status == "failed"
    assert "No readable text" in r.error and doc.error_message
    assert db.scalar(select(func.count()).select_from(Chunk)) == 0 and deps.vectors.count() == 0


def test_blank_pdf_without_ocr_fails_clearly(db, deps):
    deps.ocr = FakeOcr(unavailable=True)
    r = ingest(db, deps, [""])
    assert r.status == "failed" and any("OCR unavailable" in w for w in r.warnings)


def test_low_confidence_ocr_marks_partial_with_warning(db, deps, ocr):
    ocr.text, ocr.warnings = "Faint notice about fees due on 5 October", ["Low OCR confidence (41/100); text may contain errors."]
    r = ingest(db, deps, [""])
    assert r.status == "processed" and r.extraction_status == "partial" and any("Low OCR" in w for w in r.warnings)
    assert db.get(Document, r.document_id).extraction_status == "partial"


def test_partially_unreadable_pdf_is_partial(db, deps, ocr):
    ocr.text = ""
    r = ingest(db, deps, [FEE_TEXT, ""])
    assert r.status == "processed" and r.extraction_status == "partial" and any("1 of 2 pages" in w for w in r.warnings)


def test_duplicate_upload_is_rejected_but_failed_upload_can_be_retried(db, deps, ocr):
    pdf = make_pdf([FEE_TEXT])  # PDFs embed timestamps, so build the bytes once to get identical content
    kw = dict(filename="a.pdf", declared_mime="application/pdf", title="Fee", category="C", department="Accounts", source_date=date(2026, 8, 1))
    assert ingest_document(db, deps, data=pdf, **kw).status == "processed"
    with pytest.raises(UploadRejected) as e:
        ingest_document(db, deps, data=pdf, **kw)
    assert e.value.status_code == 409
    data = make_png("same bytes")
    args = dict(filename="x.png", declared_mime="image/png", title="X", category="N", department="General", source_date=date(2026, 1, 1))
    assert ingest_document(db, deps, data=data, **args).status == "failed"
    ocr.text = "Now readable text about hostel timings."
    retry = ingest_document(db, deps, data=data, **args)
    assert retry.status == "processed"
    assert db.scalar(select(func.count()).select_from(Document).where(Document.title == "X")) == 1


@pytest.mark.parametrize("name,mime,data,code", [
    ("a.txt", "text/plain", b"hello", 415),
    ("a.pdf", "application/pdf", make_png(), 415),  # PNG bytes labelled as PDF
    ("a.png", "image/png", b"%PDF-1.4 not an image", 415),
    ("a.exe", "application/x-msdownload", b"MZ\x90\x00", 415),
    ("a.pdf", "application/pdf", b"", 422),
])
def test_upload_validation_rejects_bad_files(name, mime, data, code):
    with pytest.raises(UploadRejected) as e:
        validate_upload(name, mime, data, 1_000_000)
    assert e.value.status_code == code


def test_oversize_file_rejected():
    with pytest.raises(UploadRejected) as e:
        validate_upload("a.pdf", "application/pdf", b"%PDF-" + b"0" * 2000, 1000)
    assert e.value.status_code == 413


def test_corrupt_pdf_ends_failed_not_processed(db, deps):
    r = ingest_document(db, deps, data=b"%PDF-1.4 this is not really a pdf", filename="bad.pdf", declared_mime="application/pdf",
                        title="Bad", category="N", department="General", source_date=date(2026, 1, 1))
    assert r.status == "failed" and db.get(Document, r.document_id).processing_status == "failed"


def test_indexing_failure_rolls_back_and_marks_failed(db, deps, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("chroma down")
    monkeypatch.setattr(deps.vectors, "upsert", boom)
    r = ingest(db, deps, [FEE_TEXT])
    assert r.status == "failed" and "Indexing failed" in r.error
    assert db.scalar(select(func.count()).select_from(Chunk)) == 0 and deps.vectors.count() == 0


def test_unknown_supersedes_id_rejected(db, deps):
    with pytest.raises(UploadRejected):
        ingest(db, deps, [FEE_TEXT], supersedes_id="does-not-exist")


def test_dangerous_filename_is_sanitised(db, deps):
    r = ingest(db, deps, [FEE_TEXT], filename="../../etc/passwd.pdf")
    path = db.get(Document, r.document_id).storage_path
    assert ".." not in path and path.startswith(f"documents/{r.document_id}/")


@pytest.mark.skipif(not __import__("shutil").which("tesseract"), reason="tesseract not installed")
def test_real_tesseract_reads_an_image(db, deps):
    deps.ocr = TesseractOcr("eng")
    import pymupdf
    doc = pymupdf.open(); p = doc.new_page(); p.insert_text((50, 100), "Holiday on 8 November 2026", fontsize=24)
    png = doc[0].get_pixmap(dpi=200).tobytes("png")
    r = ingest_document(db, deps, data=png, filename="h.png", declared_mime="image/png", title="H", category="N", department="General",
                        source_date=date(2026, 8, 1))
    assert r.status == "processed"
    assert "8 November 2026" in db.scalar(select(Chunk.content))


def test_reindex_rebuilds_chroma_from_canonical_chunks(db, deps):
    from app.scripts.reindex import processed_chunk_count, reindex
    from app.services.vectorstore import VectorStore
    import uuid

    a = ingest(db, deps, [FEE_TEXT], title="A")
    ingest(db, deps, [BUS_TEXT], title="B", department="Transport")
    lost = VectorStore("/tmp/reindex_" + uuid.uuid4().hex, "fresh")  # an empty index
    assert processed_chunk_count(db) == 2 and lost.count() == 0
    assert reindex(db, deps.embedder, lost) == 2 and lost.count() == 2
    assert reindex(db, deps.embedder, lost) == 0  # idempotent
    meta = lost._col.get(where={"document_id": a.document_id}, include=["metadatas"])["metadatas"][0]
    assert meta["title"] == "A" and meta["page_number"] == 1
    assert reindex(db, deps.embedder, lost, full=True) == 2 and lost.count() == 2
