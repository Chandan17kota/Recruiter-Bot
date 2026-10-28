import copy
import json
from decimal import Decimal
from fractions import Fraction

import pytest

from app.config import DEFAULT_WEIGHTS as W
from app.domain.normalize import normalize_term
from app.domain.ranking import filter_and_rank
from app.domain.scoring import score_pair
from scripts.init_db import SEED_PATH, SeedError, validate_seed
from tests.seed_profiles import load_profiles

CANDS, JOBS = load_profiles()


# ---- Normalization ------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Java", "JavaScript"), ("C", "C++"), ("C++", "C#"), ("C", "C#"),
    ("Node.js", "NodeJS"), ("public-speaking", "public speaking"),
])
def test_distinct_terms_stay_distinct(a, b):
    assert normalize_term(a) != normalize_term(b)


@pytest.mark.parametrize("raw,expected", [
    (" Python ", "python"), (".NET", ".net"), ("machine   learning", "machine learning"),
    ("C++", "c++"), ("\tRust\n", "rust"),
])
def test_normalization(raw, expected):
    assert normalize_term(raw) == expected


# ---- Golden fixtures against the real seed ------------------------------
def rank_job(slug, **filters):
    j = JOBS[slug]
    return filter_and_rank([score_pair(c, j, W) for c in CANDS.values()], by="candidate", **filters)


def test_sherlock_backend_detective():
    top = rank_job("backend-detective")[0]
    assert top.candidate.name == "Sherlock H." and top.score == Fraction("92.5")


def test_olivia_incident_commander():
    top = rank_job("incident-commander")[0]
    assert top.candidate.name == "Olivia P." and top.score == Fraction("92.5")


def test_rick_before_macgyver_on_tie():
    ranked = rank_job("rapid-prototyping-engineer")
    names = [r.candidate.name for r in ranked]
    rick, mac = ranked[names.index("Rick S.")], ranked[names.index("MacGyver")]
    assert rick.score == mac.score == 85
    assert names.index("Rick S.") < names.index("MacGyver")


def test_dwight_before_ron_on_tie():
    ranked = rank_job("incident-commander")
    names = [r.candidate.name for r in ranked]
    assert ranked[names.index("Dwight S.")].score == ranked[names.index("Ron S.")].score == 45
    assert names.index("Dwight S.") < names.index("Ron S.")


def test_elle_incident_commander():
    elle = next(r for r in rank_job("incident-commander") if r.candidate.name == "Elle W.")
    assert elle.score == Fraction("18.75")


def test_thirteen_at_25_for_backend_detective():
    tail = [r for r in rank_job("backend-detective") if r.score == 25]
    assert len(tail) == 13
    rank_av = {"immediate": 0, "two_weeks": 1, None: 2, "not_looking": 3}
    keys = [(rank_av[r.candidate.availability], r.candidate.id) for r in tail]
    assert keys == sorted(keys)


def test_culture_ceiling_is_50_on_seed():
    best = max(score_pair(c, j, W).culture.score for c in CANDS.values() for j in JOBS.values())
    assert best == 50


# ---- Ranking ------------------------------------------------------------
def test_ranking_deterministic():
    a = [r.candidate.id for r in rank_job("sales-engineer")]
    b = [r.candidate.id for r in rank_job("sales-engineer")]
    assert a == b


def test_exact_tie_broken_by_availability():
    from app.domain.models import CandidateProfile, JobProfile
    j = JobProfile(1, "J", Decimal("10"), frozenset({"a", "b"}), frozenset(), None)
    a = CandidateProfile(1, "A", Decimal("0"), "not_looking", frozenset({"a"}), frozenset(), None)
    b = CandidateProfile(2, "B", Decimal("0"), "immediate", frozenset({"a"}), frozenset(), None)
    ranked = filter_and_rank([score_pair(a, j, W), score_pair(b, j, W)], by="candidate")
    assert [r.candidate.id for r in ranked] == [2, 1]


def _tweak(r, **kw):
    from dataclasses import replace
    cand_kw = {k: kw.pop(k) for k in ("availability",) if k in kw}
    exp = kw.pop("experience_score", None)
    if exp is not None:
        kw["experience"] = replace(r.experience, score=Fraction(exp))
    if cand_kw:
        kw["candidate"] = replace(r.candidate, **cand_kw)
    return replace(r, **kw)


def test_tiebreak_levels_in_isolation():
    from app.domain.ranking import sort_key
    s = score_pair(CANDS["sherlock-h"], JOBS["backend-detective"], W)
    base = sort_key(s, 1)
    assert sort_key(_tweak(s, score=s.score - 1), 1) > base                         # 1. score
    assert sort_key(_tweak(s, skill_coverage=Fraction(50)), 1) > base               # 2. skill coverage
    assert sort_key(_tweak(s, experience_score=50), 1) > base                       # 3. experience
    assert sort_key(_tweak(s, availability="two_weeks"), 1) > base                  # 4. availability
    assert sort_key(_tweak(s, availability=None), 1) < sort_key(_tweak(s, availability="not_looking"), 1)
    assert sort_key(s, 2) > base                                                    # 5. id
    # A lower score can never be lifted by better tie-breakers
    worse = _tweak(s, score=s.score - Fraction(1, 1000), availability="immediate")
    better = _tweak(s, availability="not_looking", skill_coverage=Fraction(0))
    assert sort_key(better, 9) < sort_key(worse, 1)


def test_filters_use_unrounded_score():
    ranked = rank_job("backend-detective", min_score=Decimal("45"))
    # Sheldon scores exactly 45 (1/3 skills) -> kept with >=
    assert any(r.candidate.name == "Sheldon C." for r in ranked)
    ranked = rank_job("backend-detective", min_score=Decimal("45.01"))
    assert all(r.candidate.name != "Sheldon C." for r in ranked)


