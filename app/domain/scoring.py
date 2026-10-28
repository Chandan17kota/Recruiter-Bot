"""The single scoring implementation, used by BOTH match directions.

score = wS*S + wE*E + wC*C, each component on a 0..100 scale.
All arithmetic is exact (Fraction). Decimals from the DB convert exactly;
floats are never passed to Fraction.
"""
from dataclasses import replace
from fractions import Fraction

from .explain import build_explanation
from .models import (
    CULTURE_NO_JOB_KEYWORDS,
    CULTURE_SCORED,
    CULTURE_UNKNOWN_TRAITS,
    CandidateProfile,
    CultureComponent,
    ExperienceComponent,
    JobProfile,
    MatchResult,
    SkillComponent,
)

HUNDRED = Fraction(100)


def skill_score(candidate_skills: frozenset[str], required: frozenset[str]) -> Fraction:
    """Share of required skills the candidate has. Extra skills earn nothing."""
    if not required:
        return HUNDRED
    return HUNDRED * len(candidate_skills & required) / len(required)


def experience_score(years, minimum) -> Fraction:
    """100 if no minimum; otherwise proportional, capped at 100."""
    years, minimum = Fraction(years), Fraction(minimum)
    if minimum == 0:
        return HUNDRED
    return HUNDRED * min(years / minimum, Fraction(1))


def culture_status(traits, keywords) -> str:
    if not keywords:
        return CULTURE_NO_JOB_KEYWORDS
    if traits is None:
        return CULTURE_UNKNOWN_TRAITS
    return CULTURE_SCORED


def score_pair(candidate: CandidateProfile, job: JobProfile, weights) -> MatchResult:
    """Score one candidate against one job. `weights` has .skills/.experience/.culture Fractions."""
    req = job.required_skills
    matched_skills = candidate.skills & req
    s = skill_score(candidate.skills, req)
    e = experience_score(candidate.experience_years, job.min_experience_years)

    status = culture_status(candidate.traits, job.culture_keywords)
    if status == CULTURE_SCORED:
        matched_kw = candidate.traits & job.culture_keywords
        c = HUNDRED * len(matched_kw) / len(job.culture_keywords)
        ws, we, wc = weights.skills, weights.experience, weights.culture
        renormalized = False
        culture = CultureComponent(status, c, wc, tuple(sorted(matched_kw)),
                                   tuple(sorted(job.culture_keywords - matched_kw)))
    else:
        # Culture can't be judged: drop it and rescale the other two to sum to 1.
        base = weights.skills + weights.experience
        ws, we, wc = weights.skills / base, weights.experience / base, Fraction(0)
        c = None
        renormalized = weights.culture != 0
        culture = CultureComponent(status, None, wc, (), ())

    total = ws * s + we * e + (wc * c if c is not None else 0)

    skills = SkillComponent(s, ws, tuple(sorted(matched_skills)), tuple(sorted(req - matched_skills)))
    experience = ExperienceComponent(
        e, we, candidate.experience_years, job.min_experience_years,
        Fraction(candidate.experience_years) >= Fraction(job.min_experience_years),
    )
    result = MatchResult(
        candidate=candidate,
        job=job,
        score=total,
        skill_coverage=s,
        matched_required_skill_count=len(matched_skills),
        required_skill_count=len(req),
        skills=skills,
        experience=experience,
        culture=culture,
        renormalized=renormalized,
        explanation="",
    )
    return replace(result, explanation=build_explanation(result))
