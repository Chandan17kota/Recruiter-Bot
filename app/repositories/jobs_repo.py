"""Job reads. Static, hand-written SQL with named, server-bound parameters."""
from typing import Optional

from app.domain.models import JobProfile

_SELECT = """
SELECT j.id, j.title, j.min_experience_years, j.tagline,
       ARRAY(SELECT s.name FROM job_required_skills rs
             JOIN skills s ON s.id = rs.skill_id
             WHERE rs.job_id = j.id ORDER BY s.name) AS required_skills,
       ARRAY(SELECT t.name FROM job_culture_keywords ck
             JOIN traits t ON t.id = ck.trait_id
             WHERE ck.job_id = j.id ORDER BY t.name) AS culture_keywords
FROM jobs j
"""

GET_JOB_SQL = _SELECT + "WHERE j.id = %(id)s"
LIST_JOBS_SQL = _SELECT + "ORDER BY j.id"


def _to_profile(row: dict) -> JobProfile:
    return JobProfile(
        id=row["id"],
        title=row["title"],
        min_experience_years=row["min_experience_years"],
        required_skills=frozenset(row["required_skills"]),
        culture_keywords=frozenset(row["culture_keywords"]),
        tagline=row["tagline"],
    )


def get_job(conn, job_id: int) -> Optional[JobProfile]:
    row = conn.execute(GET_JOB_SQL, {"id": job_id}).fetchone()
    return _to_profile(row) if row else None


def list_jobs(conn) -> list[JobProfile]:
    return [_to_profile(r) for r in conn.execute(LIST_JOBS_SQL).fetchall()]
