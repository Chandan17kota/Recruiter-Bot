"""Build domain profiles straight from data/seed.json (no DB), for unit tests."""
import json

from app.domain.models import CandidateProfile, JobProfile
from scripts.init_db import SEED_PATH, validate_seed


def load_profiles():
    seed = validate_seed(json.loads(SEED_PATH.read_text(encoding="utf-8")))
    cands = {
        c["slug"]: CandidateProfile(
            id=i, name=c["name"], experience_years=c["experience_years"],
            availability=c["availability"], skills=frozenset(c["skills"]),
            traits=frozenset(c["traits"]) if c["traits_known"] else None, quirk=c["quirk"],
        )
        for i, c in enumerate(seed["candidates"], start=1)
    }
    jobs = {
        j["slug"]: JobProfile(
            id=i, title=j["title"], min_experience_years=j["min_experience_years"],
            required_skills=frozenset(j["required_skills"]),
            culture_keywords=frozenset(j["culture_keywords"]), tagline=j["tagline"],
        )
        for i, j in enumerate(seed["jobs"], start=1)
    }
    return cands, jobs
