"""
Deterministic Escalation and Ticket Service
Creates official college helpdesk tickets when verified official evidence is unavailable.
"""
import uuid
import re
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.db.models import Ticket

logger = logging.getLogger("campusvoice.tickets")

SUPPORTED_DEPARTMENTS = [
    "Exam Cell",
    "Accounts",
    "Hostel",
    "Transport",
    "Library",
    "Admissions",
    "General"
]

DEPARTMENT_KEYWORDS = {
    "Exam Cell": ["exam", "hall ticket", "marks", "results", "mid-term", "semester exam", "revaluation", "పరీక్ష", "హాల్ టికెట్"],
    "Accounts": ["fee", "tuition", "payment", "scholarship", "receipt", "fine", "refund", "challan", "ఫీజు", "చెల్లింపు"],
    "Hostel": ["hostel", "mess", "curfew", "room", "warden", "laundry", "gate timing", "హాస్టల్", "మెస్"],
    "Transport": ["bus", "route", "driver", "transport", "pass", "pickup", "drop", "బస్సు", "రవాణా"],
    "Library": ["library", "book", "due date", "borrow", "journal", "లైబ్రరీ", "పుస్తకం"],
    "Admissions": ["admission", "counseling", "seat", "cutoff", "eligibility", "eamcet", "అడ్మిషన్"]
}

OFF_TOPIC_KEYWORDS = [
    "cricket", "movie", "weather in", "recipe", "joke", "song", "who is the prime minister",
    "bitcoin", "cryptocurrency", "capital of", "tell me a story", "write python code"
]

def is_off_topic_query(query: str) -> bool:
    """Detects whether a query is completely unrelated to college matters."""
    q_lower = query.lower()
    return any(k in q_lower for k in OFF_TOPIC_KEYWORDS)

def infer_department(query: str) -> str:
    """Infers the most appropriate college department using keyword matching with General fallback."""
    q_lower = query.lower()
    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            return dept
    return "General"

def create_department_ticket(
    db: Session,
    question: str,
    language: str = "en",
    department: Optional[str] = None,
    summary: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
    user_phone: Optional[str] = None,
    contact: Optional[str] = None
) -> Ticket:
    """
    Creates an official college helpdesk ticket stamped with user details.
    """
    assigned_dept = department or infer_department(question)
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    resolved_contact = contact or user_email or user_phone or "Guest Visitor"

    ticket = Ticket(
        id=ticket_id,
        question=question,
        language=language,
        department=assigned_dept,
        status="open",
        contact=resolved_contact,
        transcript=question,
        resolution_note=summary or "Automatically escalated due to insufficient official documentation.",
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        user_phone=user_phone
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info(f"[TICKET] Created {ticket.id} for user '{user_name or 'Guest'}' assigned to '{assigned_dept}'")
    return ticket
