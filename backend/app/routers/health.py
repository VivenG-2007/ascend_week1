import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Base
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


def service_states() -> dict[str, str]:
    """Configuration state only; never makes paid or slow external calls."""
    s = get_settings()
    return {
        "agent": "azure" if s.use_azure_agent else "offline (rule-based, no LLM)",
        "speech": "azure" if s.azure_speech_configured else "not configured (text only)",
        "embeddings": f"azure/{s.azure_embedding_deployment}" if s.azure_embedding_configured else s.embedding_provider,
        "ocr": "azure-document-intelligence" if s.azure_ocr_configured else s.ocr_provider,
        "storage": "supabase" if s.supabase_url else "local",
        "vectorstore": f"chroma-cloud ({s.chroma_host}:{s.chroma_port})" if s.chroma_host else "chroma-local",
    }
log = logging.getLogger("campusvoice.health")


@router.get("/health", response_model=HealthResponse)
def health(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    database, schema_ready, detail = "ok", False, None
    try:
        db.execute(text("SELECT 1"))
        existing = set(inspect(db.get_bind()).get_table_names())
        missing = sorted(set(Base.metadata.tables) - existing)
        schema_ready = not missing
        if missing:
            detail = "Database schema is not up to date. Run: alembic upgrade head"
    except Exception:  # noqa: BLE001 - report, never leak driver details to the client
        log.exception("Health check could not reach the database")
        database, detail = "unreachable", "Database connection failed. Check DATABASE_URL."
    healthy = database == "ok" and schema_ready
    if not healthy:
        response.status_code = 503
    return HealthResponse(
        status="ok" if healthy else "degraded",
        college_name=settings.college_name,
        environment=settings.app_env,
        database=database,
        schema_ready=schema_ready,
        detail=detail,
        services=service_states(),
    )
