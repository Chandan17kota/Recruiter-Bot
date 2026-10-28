import json

import psycopg
import pytest

from scripts.init_db import SEED_PATH, SeedError, init_db

TOP_KEYS = {"rank", "score", "skill_coverage", "matched_required_skill_count",
            "required_skill_count", "components", "explanation"}


def counts(url):
    with psycopg.connect(url) as conn:
        return conn.execute("""
            SELECT (SELECT count(*) FROM candidates), (SELECT count(*) FROM jobs),
                   (SELECT count(*) FROM skills), (SELECT count(*) FROM traits),
                   (SELECT count(*) FROM candidate_skills), (SELECT count(*) FROM candidate_traits),
                   (SELECT count(*) FROM job_required_skills), (SELECT count(*) FROM job_culture_keywords)
        """).fetchone()


def snapshot(url):
    queries = [
        "SELECT slug, full_name, experience_years, availability, traits_known, quirk FROM candidates ORDER BY slug",
        "SELECT slug, title, min_experience_years, tagline FROM jobs ORDER BY slug",
        "SELECT c.slug, s.name FROM candidate_skills cs JOIN candidates c ON c.id = cs.candidate_id JOIN skills s ON s.id = cs.skill_id ORDER BY c.slug, s.name",
        "SELECT c.slug, t.name FROM candidate_traits ct JOIN candidates c ON c.id = ct.candidate_id JOIN traits t ON t.id = ct.trait_id ORDER BY c.slug, t.name",
        "SELECT j.slug, s.name FROM job_required_skills rs JOIN jobs j ON j.id = rs.job_id JOIN skills s ON s.id = rs.skill_id ORDER BY j.slug, s.name",
        "SELECT j.slug, t.name FROM job_culture_keywords ck JOIN jobs j ON j.id = ck.job_id JOIN traits t ON t.id = ck.trait_id ORDER BY j.slug, t.name",
    ]
    with psycopg.connect(url) as conn:
        return tuple(tuple(conn.execute(query).fetchall()) for query in queries)


# ---- Seed ---------------------------------------------------------------
def test_seed_loaded_and_idempotent(db_url):
    before = counts(db_url)
    before_data = snapshot(db_url)
    assert before[:2] == (15, 6)
    init_db(db_url)
    assert counts(db_url) == before
    assert snapshot(db_url) == before_data


def test_invalid_seed_does_not_change_database(db_url, tmp_path):
    before = snapshot(db_url)
    bad_seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    bad_seed["candidates"][0]["experience_years"] = "999"
    seed_path = tmp_path / "invalid-seed.json"
    seed_path.write_text(json.dumps(bad_seed), encoding="utf-8")

    with pytest.raises(SeedError):
        init_db(db_url, seed_path)
    assert snapshot(db_url) == before


def test_seed_ids_follow_pdf_order(ids):
    assert ids["candidates"]["sherlock-h"] == 1 and ids["candidates"]["dwight-s"] == 15
    assert ids["jobs"]["backend-detective"] == 1 and ids["jobs"]["sales-engineer"] == 6


def test_db_constraints_reject_bad_rows(db_url):
    with psycopg.connect(db_url) as conn:
        for sql in [
            "INSERT INTO candidates (slug, full_name, experience_years) VALUES ('x', 'X', -1)",
            "INSERT INTO skills (name) VALUES ('Not Normalized')",
            "INSERT INTO skills (name) VALUES ('')",
            "INSERT INTO candidates (slug, full_name, experience_years, availability) VALUES ('y','Y',1,'soon')",
        ]:
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute(sql)


# ---- Job -> candidates --------------------------------------------------
def test_job_matches_full_shape(client, ids):
    body = client.get(f"/jobs/{ids['jobs']['backend-detective']}/matches").json()
    assert body["total"] == len(body["matches"]) == 15
    assert [m["rank"] for m in body["matches"]] == list(range(1, 16))
    first = body["matches"][0]
    assert TOP_KEYS | {"candidate"} == set(first)
    assert first["candidate"]["name"] == "Sherlock H." and first["score"] == 92.5
    assert set(first["components"]) == {"skills", "experience", "culture"}
    assert body["job"]["required_skills"] == ["deduction", "forensics", "pattern-recognition"]


