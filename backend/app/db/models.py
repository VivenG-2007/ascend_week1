"""SQLAlchemy models for CampusVoice.

Portable across SQLite (dev fallback) and PostgreSQL (Supabase): enums are stored as
strings guarded by CHECK constraints, JSON uses the generic JSON type.

Supabase/Postgres is the canonical store for text and metadata. ChromaDB (Phase 3) only
holds vectors; chunk ids here are the ids used in Chroma, so the two can always be joined.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


def new_ticket_id() -> str:
    return "CV-" + uuid.uuid4().hex[:8].upper()


def _in_list(column: str, values: list[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:
        return self.value


class DocumentStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class ExtractionStatus(StrEnum):
    pending = "pending"
    ok = "ok"
    partial = "partial"  # some pages unreadable
    failed = "failed"


class TicketStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TicketDepartment(StrEnum):
    exam_cell = "Exam Cell"
    accounts = "Accounts"
    hostel = "Hostel"
    transport = "Transport"
    library = "Library"
    admissions = "Admissions"
    general = "General"


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class Language(StrEnum):
    en = "en"
    te = "te"


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# --------------------------------------------------------------------------- documents


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(_in_list("processing_status", [s.value for s in DocumentStatus]), name="processing_status"),
        CheckConstraint(_in_list("extraction_status", [s.value for s in ExtractionStatus]), name="extraction_status"),
        Index("ix_documents_department_source_date", "department", "source_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    source_date: Mapped[date] = mapped_column(Date)
    storage_path: Mapped[str | None] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(8))
    content_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    processing_status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.pending.value)
    extraction_status: Mapped[str] = mapped_column(String(20), default=ExtractionStatus.pending.value)
    error_message: Mapped[str | None] = mapped_column(Text)
    # A revised circular points at the document it replaces.
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))

    pages: Mapped[list["DocumentPage"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="document_page"),
        CheckConstraint("page_number >= 1", name="page_number_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extraction_method: Mapped[str | None] = mapped_column(String(20))  # text | ocr | vision
    ocr_status: Mapped[str | None] = mapped_column(String(20))  # not_needed | ok | low_quality | failed
    warnings: Mapped[list | None] = mapped_column(JSON)

    document: Mapped[Document] = relationship(back_populates="pages")


class Chunk(Base):
    """Canonical chunk text. `id` is also the vector id in ChromaDB."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="document_chunk"),
        CheckConstraint("page_number >= 1", name="page_number_positive"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    vector_id: Mapped[str | None] = mapped_column(String(100))  # set once indexed in ChromaDB
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


# --------------------------------------------------------------------- structured data


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    designation: Mapped[str] = mapped_column(String(100))
    cabin: Mapped[str | None] = mapped_column(String(50))
    block: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    office_hours: Mapped[str | None] = mapped_column(String(200))


class Timetable(Base):
    __tablename__ = "timetable"
    __table_args__ = (
        UniqueConstraint("section", "day", "period", name="section_day_period"),
        CheckConstraint(_in_list("day", WEEKDAYS), name="day"),
        CheckConstraint("period >= 1", name="period_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section: Mapped[str] = mapped_column(String(30), index=True)
    day: Mapped[str] = mapped_column(String(10))
    period: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    subject: Mapped[str] = mapped_column(String(150))
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id", ondelete="SET NULL"))
    room: Mapped[str | None] = mapped_column(String(50))

    faculty: Mapped[Faculty | None] = relationship()


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_type: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(150))
    section: Mapped[str] = mapped_column(String(30), index=True)
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str | None] = mapped_column(String(50))


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    venue: Mapped[str | None] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    organizer: Mapped[str | None] = mapped_column(String(150))


# ------------------------------------------------------------------ tickets & messages


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(_in_list("status", [s.value for s in TicketStatus]), name="status"),
        CheckConstraint(_in_list("department", [d.value for d in TicketDepartment]), name="department"),
        Index("ix_tickets_department_status", "department", "status"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_ticket_id)
    question: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8), default=Language.en.value)
    department: Mapped[str] = mapped_column(String(50), default=TicketDepartment.general.value)
    status: Mapped[str] = mapped_column(String(20), default=TicketStatus.open.value)
    contact: Mapped[str | None] = mapped_column(String(200))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    transcript: Mapped[str | None] = mapped_column(Text)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint(_in_list("role", [r.value for r in MessageRole]), name="role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(8))
    sources: Mapped[list | None] = mapped_column(JSON)
    retrieval_metrics: Mapped[dict | None] = mapped_column(JSON)
    stt_ms: Mapped[int | None] = mapped_column(Integer)
    llm_ms: Mapped[int | None] = mapped_column(Integer)
    tts_ms: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
