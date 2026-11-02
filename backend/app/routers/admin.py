import statistics
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Chunk, Document, DocumentPage, DocumentStatus, Message, MessageRole, Ticket, TicketDepartment, TicketStatus, utcnow
from app.db.session import get_db
from app.deps import get_ingestion_deps
from app.schemas.admin import DocumentOut, DocumentPatch, LoginRequest, TicketList, TicketOut, TicketPatch, TokenResponse, UploadReport
from app.services.auth import authenticate, create_token, require_admin
from app.services.ingestion import IngestionDeps, UploadRejected, ingest_document
from app.services.ratelimit import login_limit

router = APIRouter(prefix="/api/admin", tags=["admin"])
protected = [Depends(require_admin)]
DEPARTMENTS = [d.value for d in TicketDepartment]


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_limit)])
def login(body: LoginRequest, settings: Settings = Depends(get_settings)) -> TokenResponse:
    if not settings.jwt_secret or not settings.admin_password_hash:
        raise HTTPException(503, "Admin access is not configured on this server.")
    if not authenticate(settings, body.username, body.password):
        raise HTTPException(401, "Incorrect username or password.")
    token, ttl = create_token(settings, body.username)
    return TokenResponse(access_token=token, expires_in=ttl)


# ---------------------------------------------------------------------------- documents


def _doc_out(db: Session, d: Document) -> DocumentOut:
    pages = db.scalars(select(DocumentPage).where(DocumentPage.document_id == d.id)).all()
    chunk_count = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == d.id)) or 0
    newer = db.scalar(select(Document.id).where(Document.supersedes_id == d.id))
    warnings = [w for p in pages for w in (p.warnings or [])]
    return DocumentOut(
        id=d.id, title=d.title, category=d.category, department=d.department, source_date=d.source_date, language=d.language,
        processing_status=d.processing_status, extraction_status=d.extraction_status, original_filename=d.original_filename,
        mime_type=d.mime_type, page_count=len(pages), ocr_pages=sum(1 for p in pages if p.extraction_method == "ocr"),
        chunk_count=chunk_count, warnings=warnings, error_message=d.error_message, supersedes_id=d.supersedes_id,
        superseded_by_id=newer, created_at=d.created_at)


@router.get("/documents", response_model=list[DocumentOut], dependencies=protected)
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [_doc_out(db, d) for d in docs]


@router.post("/documents", response_model=UploadReport, status_code=201, dependencies=protected)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=300),
    category: str = Form(..., min_length=1, max_length=100),
    department: str = Form(..., min_length=1, max_length=100),
    source_date: date = Form(...),
    supersedes_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    deps: IngestionDeps = Depends(get_ingestion_deps),
    settings: Settings = Depends(get_settings),
) -> UploadReport:
    limit = settings.max_upload_bytes
    data = file.file.read(limit + 1)  # never buffer more than the limit
    try:
        report = ingest_document(db, deps, data=data, filename=file.filename or "upload", declared_mime=file.content_type,
                                 title=title, category=category, department=department, source_date=source_date,
                                 supersedes_id=supersedes_id or None, max_bytes=limit)
    except UploadRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
    doc = db.get(Document, report.document_id)
    return UploadReport(document=_doc_out(db, doc), pages=report.pages, ocr_pages=report.ocr_pages, chunks=report.chunks,
                        warnings=report.warnings, error=report.error, duration_ms=report.duration_ms)


@router.patch("/documents/{doc_id}", response_model=DocumentOut, dependencies=protected)
def patch_document(doc_id: str, body: DocumentPatch, db: Session = Depends(get_db), deps: IngestionDeps = Depends(get_ingestion_deps)) -> DocumentOut:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found.")
    changes = body.model_dump(exclude_unset=True)
    if "supersedes_id" in changes and changes["supersedes_id"]:
        target = changes["supersedes_id"]
        if target == doc_id or db.get(Document, target) is None:
            raise HTTPException(422, "Invalid document to supersede.")
        cur = db.get(Document, target)
        while cur is not None:  # refuse cycles
            if cur.supersedes_id == doc_id:
                raise HTTPException(422, "That would create a circular supersession chain.")
            cur = db.get(Document, cur.supersedes_id) if cur.supersedes_id else None
    for k, v in changes.items():
        setattr(doc, k, v)
    db.commit()
    meta = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in changes.items() if k in ("title", "category", "department", "source_date")}
    if meta and doc.processing_status == DocumentStatus.processed.value:
        deps.vectors.update_document_metadata(doc_id, meta)
    return _doc_out(db, doc)