def test_golden_via_api(client, ids):
    ic = client.get(f"/jobs/{ids['jobs']['incident-commander']}/matches").json()["matches"]
    names = [m["candidate"]["name"] for m in ic]
    assert ic[0]["candidate"]["name"] == "Olivia P." and ic[0]["score"] == 92.5
    assert names.index("Dwight S.") < names.index("Ron S.")
    assert next(m for m in ic if m["candidate"]["name"] == "Elle W.")["score"] == 18.75

    rp = client.get(f"/jobs/{ids['jobs']['rapid-prototyping-engineer']}/matches").json()["matches"]
    names = [m["candidate"]["name"] for m in rp]
    assert names.index("Rick S.") < names.index("MacGyver")

    bd = client.get(f"/jobs/{ids['jobs']['backend-detective']}/matches").json()["matches"]
    assert sum(1 for m in bd if m["score"] == 25.0) == 13


def test_availability_filter(client, ids):
    jid = ids["jobs"]["sales-engineer"]
    body = client.get(f"/jobs/{jid}/matches", params=[("availability", "immediate"), ("availability", "two_weeks")]).json()
    assert {m["candidate"]["availability"] for m in body["matches"]} <= {"immediate", "two_weeks"}
    assert body["filters_applied"]["availability"] == ["immediate", "two_weeks"]
    assert body["total"] == 11
    assert client.get(f"/jobs/{jid}/matches?availability=unknown").json()["total"] == 0


def test_min_score_filter(client, ids):
    body = client.get(f"/jobs/{ids['jobs']['backend-detective']}/matches?min_score=45").json()
    assert [m["candidate"]["name"] for m in body["matches"]] == ["Sherlock H.", "Sheldon C."]


def test_min_skill_coverage_filter(client, ids):
    url = f"/jobs/{ids['jobs']['backend-detective']}/matches"
    assert client.get(url).json()["total"] == 15                              # default keeps zero-skill
    assert client.get(url + "?min_skill_coverage=1").json()["total"] == 2
    full = client.get(url + "?min_skill_coverage=100").json()
    assert [m["candidate"]["name"] for m in full["matches"]] == ["Sherlock H."]


def test_empty_result_is_200(client, ids):
    r = client.get(f"/jobs/{ids['jobs']['backend-detective']}/matches?min_score=100")
    assert r.status_code == 200 and r.json()["matches"] == [] and r.json()["total"] == 0


# ---- Candidate -> jobs --------------------------------------------------
def test_candidate_matches(client, ids):
    body = client.get(f"/candidates/{ids['candidates']['olivia-p']}/matches").json()
    assert body["candidate"]["name"] == "Olivia P."
    assert body["total"] == len(body["matches"]) == 6
    assert [m["rank"] for m in body["matches"]] == list(range(1, 7))
    first = body["matches"][0]
    assert TOP_KEYS | {"job"} == set(first)
    assert first["job"]["title"] == "Incident Commander" and first["score"] == 92.5
    assert set(first["job"]) == {"id", "title", "min_experience_years", "tagline"}
    assert "availability" not in body["filters_applied"]


def test_both_directions_agree(client, ids):
    """The same pair must score identically from either side."""
    sid, jid = ids["candidates"]["sheldon-c"], ids["jobs"]["backend-detective"]
    a = next(m for m in client.get(f"/jobs/{jid}/matches").json()["matches"] if m["candidate"]["id"] == sid)
    b = next(m for m in client.get(f"/candidates/{sid}/matches").json()["matches"] if m["job"]["id"] == jid)
    for k in ("score", "skill_coverage", "components", "explanation"):
        assert a[k] == b[k]


def test_identical_calls_identical_bodies(client, ids):
    url = f"/jobs/{ids['jobs']['sales-engineer']}/matches"
    assert client.get(url).json() == client.get(url).json()


