import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.deps import get_agent, get_stt_service, get_tts_service
from app.schemas.chat import ChatResponse
from app.services.audio import SILENCE_RMS, AudioError, validate_audio
from app.services.chat_service import handle_turn
from app.services.llm_agent import Agent
from app.services.ratelimit import chat_limit
from app.services.stt import SpeechError, SpeechToText
from app.services.tts import TextToSpeech
import re

router = APIRouter(prefix="/api", tags=["voice"])
log = logging.getLogger("campusvoice.voice")
_SESSION = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@router.post("/voice", response_model=ChatResponse, dependencies=[Depends(chat_limit)])
def voice(
    audio: Annotated[UploadFile, File(description="16 kHz mono WAV, at most MAX_AUDIO_SECONDS long")],
    language: Annotated[str, Form()] = "auto",
    session_id: Annotated[str | None, Form()] = None,
    speak: Annotated[bool, Form()] = True,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_agent),
    settings: Settings = Depends(get_settings),
    tts: TextToSpeech | None = Depends(get_tts_service),
    stt: SpeechToText = Depends(get_stt_service),
) -> ChatResponse:
    started = perf_counter()
    if language not in ("auto", "en", "te"):
        raise HTTPException(422, "language must be auto, en or te")
    if session_id is not None and not _SESSION.match(session_id):
        raise HTTPException(422, "Invalid session_id")

    raw = audio.file.read(4 * 1024 * 1024 + 1)
    try:
        info = validate_audio(raw, settings.max_audio_seconds)
    except AudioError as exc:
        raise HTTPException(exc.status_code, exc.message)
    if info.rms < SILENCE_RMS:
        raise HTTPException(422, "I could not hear anything. Check your microphone and try again, or type your question.")

    t0 = perf_counter()
    try:
        result = stt.transcribe(info.wav, language)
    except SpeechError as exc:
        raise HTTPException(503 if exc.unavailable else 422 if exc.empty else 502, exc.message)
    stt_ms = round((perf_counter() - t0) * 1000)
    if not result.text.strip():
        raise HTTPException(422, "I could not hear any speech. Please try again or type your question.")

    # Auto: trust the language the STT picked; the text's script (Telugu letters) still wins inside handle_turn.
    return handle_turn(db, agent, question=result.text[: settings.max_question_chars], language=language if language != "auto" else result.language,
                       session_id=session_id, speak=speak, tts=tts, stt_ms=stt_ms, started=started)
