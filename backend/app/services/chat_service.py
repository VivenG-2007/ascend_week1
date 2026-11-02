"""One conversation turn, shared by text chat and voice chat."""
from __future__ import annotations

import base64
import logging
import uuid
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Message, MessageRole
from app.schemas.chat import ChatResponse
from app.services.language import resolve_language
from app.services.llm_agent import Agent
from app.services.stt import SpeechError
from app.services.tts import TextToSpeech, make_spoken

log = logging.getLogger("campusvoice.chat")


def _history(db: Session, session_id: str, limit: int = 6) -> list[dict[str, str]]:
    rows = db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.id.desc()).limit(limit)).all()
    return [{"role": m.role, "text": m.text} for m in reversed(rows)]


def handle_turn(db: Session, agent: Agent, *, question: str, language: str = "auto", session_id: str | None = None,
                department: str | None = None, speak: bool = False, tts: TextToSpeech | None = None,
                stt_ms: int | None = None, started: float | None = None, warnings: list[str] | None = None) -> ChatResponse:
    started = started if started is not None else perf_counter()
    session_id = session_id or uuid.uuid4().hex
    lang = resolve_language(question, language)
    warns = list(warnings or [])

    history = _history(db, session_id)
    result = agent.answer(question, lang, session_id, department, history)
    warns += result.warnings

    audio_b64, tts_ms = None, None
    if speak:
        if tts is None:
            warns.append("tts_unavailable")
        else:
            t0 = perf_counter()
            try:
                audio = tts.synthesize(make_spoken(result.answer_text), lang)
                audio_b64 = base64.b64encode(audio).decode()
                tts_ms = round((perf_counter() - t0) * 1000)
            except SpeechError:
                warns.append("tts_failed")
            except Exception:  # noqa: BLE001
                log.exception("TTS crashed")
                warns.append("tts_failed")

    latency_ms = round((perf_counter() - started) * 1000)
    db.add(Message(session_id=session_id, role=MessageRole.user.value, text=question, language=lang, stt_ms=stt_ms))
    db.add(Message(session_id=session_id, role=MessageRole.assistant.value, text=result.answer_text, language=lang,
                   sources=[s.model_dump(mode="json") for s in result.sources],
                   retrieval_metrics=result.retrieval.model_dump() if result.retrieval else None,
                   stt_ms=stt_ms, llm_ms=result.llm_ms, tts_ms=tts_ms, latency_ms=latency_ms,
                   ticket_id=result.ticket.id if result.ticket else None))
    db.commit()  # also commits any ticket created during the turn

    # Timings and sizes only; never question text, audio, or credentials.
    log.info("turn session=%s lang=%s q_len=%d stt_ms=%s llm_ms=%s tts_ms=%s total_ms=%d decision=%s", session_id, lang, len(question),
             stt_ms, result.llm_ms, tts_ms, latency_ms, result.retrieval.decision if result.retrieval else None)
    return ChatResponse(session_id=session_id, transcript=question, language=lang, answer_text=result.answer_text,  # type: ignore[arg-type]
                        audio_base64=audio_b64, sources=result.sources, ticket=result.ticket, retrieval=result.retrieval,
                        latency_ms=latency_ms, stt_ms=stt_ms, llm_ms=result.llm_ms, tts_ms=tts_ms, warnings=warns)