# ---- Errors -------------------------------------------------------------
@pytest.mark.parametrize("url,status,code", [
    ("/jobs/999/matches", 404, "JOB_NOT_FOUND"),
    ("/candidates/999/matches", 404, "CANDIDATE_NOT_FOUND"),
    ("/jobs/abc/matches", 422, "VALIDATION_ERROR"),
    ("/jobs/0/matches", 422, "VALIDATION_ERROR"),
    ("/jobs/1/matches?min_score=150", 422, "VALIDATION_ERROR"),
    ("/jobs/1/matches?min_score=-1", 422, "VALIDATION_ERROR"),
    ("/jobs/1/matches?min_skill_coverage=abc", 422, "VALIDATION_ERROR"),
    ("/jobs/1/matches?min_score=NaN", 422, "VALIDATION_ERROR"),
    ("/jobs/1/matches?availability=soon", 422, "VALIDATION_ERROR"),
    ("/jobs/99999999999/matches", 422, "VALIDATION_ERROR"),
    ("/does-not-exist", 404, "ROUTE_NOT_FOUND"),
])
def test_error_envelope(client, url, status, code):
    r = client.get(url)
    assert r.status_code == status
    assert set(r.json()) == {"error"}
    assert r.json()["error"]["code"] == code
    assert set(r.json()["error"]) == {"code", "message", "details"}


def test_validation_details_name_fields(client):
    details = client.get("/jobs/1/matches?min_score=150&min_skill_coverage=-5").json()["error"]["details"]
    assert {d["field"] for d in details} == {"min_score", "min_skill_coverage"}


def test_method_not_allowed(client):
    r = client.post("/jobs/1/matches")
    assert r.status_code == 405 and r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_db_failure_returns_503(client, monkeypatch):
    from app.repositories import jobs_repo

    def boom(*a, **k):
        raise psycopg.OperationalError("connection refused: secret-host:5432 password=hunter2")
    monkeypatch.setattr(jobs_repo, "get_job", boom)
    r = client.get("/jobs/1/matches")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "hunter2" not in r.text and "secret-host" not in r.text


def test_other_db_error_returns_generic_500(client, monkeypatch):
    from app.repositories import jobs_repo

    def boom(*a, **k):
        raise psycopg.errors.UndefinedTable('relation "jobs" does not exist')
    monkeypatch.setattr(jobs_repo, "get_job", boom)
    r = client.get("/jobs/1/matches")
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "relation" not in r.text


def test_unexpected_error_returns_500_envelope(client, monkeypatch):
    from app.repositories import jobs_repo
    monkeypatch.setattr(jobs_repo, "get_job", lambda *a, **k: 1 / 0)
    r = client.get("/jobs/1/matches")
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"


def test_unreachable_database_returns_503():
    from fastapi.testclient import TestClient

    from app.config import DEFAULT_WEIGHTS, Settings
    from app.main import create_app
    app = create_app(Settings(database_url="postgresql://nobody@127.0.0.1:1/none",
                              weights=DEFAULT_WEIGHTS, pool_timeout_s=1.0))
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/jobs/1/matches")
    assert r.status_code == 503 and r.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


# ---- Hostile input ------------------------------------------------------
@pytest.mark.parametrize("url", [
    "/jobs/1;DROP TABLE jobs/matches",
    "/jobs/1%20OR%201=1/matches",
    "/jobs/1/matches?availability=immediate';DROP TABLE candidates;--",
    "/jobs/1/matches?min_score=1;DELETE FROM jobs",
])
def test_hostile_input_rejected_tables_survive(client, db_url, url):
    r = client.get(url)
    assert r.status_code in (404, 422)
    assert counts(db_url)[:2] == (15, 6)


def test_statement_timeout_is_applied(db_url):
    from app.db.pool import make_pool
    pool = make_pool(db_url, statement_timeout_ms=200)
    pool.open(wait=True)
    try:
        with pool.connection() as conn:
            assert conn.execute("SHOW statement_timeout").fetchone()["statement_timeout"] == "200ms"
            with pytest.raises(psycopg.errors.QueryCanceled):
                conn.execute("SELECT pg_sleep(1)")
    finally:
        pool.close()
