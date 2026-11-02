from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class DocumentOut(BaseModel):
    id: str
    title: str
    category: str
    department: str
    source_date: date
    language: str | None
    processing_status: str
    extraction_status: str
    original_filename: str | None
    mime_type: str | None
    page_count: int
    ocr_pages: int
    chunk_count: int
    warnings: list[str]
    error_message: str | None
    supersedes_id: str | None
    superseded_by_id: str | None
    created_at: datetime


class UploadReport(BaseModel):
    document: DocumentOut
    pages: int
    ocr_pages: int
    chunks: int
    warnings: list[str]
    error: str | None
    duration_ms: int


class DocumentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    source_date: date | None = None
    supersedes_id: str | None = None


class TicketOut(BaseModel):
    id: str
    question: str
    summary: str | None
    transcript: str | None
    language: str
    department: str
    status: str
    contact: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketPatch(BaseModel):
    status: Literal["open", "in_progress", "resolved"] | None = None
    resolution_note: str | None = Field(default=None, max_length=2000)


class TicketList(BaseModel):
    total: int
    items: list[TicketOut]
