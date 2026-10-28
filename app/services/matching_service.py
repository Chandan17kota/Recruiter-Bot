"""Orchestrates: load target -> load opposing set -> score -> filter -> rank.

Both directions run the identical pipeline and the same score_pair().
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence

from app.config import Weights
from app.domain.models import CandidateProfile, JobProfile, MatchResult
from app.domain.ranking import filter_and_rank
from app.domain.scoring import score_pair
from app.repositories import candidates_repo, jobs_repo


class NotFoundError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class JobMatches:
    job: JobProfile
    matches: list[MatchResult]


@dataclass(frozen=True)
class CandidateMatches:
    candidate: CandidateProfile
    matches: list[MatchResult]


class MatchingService:
    def __init__(self, pool, weights: Weights):
        self._pool = pool
        self._weights = weights

    def matches_for_job(self, job_id: int, *, min_score: Decimal = Decimal(0),
                        min_skill_coverage: Decimal = Decimal(0),
                        availabilities: Optional[Sequence[str]] = None) -> JobMatches:
        with self._pool.connection() as conn:
            job = jobs_repo.get_job(conn, job_id)
            if job is None:
                raise NotFoundError("JOB_NOT_FOUND", f"Job {job_id} does not exist")
            candidates = candidates_repo.list_candidates(conn, availabilities)
        results = [score_pair(c, job, self._weights) for c in candidates]
        ranked = filter_and_rank(results, by="candidate", min_score=min_score,
                                 min_skill_coverage=min_skill_coverage)
        return JobMatches(job, ranked)

    def matches_for_candidate(self, candidate_id: int, *, min_score: Decimal = Decimal(0),
                              min_skill_coverage: Decimal = Decimal(0)) -> CandidateMatches:
        with self._pool.connection() as conn:
            candidate = candidates_repo.get_candidate(conn, candidate_id)
            if candidate is None:
                raise NotFoundError("CANDIDATE_NOT_FOUND", f"Candidate {candidate_id} does not exist")
            jobs = jobs_repo.list_jobs(conn)
        results = [score_pair(candidate, j, self._weights) for j in jobs]
        ranked = filter_and_rank(results, by="job", min_score=min_score,
                                 min_skill_coverage=min_skill_coverage)
        return CandidateMatches(candidate, ranked)
