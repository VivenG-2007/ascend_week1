"""
Campus Events Lookup Tool
Queries the structured Events table for upcoming college events.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Event

def get_events(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(Event)
    if from_date:
        query = query.filter(Event.event_date >= from_date)
    if to_date:
        query = query.filter(Event.event_date <= to_date)

    query = query.order_by(Event.event_date.asc())
    results = query.all()

    return [
        {
            "title": ev.title,
            "event_date": ev.event_date,
            "venue": ev.venue,
            "description": ev.description,
            "organizer": ev.organizer
        }
        for ev in results
    ]
