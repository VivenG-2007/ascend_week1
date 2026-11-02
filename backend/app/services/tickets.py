"""Ticket creation with duplicate protection."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Ticket, TicketStatus


def _norm(q: str) -> str:
    return re.sub(r"\W+", " ", q.lower()).strip()


def create_ticket(db: Session, *, question: str, language: str, department: str, summary: str | None,
                  session_id: str | None, transcript: str | None = None) -> Ticket:
    """Return an existing open ticket for the same session+question instead of creating a duplicate."""
    if session_id:
        open_tickets = db.scalars(
            select(Ticket).where(Ticket.session_id == session_id, Ticket.status != TicketStatus.resolved.value)
        ).all()
        for t in open_tickets:
            if _norm(t.question) == _norm(question):
                return t
    t = Ticket(question=question, language=language, department=department, summary=(summary or question)[:500],
               session_id=session_id, transcript=transcript or question)
    db.add(t)
    db.flush()
    return t
