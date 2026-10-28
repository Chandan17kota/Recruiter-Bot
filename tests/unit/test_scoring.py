from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import pytest

from app.config import DEFAULT_WEIGHTS, ConfigError, Weights
from app.api.schemas import components_out
from app.domain.models import (
    CULTURE_NO_JOB_KEYWORDS, CULTURE_SCORED, CULTURE_UNKNOWN_TRAITS, CandidateProfile, JobProfile,
)
from app.domain.scoring import experience_score, score_pair, skill_score

W = DEFAULT_WEIGHTS


def cand(**kw):
    base = dict(id=1, name="C", experience_years=Decimal("5"), availability="immediate",
                skills=frozenset({"a", "b"}), traits=frozenset({"x"}), quirk=None)
    base.update(kw)
    return CandidateProfile(**base)


def job(**kw):
    base = dict(id=1, title="J", min_experience_years=Decimal("4"),
                required_skills=frozenset({"a", "b", "c"}), culture_keywords=frozenset({"x", "y"}), tagline=None)
    base.update(kw)
    return JobProfile(**base)


# ---- Skills -------------------------------------------------------------
@pytest.mark.parametrize("have,req,expected", [
    ({"a", "b", "c"}, {"a", "b", "c"}, 100),
    ({"a"}, {"a", "b", "c"}, Fraction(100, 3)),
    (set(), {"a", "b"}, 0),
    ({"a", "b", "z", "q"}, {"a", "b"}, 100),      # extra skills earn nothing extra
    ({"a"}, set(), 100),                           # no required skills -> full marks
])
def test_skill_score(have, req, expected):
    assert skill_score(frozenset(have), frozenset(req)) == expected


def test_no_required_skills_explained():
    r = score_pair(cand(), job(required_skills=frozenset()), W)
    assert r.skills.score == 100
    assert "no required skills" in r.explanation


# ---- Experience ---------------------------------------------------------
@pytest.mark.parametrize("years,minimum,expected", [
    ("8", "3", 100), ("3", "3", 100), ("3", "4", 75), ("0", "4", 0), ("0", "0", 100), ("2.5", "5", 50),
])
def test_experience_score(years, minimum, expected):
    assert experience_score(Decimal(years), Decimal(minimum)) == expected


def test_below_minimum_flag():
    r = score_pair(cand(experience_years=Decimal("3")), job(), W)
    assert r.experience.meets_minimum is False
    assert "below the 4-yr minimum" in r.explanation


# ---- Culture: three distinct cases --------------------------------------
def test_culture_known_empty_scores_zero():
    r = score_pair(cand(traits=frozenset()), job(), W)
    assert r.culture.status == CULTURE_SCORED
    assert r.culture.score == 0
    assert r.culture.weight == Fraction("0.15")
    assert not r.renormalized


def test_culture_unknown_traits_excluded_and_renormalized():
    r = score_pair(cand(traits=None), job(), W)
    assert r.culture.status == CULTURE_UNKNOWN_TRAITS
    assert r.culture.score is None
    assert r.culture.weight == 0
    assert r.culture.matched == r.culture.missing == ()
    assert r.renormalized
    assert "traits are unknown" in r.explanation and "rescaled" in r.explanation
    assert "matches none of" not in r.explanation
    assert components_out(r).culture.missing == []


def test_culture_no_job_keywords_excluded():
    r = score_pair(cand(), job(culture_keywords=frozenset()), W)
    assert r.culture.status == CULTURE_NO_JOB_KEYWORDS
    assert r.culture.score is None
    assert r.culture.matched == r.culture.missing == ()
    assert r.renormalized


def test_renormalized_weights_and_sum():
    r = score_pair(cand(traits=None), job(), W)
    assert r.skills.weight == Fraction(12, 17)          # 0.60 / 0.85
    assert r.experience.weight == Fraction(5, 17)       # 0.25 / 0.85
    assert round(float(r.skills.weight) * 100, 2) == 70.59
    assert round(float(r.experience.weight) * 100, 2) == 29.41
    assert r.skills.weight + r.experience.weight + r.culture.weight == 1


def test_scored_weights_sum_to_one():
    r = score_pair(cand(), job(), W)
    assert r.skills.weight + r.experience.weight + r.culture.weight == 1


def test_documented_limitation_unknown_beats_known_mismatch():
    perfect = dict(skills=frozenset({"a", "b", "c"}), experience_years=Decimal("10"))
    unknown = score_pair(cand(traits=None, **perfect), job(), W)
    mismatch = score_pair(cand(traits=frozenset({"zzz"}), **perfect), job(), W)
    assert unknown.score == 100
    assert mismatch.score == 85


# ---- Exactness ----------------------------------------------------------
def test_full_score_formula_exact():
    # 2/3 skills, 5>=4 yrs, 1/2 culture -> 0.6*66.67 + 25 + 7.5 = 72.5 exactly
    r = score_pair(cand(), job(), W)
    assert r.score == Fraction(145, 2)


def test_equal_scores_compare_equal():
    a = score_pair(cand(id=1, experience_years=Decimal("4")), job(), W)
    b = score_pair(cand(id=2, experience_years=Decimal("4.0")), job(), W)
    assert a.score == b.score


def test_scores_are_fractions_not_floats():
    r = score_pair(cand(), job(), W)
    for v in (r.score, r.skill_coverage, r.experience.score, r.culture.score):
        assert isinstance(v, Fraction)


def test_display_fields_never_change_score():
    a = score_pair(cand(quirk=None), job(tagline=None), W)
    b = score_pair(cand(quirk="weird"), job(tagline="catchy"), W)
    assert a.score == b.score


# ---- Weights config -----------------------------------------------------
def test_weights_from_strings_exact():
    w = Weights.from_strings("0.60", "0.25", "0.15")
    assert w == DEFAULT_WEIGHTS


@pytest.mark.parametrize("s,e,c", [
    ("0.5", "0.25", "0.15"),     # sum != 1
    ("-0.1", "0.95", "0.15"),    # negative
    ("0", "0.85", "0.15"),       # skills must be > 0
    ("0.85", "0", "0.15"),       # experience must be > 0
    ("abc", "0.25", "0.15"),     # not a number
])
def test_invalid_weights_rejected(s, e, c):
    with pytest.raises(ConfigError):
        Weights.from_strings(s, e, c)


def test_zero_culture_weight_allowed():
    w = Weights.from_strings("0.7", "0.3", "0")
    r = score_pair(cand(traits=None), job(), w)
    assert r.renormalized is False   # nothing to rescale
