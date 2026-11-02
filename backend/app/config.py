"""Application settings, loaded from environment variables and optional .env files.

Validation happens once at startup so misconfiguration fails fast with a clear message.

Services used:
  - Azure AI Foundry   : LLM (chat) + text embeddings
  - Azure AI Speech    : STT + TTS
  - Azure Document Intelligence : OCR
  - Supabase           : PostgreSQL (DATABASE_URL) + object storage
  - ChromaDB           : vector store (local PersistentClient or remote HttpClient)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class ConfigError(ValueError):
    """Raised when the configuration is unusable."""


class Settings(BaseSettings):
    # backend/.env is the canonical env file; it is the ONLY file loaded.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- core
    app_env: Literal["development", "test", "production"] = "development"
    college_name: str = "Demo College of Engineering"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "sqlite:///./campusvoice.db"
    log_level: str = "DEBUG"
    max_question_chars: int = Field(default=1000, ge=50, le=5000)

    # ---- vector search (ChromaDB)
    # Chroma Cloud (api.trychroma.com): set CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE.
    # Self-hosted / local: leave CHROMA_API_KEY empty and set CHROMA_HOST (HttpClient)
    #   or leave CHROMA_HOST empty too (local PersistentClient at CHROMA_PERSIST_DIRECTORY).
    chroma_api_key: str | None = None          # Chroma Cloud auth key
    chroma_tenant: str | None = None           # Chroma Cloud tenant UUID
    chroma_database: str | None = None         # Chroma Cloud database name
    chroma_host: str | None = None             # self-hosted HttpClient host (ignored when chroma_api_key set)
    chroma_port: int = Field(default=8001, ge=1, le=65535)
    chroma_ssl: bool = False
    chroma_persist_directory: str = "./chroma_data"   # used only when no cloud/remote host
    chroma_collection_name: str = "campusvoice_chunks"

    # Embedding provider: "azure" uses Azure OpenAI embeddings API; "hash" is offline/test only.
    embedding_provider: Literal["azure", "hash"] = "azure"
    azure_embedding_deployment: str | None = None      # e.g. text-embedding-3-large
    azure_embedding_dimension: int = Field(default=1536, ge=256, le=4096)
    similarity_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    auto_reindex: bool = True

    # ---- documents / OCR / storage
    max_upload_mb: int = Field(default=15, ge=1, le=100)

    # OCR provider: "azure" uses Azure Document Intelligence; "none" disables OCR.
    ocr_provider: Literal["azure", "none"] = "azure"
    azure_document_intelligence_endpoint: str | None = None   # https://<resource>.cognitiveservices.azure.com/
    azure_document_intelligence_key: str | None = None

    # Supabase storage (required in production; local fallback uses local_storage_directory)
    local_storage_directory: str = "./uploads"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None       # backend only — NEVER expose to frontend
    supabase_storage_bucket: str = "campusvoice-documents"

    # ---- Azure AI Foundry (LLM)
    agent_mode: Literal["auto", "azure", "offline"] = "auto"
    azure_ai_foundry_endpoint: str | None = None       # https://<resource>.openai.azure.com/
    azure_ai_foundry_api_key: str | None = None
    azure_ai_foundry_deployment: str | None = None     # e.g. gpt-4o
    azure_ai_foundry_api_version: str = "2024-10-21"

    # ---- Azure AI Speech (STT + TTS)
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None             # e.g. centralindia
    azure_speech_stt_languages: str = "en-IN,te-IN"
    azure_speech_tts_voice_en: str = "en-IN-NeerjaNeural"
    azure_speech_tts_voice_te: str = "te-IN-ShrutiNeural"
    max_audio_seconds: int = Field(default=30, ge=5, le=60)

    # ---- admin auth
    jwt_secret: str | None = None
    jwt_expire_minutes: int = Field(default=60, ge=5, le=1440)
    admin_username: str = "admin"
    admin_password_hash: str | None = None             # bcrypt hash; see `python -m app.scripts.hash_password`

    # ---- abuse protection (in-memory, per process)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=30, ge=1)
    login_rate_limit_per_minute: int = Field(default=5, ge=1)

    # ---- validators ----

    @field_validator("college_name")
    @classmethod
    def _college_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("COLLEGE_NAME must not be blank")
        return v

    @field_validator("log_level")
    @classmethod
    def _log_level_valid(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
        return v

    @field_validator("database_url")
    @classmethod
    def _database_url_supported(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        try:
            backend = make_url(v).get_backend_name()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"DATABASE_URL is not a valid SQLAlchemy URL: {exc}") from exc
        if backend not in {"sqlite", "postgresql", "postgres"}:
            raise ValueError("DATABASE_URL must use sqlite or postgresql")
        return v

    @model_validator(mode="after")
    def _check_origins_and_env(self) -> "Settings":
        origins = self.cors_origins
        if not origins:
            raise ValueError("FRONTEND_ORIGIN must contain at least one origin")
        for origin in origins:
            if "*" in origin:
                raise ValueError("Wildcard origins are not allowed; list exact frontend origins")
            if not origin.startswith(("http://", "https://")) or origin.endswith("/"):
                raise ValueError(
                    f"FRONTEND_ORIGIN entry {origin!r} must look like https://example.com (no trailing slash)"
                )
        if self.app_env == "production":
            if not self.jwt_secret or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET (at least 32 characters) is required when APP_ENV=production")
            if not self.admin_password_hash:
                raise ValueError("ADMIN_PASSWORD_HASH is required when APP_ENV=production")
        if self.app_env == "production" and self.is_sqlite:
            raise ValueError(
                "DATABASE_URL points to SQLite while APP_ENV=production. "
                "Configure Supabase PostgreSQL instead of silently using a local file."
            )
        return self

    # ---- computed properties ----

    @property
    def chroma_cloud_configured(self) -> bool:
        """True when all three Chroma Cloud credentials are present (api.trychroma.com)."""
        return bool(self.chroma_api_key and self.chroma_tenant and self.chroma_database)

    @property
    def azure_llm_configured(self) -> bool:
        return bool(
            self.azure_ai_foundry_endpoint
            and self.azure_ai_foundry_api_key
            and self.azure_ai_foundry_deployment
        )

    @property
    def azure_speech_configured(self) -> bool:
        return bool(self.azure_speech_key and self.azure_speech_region)

    @property
    def azure_ocr_configured(self) -> bool:
        return bool(self.azure_document_intelligence_endpoint and self.azure_document_intelligence_key)

    @property
    def azure_embedding_configured(self) -> bool:
        return bool(
            self.azure_ai_foundry_endpoint
            and self.azure_ai_foundry_api_key
            and self.azure_embedding_deployment
        )

    @property
    def use_azure_agent(self) -> bool:
        if self.agent_mode == "offline":
            return False
        if self.agent_mode == "azure" and not self.azure_llm_configured:
            raise ValueError("AGENT_MODE=azure requires AZURE_AI_FOUNDRY_ENDPOINT, _API_KEY and _DEPLOYMENT")
        return self.azure_llm_configured

    @property
    def stt_languages(self) -> list[str]:
        return [x.strip() for x in self.azure_speech_stt_languages.split(",") if x.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return make_url(self.database_url).get_backend_name() == "sqlite"

    @property
    def sqlalchemy_url(self) -> str:
        """Normalised URL: psycopg v3 driver for Postgres, SQLite paths anchored to backend/."""
        url = make_url(self.database_url)
        if url.get_backend_name() in {"postgresql", "postgres"}:
            return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
        db = url.database
        if db and db != ":memory:" and not Path(db).is_absolute():
            url = url.set(database=str((BACKEND_DIR / db).resolve()))
        return url.render_as_string(hide_password=False)

    @property
    def safe_database_description(self) -> str:
        """Database description that never contains credentials (for logs and /health)."""
        url = make_url(self.sqlalchemy_url)
        if self.is_sqlite:
            return f"sqlite:{Path(url.database).name if url.database else 'memory'}"
        return f"{url.get_backend_name()}://{url.host}/{url.database}"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValueError as exc:
        raise ConfigError(f"Invalid configuration:\n{exc}") from exc
