"""Ingest the sample circulars through the real pipeline (extract/OCR -> chunk -> embed -> Postgres/SQLite + Chroma).
Safe to re-run: files already ingested are skipped.   python -m app.scripts.seed_documents"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db.models import Document
from app.db.session import get_sessionmaker
from app.deps import get_ingestion_deps
from app.services.ingestion import UploadRejected, ingest_document

SAMPLES = Path(__file__).resolve().parents[3] / "data" / "sample_circulars"
# filename, title, category, department, source_date, replaces-title
CATALOG = [
    ("fee_circular_2026-08-10.pdf", "Fee Payment Circular - Odd Semester 2026-27", "Circular", "Accounts", date(2026, 8, 10), None),
    ("exam_circular_2026-09-20.pdf", "Mid-Term 1 Examination Circular", "Circular", "Exam Cell", date(2026, 9, 20), None),
    ("hostel_rules_2026-07-15.pdf", "Hostel Rules and Timings", "Rules", "Hostel", date(2026, 7, 15), None),
    ("scanned_bus_routes_2026-07-20.png", "Bus Routes 2026-27", "Notice", "Transport", date(2026, 7, 20), None),
    ("scanned_holiday_list_2026-08-01.pdf", "Holiday List 2026-27", "Notice", "General", date(2026, 8, 1), None),
    ("fee_circular_revised_2026-10-12.pdf", "Revised Fee Payment Circular - Odd Semester 2026-27", "Circular", "Accounts", date(2026, 10, 12),
     "Fee Payment Circular - Odd Semester 2026-27"),
    ("library_timings_telugu_2026-09-05.pdf", "గ్రంథాలయ సమయాలు (Library Timings, Telugu)", "Notice", "Library", date(2026, 9, 5), None),
]
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}


def main() -> None:
    deps = get_ingestion_deps()
    with get_sessionmaker()() as db:
        for fname, title, cat, dept, sdate, replaces in CATALOG:
            path = SAMPLES / fname
            if not path.exists():
                print(f"skip   {fname} (file missing; run python -m app.scripts.make_samples)")
                continue
            old_id = db.scalar(select(Document.id).where(Document.title == replaces)) if replaces else None
            try:
                r = ingest_document(db, deps, data=path.read_bytes(), filename=fname, declared_mime=MIME[path.suffix],
                                    title=title, category=cat, department=dept, source_date=sdate, supersedes_id=old_id)
            except UploadRejected as exc:
                print(f"skip   {fname}: {exc.message}")
                continue
            print(f"{r.status:9} {fname}: pages={r.pages} ocr_pages={r.ocr_pages} chunks={r.chunks} {r.duration_ms}ms {r.warnings or ''} {r.error or ''}")


if __name__ == "__main__":
    main()
