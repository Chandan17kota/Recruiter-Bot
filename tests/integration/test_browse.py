"""GET /jobs, GET /candidates, GET /health and CORS (added for the v2 frontend)."""
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_WEIGHTS, Settings
from app.main import create_app

UNREACHABLE = "postgresql://nobody@127.0.0.1:1/none"


# ---- GET /jobs ------------------------------------------------------------
def test_list_jobs_full_shape(client, ids):
    r = client.get("/jobs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == len(body["jobs"]) == 6
    assert [j["id"] for j in body["jobs"]] == sorted(ids["jobs"].values())
    detective = body["jobs"][0]
    assert detective == {
        "id": ids["jobs"]["backend-detective"],
        "title": "Backend Detective",
        "min_experience_years": 3.0,
        "required_skills": ["deduction", "forensics", "pattern-recognition"],
        "culture_keywords": ["analytical", "autonomous"],
        "tagline": "We have a bug. We have no leads. We have you.",
    }


def test_list_jobs_matches_job_header_of_matches_endpoint(client, ids):
    listed = {j["id"]: j for j in client.get("/jobs").json()["jobs"]}
    for job_id in ids["jobs"].values():
        assert client.get(f"/jobs/{job_id}/matches").json()["job"] == listed[job_id]


# ---- GET /candidates -------------------------------------------------------
def test_list_candidates_full_shape(client, ids):
    body = client.get("/candidates").json()
    assert body["total"] == len(body["candidates"]) == 15
    assert body["filters_applied"] == {"availability": None}
    assert [c["id"] for c in body["candidates"]] == sorted(ids["candidates"].values())
    sherlock = body["candidates"][0]
    assert sherlock == {
        "id": ids["candidates"]["sherlock-h"],
        "name": "Sherlock H.",
        "experience_years": 8.0,
        "availability": "immediate",
        "quirk": "Solves problems by eliminating the impossible; occasionally insufferable in standups.",
        "skills": ["deduction", "forensics", "pattern-recognition"],
        "traits": ["analytical", "blunt"],
    }


def test_list_candidates_matches_candidate_header_of_matches_endpoint(client, ids):
    listed = {c["id"]: c for c in client.get("/candidates").json()["candidates"]}
    for cid in ids["candidates"].values():
        assert client.get(f"/candidates/{cid}/matches").json()["candidate"] == listed[cid]


@pytest.mark.parametrize("query,expected", [
    ("availability=not_looking", 4),
    ("availability=two_weeks", 3),
    ("availability=immediate&availability=two_weeks", 11),
    ("availability=unknown", 0),
])
def test_list_candidates_availability_filter(client, query, expected):
    body = client.get(f"/candidates?{query}").json()
    assert body["total"] == expected
    wanted = set(body["filters_applied"]["availability"])
    assert all(c["availability"] in wanted for c in body["candidates"])


def test_list_candidates_bad_availability_is_422(client):
    r = client.get("/candidates?availability=soon")
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("url", ["/jobs", "/candidates", "/health"])
def test_browse_routes_reject_post(client, url):
    r = client.post(url)
    assert r.status_code == 405 and r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


@pytest.mark.parametrize("url,repo,fn", [
    ("/jobs", "jobs_repo", "list_jobs"),
    ("/candidates", "candidates_repo", "list_candidates"),
])
def test_browse_db_failure_returns_503(client, monkeypatch, url, repo, fn):
    import importlib
    module = importlib.import_module(f"app.repositories.{repo}")

    def boom(*a, **k):
        raise psycopg.OperationalError("connection refused: secret-host:5432")
    monkeypatch.setattr(module, fn, boom)
    r = client.get(url)
    assert r.status_code == 503 and r.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "secret-host" not in r.text


# ---- GET /health -------------------------------------------------------------
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_degraded_when_query_fails(client, monkeypatch):
    from app.repositories import health_repo

    def boom(*a, **k):
        raise psycopg.OperationalError("connection refused: secret-host:5432")
    monkeypatch.setattr(health_repo, "ping", boom)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "database": "unavailable"}
    assert "secret-host" not in r.text


def test_health_degraded_when_database_unreachable():
    app = create_app(Settings(database_url=UNREACHABLE, weights=DEFAULT_WEIGHTS, pool_timeout_s=1.0))
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/health")
    assert r.status_code == 503 and r.json()["database"] == "unavailable"


# ---- CORS ----------------------------------------------------------------
def test_no_cors_headers_by_default(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_allows_only_configured_origins(db_url):
    app = create_app(Settings(database_url=db_url, weights=DEFAULT_WEIGHTS,
                              cors_origins=("http://localhost:5173",)))
    with TestClient(app) as c:
        ok = c.get("/jobs", headers={"Origin": "http://localhost:5173"})
        other = c.get("/jobs", headers={"Origin": "http://evil.example"})
        preflight = c.options("/jobs", headers={"Origin": "http://localhost:5173",
                                                "Access-Control-Request-Method": "POST"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in other.headers
    assert preflight.status_code == 400   # only GET is allowed cross-origin
