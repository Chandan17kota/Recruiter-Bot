import pytest

from app.config import ConfigError, load_settings


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)   # ignore the developer's .env
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@localhost/db")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    return monkeypatch


def test_cors_origins_default_empty(env):
    assert load_settings().cors_origins == ()


def test_cors_origins_parsed_and_trimmed(env):
    env.setenv("CORS_ORIGINS", " http://localhost:5173 , https://app.example ,")
    assert load_settings().cors_origins == ("http://localhost:5173", "https://app.example")


def test_cors_wildcard_rejected(env):
    env.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfigError, match="explicit origins"):
        load_settings()
