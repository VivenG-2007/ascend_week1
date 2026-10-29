"""
Cloud Status and Connectivity Service for Supabase Cloud and ChromaDB Cloud
Provides real-time validation and diagnostics for cloud resources.
"""
import logging
from typing import Dict, Any, Optional
from app.config import settings
from app.db.session import engine

logger = logging.getLogger("campusvoice.cloud")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def check_supabase_cloud() -> Dict[str, Any]:
    """Check connectivity to Supabase PostgreSQL database and Supabase client."""
    is_postgres = "postgresql" in settings.DATABASE_URL
    status = {
        "configured": is_postgres or bool(settings.SUPABASE_URL),
        "database_type": "Supabase PostgreSQL (Cloud)" if is_postgres else "SQLite (Local Fallback)",
        "database_connected": False,
        "supabase_url": settings.SUPABASE_URL or "Not set",
        "storage_bucket": settings.SUPABASE_STORAGE_BUCKET,
        "storage_connected": False,
        "detail": ""
    }

    # 1. Test database connection
    try:
        with engine.connect() as conn:
            status["database_connected"] = True
            if is_postgres:
                logger.info(f"[SUPABASE] Successfully connected to Supabase PostgreSQL Cloud database.")
            else:
                logger.info(f"[DATABASE] Connected to local fallback SQLite database ({engine.url}).")
    except Exception as e:
        status["detail"] += f"DB Error: {str(e)}; "
        logger.error(f"[DATABASE] Database connection check failed: {e}")

    # 2. Test Supabase Client / Storage if configured
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            # Verify storage connection
            buckets = supabase_client.storage.list_buckets()
            status["storage_connected"] = True
            logger.info(f"[SUPABASE CLOUD] Connected to Supabase Storage. Available buckets: {[b.name for b in buckets]}")
        except Exception as e:
            status["detail"] += f"Supabase Storage Error: {str(e)}; "
            logger.warning(f"[SUPABASE CLOUD] Storage check failed: {e}")
    else:
        logger.info("[SUPABASE CLOUD] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured. Using local filesystem storage.")

    return status

def check_chromadb_cloud() -> Dict[str, Any]:
    """Check connectivity to ChromaDB Cloud / Remote or Local Persistent ChromaDB."""
    is_cloud = bool(settings.CHROMA_SERVER_HOST or settings.CHROMA_CLOUD_API_KEY)
    status = {
        "configured": is_cloud,
        "chroma_type": "ChromaDB Cloud / Remote" if is_cloud else "ChromaDB Local Persisted",
        "connected": False,
        "host": settings.CHROMA_SERVER_HOST or "local",
        "collection_name": settings.CHROMA_COLLECTION_NAME,
        "detail": ""
    }

    try:
        import chromadb
        if is_cloud:
            logger.info(f"[CHROMADB CLOUD] Connecting to ChromaDB Cloud at host: {settings.CHROMA_SERVER_HOST}...")
            # Chroma Cloud client initialization
            headers = {}
            if settings.CHROMA_CLOUD_API_KEY:
                headers["x-chroma-token"] = settings.CHROMA_CLOUD_API_KEY

            client = chromadb.HttpClient(
                host=settings.CHROMA_SERVER_HOST,
                port=settings.CHROMA_SERVER_HTTP_PORT or (443 if settings.CHROMA_SERVER_SSL_ENABLED else 8000),
                ssl=settings.CHROMA_SERVER_SSL_ENABLED,
                headers=headers,
                tenant=settings.CHROMA_CLOUD_TENANT or "default_tenant",
                database=settings.CHROMA_CLOUD_DATABASE or "default_database"
            )
            # Ping
            client.heartbeat()
            status["connected"] = True
            logger.info(f"[CHROMADB CLOUD] Heartbeat successful! Connected to ChromaDB Cloud.")
        else:
            logger.info(f"[CHROMADB] Initializing local ChromaDB persistent client at {settings.CHROMA_PERSIST_DIRECTORY}...")
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
            client.heartbeat()
            status["connected"] = True
            logger.info(f"[CHROMADB] Heartbeat successful! Local ChromaDB is online and healthy.")
    except Exception as e:
        status["detail"] = str(e)
        logger.warning(f"[CHROMADB] Connection check reported: {e}")

    return status

def get_full_cloud_diagnostics() -> Dict[str, Any]:
    supabase_info = check_supabase_cloud()
    chroma_info = check_chromadb_cloud()
    return {
        "college_name": settings.COLLEGE_NAME,
        "supabase": supabase_info,
        "chromadb": chroma_info,
    }
