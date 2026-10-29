"""
Exam Schedule Lookup Tool
Queries the structured Exams table for section or subject.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Exam

def get_exam_schedule(db: Session, section: Optional[str] = None, subject: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(Exam)
    if section:
        query = query.filter(Exam.section.ilike(f"%{section.strip()}%"))
    if subject:
        query = query.filter(Exam.subject.ilike(f"%{subject.strip()}%"))

    query = query.order_by(Exam.exam_date.asc())
    results = query.all()

    return [
        {
            "exam_type": e.exam_type,
            "subject": e.subject,
            "section": e.section,
            "exam_date": e.exam_date,
            "start_time": e.start_time,
            "room": e.room
        }
        for e in results
    ]
