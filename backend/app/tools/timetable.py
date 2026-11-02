from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Timetable
from app.tools.common import ToolResult, normalize_day, normalize_section, structured_source


def get_timetable(db: Session, section: str | None, day: str | None, today: date | None = None) -> ToolResult:
    sec, d = normalize_section(section), normalize_day(day, today)
    known = sorted({s for (s,) in db.execute(select(Timetable.section).distinct())})
    if sec is None or sec not in known:
        return ToolResult(tool="get_timetable", status="ambiguous",
                          message=f"Section not recognised or not provided. Available sections: {', '.join(known) or 'none'}.",
                          data={"available_sections": known})
    if d is None:
        return ToolResult(tool="get_timetable", status="ambiguous", message="Day not recognised or not provided.",
                          data={"section": sec})
    rows = db.scalars(select(Timetable).where(Timetable.section == sec, Timetable.day == d).order_by(Timetable.period)).all()
    if not rows:
        return ToolResult(tool="get_timetable", status="not_found", message=f"No classes are scheduled for {sec} on {d}.")
    data = [{"period": r.period, "start": r.start_time.strftime("%H:%M"), "end": r.end_time.strftime("%H:%M"),
             "subject": r.subject, "faculty": r.faculty.name if r.faculty else None, "room": r.room} for r in rows]
    return ToolResult(tool="get_timetable", status="found", data={"section": sec, "day": d, "periods": data},
                      sources=[structured_source(f"Timetable {sec}")])
