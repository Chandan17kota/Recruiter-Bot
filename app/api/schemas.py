"""Response models and the one place where exact values become rounded floats."""
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from fractions import Fraction
from typing import Literal, Optional

from pydantic import BaseModel

from app.domain.models import MatchResult


class Availability(str, Enum):
    immediate = "immediate"
    two_weeks = "two_weeks"
    not_looking = "not_looking"
    unknown = "unknown"


AvailabilityValue = Literal["immediate", "two_weeks", "not_looking", "unknown"]
CultureStatus = Literal["scored", "unknown_candidate_traits", "no_job_keywords"]


def round_to(value, places: int) -> float:
    """Exact half-up rounding of a Fraction/Decimal, emitted as a JSON number."""
    if isinstance(value, Fraction):
        value = Decimal(value.numerator) / Decimal(value.denominator)
    q = Decimal(1).scaleb(-places)
    return float(Decimal(value).quantize(q, rounding=ROUND_HALF_UP))


def r2(value) -> float:
    return round_to(value, 2)


def r4(value) -> float:
    return round_to(value, 4)


# ---- Components ---------------------------------------------------------
class SkillsComponentOut(BaseModel):
    score: float
    weight_applied: float
    matched: list[str]
    missing: list[str]


class ExperienceComponentOut(BaseModel):
    score: float
    weight_applied: float
    candidate_years: float
    required_years: float
    meets_minimum: bool


class CultureComponentOut(BaseModel):
    status: CultureStatus
    score: Optional[float]
    weight_applied: float
    matched: list[str]
    missing: list[str]


class ComponentsOut(BaseModel):
    skills: SkillsComponentOut
    experience: ExperienceComponentOut
    culture: CultureComponentOut


def components_out(r: MatchResult) -> ComponentsOut:
    return ComponentsOut(
        skills=SkillsComponentOut(score=r2(r.skills.score), weight_applied=r4(r.skills.weight),
                                  matched=list(r.skills.matched), missing=list(r.skills.missing)),
        experience=ExperienceComponentOut(
            score=r2(r.experience.score), weight_applied=r4(r.experience.weight),
            candidate_years=float(r.experience.candidate_years), required_years=float(r.experience.required_years),
            meets_minimum=r.experience.meets_minimum),
        culture=CultureComponentOut(
            status=r.culture.status, score=None if r.culture.score is None else r2(r.culture.score),
            weight_applied=r4(r.culture.weight), matched=list(r.culture.matched), missing=list(r.culture.missing)),
    )


# ---- Entity summaries ---------------------------------------------------
class JobOut(BaseModel):
    id: int
    title: str
    min_experience_years: float
    required_skills: list[str]
    culture_keywords: list[str]
    tagline: Optional[str]


class JobSummaryOut(BaseModel):
    id: int
    title: str
    min_experience_years: float
    tagline: Optional[str]


class CandidateSummaryOut(BaseModel):
    id: int
    name: str
    experience_years: float
    availability: AvailabilityValue   # "unknown" when NULL in the DB
    quirk: Optional[str]


class CandidateOut(CandidateSummaryOut):
    skills: list[str]
    traits: Optional[list[str]]  # null = unknown


def job_out(j) -> JobOut:
    return JobOut(id=j.id, title=j.title, min_experience_years=float(j.min_experience_years),
                  required_skills=sorted(j.required_skills), culture_keywords=sorted(j.culture_keywords),
                  tagline=j.tagline)


def candidate_summary_out(c) -> CandidateSummaryOut:
    return CandidateSummaryOut(id=c.id, name=c.name, experience_years=float(c.experience_years),
                               availability=c.availability or "unknown", quirk=c.quirk)


def candidate_out(c) -> CandidateOut:
    return CandidateOut(**candidate_summary_out(c).model_dump(), skills=sorted(c.skills),
                        traits=None if c.traits is None else sorted(c.traits))


# ---- Match rows and envelopes -------------------------------------------
class CandidateMatchOut(BaseModel):
    rank: int
    candidate: CandidateSummaryOut
    score: float
    skill_coverage: float
    matched_required_skill_count: int
    required_skill_count: int
    components: ComponentsOut
    explanation: str


class JobMatchOut(BaseModel):
    rank: int
    job: JobSummaryOut
    score: float
    skill_coverage: float
    matched_required_skill_count: int
    required_skill_count: int
    components: ComponentsOut
    explanation: str


def _base(rank: int, r: MatchResult) -> dict:
    return dict(rank=rank, score=r2(r.score), skill_coverage=r2(r.skill_coverage),
                matched_required_skill_count=r.matched_required_skill_count,
                required_skill_count=r.required_skill_count,
                components=components_out(r), explanation=r.explanation)


class JobFiltersOut(BaseModel):
    min_score: float
    min_skill_coverage: float
    availability: Optional[list[AvailabilityValue]]


class CandidateFiltersOut(BaseModel):
    min_score: float
    min_skill_coverage: float


class JobMatchesResponse(BaseModel):
    job: JobOut
    filters_applied: JobFiltersOut
    total: int
    matches: list[CandidateMatchOut]


class CandidateMatchesResponse(BaseModel):
    candidate: CandidateOut
    filters_applied: CandidateFiltersOut
    total: int
    matches: list[JobMatchOut]


def job_matches_response(result, filters: JobFiltersOut) -> JobMatchesResponse:
    rows = [CandidateMatchOut(**_base(i, r), candidate=candidate_summary_out(r.candidate))
            for i, r in enumerate(result.matches, start=1)]
    return JobMatchesResponse(job=job_out(result.job), filters_applied=filters, total=len(rows), matches=rows)


def candidate_matches_response(result, filters: CandidateFiltersOut) -> CandidateMatchesResponse:
    rows = [JobMatchOut(**_base(i, r), job=JobSummaryOut(id=r.job.id, title=r.job.title,
                                                         min_experience_years=float(r.job.min_experience_years),
                                                         tagline=r.job.tagline))
            for i, r in enumerate(result.matches, start=1)]
    return CandidateMatchesResponse(candidate=candidate_out(result.candidate), filters_applied=filters,
                                    total=len(rows), matches=rows)


# ---- Browse lists and health --------------------------------------------
class JobListResponse(BaseModel):
    total: int
    jobs: list[JobOut]


class CandidateListFiltersOut(BaseModel):
    availability: Optional[list[AvailabilityValue]]


class CandidateListResponse(BaseModel):
    filters_applied: CandidateListFiltersOut
    total: int
    candidates: list[CandidateOut]


def job_list_response(jobs) -> JobListResponse:
    rows = [job_out(j) for j in jobs]
    return JobListResponse(total=len(rows), jobs=rows)


def candidate_list_response(candidates, filters: CandidateListFiltersOut) -> CandidateListResponse:
    rows = [candidate_out(c) for c in candidates]
    return CandidateListResponse(filters_applied=filters, total=len(rows), candidates=rows)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[list | dict] = None


class ErrorResponse(BaseModel):
    error: ErrorBody
