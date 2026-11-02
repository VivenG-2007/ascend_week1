"""FastAPI dependencies for providers. Tests override these to inject fakes."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.services.embeddings import get_embedder
from app.services.llm_agent import Agent, build_agent
from app.services.ingestion import IngestionDeps
from app.services.ocr import get_ocr
from app.services.storage import get_storage
from app.services.stt import SpeechError, SpeechToText, get_stt as _get_stt
from app.services.tts import TextToSpeech, get_tts as _get_tts
from app.services.vectorstore import get_vectorstore


def get_agent(db: Session = Depends(get_db)) -> Agent:
    return build_agent(db)


def get_ingestion_deps() -> IngestionDeps:
    return IngestionDeps(storage=get_storage(), ocr=get_ocr(), embedder=get_embedder(), vectors=get_vectorstore())


class _UnconfiguredStt:
    """Lets the voice route validate audio first and only then report that speech is not configured."""

    def __init__(self, error: SpeechError) -> None:
        self.error = error

    def transcribe(self, wav: bytes, language: str = "auto"):
        raise self.error


def get_stt_service(settings: Settings = Depends(get_settings)) -> SpeechToText:
    try:
        return _get_stt(settings)
    except SpeechError as exc:
        return _UnconfiguredStt(exc)


def get_tts_service(settings: Settings = Depends(get_settings)) -> TextToSpeech | None:
    try:
        return _get_tts(settings)
    except SpeechError:
        return None
