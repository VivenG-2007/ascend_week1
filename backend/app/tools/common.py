from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.chat import SourceRef

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_TELUGU_DAYS = {"సోమవారం": 0, "మంగళవారం": 1, "బుధవారం": 2, "గురువారం": 3, "శుక్రవారం": 4, "శనివారం": 5, "ఆదివారం": 6}


class ToolResult(BaseModel):
    tool: str
    status: Literal["found", "not_found", "ambiguous", "error", "rejected"]
    message: str = ""
    data: Any = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)

    @property
    def adequate(self) -> bool:
        """Only a complete, unambiguous result counts as evidence."""
        return self.status == "found"


def weekday_name(d: date) -> str:
    return WEEKDAYS[d.weekday()]


TE_WEEKDAYS = ["సోమవారం", "మంగళవారం", "బుధవారం", "గురువారం", "శుక్రవారం", "శనివారం", "ఆదివారం"]
TE_MONTHS = ["జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్", "జూలై", "ఆగస్టు", "సెప్టెంబర్", "అక్టోబర్", "నవంబర్", "డిసెంబర్"]


def format_date(d: date, lang: str = "en") -> str:
    """Date with weekday, e.g. 'Monday, 16 November 2026'."""
    if lang == "te":
        return f"{TE_WEEKDAYS[d.weekday()]}, {d.day} {TE_MONTHS[d.month - 1]} {d.year}"
    return f"{weekday_name(d)}, {d.day} {d.strftime('%B %Y')}"


def structured_source(title: str) -> SourceRef:
    return SourceRef(document_id="structured-data", title=title, source_date=None)


def normalize_section(raw: str | None) -> str | None:
    if not raw:
        return None
    m = re.match(r"^\s*([A-Za-z]{2,5})\s*[-_ ]?\s*([A-Za-z0-9])\s*$", raw)
    return f"{m.group(1).upper()}-{m.group(2).upper()}" if m else None


def normalize_day(raw: str | None, today: date | None = None) -> str | None:
    if not raw:
        return None
    today = today or date.today()
    t = raw.strip().lower()
    if t in ("today", "ఈ రోజు", "ఈరోజు"):
        return weekday_name(today)
    if t in ("tomorrow", "రేపు"):
        return weekday_name(today + timedelta(days=1))
    for name in WEEKDAYS:
        if len(t) >= 3 and name.lower().startswith(t[:3]) and (t == name.lower() or len(t) <= 4):
            return name
    for te, idx in _TELUGU_DAYS.items():
        if te in raw:
            return WEEKDAYS[idx]
    return None


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
