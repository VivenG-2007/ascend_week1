"""Synthetic demo data: faculty, timetable, exam schedule, events.

Everything here is FICTIONAL. There are no student records. The script is idempotent:
a table that already has rows is left untouched.

    python -m app.db.seed
"""
from __future__ import annotations

from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import WEEKDAYS, Event, Exam, Faculty, Timetable

SECTIONS = ["CSE-A", "CSE-B"]
EMAIL_DOMAIN = "campusvoice.example"  # reserved-style domain: these addresses do not exist

# (name, department, designation, cabin, block, office_hours)
FACULTY = [
    ("Dr. Meera Nandan", "CSE", "Professor & HOD", "C-301", "Block C", "Mon-Fri 10:00-11:00"),
    ("Dr. Rohan Keshav", "CSE", "Associate Professor", "C-304", "Block C", "Tue/Thu 14:00-16:00"),
    ("Ms. Lavanya Prasad", "CSE", "Assistant Professor", "C-306", "Block C", "Mon/Wed 15:00-16:00"),
    ("Mr. Imran Sheikh", "CSE", "Assistant Professor", "C-308", "Block C", "Wed/Fri 11:00-12:00"),
    ("Dr. Sunita Varma", "CSE", "Associate Professor", "C-310", "Block C", "Tue/Fri 10:00-11:30"),
    ("Mr. Tarun Bhat", "CSE", "Assistant Professor", "C-312", "Block C", "Mon/Thu 12:00-13:00"),
    ("Dr. Kavya Rangan", "ECE", "Professor", "B-205", "Block B", "Mon-Wed 14:00-15:00"),
    ("Mr. Anil Deshmukh", "Mathematics", "Assistant Professor", "A-112", "Block A", "Tue/Thu 11:00-12:00"),
    ("Ms. Priya Menon", "English", "Assistant Professor", "A-118", "Block A", "Wed/Fri 14:00-15:00"),
    ("Mr. Farhan Qureshi", "Library", "Librarian", "L-001", "Library Block", "Mon-Sat 09:00-17:00"),
]

# (subject, faculty name, is lab)
SUBJECTS = [
    ("Data Structures", "Dr. Rohan Keshav"),
    ("Discrete Mathematics", "Mr. Anil Deshmukh"),
    ("Database Systems", "Dr. Sunita Varma"),
    ("Operating Systems", "Ms. Lavanya Prasad"),
    ("Computer Networks", "Mr. Imran Sheikh"),
    ("Technical English", "Ms. Priya Menon"),
]

PERIOD_TIMES = [
    (time(9, 0), time(9, 50)),
    (time(9, 50), time(10, 40)),
    (time(10, 50), time(11, 40)),
    (time(11, 40), time(12, 30)),
    (time(13, 30), time(14, 20)),
    (time(14, 20), time(15, 10)),
]

EVENTS = [
    ("Aurora Tech Fest: Opening Day", 2, "Main Auditorium", "Inauguration and project showcase (synthetic demo event).", "Student Council"),
    ("Intro to Cloud Workshop", 3, "Seminar Hall 2", "Hands-on beginner workshop (synthetic demo event).", "CSE Department"),
    ("Inter-Section Quiz", 5, "Block A Room 104", "Quiz for all first and second-year sections (synthetic demo event).", "Literary Club"),
    ("Placement Preparation Talk", 7, "Main Auditorium", "Aptitude and interview preparation session (synthetic demo event).", "Training & Placement Cell"),
    ("Blood Donation Camp", 9, "Sports Complex Lobby", "Community donation drive (synthetic demo event).", "NSS Unit"),
    ("Robotics Club Demo Day", 12, "Innovation Lab", "Open demonstrations of student robots (synthetic demo event).", "Robotics Club"),
    ("Cultural Evening", 15, "Open Air Theatre", "Music and dance performances (synthetic demo event).", "Cultural Committee"),
    ("Alumni Meet", 20, "Conference Hall", "Alumni interaction and networking (synthetic demo event).", "Alumni Association"),
]


def _empty(db: Session, model) -> bool:
    return db.scalar(select(func.count()).select_from(model)) == 0


def seed(db: Session, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    added = {"faculty": 0, "timetable": 0, "exams": 0, "events": 0}

    if _empty(db, Faculty):
        for i, (name, dept, desig, cabin, block, hours) in enumerate(FACULTY, start=1):
            slug = name.lower().replace("dr. ", "").replace("mr. ", "").replace("ms. ", "").replace(" ", ".")
            db.add(
                Faculty(
                    name=name, department=dept, designation=desig, cabin=cabin, block=block,
                    email=f"{slug}@{EMAIL_DOMAIN}", phone=f"+91 00000 {i:05d}", office_hours=hours,
                )
            )
            added["faculty"] += 1
        db.flush()

    faculty_by_name = {f.name: f.id for f in db.scalars(select(Faculty))}

    if _empty(db, Timetable):
        for s_idx, section in enumerate(SECTIONS):
            room = f"C-10{s_idx + 1}"
            for d_idx, day in enumerate(WEEKDAYS[:5]):
                for p_idx, (start, end) in enumerate(PERIOD_TIMES):
                    subject, teacher = SUBJECTS[(d_idx + p_idx + s_idx * 2) % len(SUBJECTS)]
                    db.add(
                        Timetable(
                            section=section, day=day, period=p_idx + 1, start_time=start, end_time=end,
                            subject=subject, faculty_id=faculty_by_name.get(teacher), room=room,
                        )
                    )
                    added["timetable"] += 1

    if _empty(db, Exam):
        first_exam_day = today + timedelta(days=18)
        exam_day = first_exam_day
        for subject, _ in SUBJECTS[:5]:
            while exam_day.weekday() >= 5:  # skip Sat/Sun
                exam_day += timedelta(days=1)
            for section in SECTIONS:
                db.add(Exam(exam_type="Mid-Term 1 (demo)", subject=subject, section=section,
                            exam_date=exam_day, start_time=time(10, 0), room="Exam Hall " + ("1" if section == "CSE-A" else "2")))
                added["exams"] += 1
            exam_day += timedelta(days=1)

    if _empty(db, Event):
        for title, offset, venue, desc, organizer in EVENTS:
            db.add(Event(title=title, event_date=today + timedelta(days=offset), venue=venue, description=desc, organizer=organizer))
            added["events"] += 1

    db.commit()
    return added


def main() -> None:
    from app.db.session import get_sessionmaker

    with get_sessionmaker()() as db:
        counts = seed(db)
    print("Seed complete (rows added):", counts)


if __name__ == "__main__":
    main()
