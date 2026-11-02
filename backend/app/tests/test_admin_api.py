import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.tests.conftest import ADMIN_PASSWORD, FEE_TEXT, HOSTEL_TEXT, FakeOcr, make_pdf, make_png

ADMIN_ROUTES = [("GET", "/api/admin/documents"), ("POST", "/api/admin/documents"), ("PATCH", "/api/admin/documents/x"),
                ("GET", "/api/admin/tickets"), ("PATCH", "/api/admin/tickets/x"), ("GET", "/api/admin/analytics")]


def upload(client, headers, data=None, name="fee.pdf", mime="application/pdf", **over):
    form = {"title": "Fee Circular", "category": "Circular", "department": "Accounts", "source_date": "2026-08-10", **over}
    return client.post("/api/admin/documents", headers=headers, files={"file": (name, data if data is not None else make_pdf([FEE_TEXT]), mime)}, data=form)


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_every_admin_route_requires_authentication(client, method, path):
    assert client.request(method, path).status_code == 401
    assert client.request(method, path, headers={"Authorization": "Bearer not.a.token"}).status_code == 401


def test_login_success_and_failures(client):
    ok = client.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer" and ok.json()["expires_in"] > 0
    assert client.post("/api/admin/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "root", "password": ADMIN_PASSWORD}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "admin"}).status_code == 422


def test_login_is_rate_limited(client, settings_env):
    settings_env(rate_limit_enabled="true", login_rate_limit_per_minute="3")
    codes = [client.post("/api/admin/login", json={"username": "admin", "password": "bad"}).status_code for _ in range(5)]
    assert codes[:3] == [401, 401, 401] and 429 in codes[3:]


def test_login_unavailable_when_admin_not_configured(client, settings_env):
    settings_env(admin_password_hash="")
    assert client.post("/api/admin/login", json={"username": "admin", "password": "x"}).status_code == 503


def _token(role="admin", exp_delta=300, secret=None):
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": "u", "role": role, "iat": now, "exp": now + timedelta(seconds=exp_delta)}, secret or s.jwt_secret, algorithm="HS256")


def test_expired_wrongly_signed_and_unprivileged_tokens(client):
    h = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
    assert client.get("/api/admin/tickets", headers=h(_token(exp_delta=-10))).status_code == 401
    assert client.get("/api/admin/tickets", headers=h(_token(secret="x" * 40))).status_code == 401
    assert client.get("/api/admin/tickets", headers=h(_token(role="viewer"))).status_code == 403
    assert client.get("/api/admin/tickets", headers=h(_token())).status_code == 200


def test_alg_none_token_is_rejected(client):
    forged = jwt.encode({"sub": "u", "role": "admin", "exp": time.time() + 300}, key=None, algorithm="none")
    assert client.get("/api/admin/tickets", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_upload_processes_and_lists_with_counts(client, admin_headers):
    r = upload(client, admin_headers)
    assert r.status_code == 201
    rep = r.json()
    assert rep["document"]["processing_status"] == "processed" and rep["chunks"] == 1 and rep["document"]["chunk_count"] == 1
    listing = client.get("/api/admin/documents", headers=admin_headers).json()
    assert listing[0]["title"] == "Fee Circular" and listing[0]["source_date"] == "2026-08-10" and listing[0]["page_count"] == 1


def test_uploaded_document_is_immediately_searchable_by_chat(client, admin_headers):
    upload(client, admin_headers, data=make_pdf([HOSTEL_TEXT]), title="Hostel Rules", department="Hostel")
    b = client.post("/api/chat", json={"question": "hostel gate closes at what time"}).json()
    assert b["retrieval"]["decision"] == "answered" and b["sources"][0]["title"] == "Hostel Rules" and "9:30 PM" in b["answer_text"]


def test_unreadable_image_upload_shows_failure_and_warnings(client, admin_headers, deps):
    deps.ocr = FakeOcr(text="", warnings=["OCR found no readable text."])
    rep = upload(client, admin_headers, data=make_png(), name="blur.png", mime="image/png").json()
    assert rep["document"]["processing_status"] == "failed" and "No readable text" in rep["error"] and rep["chunks"] == 0
    assert any(d["error"] for d in client.get("/api/admin/analytics", headers=admin_headers).json()["document_failures"])


def test_upload_rejections(client, admin_headers, settings_env):
    assert upload(client, admin_headers, data=b"hello", name="a.txt", mime="text/plain").status_code == 415
    assert upload(client, admin_headers, data=make_png(), mime="application/pdf").status_code == 415
    assert upload(client, admin_headers, data=b"").status_code == 422
    assert client.post("/api/admin/documents", headers=admin_headers, files={"file": ("a.pdf", make_pdf(["x"]), "application/pdf")}, data={"title": "t"}).status_code == 422
    settings_env(max_upload_mb="1")
    assert upload(client, admin_headers, data=b"%PDF-" + b"0" * (1024 * 1024 + 10)).status_code == 413
    pdf = make_pdf([FEE_TEXT])
    assert upload(client, admin_headers, data=pdf).status_code == 201
    assert upload(client, admin_headers, data=pdf).status_code == 409


def test_patch_document_updates_metadata_everywhere_and_blocks_cycles(client, admin_headers, deps):
    a = upload(client, admin_headers).json()["document"]["id"]
    b = upload(client, admin_headers, data=make_pdf([HOSTEL_TEXT]), title="B").json()["document"]["id"]
    r = client.patch(f"/api/admin/documents/{a}", headers=admin_headers, json={"title": "Fee Circular v2", "department": "Exam Cell"})
    assert r.status_code == 200 and r.json()["title"] == "Fee Circular v2"
    meta = deps.vectors._col.get(where={"document_id": a}, include=["metadatas"])["metadatas"][0]
    assert meta["title"] == "Fee Circular v2" and meta["department"] == "Exam Cell"
    assert client.patch(f"/api/admin/documents/{b}", headers=admin_headers, json={"supersedes_id": a}).status_code == 200
    assert client.patch(f"/api/admin/documents/{a}", headers=admin_headers, json={"supersedes_id": b}).status_code == 422
    assert client.patch(f"/api/admin/documents/{a}", headers=admin_headers, json={"supersedes_id": a}).status_code == 422
    assert client.patch("/api/admin/documents/nope", headers=admin_headers, json={"title": "x"}).status_code == 404
    assert client.get("/api/admin/documents", headers=admin_headers).json()[0]["superseded_by_id"] in (a, b, None)


def test_revised_circular_flow_through_admin_api(client, admin_headers):
    old = upload(client, admin_headers, title="Fee Circular").json()["document"]["id"]
    upload(client, admin_headers, data=make_pdf(["Revised fee notice. The last date to pay the semester tuition fee is now 10 November 2026."]),
           title="Revised Fee Circular", source_date="2026-10-12", supersedes_id=old)
    b = client.post("/api/chat", json={"question": "last date to pay the semester tuition fee"}).json()
    assert "10 November 2026" in b["answer_text"] and b["sources"][0]["title"] == "Revised Fee Circular"
    assert "replaces" in b["sources"][0]["superseded_note"]


def test_ticket_management(client, admin_headers):
    t1 = client.post("/api/chat", json={"question": "Is there a rooftop garden at the college?"}).json()["ticket"]["id"]
    client.post("/api/chat", json={"question": "Can the hostel mess serve jain food at the college?"})
    all_t = client.get("/api/admin/tickets", headers=admin_headers).json()
    assert all_t["total"] == 2
    assert client.get("/api/admin/tickets?department=Hostel", headers=admin_headers).json()["total"] == 1
    assert client.get("/api/admin/tickets?status=resolved", headers=admin_headers).json()["total"] == 0
    assert client.get("/api/admin/tickets?department=Nope", headers=admin_headers).status_code == 422
    r = client.patch(f"/api/admin/tickets/{t1}", headers=admin_headers, json={"status": "resolved", "resolution_note": "Answered by phone."})
    assert r.status_code == 200 and r.json()["status"] == "resolved" and r.json()["resolved_at"] and r.json()["resolution_note"] == "Answered by phone."
    r = client.patch(f"/api/admin/tickets/{t1}", headers=admin_headers, json={"status": "in_progress"})
    assert r.json()["resolved_at"] is None
    assert client.patch(f"/api/admin/tickets/{t1}", headers=admin_headers, json={"status": "closed"}).status_code == 422
    assert client.patch("/api/admin/tickets/CV-NOPE", headers=admin_headers, json={"status": "open"}).status_code == 404


def test_analytics_uses_real_aggregates(client, admin_headers, seeded):
    upload(client, admin_headers, data=make_pdf([HOSTEL_TEXT]), title="Hostel Rules", department="Hostel")
    for q in ["hostel rules", "hostel rules", "first period CSE-A Monday timetable", "Is there a rooftop garden at the college?", "ఫీజు కళాశాల"]:
        client.post("/api/chat", json={"question": q})
    a = client.get("/api/admin/analytics", headers=admin_headers).json()
    assert a["totals"]["questions"] == 5 and a["totals"]["tickets"] >= 1
    assert a["top_questions"][0] == {"question": "hostel rules", "count": 2}
    assert a["language_usage"]["en"] == 4 and a["language_usage"]["te"] == 1
    assert a["latency"]["total"]["count"] == 5 and a["latency"]["total"]["median_ms"] is not None
    assert sum(b["count"] for b in a["retrieval_confidence"]["buckets"]) >= 1 and "escalated" in a["retrieval_confidence"]["decisions"]
    assert a["tickets_by_status"].get("open", 0) >= 1 and a["unanswered_questions"]


def test_public_document_file_only_for_processed_documents(client, admin_headers, deps):
    from app.services import storage
    storage.get_storage.cache_clear()
    doc = upload(client, admin_headers).json()["document"]
    import app.routers.documents as docs
    docs.get_storage = lambda: deps.storage
    r = client.get(f"/api/documents/{doc['id']}/file")
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and r.headers["x-content-type-options"] == "nosniff"
    deps.ocr = FakeOcr(text="")
    bad = upload(client, admin_headers, data=make_png(), name="x.png", mime="image/png").json()["document"]
    assert client.get(f"/api/documents/{bad['id']}/file").status_code == 404
    assert client.get("/api/documents/missing/file").status_code == 404
