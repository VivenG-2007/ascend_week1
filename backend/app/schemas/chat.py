from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question or query")
    language: Optional[str] = Field("en", description="Detected or chosen language (en or te)")
    session_id: Optional[str] = Field(None, description="Client session identifier")
    user_id: Optional[str] = Field(None, description="Logged in user ID")
    user_name: Optional[str] = Field(None, description="Logged in user full name")
    user_email: Optional[str] = Field(None, description="Logged in user email")
    user_phone: Optional[str] = Field(None, description="Logged in user contact phone")

class SourceCitation(BaseModel):
    title: str
    department: Optional[str] = None
    source_date: Optional[str] = None
    page_number: Optional[int] = None
    document_id: Optional[str] = None
    replaces: Optional[str] = None
    superseded: Optional[bool] = False

class TicketInfo(BaseModel):
    id: str
    question: str
    department: str
    status: str
    summary: Optional[str] = None
    created_at: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

class ChatResponse(BaseModel):
    transcript: str
    language: str
    answer_text: str
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    sources: List[SourceCitation] = Field(default_factory=list)
    ticket: Optional[TicketInfo] = None
    confidence: Optional[float] = None
    latency_ms: float
    stt_ms: Optional[float] = 0.0
    llm_ms: float
    tts_ms: Optional[float] = 0.0

class HealthResponse(BaseModel):
    status: str
    app: str
    college_name: str
    database: str
    database_type: Optional[str] = "SQLite (Local Fallback)"
    supabase_storage: Optional[str] = "Not configured"
    chromadb_type: Optional[str] = "ChromaDB Local Persisted"
    chromadb_status: Optional[str] = "connected"
    timestamp: str
