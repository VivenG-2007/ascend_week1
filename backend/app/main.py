import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.db.session import engine, Base
from app.db.seed import seed_database
from app.schemas.chat import HealthResponse
from app.routers.chat import router as chat_router
from app.routers.voice import router as voice_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.services.cloud_status import get_full_cloud_diagnostics, check_supabase_cloud, check_chromadb_cloud

logger = logging.getLogger("campusvoice")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log College name and configuration
    print("=" * 60)
    print(f" CAMPUSVOICE: {settings.COLLEGE_NAME}")
    print("=" * 60)
    
    # Startup diagnostics
    cloud_diag = get_full_cloud_diagnostics()
    print(f"[CLOUD LOG] Database Engine: {cloud_diag['supabase']['database_type']}")
    print(f"[CLOUD LOG] Database Status: {'CONNECTED' if cloud_diag['supabase']['database_connected'] else 'DISCONNECTED'}")
    print(f"[CLOUD LOG] Supabase Storage: {'CONNECTED' if cloud_diag['supabase']['storage_connected'] else 'LOCAL FALLBACK'}")
    print(f"[CLOUD LOG] ChromaDB Engine: {cloud_diag['chromadb']['chroma_type']}")
    print(f"[CLOUD LOG] ChromaDB Status: {'CONNECTED' if cloud_diag['chromadb']['connected'] else 'ERROR'}")
    print("=" * 60)

    # Ensure clean tables exist without seeding mock records
    try:
        Base.metadata.create_all(bind=engine)
        print("[DATABASE] Relational schema tables initialized cleanly (no auto-seeded records).")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

    yield

app = FastAPI(
    title=f"CampusVoice API - {settings.COLLEGE_NAME}",
    description="Multilingual Voice AI Helpdesk for College Information",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    settings.FRONTEND_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe error handling
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact the administrator."}
    )

# Routers
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(admin_router)
app.include_router(auth_router)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    supabase_info = check_supabase_cloud()
    chroma_info = check_chromadb_cloud()

    db_status = "connected" if supabase_info["database_connected"] else f"unhealthy: {supabase_info['detail']}"

    return HealthResponse(
        status="ok" if supabase_info["database_connected"] else "degraded",
        app="CampusVoice",
        college_name=settings.COLLEGE_NAME,
        database=db_status,
        database_type=supabase_info["database_type"],
        supabase_storage="connected" if supabase_info["storage_connected"] else "not_configured (using local)",
        chromadb_type=chroma_info["chroma_type"],
        chromadb_status="connected" if chroma_info["connected"] else f"failed: {chroma_info['detail']}",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/cloud/status", tags=["Cloud Diagnostics"])
def cloud_diagnostics():
    """Returns detailed real-time connectivity status and logs for Supabase Cloud and ChromaDB Cloud."""
    return get_full_cloud_diagnostics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