# ------------------------------------------------------------------------------ tickets


@router.get("/tickets", response_model=TicketList, dependencies=protected)
def list_tickets(department: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=500),
                 offset: int = Query(0, ge=0), db: Session = Depends(get_db)) -> TicketList:
    if department and department not in DEPARTMENTS:
        raise HTTPException(422, "Unknown department.")
    if status and status not in [s.value for s in TicketStatus]:
        raise HTTPException(422, "Unknown status.")
    q = select(Ticket)
    if department:
        q = q.where(Ticket.department == department)
    if status:
        q = q.where(Ticket.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)).all()
    return TicketList(total=total, items=[TicketOut.model_validate(r, from_attributes=True) for r in rows])


@router.patch("/tickets/{ticket_id}", response_model=TicketOut, dependencies=protected)
def patch_ticket(ticket_id: str, body: TicketPatch, db: Session = Depends(get_db)) -> TicketOut:
    t = db.get(Ticket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found.")
    if body.status is not None:
        t.status = body.status
        t.resolved_at = utcnow() if body.status == TicketStatus.resolved.value else None
    if body.resolution_note is not None:
        t.resolution_note = body.resolution_note.strip() or None
    db.commit()
    return TicketOut.model_validate(t, from_attributes=True)


# --------------------------------------------------------------------------- analytics

BUCKETS = [(0.0, 0.3), (0.3, 0.45), (0.45, 0.55), (0.55, 0.7), (0.7, 0.85), (0.85, 1.01)]


@router.get("/analytics", dependencies=protected)
def analytics(db: Session = Depends(get_db)) -> dict:
    user_msgs = func.lower(Message.text)
    top = db.execute(select(user_msgs, func.count().label("n")).where(Message.role == MessageRole.user.value)
                     .group_by(user_msgs).order_by(func.count().desc()).limit(10)).all()
    languages = dict(db.execute(select(Message.language, func.count()).where(Message.role == MessageRole.user.value).group_by(Message.language)).all())
    tickets_by_status = dict(db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all())
    tickets_by_dept = dict(db.execute(select(Ticket.department, func.count()).group_by(Ticket.department)).all())
    unanswered = db.execute(select(Ticket.id, Ticket.question, Ticket.department, Ticket.status, Ticket.created_at)
                            .order_by(Ticket.created_at.desc()).limit(10)).all()

    assistant = db.scalars(select(Message).where(Message.role == MessageRole.assistant.value)).all()
    lat = [m.latency_ms for m in assistant if m.latency_ms is not None]
    voice_parts = {k: [getattr(m, k) for m in assistant if getattr(m, k) is not None] for k in ("stt_ms", "llm_ms", "tts_ms")}
    scores = [m.retrieval_metrics.get("top_score") for m in assistant if m.retrieval_metrics and m.retrieval_metrics.get("top_score") is not None]
    dist = [{"range": f"{lo:.2f}-{min(hi, 1.0):.2f}", "count": sum(1 for s in scores if lo <= s < hi)} for lo, hi in BUCKETS]
    decisions = Counter((m.retrieval_metrics or {}).get("decision") or "unknown" for m in assistant)
    failures = db.scalars(select(Document).where(Document.processing_status == DocumentStatus.failed.value).order_by(Document.created_at.desc())).all()

    def stats(xs: list[int]) -> dict:
        return {"count": len(xs), "average_ms": round(statistics.mean(xs)) if xs else None, "median_ms": round(statistics.median(xs)) if xs else None}

    return {
        "totals": {"questions": sum(languages.values()), "tickets": sum(tickets_by_status.values()),
                   "documents": db.scalar(select(func.count()).select_from(Document)) or 0},
        "top_questions": [{"question": q, "count": n} for q, n in top],
        "unanswered_questions": [{"ticket_id": i, "question": q, "department": d, "status": s, "created_at": c.isoformat()} for i, q, d, s, c in unanswered],
        "tickets_by_status": tickets_by_status, "tickets_by_department": tickets_by_dept,
        "language_usage": {k or "unknown": v for k, v in languages.items()},
        "latency": {"total": stats(lat), **{k.replace("_ms", ""): stats(v) for k, v in voice_parts.items()}},
        "retrieval_confidence": {"buckets": dist, "decisions": dict(decisions)},
        "document_failures": [{"id": d.id, "title": d.title, "error": d.error_message, "created_at": d.created_at.isoformat()} for d in failures],
    }
