"""Apply db/schema.sql and load data/seed.json in ONE transaction.

Usage:  python -m scripts.init_db            (uses DATABASE_URL)
        python -m scripts.init_db --test     (uses TEST_DATABASE_URL)

Idempotent: entities are upserted on slug, vocabularies on name, and each
entity's link rows are replaced, so re-running leaves the same data.
A validation failure or DB error rolls everything back.
"""
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg

from app.config import load_settings
from app.domain.normalize import normalize_term

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "data" / "seed.json"

AVAILABILITIES = {"immediate", "two_weeks", "not_looking", None}

# Values transcribed independently from the assignment PDF. They guard the
# fields most likely to be mistyped in seed.json: (name, years, availability)
# per candidate and (title, minimum years) per job.
PDF_CANDIDATES = {
    "sherlock-h": ("Sherlock H.", "8", "immediate"),
    "hermione-g": ("Hermione G.", "4", "two_weeks"),
    "tony-s": ("Tony S.", "12", "not_looking"),
    "leslie-k": ("Leslie K.", "6", "immediate"),
    "ron-s": ("Ron S.", "15", "not_looking"),
    "rick-s": ("Rick S.", "20", "immediate"),
    "elle-w": ("Elle W.", "3", "immediate"),
    "macgyver": ("MacGyver", "10", "two_weeks"),
    "sheldon-c": ("Sheldon C.", "9", "immediate"),
    "katniss-e": ("Katniss E.", "5", "immediate"),
    "michael-s": ("Michael S.", "11", "not_looking"),
    "olivia-p": ("Olivia P.", "13", "two_weeks"),
    "ted-l": ("Ted L.", "7", "immediate"),
    "miranda-p": ("Miranda P.", "18", "not_looking"),
    "dwight-s": ("Dwight S.", "9", "immediate"),
}
PDF_JOBS = {
    "backend-detective": ("Backend Detective", "3"),
    "rapid-prototyping-engineer": ("Rapid Prototyping Engineer", "2"),
    "developer-relations-lead": ("Developer Relations Lead", "2"),
    "engineering-manager-chaos-team": ("Engineering Manager, Chaos Team", "5"),
    "incident-commander": ("Incident Commander", "4"),
    "sales-engineer": ("Sales Engineer", "3"),
}


class SeedError(ValueError):
    pass


def _clean_terms(owner: str, field: str, terms) -> list[str]:
    if not isinstance(terms, list):
        raise SeedError(f"{owner}: '{field}' must be a list")
    out: list[str] = []
    for raw in terms:
        if not isinstance(raw, str):
            raise SeedError(f"{owner}: '{field}' contains a non-string value {raw!r}")
        term = normalize_term(raw)
        if not term:
            raise SeedError(f"{owner}: '{field}' contains an empty term")
        if term in out:
            raise SeedError(f"{owner}: '{field}' lists {term!r} more than once")
        out.append(term)
    return out


def _years(owner: str, value) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SeedError(f"{owner}: experience {value!r} is not a number") from exc
    if not d.is_finite() or d < 0 or d > 60:
        raise SeedError(f"{owner}: experience {value!r} must be between 0 and 60")
    return d


def _require_fields(record: dict, fields: set[str], owner: str) -> None:
    missing = fields - record.keys()
    extra = record.keys() - fields
    if missing:
        raise SeedError(f"{owner}: missing required field(s) {sorted(missing)}")
    if extra:
        raise SeedError(f"{owner}: unexpected field(s) {sorted(extra)}")


def _check_against_pdf(candidates: list[dict], jobs: list[dict]) -> None:
    if {c["slug"] for c in candidates} != PDF_CANDIDATES.keys():
        raise SeedError("candidate slugs do not match the assignment PDF")
    if {j["slug"] for j in jobs} != PDF_JOBS.keys():
        raise SeedError("job slugs do not match the assignment PDF")
    for c in candidates:
        name, years, availability = PDF_CANDIDATES[c["slug"]]
        if (c["name"], c["experience_years"], c["availability"]) != (name, Decimal(years), availability):
            raise SeedError(f"candidate {c['slug']!r}: name, experience, or availability differs from the PDF")
    for j in jobs:
        title, years = PDF_JOBS[j["slug"]]
        if (j["title"], j["min_experience_years"]) != (title, Decimal(years)):
            raise SeedError(f"job {j['slug']!r}: title or minimum experience differs from the PDF")


