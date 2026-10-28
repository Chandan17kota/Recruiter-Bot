"""Ranking and filtering, identical for both directions.

Sort key: highest score, then highest skill coverage, then highest experience
score, then availability (only ever breaks exact ties), then lowest ID.
Filters and sorting use the unrounded scores.
"""
from decimal import Decimal
from fractions import Fraction
from typing import Iterable

from .models import MatchResult

AVAILABILITY_RANK = {"immediate": 0, "two_weeks": 1, None: 2, "not_looking": 3}


def sort_key(r: MatchResult, opposing_id: int):
    return (
        -r.score,
        -r.skill_coverage,
        -r.experience.score,
        AVAILABILITY_RANK.get(r.candidate.availability, 2),
        opposing_id,
    )


def filter_and_rank(results: Iterable[MatchResult], *, by: str,
                    min_score: Decimal = Decimal(0),
                    min_skill_coverage: Decimal = Decimal(0)) -> list[MatchResult]:
    """`by` is 'candidate' (ranking candidates for a job) or 'job' (jobs for a candidate)."""
    ms, msc = Fraction(min_score), Fraction(min_skill_coverage)
    kept = [r for r in results if r.score >= ms and r.skill_coverage >= msc]
    if by == "candidate":
        return sorted(kept, key=lambda r: sort_key(r, r.candidate.id))
    if by == "job":
        return sorted(kept, key=lambda r: sort_key(r, r.job.id))
    raise ValueError(f"by must be 'candidate' or 'job', got {by!r}")
