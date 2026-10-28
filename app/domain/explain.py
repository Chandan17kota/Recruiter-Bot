"""Human-readable explanation built only from the computed components."""
from decimal import Decimal
from fractions import Fraction

from .models import CULTURE_NO_JOB_KEYWORDS, CULTURE_SCORED, MatchResult


def _yrs(d: Decimal) -> str:
    d = Decimal(d).normalize()
    text = format(d, "f")
    return text


def _pct(f: Fraction) -> str:
    return format(Decimal(f.numerator) / Decimal(f.denominator) * 100, ".2f").rstrip("0").rstrip(".") + "%"


def build_explanation(r: MatchResult) -> str:
    parts = []

    # Skills
    req, got = r.required_skill_count, r.matched_required_skill_count
    if req == 0:
        parts.append("Job lists no required skills, so skills score full marks")
    elif got == req:
        parts.append("Has both required skills" if req == 2 else f"Has all {req} required skills")
    elif got == 0:
        parts.append(f"Has none of the {req} required skills (missing {', '.join(r.skills.missing)})")
    else:
        parts.append(
            f"Has {got} of {req} required skills ({', '.join(r.skills.matched)}; "
            f"missing {', '.join(r.skills.missing)})"
        )

    # Experience
    ex = r.experience
    if ex.required_years == 0:
        parts.append(f"{_yrs(ex.candidate_years)} yrs; job has no experience minimum")
    elif ex.meets_minimum:
        parts.append(f"{_yrs(ex.candidate_years)} yrs meets the {_yrs(ex.required_years)}-yr minimum")
    else:
        parts.append(f"{_yrs(ex.candidate_years)} yrs is below the {_yrs(ex.required_years)}-yr minimum")

    # Culture
    cu = r.culture
    total_kw = len(cu.matched) + len(cu.missing)
    if cu.status == CULTURE_SCORED:
        if cu.matched:
            parts.append(f"matches {len(cu.matched)} of {total_kw} culture keywords ({', '.join(cu.matched)})")
        else:
            parts.append(f"matches none of the {total_kw} culture keywords")
    elif cu.status == CULTURE_NO_JOB_KEYWORDS:
        parts.append("culture not scored (job has no culture keywords)")
    else:
        parts.append("culture not scored (candidate's traits are unknown)")

    text = "; ".join(parts) + "."
    if r.renormalized:
        text += (f" Weights rescaled to skills {_pct(r.skills.weight)} / "
                 f"experience {_pct(r.experience.weight)}.")
    return text
