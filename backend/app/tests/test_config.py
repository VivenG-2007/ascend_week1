import pytest

from app.config import Settings


def test_postgres_url_is_normalised_to_psycopg_driver():
    s = Settings(database_url="postgresql://u:p@db.example.supabase.co:5432/postgres", _env_file=None)
    assert s.sqlalchemy_url.startswith("postgresql+psycopg://")
    assert "p@" in s.sqlalchemy_url  # real URL keeps credentials...
    assert "u:p" not in s.safe_database_description  # ...but the loggable form never does


def test_relative_sqlite_path_is_anchored_to_backend_dir():
    s = Settings(database_url="sqlite:///./x.db", _env_file=None)
    assert s.sqlalchemy_url.endswith("/backend/x.db") or s.sqlalchemy_url.endswith("\\backend\\x.db")


def test_production_refuses_sqlite():
    with pytest.raises(ValueError, match="SQLite"):
        Settings(app_env="production", database_url="sqlite:///./x.db", _env_file=None)


def test_wildcard_origin_rejected():
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(frontend_origin="*", _env_file=None)


def test_origin_with_trailing_slash_rejected():
    with pytest.raises(ValueError, match="trailing slash"):
        Settings(frontend_origin="http://localhost:3000/", _env_file=None)


def test_multiple_origins_parse():
    s = Settings(frontend_origin="http://localhost:3000, https://app.example.com", _env_file=None)
    assert s.cors_origins == ["http://localhost:3000", "https://app.example.com"]


def test_blank_college_name_rejected():
    with pytest.raises(ValueError):
        Settings(college_name="   ", _env_file=None)


def test_unsupported_database_rejected():
    with pytest.raises(ValueError, match="sqlite or postgresql"):
        Settings(database_url="mysql://u:p@h/db", _env_file=None)


def test_production_requires_jwt_secret_and_admin_hash():
    base = dict(app_env="production", database_url="postgresql://u:p@h/db", _env_file=None)
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(jwt_secret=None, admin_password_hash=None, **base)
    with pytest.raises(ValueError, match="ADMIN_PASSWORD_HASH"):
        Settings(jwt_secret="x" * 40, admin_password_hash=None, **base)
    assert Settings(jwt_secret="x" * 40, admin_password_hash="$2b$12$abc", **base).app_env == "production"


def test_agent_mode_azure_requires_credentials():
    with pytest.raises(ValueError, match="AGENT_MODE=azure"):
        Settings(agent_mode="azure", _env_file=None).use_azure_agent
    s = Settings(agent_mode="auto", azure_ai_foundry_endpoint="https://x.openai.azure.com", azure_ai_foundry_api_key="k", azure_ai_foundry_deployment="gpt-4.1", _env_file=None)
    assert s.use_azure_agent
    assert Settings(agent_mode="offline", azure_ai_foundry_endpoint="https://x", azure_ai_foundry_api_key="k", azure_ai_foundry_deployment="d", _env_file=None).use_azure_agent is False


def test_password_hashing_roundtrip():
    from app.services.auth import hash_password, verify_password
    h = hash_password("a-long-password")
    assert h != "a-long-password" and verify_password("a-long-password", h) and not verify_password("nope", h) and not verify_password("x", None)
