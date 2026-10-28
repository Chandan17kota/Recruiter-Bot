"""Candidate reads. Static, hand-written SQL with named, server-bound parameters."""
from typing import Optional, Sequence

from app.domain.models import CandidateProfile

# Skills and traits are gathered with correlated ARRAY() subqueries:
# one row per candidate, no join fan-out, no N+1 queries.
_SELECT = """
SELECT c.id, c.full_name, c.experience_years, c.availability, c.traits_known, c.quirk,
       ARRAY(SELECT s.name FROM candidate_skills cs
             JOIN skills s ON s.id = cs.skill_id
             WHERE cs.candidate_id = c.id ORDER BY s.name) AS skills,
       ARRAY(SELECT t.name FROM candidate_traits ct
             JOIN traits t ON t.id = ct.trait_id
             WHERE ct.candidate_id = c.id ORDER BY t.name) AS traits
FROM candidates c
"""

GET_CANDIDATE_SQL = _SELECT + "WHERE c.id = %(id)s"

LIST_CANDIDATES_SQL = _SELECT + """
WHERE (%(availabilities)s::text[] IS NULL
       OR COALESCE(c.availability, 'unknown') = ANY(%(availabilities)s::text[]))
ORDER BY c.id
"""


def _to_profile(row: dict) -> CandidateProfile:
    return CandidateProfile(
        id=row["id"],
        name=row["full_name"],
        experience_years=row["experience_years"],          # NUMERIC -> Decimal
        availability=row["availability"],
        skills=frozenset(row["skills"]),
        # traits_known = false means "unknown": ignore any trait rows.
        traits=frozenset(row["traits"]) if row["traits_known"] else None,
        quirk=row["quirk"],
    )


def get_candidate(conn, candidate_id: int) -> Optional[CandidateProfile]:
    row = conn.execute(GET_CANDIDATE_SQL, {"id": candidate_id}).fetchone()
    return _to_profile(row) if row else None


def list_candidates(conn, availabilities: Optional[Sequence[str]] = None) -> list[CandidateProfile]:
    params = {"availabilities": list(availabilities) if availabilities else None}
    return [_to_profile(r) for r in conn.execute(LIST_CANDIDATES_SQL, params).fetchall()]
