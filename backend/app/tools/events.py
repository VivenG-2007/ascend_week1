from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event
from app.tools.common import ToolResult, format_date, structured_source


def get_events(db: Session, from_date: date | None = None, to_date: date | None = None, today: date | None = None) -> ToolResult:
    start = from_date or today or date.today()
    end = to_date or start + timedelta(days=7)
    if end < start:
        return ToolResult(tool="get_events", status="error", message="to_date is before from_date.")
    rows = db.scalars(select(Event).where(Event.event_date >= start, Event.event_date <= end).order_by(Event.event_date)).all()
    if not rows:
        return ToolResult(tool="get_events", status="not_found", message=f"No events between {start} and {end}.")
    data = [{"title": r.title, "date": r.event_date.isoformat(), "date_text": format_date(r.event_date), "venue": r.venue,
             "organizer": r.organizer, "description": r.description} for r in rows]
    return ToolResult(tool="get_events", status="found", data={"from": start.isoformat(), "to": end.isoformat(), "events": data},
                      sources=[structured_source("Campus events calendar")])
