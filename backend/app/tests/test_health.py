def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["schema_ready"] is True and body["college_name"] == "Test College"
    assert body["services"]["agent"].startswith("offline")
    assert "key" not in str(body).lower()


def test_health_degraded_when_schema_missing(app):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.session import get_db

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=eng)

    def empty_db():
        with factory() as s:
            yield s

    app.dependency_overrides[get_db] = empty_db
    r = TestClient(app).get("/health")
    assert r.status_code == 503 and r.json()["status"] == "degraded" and "alembic upgrade head" in r.json()["detail"]
