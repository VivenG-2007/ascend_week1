"""Deterministic rules: input guards, scope classification and ticket-department routing.
These run in Python so behaviour never depends on the model obeying a prompt."""
from __future__ import annotations

import re
from typing import Literal

from app.db.models import TicketDepartment

Scope = Literal["college", "off_topic", "unknown"]

INJECTION = re.compile(
    r"(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,30}\b(instruction|rule|prompt|polic)"
    r"|system prompt|developer message|reveal.{0,25}(prompt|instruction|secret|key|password|token)"
    r"|(api|secret|access)[ _-]?key|jwt|service[ _-]?role|you are now\b|act as (?!a student)|jailbreak|\bDAN\b"
    r"|(show|list|give|get|read|open).{0,25}\b(all |every |other |open )?tickets?\b.{0,20}(admin|everyone|all|others?)"
    r"|admin (password|login|token|panel)",
    re.I,
)
PERSONAL_DATA = re.compile(
    r"\b(my|his|her|their|student'?s?)\b.{0,25}\b(marks?|grades?|cgpa|sgpa|attendance|result|backlogs?|fee (status|due|balance)|aadhaar|aadhar|phone number|address)\b"
    r"|\b(roll|hall ticket|registration|admission)\s*(no|number|#)\b.{0,20}\d"
    r"|\b\d{2}[a-z0-9]{8,10}\b.{0,20}(marks?|result|attendance)"
    r"|(marks?|result|attendance|grades?) of (student|roll|\d)",
    re.I,
)

# English + Telugu keyword stems that indicate a college topic.
COLLEGE_WORDS = [
    "fee", "fees", "tuition", "scholarship", "receipt", "payment", "exam", "examination", "mid", "semester", "hall ticket",
    "result", "revaluation", "supplementary", "timetable", "time table", "period", "class", "section", "lecture", "lab",
    "faculty", "professor", "hod", "cabin", "teacher", "office hours", "hostel", "mess", "warden", "room", "bus", "transport",
    "route", "library", "book", "journal", "admission", "eligibility", "counselling", "cutoff", "event", "fest", "workshop",
    "seminar", "holiday", "circular", "notice", "canteen", "campus", "college", "department", "dept", "principal", "attendance",
    "placement", "internship", "id card", "bonafide", "certificate", "sports", "club", "wifi", "parking", "dress code",
    "పీరియడ్", "ఫీజు", "ఫీజులు", "పరీక్ష", "పరీక్షలు", "హాస్టల్", "బస్సు", "గ్రంథాలయం", "లైబ్రరీ", "ప్రవేశ", "సెలవు", "తరగతి", "కళాశాల",
    "కాలేజీ", "అధ్యాపక", "ఫ్యాకల్టీ", "టైమ్ టేబుల్", "సమయ పట్టిక", "సర్క్యులర్", "ఈవెంట్", "కార్యక్రమ", "క్యాంటీన్", "విభాగం",
]
_COLLEGE_RE = re.compile("|".join(re.escape(w) for w in sorted(COLLEGE_WORDS, key=len, reverse=True)), re.I)
_SECTION_RE = re.compile(r"\b[a-z]{2,5}[- ]?[a-d]\b", re.I)

_ROUTES: list[tuple[TicketDepartment, list[str]]] = [
    (TicketDepartment.exam_cell, ["exam", "hall ticket", "result", "revaluation", "supplementary", "mid", "backlog", "పరీక్ష", "ఫలితాలు"]),
    (TicketDepartment.accounts, ["fee", "fees", "tuition", "scholarship", "receipt", "refund", "payment", "challan", "ఫీజు", "ఫీజులు", "రసీదు"]),
    (TicketDepartment.hostel, ["hostel", "mess", "warden", "హాస్టల్", "మెస్"]),
    (TicketDepartment.transport, ["bus", "transport", "route", "driver", "బస్సు", "రవాణా"]),
    (TicketDepartment.library, ["library", "book", "journal", "లైబ్రరీ", "గ్రంథాలయం", "పుస్తక"]),
    (TicketDepartment.admissions, ["admission", "eligibility", "counselling", "cutoff", "seat", "ప్రవేశ", "అడ్మిషన్"]),
]


def check_guards(text: str) -> Literal["injection", "personal_data"] | None:
    if INJECTION.search(text):
        return "injection"
    if PERSONAL_DATA.search(text):
        return "personal_data"
    return None


def classify_scope(text: str) -> Scope:
    if _COLLEGE_RE.search(text):
        return "college"
    if _SECTION_RE.search(text) and re.search(r"\b(mon|tues?|wed|thur?s?|fri|sat)", text, re.I):
        return "college"
    return "unknown"


def route_department(text: str) -> str:
    low = text.lower()
    for dept, words in _ROUTES:
        if any(w in low for w in words):
            return dept.value
    return TicketDepartment.general.value


def valid_department(name: str | None) -> str | None:
    for d in TicketDepartment:
        if name and name.strip().lower() == d.value.lower():
            return d.value
    return None
