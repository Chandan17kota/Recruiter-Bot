"""Integration fixtures: a real local Postgres test DB, wiped and reseeded per module."""
import os

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.config import DEFAULT_WEIGHTS, Settings
from app.main import create_app
from scripts.init_db import init_db

load_dotenv()
TEST_URL = os.environ.get("TEST_DATABASE_URL")

DROP_ALL = """
DROP TABLE IF EXISTS candidate_skills, candidate_traits, job_required_skills,
                     job_culture_keywords, skills, traits, candidates, jobs CASCADE
"""


def _reachable(url) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=2):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def db_url():
    if not TEST_URL or not _reachable(TEST_URL):
        pytest.skip("TEST_DATABASE_URL not set or Postgres not reachable")
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(DROP_ALL)
    init_db(TEST_URL)
    return TEST_URL


@pytest.fixture(scope="module")
def client(db_url):
    app = create_app(Settings(database_url=db_url, weights=DEFAULT_WEIGHTS))
    with TestClient(app, raise_server_exceptions=False) as c:   # runs lifespan (pool open/close)
        yield c


@pytest.fixture(scope="module")
def ids(db_url):
    """Look entities up by slug instead of hardcoding IDs."""
    with psycopg.connect(db_url) as conn:
        cands = dict(conn.execute("SELECT slug, id FROM candidates").fetchall())
        jobs = dict(conn.execute("SELECT slug, id FROM jobs").fetchall())
    return {"candidates": cands, "jobs": jobs}
