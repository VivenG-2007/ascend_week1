from datetime import date

import httpx
import pytest

from app.services.storage import LocalStorage, SupabaseStorage, safe_filename
from app.tools.events import get_events
from app.tools.exams import get_exam_schedule
from app.tools.faculty import find_faculty
from app.tools.timetable import get_timetable
from app.tests.conftest import TODAY  # Friday 30 Oct 2026


def test_timetable_first_period(seeded):
    r = get_timetable(seeded, "CSE-B", "Monday", TODAY)
    assert r.status == "found" and r.data["periods"][0]["period"] == 1 and r.data["periods"][0]["subject"]
    assert r.sources[0].title == "Timetable CSE-B"


@pytest.mark.parametrize("section", ["cse b", "CSE-B", "cse_b", " CSE B "])
def test_section_formats_are_normalised(seeded, section):
    assert get_timetable(seeded, section, "mon", TODAY).data["section"] == "CSE-B"


def test_timetable_today_and_tomorrow_use_the_calendar(seeded):
    assert get_timetable(seeded, "CSE-A", "today", TODAY).data["day"] == "Friday"
    assert get_timetable(seeded, "CSE-A", "tomorrow", TODAY).status == "not_found"  # Saturday has no classes
    assert get_timetable(seeded, "CSE-A", "రేపు", TODAY).status == "not_found"


def test_timetable_partial_inputs_are_ambiguous_not_guessed(seeded):
    unknown = get_timetable(seeded, "ECE-Z", "Monday", TODAY)
    assert unknown.status == "ambiguous" and "CSE-A" in unknown.message and not unknown.adequate
    assert get_timetable(seeded, "CSE-A", None, TODAY).status == "ambiguous"
    assert get_timetable(seeded, None, "Monday", TODAY).status == "ambiguous"


def test_exam_schedule_has_weekday_ready_dates_and_ambiguity(seeded):
    r = get_exam_schedule(seeded, "CSE-A")
    assert r.status == "found" and len(r.data["exams"]) == 5 and "," in r.data["exams"][0]["date_text"]
    assert get_exam_schedule(seeded, "XYZ").status == "ambiguous"


def test_faculty_lookup_variants(seeded):
    assert find_faculty(seeded, "Dr. Rohan Keshav").data[0]["cabin"] == "C-304"
    assert find_faculty(seeded, "Keshav").status == "found"
    assert len(find_faculty(seeded, "ECE").data) == 1
    assert find_faculty(seeded, "Zebra").status == "not_found"
    assert find_faculty(seeded, "").status == "ambiguous"


def test_faculty_many_matches_is_ambiguous(seeded):
    assert find_faculty(seeded, "CSE").status == "ambiguous"


def test_events_default_window_and_range(seeded):
    week = get_events(seeded, today=TODAY)
    assert week.status == "found" and {e["title"] for e in week.data["events"]}
    assert all(date.fromisoformat(e["date"]) <= date(2026, 11, 6) for e in week.data["events"])
    assert get_events(seeded, date(2030, 1, 1), date(2030, 1, 5)).status == "not_found"
    assert get_events(seeded, date(2026, 11, 5), date(2026, 11, 1)).status == "error"


# ------------------------------------------------------------------------- storage
def test_safe_filename_blocks_traversal_and_odd_characters():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\Users\\x\\fee circular (final).pdf") == "fee_circular_final_.pdf"
    assert safe_filename("") == "upload" and len(safe_filename("a" * 500)) <= 100


def test_local_storage_roundtrip_and_traversal_guard(tmp_path):
    st = LocalStorage(str(tmp_path))
    st.save("documents/1/a.pdf", b"data", "application/pdf")
    assert st.read("documents/1/a.pdf") == b"data"
    with pytest.raises(ValueError):
        st.save("../escape.txt", b"x", "text/plain")


def test_supabase_storage_uses_server_side_key_and_bucket():
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        if "/object/sign/" in req.url.path:
            return httpx.Response(200, json={"signedURL": "/object/sign/b/documents/1/a.pdf?token=abc"})
        return httpx.Response(200, content=b"filedata")

    st = SupabaseStorage("https://proj.supabase.co", "SERVICE-KEY", "b", httpx.Client(transport=httpx.MockTransport(handler)))
    st.save("documents/1/a.pdf", b"x", "application/pdf")
    assert seen[0].method == "POST" and seen[0].url.path == "/storage/v1/object/b/documents/1/a.pdf"
    assert seen[0].headers["authorization"] == "Bearer SERVICE-KEY" and seen[0].headers["content-type"] == "application/pdf"
    assert st.read("documents/1/a.pdf") == b"filedata"
    assert st.public_url("documents/1/a.pdf").startswith("https://proj.supabase.co/storage/v1/object/sign/b/")


def test_supabase_storage_failure_raises_without_leaking_key():
    st = SupabaseStorage("https://p.supabase.co", "SECRET-KEY", "b", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    with pytest.raises(RuntimeError) as e:
        st.save("a", b"x", "text/plain")
    assert "SECRET-KEY" not in str(e.value)
