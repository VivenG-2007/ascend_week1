import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = (PROJECT_ROOT / "campusvoice.db").as_posix()

class Settings(BaseSettings):
    # Institution Info
    COLLEGE_NAME: str = "Geethanjali College of Engineering and Technology"
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    
    # Relational Database (Supabase PostgreSQL Cloud or SQLite fallback)
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    
    # Supabase Cloud
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "campusvoice-documents"
    
    # ChromaDB (Cloud or Local Persisted)
    CHROMA_PERSIST_DIRECTORY: str = (PROJECT_ROOT / "chroma_db").as_posix()
    CHROMA_COLLECTION_NAME: str = "campusvoice_chunks"
    CHROMA_SERVER_HOST: Optional[str] = None
    CHROMA_SERVER_HTTP_PORT: Optional[int] = None
    CHROMA_SERVER_SSL_ENABLED: bool = True
    CHROMA_CLOUD_API_KEY: Optional[str] = None
    CHROMA_CLOUD_TENANT: Optional[str] = None
    CHROMA_CLOUD_DATABASE: Optional[str] = None

    @field_validator("CHROMA_SERVER_HTTP_PORT", mode="before")
    @classmethod
    def parse_empty_port(cls, v):
        if v == "" or v is None:
            return None
        return int(v)
    
    # Cache
    REDIS_URL: Optional[str] = None
    
    # AI Models (Azure AI Foundry / OpenAI API Compatible)
    AZURE_AI_FOUNDRY_ENDPOINT: Optional[str] = None
    AZURE_AI_FOUNDRY_API_KEY: Optional[str] = None
    AZURE_AI_FOUNDRY_API_VERSION: str = "2024-02-15-preview"
    
    # Model Deployments
    MODEL_MAIN: str = "gpt-4.1"                # Main reasoning, answers, tool calling
    MODEL_MINI: str = "gpt-4.1-mini"           # Cost-efficient faster routine responses
    MODEL_VISION: str = "gpt-4.1"              # Image understanding and visual document interpretation
    
    # Multilingual Embeddings
    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-small"
    
    # OCR Services
    AZURE_DOC_INTEL_ENDPOINT: Optional[str] = None
    AZURE_DOC_INTEL_KEY: Optional[str] = None
    
    # Azure AI Speech (STT & TTS)
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: str = "eastus"
    AZURE_SPEECH_STT_LANGUAGE: str = "en-IN" # or te-IN
    AZURE_SPEECH_TTS_VOICE_EN: str = "en-IN-NeerjaNeural"
    AZURE_SPEECH_TTS_VOICE_TE: str = "te-IN-ShrutiNeural"
    
    # Security & Admin Authentication
    JWT_SECRET: str = "dev-secret-key-change-in-production-campusvoice"
    JWT_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" # default: admin123
    
    # RAG, Guardrails & Thresholds
    SIMILARITY_THRESHOLD: float = 0.35
    MAX_AUDIO_SECONDS: int = 30
    MAX_UPLOAD_MB: int = 15
    MAX_CHUNKS_RETURNED: int = 5
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
