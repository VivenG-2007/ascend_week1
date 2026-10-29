"""
Faculty Information Lookup Tool
Queries the structured Faculty table for cabin, department, designation, email, and office hours.
"""
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models import Faculty

def find_faculty(db: Session, query_text: str) -> List[Dict[str, Any]]:
    # Remove common question filler words
    cleaned = re.sub(r'(?i)\b(where|is|the|cabin|room|office|of|who|what|details|dr\.|prof\.|faculty)\b', ' ', query_text)
    cleaned = cleaned.replace("?", " ").replace("'", " ")
    keywords = [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

    if not keywords:
        return []

    filters = []
    for kw in keywords:
        term = f"%{kw}%"
        filters.append(Faculty.name.ilike(term))
        filters.append(Faculty.department.ilike(term))
        filters.append(Faculty.cabin.ilike(term))

    results = db.query(Faculty).filter(or_(*filters)).all()

    return [
        {
            "name": f.name,
            "department": f.department,
            "designation": f.designation,
            "cabin": f.cabin,
            "block": f.block,
            "email": f.email,
            "phone": f.phone,
            "office_hours": f.office_hours
        }
        for f in results
    ]
