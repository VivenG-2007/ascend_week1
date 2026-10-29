"""
Timetable Lookup Tool
Queries the structured Timetable table for section and day.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Timetable, Faculty

def get_timetable(db: Session, section: str, day: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(Timetable).join(Faculty, Timetable.faculty_id == Faculty.id, isouter=True)
    query = query.filter(Timetable.section.ilike(f"%{section.strip()}%"))
    
    if day:
        query = query.filter(Timetable.day.ilike(f"%{day.strip()}%"))

    query = query.order_by(Timetable.period.asc())
    results = query.all()

    return [
        {
            "section": t.section,
            "day": t.day,
            "period": t.period,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "subject": t.subject,
            "room": t.room,
            "faculty_name": t.faculty.name if t.faculty else "TBA"
        }
        for t in results
    ]
