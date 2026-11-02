import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import Chunk, Document, Event, Exam, Faculty, Message, Ticket, Timetable
from app.db.seed import seed
from datetime import date


def test_seed_populates_and_is_idempotent(db):
    first = seed(db, today=date(2026, 11, 1))
    assert first == {"faculty": 10, "timetable": 60, "exams": 10, "events": 8}
    assert seed(db, today=date(2026, 11, 1)) == {"faculty": 0, "timetable": 0, "exams": 0, "events": 0}
    assert db.scalar(select(func.count()).select_from(Faculty)) == 10


def test_seed_timetable_has_first_period_for_cse_b_monday(db):
    seed(db)
    row = db.scalar(select(Timetable).where(Timetable.section == "CSE-B", Timetable.day == "Monday", Timetable.period == 1))
    assert row is not None and row.subject and row.faculty_id is not None


def test_seed_exams_never_fall_on_weekends(db):
    seed(db)
    assert all(e.exam_date.weekday() < 5 for e in db.scalars(select(Exam)))


def test_seed_events_are_synthetic_and_in_the_future(db):
    seed(db, today=date(2026, 11, 1))
    events = db.scalars(select(Event)).all()
    assert len(events) == 8 and all(e.event_date > date(2026, 11, 1) for e in events)
    assert all("synthetic" in (e.description or "").lower() for e in events)


def _doc(**kw):
    return Document(title="Fee circular", category="Circular", department="Accounts", source_date=date(2026, 8, 1), **kw)


def test_ticket_defaults_and_status_constraint(db):
    t = Ticket(question="Where is the bursar?")
    db.add(t)
    db.commit()
    assert t.id.startswith("CV-") and t.status == "open" and t.department == "General"
    db.add(Ticket(question="x", status="closed"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_ticket_department_constraint(db):
    db.add(Ticket(question="x", department="Cafeteria"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_duplicate_content_hash_rejected(db):
    db.add(_doc(content_hash="abc"))
    db.commit()
    db.add(_doc(content_hash="abc"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_chunks_cascade_with_document_and_keep_page_metadata(db):
    doc = _doc()
    doc.chunks.append(Chunk(page_number=2, chunk_index=0, content="Last date is 15 September."))
    db.add(doc)
    db.commit()
    chunk = db.scalar(select(Chunk))
    assert chunk.page_number == 2 and chunk.document_id == doc.id
    db.delete(doc)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Chunk)) == 0


def test_revised_document_links_to_superseded(db):
    old = _doc()
    db.add(old)
    db.flush()
    new = _doc(supersedes_id=old.id)
    db.add(new)
    db.commit()
    assert new.supersedes_id == old.id


def test_message_role_constraint(db):
    db.add(Message(session_id="s" * 8, role="system", text="x"))
    with pytest.raises(IntegrityError):
        db.commit()
