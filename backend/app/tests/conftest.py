import os
import tempfile
import uuid
from datetime import date
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="campusvoice_tests_")
# Must be set before any app module reads settings.
os.environ.update({
    "APP_ENV": "test", "DATABASE_URL": "sqlite:///:memory:", "FRONTEND_ORIGIN": "http://localhost:3000",
    "COLLEGE_NAME": "Test College", "EMBEDDING_PROVIDER": "hash", "OCR_PROVIDER": "none", "SIMILARITY_THRESHOLD": "0.4",
    "CHROMA_PERSIST_DIRECTORY": f"{_TMP}/chroma", "LOCAL_STORAGE_DIRECTORY": f"{_TMP}/uploads",
    "JWT_SECRET": "unit-test-secret-that-is-at-least-32-characters-long", "RATE_LIMIT_ENABLED": "false",
    "AGENT_MODE": "offline", "AZURE_SPEECH_KEY": "", "AZURE_SPEECH_REGION": "",
})
from app.services.auth import hash_password  # noqa: E402

ADMIN_PASSWORD = "correct-horse-battery"
os.environ["ADMIN_PASSWORD_HASH"] = hash_password(ADMIN_PASSWORD)

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app import deps as app_deps  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services import ratelimit  # noqa: E402
from app.services.embeddings import HashEmbedder  # noqa: E402
from app.services.ingestion import IngestionDeps  # noqa: E402
from app.services.llm_agent import LLMReply, ToolCall, build_agent  # noqa: E402
from app.services.ocr import OcrResult, OcrUnavailable  # noqa: E402
from app.services.storage import LocalStorage  # noqa: E402
from app.services.stt import SttResult  # noqa: E402
from app.services.vectorstore import VectorStore  # noqa: E402

TODAY = date(2026, 10, 30)


# ------------------------------------------------------------------ fakes & builders
class FakeOcr:
    name = "fake"

    def __init__(self, text="", warnings=None, unavailable=False):
        self.text, self.warnings, self.unavailable, self.calls = text, warnings or [], unavailable, 0

    def ocr_image(self, png_bytes):
        self.calls += 1
        if self.unavailable:
            raise OcrUnavailable("no tesseract")
        return OcrResult(text=self.text, confidence=None, warnings=list(self.warnings))


class FakeLLM:
    """Scripted LLM: each item is an LLMReply (or an Exception to raise). Records every call."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, tools):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def tool_call(name, args, id="call_1"):
    import json
    return ToolCall(id, name, json.dumps(args) if not isinstance(args, str) else args)


class FakeStt:
    def __init__(self, text="when is the fee deadline", language="en", error=None):
        self.text, self.language, self.error, self.calls = text, language, error, []

    def transcribe(self, wav, language="auto"):
        self.calls.append(language)
        if self.error:
            raise self.error
        return SttResult(self.text, self.language, "en-IN" if self.language == "en" else "te-IN", 0.9)


class FakeTts:
    def __init__(self, error=None):
        self.error, self.calls = error, []

    def synthesize(self, text, language):
        self.calls.append((text, language))
        if self.error:
            raise self.error
        return b"ID3-fake-mp3"


def make_pdf(pages):
    doc = pymupdf.open()
    for text in pages:
        p = doc.new_page()
        if text:
            p.insert_textbox(pymupdf.Rect(50, 50, 545, 780), text, fontsize=12)
    return doc.tobytes()


def make_png(text="scanned notice"):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 100), text, fontsize=20)
    return doc[0].get_pixmap(dpi=100).tobytes("png")


def make_wav(seconds=1.0, rate=16000, amplitude=3000, channels=1):
    import array, io, math, wave
    n = int(seconds * rate)
    samples = array.array("h", [int(amplitude * math.sin(2 * math.pi * 220 * i / rate)) for i in range(n)])
    if channels == 2:
        samples = array.array("h", [x for s in samples for x in (s, s)])
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(rate); w.writeframes(samples.tobytes())
    return buf.getvalue()


# ------------------------------------------------------------------------ fixtures
@pytest.fixture
def settings_env(monkeypatch):
    """Change settings for one test: settings_env(JWT_SECRET='x')."""
    def apply(**kw):
        for k, v in kw.items():
            monkeypatch.setenv(k.upper(), str(v))
        get_settings.cache_clear()
    yield apply
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_limiter():
    ratelimit.reset()
    yield


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def ocr():
    return FakeOcr(text="")


@pytest.fixture
def deps(tmp_path, ocr):
    return IngestionDeps(storage=LocalStorage(str(tmp_path / "files")), ocr=ocr, embedder=HashEmbedder(),
                         vectors=VectorStore(str(tmp_path / "chroma"), "c" + uuid.uuid4().hex[:12]))


@pytest.fixture
def llm_holder():
    class H:
        llm = None
    return H()


@pytest.fixture
def stt_holder():
    class H:
        stt = FakeStt()
        tts = FakeTts()
    return H()


@pytest.fixture
def app(engine, deps, llm_holder, stt_holder):
    application = create_app()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        with factory() as s:
            yield s

    def _agent(db=app_deps.Depends(get_db)):
        return build_agent(db, embedder=deps.embedder, vectors=deps.vectors, llm=llm_holder.llm, today=TODAY)

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[app_deps.get_agent] = _agent
    application.dependency_overrides[app_deps.get_ingestion_deps] = lambda: deps
    application.dependency_overrides[app_deps.get_stt_service] = lambda: stt_holder.stt
    application.dependency_overrides[app_deps.get_tts_service] = lambda: stt_holder.tts
    return application


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers(client):
    r = client.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def seeded(db):
    from app.db.seed import seed
    seed(db, today=TODAY)
    return db


def ingest(db, deps, text_pages, title="Doc", department="General", source_date=date(2026, 8, 1), supersedes_id=None, filename="a.pdf"):
    from app.services.ingestion import ingest_document
    return ingest_document(db, deps, data=make_pdf(text_pages), filename=filename, declared_mime="application/pdf", title=title,
                           category="Circular", department=department, source_date=source_date, supersedes_id=supersedes_id)


FEE_TEXT = "Fee Payment Circular. The last date to pay the semester tuition fee is 15 September 2026. A late fee of Rs 100 per day applies."
FEE_REVISED = "Revised Fee Payment Circular. This circular replaces the earlier one. The last date to pay the semester tuition fee is now 10 November 2026."
HOSTEL_TEXT = "Hostel rules. The hostel gate closes at 9:30 PM every day. Visitors are allowed in the lobby only on Sundays."
BUS_TEXT = "Bus routes. Route R1 departs the north gate at 7:15 AM. Route R2 departs the station road at 7:30 AM."
