import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum
)
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True) # e.g. Circular, Notice, Rulebook
    department = Column(String(100), nullable=True) # e.g. Accounts, Exam Cell, Hostel
    source_date = Column(String(50), nullable=True) # YYYY-MM-DD
    file_url = Column(String(500), nullable=True)
    language = Column(String(10), default="en") # en, te
    content_hash = Column(String(64), nullable=True, index=True)
    processing_status = Column(String(50), default="pending") # pending, processing, completed, failed
    extraction_status = Column(String(50), default="none") # native_pdf, ocr_fallback, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=True)
    ocr_status = Column(String(50), default="none") # none, ocr_applied, ocr_failed
    warnings = Column(Text, nullable=True)

    document = relationship("Document", back_populates="pages")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    department = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=False)
    cabin = Column(String(100), nullable=False)
    block = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    office_hours = Column(String(200), nullable=True)

    timetables = relationship("Timetable", back_populates="faculty")

class Timetable(Base):
    __tablename__ = "timetable"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    section = Column(String(50), nullable=False) # e.g. CSE-A, CSE-B
    day = Column(String(20), nullable=False) # Monday, Tuesday, ...
    period = Column(Integer, nullable=False) # 1, 2, 3...
    start_time = Column(String(20), nullable=False) # e.g. 09:15 AM
    end_time = Column(String(20), nullable=False) # e.g. 10:10 AM
    subject = Column(String(200), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty.id"), nullable=True)
    room = Column(String(50), nullable=False)

    faculty = relationship("Faculty", back_populates="timetables")

class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    exam_type = Column(String(50), nullable=False) # Mid-Term, End-Semester
    subject = Column(String(200), nullable=False)
    section = Column(String(50), nullable=False)
    exam_date = Column(String(50), nullable=False) # YYYY-MM-DD
    start_time = Column(String(20), nullable=False)
    room = Column(String(50), nullable=False)

class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    event_date = Column(String(50), nullable=False) # YYYY-MM-DD
    venue = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    organizer = Column(String(150), nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default="student") # student, faculty, parent, visitor, admin
    department = Column(String(100), nullable=True) # e.g. CSE, ECE, Accounts
    phone = Column(String(50), nullable=True)
    student_id = Column(String(50), nullable=True) # e.g. Roll No / Registration No
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    tickets = relationship("Ticket", back_populates="user", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    question = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    department = Column(String(50), nullable=False) # Exam Cell, Accounts, Hostel, Transport, Library, Admissions, General
    status = Column(String(20), default="open") # open, in_progress, resolved
    contact = Column(String(100), nullable=True)
    transcript = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name = Column(String(200), nullable=True)
    user_email = Column(String(150), nullable=True)
    user_phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tickets")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(100), nullable=True, index=True)
    role = Column(String(20), nullable=False) # user, assistant
    text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    sources = Column(JSON, nullable=True) # list of citation objects
    confidence = Column(Float, nullable=True)
    stt_ms = Column(Float, nullable=True)
    llm_ms = Column(Float, nullable=True)
    tts_ms = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
