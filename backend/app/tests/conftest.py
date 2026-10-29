import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import engine, Base

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        import chromadb
        from app.config import settings
        chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        try:
            chroma_client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
        except Exception:
            pass
    except Exception:
        pass
    yield

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
