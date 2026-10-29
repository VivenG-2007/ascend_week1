"""
Database Seed Foundation for CampusVoice
Seeds:
- 10 Fictional Faculty records
- 2 Sections of Timetable data (CSE-A & CSE-B)
- 1 Examination Schedule (Mid-Term & End-Sem)
- 8 Fictional Campus Events
- 6 Official-Style Circulars (including an older fee circular and a revised fee circular superseding it)
"""
from datetime import datetime
from app.db.session import engine, SessionLocal, Base
from app.db.models import Faculty, Timetable, Exam, Event, Document, DocumentPage, Chunk

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Faculty).count() > 0:
            print("[INFO] Database already contains seeded records. Skipping.")
            return

        print("[INFO] Seeding CampusVoice fictional dataset...")

        # 1. Faculty (10 fictional faculty)
        faculty_data = [
            Faculty(
                id="fac-001",
                name="Dr. K. S. Rao",
                department="Computer Science & Engineering",
                designation="Professor & HOD",
                cabin="Room 301",
                block="C-Block (Ramanujan Block)",
                email="ksrao.cse@geethanjali.edu.in",
                phone="+91 94401 11223",
                office_hours="Mon-Fri, 3:00 PM - 4:30 PM"
            ),
            Faculty(
                id="fac-002",
                name="Dr. P. Sujatha",
                department="Computer Science & Engineering",
                designation="Associate Professor",
                cabin="Room 304",
                block="C-Block (Ramanujan Block)",
                email="sujatha.p@geethanjali.edu.in",
                phone="+91 94401 11224",
                office_hours="Mon-Thu, 2:00 PM - 3:30 PM"
            ),
            Faculty(
                id="fac-003",
                name="Prof. V. Rajesh Sharma",
                department="Computer Science & Engineering",
                designation="Assistant Professor",
                cabin="Room 308",
                block="C-Block (Ramanujan Block)",
                email="v.rajesh@geethanjali.edu.in",
                phone="+91 94401 11225",
                office_hours="Tue-Fri, 11:30 AM - 1:00 PM"
            ),
            Faculty(
                id="fac-004",
                name="Dr. M. Lakshmi Narayana",
                department="Electronics & Communication",
                designation="Professor & Dean Academics",
                cabin="Admin Block A-102",
                block="A-Block (Administrative Block)",
                email="dean.academics@geethanjali.edu.in",
                phone="+91 94401 11226",
                office_hours="Mon-Fri, 10:00 AM - 12:00 PM"
            ),
            Faculty(
                id="fac-005",
                name="Prof. Ananya Roy",
                department="Information Technology",
                designation="Assistant Professor",
                cabin="Room 212",
                block="B-Block (Aryabhata Block)",
                email="ananya.roy@geethanjali.edu.in",
                phone="+91 94401 11227",
                office_hours="Wed-Fri, 2:30 PM - 4:00 PM"
            ),
            Faculty(
                id="fac-006",
                name="Dr. T. Venkatachalam",
                department="Mechanical Engineering",
                designation="Professor",
                cabin="Workshop Complex W-15",
                block="D-Block (Visvesvaraya Block)",
                email="venkat.mech@geethanjali.edu.in",
                phone="+91 94401 11228",
                office_hours="Mon, Wed, Fri 3:00 PM - 4:00 PM"
            ),
            Faculty(
                id="fac-007",
                name="Prof. B. Sridevi",
                department="Mathematics & Humanities",
                designation="Senior Assistant Professor",
                cabin="Room 105",
                block="B-Block (Aryabhata Block)",
                email="sridevi.maths@geethanjali.edu.in",
                phone="+91 94401 11229",
                office_hours="Mon-Fri, 1:30 PM - 2:30 PM"
            ),
            Faculty(
                id="fac-008",
                name="Dr. G. Ramesh Babu",
                department="Physical Education & Sports",
                designation="Sports Officer",
                cabin="Indoor Stadium Cabin",
                block="Sports Pavilion",
                email="sports@geethanjali.edu.in",
                phone="+91 94401 11230",
                office_hours="Mon-Sat, 6:00 AM - 9:00 AM, 4:00 PM - 7:00 PM"
            ),
            Faculty(
                id="fac-009",
                name="Mr. K. Narayana Murthy",
                department="Hostel Administration",
                designation="Chief Hostel Warden",
                cabin="Hostel Office Ground Floor",
                block="Kavery Boys Hostel",
                email="hostelwarden@geethanjali.edu.in",
                phone="+91 94401 11231",
                office_hours="Daily, 5:00 PM - 8:00 PM"
            ),
            Faculty(
                id="fac-010",
                name="Mrs. Sandhya Rani",
                department="Transport Section",
                designation="Transport In-charge",
                cabin="Transport Desk T-01",
                block="Security Main Gate",
                email="transport@geethanjali.edu.in",
                phone="+91 94401 11232",
                office_hours="Mon-Sat, 8:00 AM - 5:30 PM"
            ),
        ]
        db.add_all(faculty_data)
        db.commit()

        # 2. Timetable (CSE-A and CSE-B)
        timetable_data = [
            # CSE-A Monday
            Timetable(section="CSE-A", day="Monday", period=1, start_time="09:15 AM", end_time="10:10 AM", subject="Compiler Design", faculty_id="fac-001", room="C-301"),
            Timetable(section="CSE-A", day="Monday", period=2, start_time="10:10 AM", end_time="11:05 AM", subject="Operating Systems", faculty_id="fac-002", room="C-301"),
            Timetable(section="CSE-A", day="Monday", period=3, start_time="11:15 AM", end_time="12:10 PM", subject="Artificial Intelligence", faculty_id="fac-003", room="C-301"),
            Timetable(section="CSE-A", day="Monday", period=4, start_time="12:10 PM", end_time="01:05 PM", subject="Probability & Statistics", faculty_id="fac-007", room="C-301"),
            Timetable(section="CSE-A", day="Monday", period=5, start_time="02:00 PM", end_time="04:00 PM", subject="AI & ML Lab", faculty_id="fac-003", room="Lab 3 (C-Block)"),
            
            # CSE-B Monday
            Timetable(section="CSE-B", day="Monday", period=1, start_time="09:15 AM", end_time="10:10 AM", subject="Operating Systems", faculty_id="fac-002", room="C-302"),
            Timetable(section="CSE-B", day="Monday", period=2, start_time="10:10 AM", end_time="11:05 AM", subject="Compiler Design", faculty_id="fac-001", room="C-302"),
            Timetable(section="CSE-B", day="Monday", period=3, start_time="11:15 AM", end_time="12:10 PM", subject="Web Technologies", faculty_id="fac-005", room="C-302"),
            Timetable(section="CSE-B", day="Monday", period=4, start_time="12:10 PM", end_time="01:05 PM", subject="Probability & Statistics", faculty_id="fac-007", room="C-302"),
            Timetable(section="CSE-B", day="Monday", period=5, start_time="02:00 PM", end_time="04:00 PM", subject="Compiler Design Lab", faculty_id="fac-001", room="Lab 2 (C-Block)"),

            # CSE-A Tuesday
            Timetable(section="CSE-A", day="Tuesday", period=1, start_time="09:15 AM", end_time="10:10 AM", subject="Artificial Intelligence", faculty_id="fac-003", room="C-301"),
            Timetable(section="CSE-A", day="Tuesday", period=2, start_time="10:10 AM", end_time="11:05 AM", subject="Probability & Statistics", faculty_id="fac-007", room="C-301"),
            Timetable(section="CSE-A", day="Tuesday", period=3, start_time="11:15 AM", end_time="12:10 PM", subject="Compiler Design", faculty_id="fac-001", room="C-301"),
            Timetable(section="CSE-A", day="Tuesday", period=4, start_time="12:10 PM", end_time="01:05 PM", subject="Operating Systems", faculty_id="fac-002", room="C-301"),

            # CSE-B Tuesday
            Timetable(section="CSE-B", day="Tuesday", period=1, start_time="09:15 AM", end_time="10:10 AM", subject="Web Technologies", faculty_id="fac-005", room="C-302"),
            Timetable(section="CSE-B", day="Tuesday", period=2, start_time="10:10 AM", end_time="11:05 AM", subject="Artificial Intelligence", faculty_id="fac-003", room="C-302"),
            Timetable(section="CSE-B", day="Tuesday", period=3, start_time="11:15 AM", end_time="12:10 PM", subject="Operating Systems", faculty_id="fac-002", room="C-302"),
            Timetable(section="CSE-B", day="Tuesday", period=4, start_time="12:10 PM", end_time="01:05 PM", subject="Probability & Statistics", faculty_id="fac-007", room="C-302"),
        ]
        db.add_all(timetable_data)
        db.commit()

        # 3. Exams Schedule
        exams_data = [
            Exam(exam_type="Mid-Term II", subject="Compiler Design", section="CSE-A", exam_date="2026-11-10", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 1"),
            Exam(exam_type="Mid-Term II", subject="Operating Systems", section="CSE-A", exam_date="2026-11-12", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 1"),
            Exam(exam_type="Mid-Term II", subject="Artificial Intelligence", section="CSE-A", exam_date="2026-11-14", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 1"),
            Exam(exam_type="Mid-Term II", subject="Compiler Design", section="CSE-B", exam_date="2026-11-10", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 2"),
            Exam(exam_type="Mid-Term II", subject="Operating Systems", section="CSE-B", exam_date="2026-11-12", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 2"),
            Exam(exam_type="Mid-Term II", subject="Web Technologies", section="CSE-B", exam_date="2026-11-14", start_time="10:00 AM - 12:00 PM", room="C-Block Exam Hall 2"),
        ]
        db.add_all(exams_data)
        db.commit()

        # 4. Campus Events (8 fictional events)
        events_data = [
            Event(title="TechSamaroh 2026 - Annual Technical Symposium", event_date="2026-11-05", venue="Main Auditorium", description="2-day national level technical fest with hackathons, coding contests, and paper presentations.", organizer="Department of CSE & IT"),
            Event(title="AI & Generative Voice Hackathon", event_date="2026-11-06", venue="Ramanujan Seminar Hall", description="24-hour hackathon focused on conversational AI and accessibility.", organizer="Google Developer Student Club"),
            Event(title="Guest Lecture on Quantum Computing", event_date="2026-11-08", venue="Aryabhata Seminar Hall", description="Distinguished lecture by Dr. A. P. Chari, Senior Research Scientist.", organizer="R&D Cell"),
            Event(title="Inter-College Badminton Championship", event_date="2026-11-11", venue="Indoor Sports Complex", description="Annual university sports meet for boys and girls doubles and singles.", organizer="Department of Physical Education"),
            Event(title="Campus Placement Drive - CloudCore Technologies", event_date="2026-11-15", venue="Training & Placement Cell", description="Recruitment drive for final year B.Tech CSE, IT, and ECE students.", organizer="Training & Placement Cell"),
            Event(title="Blood Donation & Health Checkup Camp", event_date="2026-11-18", venue="College Health Centre", description="Annual voluntary blood donation drive organized with Red Cross.", organizer="NSS Unit"),
            Event(title="Alumni Reunion Gala 2026", event_date="2026-11-21", venue="Open Air Amphitheatre", description="Silver Jubilee Alumni Meet for the batches of 2001 and 2006.", organizer="Alumni Affairs Office"),
            Event(title="National Science Day Project Expo", event_date="2026-11-28", venue="Visvesvaraya Innovation Pavilion", description="Exhibition of hardware and software prototypes developed by 2nd and 3rd year students.", organizer="Institution Innovation Council (IIC)"),
        ]
        db.add_all(events_data)
        db.commit()

        # 5. Documents / Circulars (6 official circulars including superseding revised fee circular)
        doc1 = Document(
            id="doc-001",
            title="Circular No. ACAD/2026/04: Odd Semester Tuition Fee Payment Schedule (Initial)",
            category="Circular",
            department="Accounts",
            source_date="2026-09-15",
            file_url="/documents/circular_fee_schedule_v1.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        doc2 = Document(
            id="doc-002",
            title="Circular No. ACAD/2026/12: Revised Tuition Fee Payment Schedule and Grace Period (Supersedes Circular No. ACAD/2026/04)",
            category="Circular",
            department="Accounts",
            source_date="2026-10-10",
            file_url="/documents/circular_fee_schedule_v2_revised.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        doc3 = Document(
            id="doc-003",
            title="Notice No. EXAM/2026/08: Mid-Term II Examination Schedule and Hall Ticket Rules",
            category="Notice",
            department="Exam Cell",
            source_date="2026-10-18",
            file_url="/documents/notice_mid2_exams.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        doc4 = Document(
            id="doc-004",
            title="Circular No. HOSTEL/2026/03: Campus Hostel Curfew Timings and Mess Rules",
            category="Circular",
            department="Hostel",
            source_date="2026-08-20",
            file_url="/documents/hostel_rules_2026.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        doc5 = Document(
            id="doc-005",
            title="Circular No. TRANS/2026/05: College Bus Routes, Timings and Pass Validation Rules",
            category="Circular",
            department="Transport",
            source_date="2026-09-01",
            file_url="/documents/bus_routes_and_rules.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        doc6 = Document(
            id="doc-006",
            title="Circular No. ADM/2026/15: Official Declaration of Diwali and Semester Break Holidays",
            category="Circular",
            department="General",
            source_date="2026-10-22",
            file_url="/documents/holiday_declaration_diwali.pdf",
            language="en",
            processing_status="completed",
            extraction_status="native_pdf"
        )
        db.add_all([doc1, doc2, doc3, doc4, doc5, doc6])
        db.commit()

        # Add corresponding pages & chunks for doc1 and doc2 to ground RAG & demo precedence
        p1 = DocumentPage(
            document_id="doc-001",
            page_number=1,
            extracted_text="Circular No. ACAD/2026/04 Dated 15 September 2026. All B.Tech students must pay Odd Semester Tuition Fees on or before 15 October 2026. Late fee of Rs. 500 applies until 25 October 2026.",
            ocr_status="none"
        )
        c1 = Chunk(
            document_id="doc-001",
            page_number=1,
            chunk_index=0,
            content="Circular No. ACAD/2026/04 Dated 15 September 2026. All B.Tech students must pay Odd Semester Tuition Fees on or before 15 October 2026. Late fee of Rs. 500 applies until 25 October 2026.",
            vector_metadata={"department": "Accounts", "source_date": "2026-09-15", "superseded_by": "doc-002"}
        )

        p2 = DocumentPage(
            document_id="doc-002",
            page_number=1,
            extracted_text="Circular No. ACAD/2026/12 Dated 10 October 2026. In supersession of Circular No. ACAD/2026/04, the last date to pay Odd Semester Tuition Fees without late fine is extended to 10 November 2026. With a late fine of Rs. 250, fees can be paid until 20 November 2026. Payments can be made via SBI Collect or Accounts Counter in A-Block.",
            ocr_status="none"
        )
        c2 = Chunk(
            document_id="doc-002",
            page_number=1,
            chunk_index=0,
            content="Circular No. ACAD/2026/12 Dated 10 October 2026. In supersession of Circular No. ACAD/2026/04, the last date to pay Odd Semester Tuition Fees without late fine is extended to 10 November 2026. With a late fine of Rs. 250, fees can be paid until 20 November 2026. Payments can be made via SBI Collect or Accounts Counter in A-Block.",
            vector_metadata={"department": "Accounts", "source_date": "2026-10-10", "replaces": "doc-001"}
        )

        p4 = DocumentPage(
            document_id="doc-004",
            page_number=1,
            extracted_text="Circular No. HOSTEL/2026/03 Dated 20 August 2026. Hostel Rules: Main gate closes strictly at 8:30 PM for boys and 8:00 PM for girls. Study hours are 9:00 PM to 11:00 PM. Mess timings: Breakfast 7:30 AM - 9:00 AM, Lunch 12:30 PM - 2:00 PM, Dinner 7:30 PM - 9:00 PM. No electrical heating appliances permitted in rooms.",
            ocr_status="none"
        )
        c4 = Chunk(
            document_id="doc-004",
            page_number=1,
            chunk_index=0,
            content="Circular No. HOSTEL/2026/03 Dated 20 August 2026. Hostel Rules: Main gate closes strictly at 8:30 PM for boys and 8:00 PM for girls. Study hours are 9:00 PM to 11:00 PM. Mess timings: Breakfast 7:30 AM - 9:00 AM, Lunch 12:30 PM - 2:00 PM, Dinner 7:30 PM - 9:00 PM. No electrical heating appliances permitted in rooms.",
            vector_metadata={"department": "Hostel", "source_date": "2026-08-20"}
        )

        db.add_all([p1, c1, p2, c2, p4, c4])
        db.commit()

        print("[INFO] Database successfully seeded with 10 faculty, 2 timetables, 6 circulars, 6 exams, and 8 events.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