def validate_seed(data: dict) -> dict:
    """Return the normalized assignment seed, or raise SeedError."""
    if not isinstance(data, dict) or set(data) != {"candidates", "jobs"}:
        raise SeedError("seed must be an object containing only 'candidates' and 'jobs'")
    if not isinstance(data["candidates"], list) or not isinstance(data["jobs"], list):
        raise SeedError("'candidates' and 'jobs' must be lists")
    if len(data["candidates"]) != 15 or len(data["jobs"]) != 6:
        raise SeedError("assignment seed must contain exactly 15 candidates and 6 jobs")

    candidates, slugs = [], set()
    for c in data["candidates"]:
        if not isinstance(c, dict):
            raise SeedError("each candidate must be an object")
        owner = f"candidate {c.get('slug') or c.get('name')!r}"
        _require_fields(c, {"slug", "name", "experience_years", "availability", "skills", "traits", "quirk"}, owner)
        if not isinstance(c["slug"], str):
            raise SeedError(f"{owner}: slug must be a string")
        slug = normalize_term(c["slug"])
        if not slug or slug != c["slug"] or slug in slugs:
            raise SeedError(f"{owner}: slug must be normalized, non-empty, and unique")
        slugs.add(slug)
        if not isinstance(c["name"], str) or not c["name"].strip():
            raise SeedError(f"{owner}: name is required")
        name = c["name"].strip()
        availability = c["availability"]
        if availability is not None and not isinstance(availability, str):
            raise SeedError(f"{owner}: availability must be a string or null")
        if availability not in AVAILABILITIES:
            raise SeedError(f"{owner}: availability {availability!r} not one of immediate/two_weeks/not_looking/null")
        if c["quirk"] is not None and not isinstance(c["quirk"], str):
            raise SeedError(f"{owner}: quirk must be a string or null")
        traits = c["traits"]  # None means "unknown", [] means "known to have none"
        candidates.append({
            "slug": slug,
            "name": name,
            "experience_years": _years(owner, c["experience_years"]),
            "availability": availability,
            "skills": _clean_terms(owner, "skills", c["skills"]),
            "traits_known": traits is not None,
            "traits": [] if traits is None else _clean_terms(owner, "traits", traits),
            "quirk": c["quirk"],
        })

    jobs, slugs = [], set()
    for j in data["jobs"]:
        if not isinstance(j, dict):
            raise SeedError("each job must be an object")
        owner = f"job {j.get('slug') or j.get('title')!r}"
        _require_fields(j, {"slug", "title", "min_experience_years", "required_skills",
                            "culture_keywords", "tagline"}, owner)
        if not isinstance(j["slug"], str):
            raise SeedError(f"{owner}: slug must be a string")
        slug = normalize_term(j["slug"])
        if not slug or slug != j["slug"] or slug in slugs:
            raise SeedError(f"{owner}: slug must be normalized, non-empty, and unique")
        slugs.add(slug)
        if not isinstance(j["title"], str) or not j["title"].strip():
            raise SeedError(f"{owner}: title is required")
        if j["tagline"] is not None and not isinstance(j["tagline"], str):
            raise SeedError(f"{owner}: tagline must be a string or null")
        jobs.append({
            "slug": slug,
            "title": j["title"].strip(),
            "min_experience_years": _years(owner, j["min_experience_years"]),
            "required_skills": _clean_terms(owner, "required_skills", j["required_skills"]),
            "culture_keywords": _clean_terms(owner, "culture_keywords", j["culture_keywords"]),
            "tagline": j["tagline"],
        })

    # Typo guard: every required skill must be held by somebody. Not applied to
    # culture keywords, several of which intentionally match no candidate.
    held = {s for c in candidates for s in c["skills"]}
    for j in jobs:
        orphans = [s for s in j["required_skills"] if s not in held]
        if orphans:
            raise SeedError(f"job {j['slug']!r}: required skill(s) {orphans} held by no candidate (typo?)")

    _check_against_pdf(candidates, jobs)

    return {"candidates": candidates, "jobs": jobs}


