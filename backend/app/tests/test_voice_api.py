import pytest
from sqlalchemy import select

from app.db.models import Message
from app.services.stt import SpeechError
from app.tests.conftest import FakeStt, FakeTts, make_wav


def post(client, wav=None, **form):
    data = {"language": "auto", **form}
    return client.post("/api/voice", files={"audio": ("rec.wav", wav if wav is not None else make_wav(1.5), "audio/wav")}, data=data)


def test_voice_happy_path_returns_everything_with_separate_timings(client, stt_holder, seeded, db):
    stt_holder.stt = FakeStt("first period for CSE-B on Monday timetable", "en")
    r = post(client)
    assert r.status_code == 200
    b = r.json()
    assert b["transcript"].startswith("first period") and b["language"] == "en"
    assert b["answer_text"] and b["audio_base64"] and b["sources"][0]["title"] == "Timetable CSE-B"
    assert all(b[k] is not None for k in ("stt_ms", "llm_ms", "tts_ms")) and b["latency_ms"] >= b["stt_ms"]
    rows = db.scalars(select(Message).where(Message.session_id == b["session_id"]).order_by(Message.id)).all()
    assert rows[1].stt_ms is not None and rows[1].tts_ms is not None and rows[1].llm_ms is not None


def test_voice_telugu_speech_gets_telugu_voice(client, stt_holder, seeded):
    stt_holder.stt = FakeStt("హాస్టల్ నియమాలు ఏమిటి", "te")
    b = post(client).json()
    assert b["language"] == "te" and stt_holder.tts.calls[0][1] == "te"


def test_voice_code_mixed_transcript_in_telugu_script_is_answered_in_telugu(client, stt_holder):
    stt_holder.stt = FakeStt("fees last date ఎప్పుడు కళాశాల", "te")
    assert post(client).json()["language"] == "te"


def test_voice_passes_selected_language_to_stt(client, stt_holder):
    post(client, language="te")
    assert stt_holder.stt.calls == ["te"]


def test_silent_recording_is_rejected_before_calling_stt(client, stt_holder):
    r = post(client, make_wav(1.0, amplitude=0))
    assert r.status_code == 422 and "could not hear" in r.json()["detail"].lower() and stt_holder.stt.calls == []


def test_stt_no_speech_gives_422_and_stt_failure_gives_502(client, stt_holder):
    stt_holder.stt = FakeStt(error=SpeechError("I could not hear any speech.", empty=True))
    assert post(client).status_code == 422
    stt_holder.stt = FakeStt(error=SpeechError("The speech service had a problem. Please type."))
    r = post(client)
    assert r.status_code == 502 and "type" in r.json()["detail"].lower()


def test_empty_transcript_is_rejected(client, stt_holder):
    stt_holder.stt = FakeStt("   ")
    assert post(client).status_code == 422


@pytest.mark.parametrize("wav,codes", [(b"", {422}), (b"garbage" * 10, {415, 422}), (make_wav(0.1), {422}), (make_wav(45), {422}), (make_wav(1, channels=2), {415})])
def test_bad_audio_is_rejected(client, wav, codes):
    r = client.post("/api/voice", files={"audio": ("rec.wav", wav, "audio/wav")}, data={"language": "auto"})
    assert r.status_code in codes and r.json()["detail"]


def test_oversize_upload_is_rejected(client):
    r = client.post("/api/voice", files={"audio": ("big.wav", b"RIFF" + b"0" * (5 * 1024 * 1024), "audio/wav")}, data={})
    assert r.status_code == 413


def test_tts_failure_still_returns_text_answer(client, stt_holder, seeded):
    stt_holder.stt = FakeStt("first period CSE-A Monday timetable")
    stt_holder.tts = FakeTts(error=SpeechError("tts down"))
    b = post(client).json()
    assert b["answer_text"] and b["audio_base64"] is None and "tts_failed" in b["warnings"] and b["tts_ms"] is None


def test_voice_unconfigured_speech_returns_503_while_text_chat_still_works(app, client, seeded):
    from app import deps
    app.dependency_overrides.pop(deps.get_stt_service)
    app.dependency_overrides.pop(deps.get_tts_service)
    assert post(client).status_code == 503
    assert post(client, make_wav(1.0, amplitude=0)).status_code == 422  # validation still runs first
    assert client.post("/api/chat", json={"question": "first period CSE-A Monday timetable"}).status_code == 200


def test_invalid_form_values(client):
    assert post(client, language="fr").status_code == 422
    assert post(client, session_id="../x").status_code == 422
