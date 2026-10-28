"""Domain models. Pure Python, no imports from other layers."""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Optional

# Culture component states
CULTURE_SCORED = "scored"
CULTURE_UNKNOWN_TRAITS = "unknown_candidate_traits"
CULTURE_NO_JOB_KEYWORDS = "no_job_keywords"


@dataclass(frozen=True)
class CandidateProfile:
    id: int
    name: str
    experience_years: Decimal
    availability: Optional[str]          # None = unknown
    skills: frozenset[str]
    traits: Optional[frozenset[str]]     # None = unknown, frozenset() = known to have none
    quirk: Optional[str] = None          # display-only


@dataclass(frozen=True)
class JobProfile:
    id: int
    title: str
    min_experience_years: Decimal
    required_skills: frozenset[str]
    culture_keywords: frozenset[str]
    tagline: Optional[str] = None        # display-only


@dataclass(frozen=True)
class SkillComponent:
    score: Fraction
    weight: Fraction
    matched: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class ExperienceComponent:
    score: Fraction
    weight: Fraction
    candidate_years: Decimal
    required_years: Decimal
    meets_minimum: bool


@dataclass(frozen=True)
class CultureComponent:
    status: str
    score: Optional[Fraction]            # None when not scorable
    weight: Fraction
    matched: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    candidate: CandidateProfile
    job: JobProfile
    score: Fraction                      # full precision, 0..100
    skill_coverage: Fraction             # 0..100, same as skills.score
    matched_required_skill_count: int
    required_skill_count: int
    skills: SkillComponent
    experience: ExperienceComponent
    culture: CultureComponent
    renormalized: bool
    explanation: str
