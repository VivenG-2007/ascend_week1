import base64

import pytest
from sqlalchemy import select

from app.db.models import Message, Ticket
from app.services.llm_agent import LLMReply
from app.tests.conftest import FakeLLM, FakeTts, tool_call
from app.services.stt import SpeechError


def test_chat_english_happy_path_with_mocked_llm(client, llm_holder, seeded):
    llm_holder.llm = FakeLLM([LLMReply(None, [tool_call("get_timetable", {"section": "CSE-B", "day": "Monday"})]),
                              LLMReply("The first period is Database Systems at nine. Source: Timetable CSE-B.")])
    r = client.post("/api/chat", json={"question": "What is the first period for CSE-B on Monday?"})
    assert r.status_code == 200
    b = r.json()
    assert b["language"] == "en" and b["answer_text"].startswith("The first period")
    assert b["sources"][0]["title"] == "Timetable CSE-B" and b["ticket"] is None
    assert b["stt_ms"] is None and b["tts_ms"] is None and b["llm_ms"] is not None and b["latency_ms"] >= b["llm_ms"]
    assert b["retrieval"]["decision"] == "answered" and b["audio_base64"] is None


def test_chat_telugu_is_detected_and_answered_in_telugu(client, seeded):
    b = client.post("/api/chat", json={"question": "ఫీజు కోసం ఏదైనా సాయం కావాలా కళాశాల"}).json()
    assert b["language"] == "te" and any(0x0C00 <= ord(c) <= 0x0C7F for c in b["answer_text"])


def test_explicit_language_overrides_detection(client):
    assert client.post("/api/chat", json={"question": "hello college fees", "language": "te"}).json()["language"] == "te"


def test_off_topic_creates_no_ticket_and_college_gap_creates_one(client, db):
    off = client.post("/api/chat", json={"question": "What is the capital of France?"}).json()
    assert off["ticket"] is None and off["retrieval"]["decision"] == "declined"
    gap = client.post("/api/chat", json={"question": "Is there a rooftop garden at the college?"}).json()
    assert gap["ticket"]["id"].startswith("CV-") and gap["ticket"]["id"] in gap["answer_text"]
    assert db.scalar(select(Ticket).where(Ticket.id == gap["ticket"]["id"])) is not None
    assert len(db.scalars(select(Ticket)).all()) == 1


def test_messages_persist_with_metrics_and_session_continuity(client, db, seeded):
    first = client.post("/api/chat", json={"question": "first period CSE-A Monday timetable"}).json()
    client.post("/api/chat", json={"question": "hostel rules", "session_id": first["session_id"]})
    rows = db.scalars(select(Message).where(Message.session_id == first["session_id"]).order_by(Message.id)).all()
    assert [m.role for m in rows] == ["user", "assistant", "user", "assistant"]
    a = rows[1]
    assert a.latency_ms is not None and a.llm_ms is not None and a.stt_ms is None and a.retrieval_metrics["decision"] == "answered"
    assert a.sources and a.sources[0]["title"] == "Timetable CSE-A"


def test_history_reaches_the_llm(client, llm_holder, seeded):
    llm_holder.llm = FakeLLM([LLMReply("one"), LLMReply("two")])
    s = client.post("/api/chat", json={"question": "hello college"}).json()["session_id"]
    client.post("/api/chat", json={"question": "and the hostel", "session_id": s})
    assert [m["role"] for m in llm_holder.llm.calls[1]["messages"]][:4] == ["system", "user", "assistant", "user"]


def test_speak_returns_audio_and_tts_timing(client, stt_holder, seeded):
    b = client.post("/api/chat", json={"question": "first period CSE-A Monday timetable", "speak": True}).json()
    assert base64.b64decode(b["audio_base64"]) == b"ID3-fake-mp3" and b["tts_ms"] is not None
    text, lang = stt_holder.tts.calls[0]
    assert lang == "en" and len(text.split()) <= 40


def test_tts_failure_does_not_break_text_answer(client, stt_holder, seeded):
    stt_holder.tts = FakeTts(error=SpeechError("down"))
    b = client.post("/api/chat", json={"question": "first period CSE-A Monday timetable", "speak": True}).json()
    assert b["answer_text"] and b["audio_base64"] is None and "tts_failed" in b["warnings"]


def test_input_validation(client):
    assert client.post("/api/chat", json={"question": "   "}).status_code == 422
    assert client.post("/api/chat", json={"question": "a" * 1001}).status_code == 422
    assert client.post("/api/chat", json={"question": "hi", "session_id": "../../etc/passwd"}).status_code == 422
    assert client.post("/api/chat", json={"question": "hi", "language": "fr"}).status_code == 422
    assert client.post("/api/chat", json={"question": "hi", "speak": "maybe"}).status_code == 422


def test_cors_allows_configured_origin_only(client):
    ok = client.options("/api/chat", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/api/chat", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_unhandled_errors_do_not_leak_details(app, client, llm_holder):
    class Boom:
        def chat(self, *a, **k):
            raise KeyError("SECRET-INTERNAL-DETAIL")

    # Force a crash outside the agent's own error handling
    from app import deps
    app.dependency_overrides[deps.get_agent] = lambda: (_ for _ in ()).throw(RuntimeError("SECRET-INTERNAL-DETAIL"))
    r = client.post("/api/chat", json={"question": "hello college"})
    assert r.status_code == 500 and "SECRET" not in r.text and "Traceback" not in r.text


def test_rate_limit_returns_429(client, settings_env):
    settings_env(rate_limit_enabled="true", rate_limit_per_minute="3")
    codes = [client.post("/api/chat", json={"question": f"hello college {i}"}).status_code for i in range(5)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]