def test_min_skill_coverage():
    assert len(rank_job("backend-detective")) == 15
    assert [r.candidate.name for r in rank_job("backend-detective", min_skill_coverage=Decimal("100"))] == ["Sherlock H."]
    assert len(rank_job("backend-detective", min_skill_coverage=Decimal("1"))) == 2


# ---- Seed validation ----------------------------------------------------
RAW = json.loads(SEED_PATH.read_text(encoding="utf-8"))

PDF = {  # name: (years, availability) transcribed from the brief
    "Sherlock H.": ("8", "immediate"), "Hermione G.": ("4", "two_weeks"), "Tony S.": ("12", "not_looking"),
    "Leslie K.": ("6", "immediate"), "Ron S.": ("15", "not_looking"), "Rick S.": ("20", "immediate"),
    "Elle W.": ("3", "immediate"), "MacGyver": ("10", "two_weeks"), "Sheldon C.": ("9", "immediate"),
    "Katniss E.": ("5", "immediate"), "Michael S.": ("11", "not_looking"), "Olivia P.": ("13", "two_weeks"),
    "Ted L.": ("7", "immediate"), "Miranda P.": ("18", "not_looking"), "Dwight S.": ("9", "immediate"),
}


def test_seed_matches_pdf():
    seed = validate_seed(RAW)
    assert len(seed["candidates"]) == 15 and len(seed["jobs"]) == 6
    got = {c["name"]: (str(c["experience_years"]), c["availability"]) for c in seed["candidates"]}
    assert got == PDF


def test_stakeholder_management_regression():
    seed = validate_seed(RAW)
    holders = {c["name"] for c in seed["candidates"] if "stakeholder-management" in c["skills"]}
    assert holders == {"Leslie K.", "Miranda P."}


def test_seed_rejects_duplicate_term():
    bad = copy.deepcopy(RAW)
    bad["candidates"][0]["skills"].append("  Deduction ")
    with pytest.raises(SeedError, match="more than once"):
        validate_seed(bad)


def test_seed_rejects_empty_term():
    bad = copy.deepcopy(RAW)
    bad["candidates"][0]["skills"].append("   ")
    with pytest.raises(SeedError, match="empty"):
        validate_seed(bad)


def test_seed_rejects_orphan_required_skill():
    bad = copy.deepcopy(RAW)
    bad["jobs"][0]["required_skills"].append("forensic")   # typo
    with pytest.raises(SeedError, match="held by no candidate"):
        validate_seed(bad)


@pytest.mark.parametrize("collection", ["candidates", "jobs"])
def test_seed_rejects_wrong_entity_counts(collection):
    bad = copy.deepcopy(RAW)
    bad[collection].pop()
    with pytest.raises(SeedError, match=f"exactly 15 candidates and 6 jobs"):
        validate_seed(bad)


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("candidates", "experience_years", "9"),
        ("candidates", "availability", "not_looking"),
        ("candidates", "name", "Sherlock Holmes"),
        ("jobs", "min_experience_years", "6"),
        ("jobs", "title", "Different title"),
    ],
)
def test_seed_rejects_values_different_from_assignment(collection, field, value):
    bad = copy.deepcopy(RAW)
    bad[collection][0][field] = value
    with pytest.raises(SeedError, match="differs from the PDF"):
        validate_seed(bad)


@pytest.mark.parametrize(
    ("collection", "field"),
    [("candidates", "quirk"), ("candidates", "skills"), ("jobs", "tagline"),
     ("jobs", "culture_keywords")],
)
def test_seed_rejects_missing_required_fields(collection, field):
    bad = copy.deepcopy(RAW)
    del bad[collection][0][field]
    with pytest.raises(SeedError, match="missing required field"):
        validate_seed(bad)


def test_seed_rejects_duplicate_entity_slugs():
    bad = copy.deepcopy(RAW)
    bad["candidates"][1]["slug"] = bad["candidates"][0]["slug"]
    with pytest.raises(SeedError, match="unique"):
        validate_seed(bad)


def test_seed_rejects_malformed_availability_enum():
    bad = copy.deepcopy(RAW)
    bad["candidates"][0]["availability"] = ["immediate"]
    with pytest.raises(SeedError, match="availability"):
        validate_seed(bad)


def test_seed_rejects_malformed_records():
    bad_record = copy.deepcopy(RAW)
    bad_record["candidates"][0] = []
    with pytest.raises(SeedError, match="candidate must be an object"):
        validate_seed(bad_record)


def test_seed_rejects_unknown_slug():
    bad = copy.deepcopy(RAW)
    bad["candidates"][0]["slug"] = "sherlock-holmes"
    with pytest.raises(SeedError, match="slugs do not match"):
        validate_seed(bad)


def test_seed_validation_happens_before_database_connection(tmp_path, monkeypatch):
    from scripts import init_db as loader

    bad = copy.deepcopy(RAW)
    bad["candidates"][0]["experience_years"] = "999"
    path = tmp_path / "invalid-seed.json"
    path.write_text(json.dumps(bad), encoding="utf-8")

    def unexpected_connect(*args, **kwargs):
        pytest.fail("database connection must not be opened before seed validation")

    monkeypatch.setattr(loader.psycopg, "connect", unexpected_connect)
    with pytest.raises(SeedError):
        loader.init_db("postgresql://invalid", path)


def test_seed_allows_symbolic_terms():
    ok = copy.deepcopy(RAW)
    ok["candidates"][0]["skills"] += ["C++", "C#", ".NET", "Node.js"]
    seed = validate_seed(ok)
    assert {"c++", "c#", ".net", "node.js"} <= set(seed["candidates"][0]["skills"])
