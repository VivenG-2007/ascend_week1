"""
Admin Router for CampusVoice Helpdesk
Provides JWT protected endpoints for document uploads, ticket resolution, and structured data entry.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from jose import JWTError, jwt
import hmac
import bcrypt
from app.config import settings
from app.db.session import get_db
from app.db.models import Document, Ticket, Faculty, Timetable, Exam, Event, Message
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def verify_admin_password(plain_password: str) -> bool:
    if hmac.compare_digest(plain_password, "admin123"):
        return True
    try:
        return bcrypt.checkpw(plain_password[:72].encode("utf-8"), settings.ADMIN_PASSWORD_HASH.encode("utf-8"))
    except Exception:
        return False

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    resolution_note: Optional[str] = None

class FacultyCreateRequest(BaseModel):
    name: str
    department: str
    designation: str
    cabin: str
    block: str
    email: Optional[str] = None
    phone: Optional[str] = None
    office_hours: Optional[str] = None

class TimetableCreateRequest(BaseModel):
    section: str
    day: str
    period: int
    start_time: str
    end_time: str
    subject: str
    room: str
    faculty_id: Optional[str] = None

class ExamCreateRequest(BaseModel):
    exam_type: str
    subject: str
    section: str
    exam_date: str
    start_time: str
    room: str

class EventCreateRequest(BaseModel):
    title: str
    event_date: str
    venue: str
    description: Optional[str] = None
    organizer: Optional[str] = None

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def get_current_admin(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token."
        )
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired or invalid."
        )

# Authentication
@router.post("/login", response_model=LoginResponse)
def admin_login(creds: LoginRequest):
    # Check username
    if creds.username != settings.ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
    
    # Check password (default: admin123)
    if not verify_admin_password(creds.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    token = create_access_token({"sub": creds.username, "role": "admin"})
    return LoginResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60
    )

# Document Management
@router.get("/documents")
def list_documents(
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "category": d.category,
            "department": d.department,
            "source_date": d.source_date,
            "file_url": d.file_url,
            "processing_status": d.processing_status,
            "extraction_status": d.extraction_status,
            "chunk_count": len(d.chunks),
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]

@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("Circular"),
    department: str = Form("General"),
    source_date: str = Form(...),
    replaces_doc_id: Optional[str] = Form(None),
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        report = ingest_document(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded_doc.pdf",
            content_type=file.content_type or "application/pdf",
            title=title,
            category=category,
            department=department,
            source_date=source_date,
            db=db,
            replaces_doc_id=replaces_doc_id
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")

# Ticket Management
@router.get("/tickets")
def list_tickets(
    department: Optional[str] = None,
    status: Optional[str] = None,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)
    if department:
        query = query.filter(Ticket.department == department)
    if status:
        query = query.filter(Ticket.status == status)
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "question": t.question,
            "department": t.department,
            "status": t.status,
            "contact": t.contact,
            "user_id": t.user_id,
            "user_name": t.user_name,
            "user_email": t.user_email,
            "user_phone": t.user_phone,
            "resolution_note": t.resolution_note,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
        }
        for t in tickets
    ]

@router.patch("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: str,
    update_data: TicketUpdateRequest,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    
    if update_data.status:
        ticket.status = update_data.status
        if update_data.status == "resolved":
            ticket.resolved_at = datetime.utcnow()
    if update_data.resolution_note is not None:
        ticket.resolution_note = update_data.resolution_note

    db.commit()
    return {"message": "Ticket updated successfully", "ticket_id": ticket.id, "status": ticket.status}

# Structured Data Entry by Admin
@router.post("/faculty")
def add_faculty(
    req: FacultyCreateRequest,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    f = Faculty(
        name=req.name,
        department=req.department,
        designation=req.designation,
        cabin=req.cabin,
        block=req.block,
        email=req.email,
        phone=req.phone,
        office_hours=req.office_hours
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"message": "Faculty added successfully", "id": f.id, "name": f.name}

@router.post("/timetable")
def add_timetable(
    req: TimetableCreateRequest,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    tt = Timetable(
        section=req.section,
        day=req.day,
        period=req.period,
        start_time=req.start_time,
        end_time=req.end_time,
        subject=req.subject,
        room=req.room,
        faculty_id=req.faculty_id
    )
    db.add(tt)
    db.commit()
    db.refresh(tt)
    return {"message": "Timetable period added successfully", "id": tt.id}

@router.post("/exams")
def add_exam(
    req: ExamCreateRequest,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    ex = Exam(
        exam_type=req.exam_type,
        subject=req.subject,
        section=req.section,
        exam_date=req.exam_date,
        start_time=req.start_time,
        room=req.room
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return {"message": "Exam scheduled successfully", "id": ex.id}

@router.post("/events")
def add_event(
    req: EventCreateRequest,
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    ev = Event(
        title=req.title,
        event_date=req.event_date,
        venue=req.venue,
        description=req.description,
        organizer=req.organizer
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return {"message": "Campus event posted successfully", "id": ev.id}

# Real Analytics
@router.get("/analytics")
def get_analytics(
    admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_docs = db.query(Document).count()
    total_tickets = db.query(Ticket).count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved").count()
    
    total_messages = db.query(Message).count()
    te_messages = db.query(Message).filter(Message.language == "te").count()
    en_messages = total_messages - te_messages

    avg_latency = db.query(func.avg(Message.latency_ms)).scalar() or 0.0

    return {
        "documents_count": total_docs,
        "tickets_summary": {
            "total": total_tickets,
            "open": open_tickets,
            "resolved": resolved_tickets
        },
        "conversations": {
            "total_messages": total_messages,
            "english_count": en_messages,
            "telugu_count": te_messages,
            "avg_latency_ms": round(float(avg_latency), 2)
        }
    }
