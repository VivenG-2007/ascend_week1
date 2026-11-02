from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Faculty
from app.tools.common import ToolResult, structured_source

TITLES = ("dr.", "dr", "mr.", "mr", "ms.", "ms", "mrs.", "mrs", "prof.", "prof", "sir", "madam")


def find_faculty(db: Session, name_or_department: str | None) -> ToolResult:
    q = (name_or_department or "").strip()
    if len(q) < 2:
        return ToolResult(tool="find_faculty", status="ambiguous", message="Provide a faculty name or department.")
    words = [w for w in q.replace(",", " ").split() if w.lower() not in TITLES]
    if not words:
        return ToolResult(tool="find_faculty", status="ambiguous", message="Provide a faculty name or department.")
    rows = db.scalars(select(Faculty).where(or_(*[Faculty.name.ilike(f"%{w}%") for w in words]))).all()
    if not rows:  # maybe a department
        rows = db.scalars(select(Faculty).where(Faculty.department.ilike(f"%{q}%"))).all()
    if not rows:
        return ToolResult(tool="find_faculty", status="not_found", message=f"No faculty matched '{q}'.")
    strict = [r for r in rows if all(w.lower() in r.name.lower() for w in words)]
    rows = strict or rows
    data = [{"name": r.name, "department": r.department, "designation": r.designation, "cabin": r.cabin, "block": r.block,
             "email": r.email, "phone": r.phone, "office_hours": r.office_hours} for r in rows[:10]]
    status = "found" if (strict or len(rows) <= 3) else "ambiguous"
    msg = "" if status == "found" else "Several people matched; ask which one is meant."
    return ToolResult(tool="find_faculty", status=status, message=msg, data=data, sources=[structured_source("Faculty directory")])
