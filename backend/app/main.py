import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.routers import admin, chat, documents, health, voice

log = logging.getLogger("campusvoice")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Force=True so uvicorn's existing handlers don't swallow our records.
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-8s %(name)-30s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )
    log.info(
        "═══ CampusVoice starting up ═══ env=%s college=%r db=%s origins=%s",
        settings.app_env,
        settings.college_name,
        settings.safe_database_description,
        settings.cors_origins,
    )
    log.info(
        "Config: embedding=%s ocr=%s storage=%s agent=%s speech=%s",
        settings.embedding_provider,
        settings.ocr_provider,
        "supabase" if settings.supabase_url else "local",
        "azure" if settings.azure_llm_configured else "offline",
        "azure" if settings.azure_speech_configured else "disabled",
    )
    if settings.chroma_cloud_configured:
        log.info("ChromaDB: Chroma Cloud tenant=%s database=%s", settings.chroma_tenant, settings.chroma_database)
    elif settings.chroma_host:
        log.info("ChromaDB: self-hosted host=%s:%d ssl=%s", settings.chroma_host, settings.chroma_port, settings.chroma_ssl)
    else:
        log.info("ChromaDB: local path=%s", settings.chroma_persist_directory)

    if settings.app_env != "test":
        _warm_up()
    yield
    log.info("═══ CampusVoice shut down ═══")


def _warm_up() -> None:
    """Load heavy, reusable services once at startup (not per request). Failures are loud but not fatal for text chat."""
    log.info("Warm-up: loading services...")
    for name, loader in (
        ("embedder", "app.services.embeddings:get_embedder"),
        ("vector store", "app.services.vectorstore:get_vectorstore"),
        ("ocr", "app.services.ocr:get_ocr"),
        ("storage", "app.services.storage:get_storage"),
    ):
        module, fn = loader.split(":")
        try:
            svc = getattr(__import__(module, fromlist=[fn]), fn)()
            log.info("Warm-up: %-20s ready  (%s)", name, getattr(svc, "name", type(svc).__name__))
        except Exception:  # noqa: BLE001
            log.exception(
                "Warm-up: %-20s FAILED — document search will be unavailable until this is fixed",
                name,
            )
    if get_settings().auto_reindex:
        _auto_reindex()
    log.info("Warm-up: complete")


def _auto_reindex() -> None:
    from app.db.session import get_sessionmaker
    from app.scripts.reindex import processed_chunk_count, reindex
    from app.services.embeddings import get_embedder
    from app.services.vectorstore import get_vectorstore

    try:
        vectors = get_vectorstore()
        with get_sessionmaker()() as db:
            expected = processed_chunk_count(db)
            actual = vectors.count()
            if expected > actual:
                log.warning(
                    "Auto-reindex: vector index has %d of %d chunks — rebuilding from database",
                    actual,
                    expected,
                )
                count = reindex(db, get_embedder(), vectors)
                log.info("Auto-reindex: reindexed %d chunk(s) successfully", count)
            else:
                log.info("Auto-reindex: index is up-to-date (%d chunks)", actual)
    except Exception:  # noqa: BLE001
        log.exception("Auto-reindex: failed — run `python -m app.scripts.reindex` manually")


def create_app() -> FastAPI:
    settings = get_settings()  # fails fast on invalid configuration
    app = FastAPI(title="CampusVoice API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("Database error")
        return JSONResponse(
            status_code=503,
            content={"detail": "The database is unavailable. Please try again shortly."},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error")
        return JSONResponse(
            status_code=500, content={"detail": "Something went wrong on our side."}
        )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(voice.router)
    app.include_router(documents.router)
    app.include_router(admin.router)
    return app


app = create_app()
