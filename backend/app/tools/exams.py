from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Exam
from app.tools.common import ToolResult, format_date, normalize_section, structured_source


def get_exam_schedule(db: Session, section: str | None) -> ToolResult:
    sec = normalize_section(section)
    known = sorted({s for (s,) in db.execute(select(Exam.section).distinct())})
    if sec is None or sec not in known:
        return ToolResult(tool="get_exam_schedule", status="ambiguous",
                          message=f"Section not recognised or not provided. Available sections: {', '.join(known) or 'none'}.",
                          data={"available_sections": known})
    rows = db.scalars(select(Exam).where(Exam.section == sec).order_by(Exam.exam_date, Exam.start_time)).all()
    if not rows:
        return ToolResult(tool="get_exam_schedule", status="not_found", message=f"No exams are scheduled for {sec}.")
    data = [{"exam_type": r.exam_type, "subject": r.subject, "date": r.exam_date.isoformat(), "date_text": format_date(r.exam_date),
             "start": r.start_time.strftime("%H:%M"), "room": r.room} for r in rows]
    return ToolResult(tool="get_exam_schedule", status="found", data={"section": sec, "exams": data},
                      sources=[structured_source(f"Exam schedule {sec}")])