def _vocab_id(cur, table: str, name: str) -> int:
    # table is one of two hard-coded literals below, never user input.
    sql = {
        "skills": "INSERT INTO skills (name) VALUES (%(n)s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        "traits": "INSERT INTO traits (name) VALUES (%(n)s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
    }[table]
    cur.execute(sql, {"n": name})
    return cur.fetchone()[0]


def load(conn: psycopg.Connection, seed: dict) -> None:
    """Load an already-validated seed. Caller owns the transaction."""
    with conn.cursor() as cur:
        for c in seed["candidates"]:
            cur.execute(
                """
                INSERT INTO candidates (slug, full_name, experience_years, availability, traits_known, quirk)
                VALUES (%(slug)s, %(name)s, %(experience_years)s, %(availability)s, %(traits_known)s, %(quirk)s)
                ON CONFLICT (slug) DO UPDATE SET
                  full_name = EXCLUDED.full_name,
                  experience_years = EXCLUDED.experience_years,
                  availability = EXCLUDED.availability,
                  traits_known = EXCLUDED.traits_known,
                  quirk = EXCLUDED.quirk
                RETURNING id
                """,
                c,
            )
            cid = cur.fetchone()[0]
            cur.execute("DELETE FROM candidate_skills WHERE candidate_id = %(id)s", {"id": cid})
            cur.execute("DELETE FROM candidate_traits WHERE candidate_id = %(id)s", {"id": cid})
            for s in c["skills"]:
                cur.execute(
                    "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (%(c)s, %(s)s) ON CONFLICT DO NOTHING",
                    {"c": cid, "s": _vocab_id(cur, "skills", s)},
                )
            for t in c["traits"]:
                cur.execute(
                    "INSERT INTO candidate_traits (candidate_id, trait_id) VALUES (%(c)s, %(t)s) ON CONFLICT DO NOTHING",
                    {"c": cid, "t": _vocab_id(cur, "traits", t)},
                )

        for j in seed["jobs"]:
            cur.execute(
                """
                INSERT INTO jobs (slug, title, min_experience_years, tagline)
                VALUES (%(slug)s, %(title)s, %(min_experience_years)s, %(tagline)s)
                ON CONFLICT (slug) DO UPDATE SET
                  title = EXCLUDED.title,
                  min_experience_years = EXCLUDED.min_experience_years,
                  tagline = EXCLUDED.tagline
                RETURNING id
                """,
                j,
            )
            jid = cur.fetchone()[0]
            cur.execute("DELETE FROM job_required_skills WHERE job_id = %(id)s", {"id": jid})
            cur.execute("DELETE FROM job_culture_keywords WHERE job_id = %(id)s", {"id": jid})
            for s in j["required_skills"]:
                cur.execute(
                    "INSERT INTO job_required_skills (job_id, skill_id) VALUES (%(j)s, %(s)s) ON CONFLICT DO NOTHING",
                    {"j": jid, "s": _vocab_id(cur, "skills", s)},
                )
            for t in j["culture_keywords"]:
                cur.execute(
                    "INSERT INTO job_culture_keywords (job_id, trait_id) VALUES (%(j)s, %(t)s) ON CONFLICT DO NOTHING",
                    {"j": jid, "t": _vocab_id(cur, "traits", t)},
                )


def init_db(database_url: str, seed_path: Path = SEED_PATH) -> dict:
    try:
        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedError(f"cannot read seed {seed_path}: {exc}") from exc
    seed = validate_seed(seed_data)
    with psycopg.connect(database_url) as conn:  # commits on success, rolls back on error
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        load(conn, seed)
    return {"candidates": len(seed["candidates"]), "jobs": len(seed["jobs"])}


def main(argv: list[str]) -> int:
    var = "TEST_DATABASE_URL" if "--test" in argv else "DATABASE_URL"
    try:
        settings = load_settings(var)
        counts = init_db(settings.database_url)
    except SeedError as exc:
        print(f"Seed validation failed: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(f"Database error, nothing was loaded: {exc}", file=sys.stderr)
        return 1
    print(f"Schema applied; loaded {counts['candidates']} candidates and {counts['jobs']} jobs.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
