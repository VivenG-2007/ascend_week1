from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

LanguageChoice = Literal["auto", "en", "te"]
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


class ChatRequest(BaseModel):
    question: str = Field(..., description="The user's question, typed or transcribed.")
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)
    language: LanguageChoice = "auto"
    department: str | None = Field(default=None, max_length=50, description="Optional retrieval filter.")
    speak: bool = Field(default=False, description="Also return synthesized audio for the answer.")

    @field_validator("question")
    @classmethod
    def _clean_question(cls, v: str) -> str:
        v = " ".join(v.split())  # collapse whitespace and control newlines
        if not v:
            raise ValueError("question must not be empty")
        return v


class SourceRef(BaseModel):
    document_id: str
    title: str
    source_date: date | None = None
    page_number: int | None = None
    department: str | None = None
    score: float | None = None
    superseded_note: str | None = None


class TicketInfo(BaseModel):
    id: str
    department: str
    status: str
    summary: str | None = None


class RetrievalMetrics(BaseModel):
    metric: str | None = None  # e.g. "cosine_distance"; set once ChromaDB is wired up
    top_score: float | None = None
    hits: int = 0
    threshold: float | None = None
    decision: str | None = None  # answered | escalated | declined


class ChatResponse(BaseModel):
    session_id: str
    transcript: str
    language: Literal["en", "te"]
    answer_text: str
    audio_base64: str | None = None
    audio_url: str | None = None
    sources: list[SourceRef] = []
    ticket: TicketInfo | None = None
    retrieval: RetrievalMetrics | None = None
    # Latencies in milliseconds. stt_ms/tts_ms are null when not applicable (text chat, TTS off).
    latency_ms: int
    stt_ms: int | None = None
    llm_ms: int | None = None
    tts_ms: int | None = None
    warnings: list[str] = []
