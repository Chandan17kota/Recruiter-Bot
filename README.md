# Recruiter Bot

A backend service that stores candidates and job openings in PostgreSQL and ranks matches in **both directions**. Every score comes with an explanation. The SQL is all hand-written: no ORM and no query builder.

- `GET /jobs/{id}/matches`: ranked candidates for a job
- `GET /candidates/{id}/matches`: ranked jobs for a candidate
- Each match includes a score, skill coverage, a per-component breakdown with the weights actually applied, and a one-line reason.
- Optional filters: `min_score`, `min_skill_coverage`, and a repeatable `availability` (job endpoint only).
- Every error uses the same JSON envelope.
- The repo also contains `sql_detective.sql` (Part 2).
- **v2:** a read-only React frontend in `frontend/`, plus `GET /jobs`, `GET /candidates` and `GET /health` to support it (see [Frontend](#frontend-v2)). The backend-only submission is tagged `v1.0.0`.

**Stack:** Python 3.11+, FastAPI, PostgreSQL 14+, psycopg 3 with psycopg_pool, pytest.

## Assignment scope and architecture

The assignment deliverables are the PostgreSQL-backed candidate/job matching API in
both directions, explainable deterministic scores, the transcribed sample data, tests, and
the five SQL Detective queries. The implementation uses five layers:

| Layer | Responsibility |
|---|---|
| API | FastAPI routes, request validation, response schemas, and error envelopes |
| Service | Loads the target/opposing records and coordinates scoring, filtering, and ranking |
| Domain | Pure-Python profiles, normalization, exact scoring, ranking, and explanations |
| Repository | Static, parameterized SQL to read records and their vocabulary |
| Database | PostgreSQL tables, constraints, indexes, and transactional seed data |

Both routes share the same scoring function. The API does not issue SQL, and the domain
does not depend on FastAPI or PostgreSQL.

---

## Setup and run

**Prerequisites:** Python 3.11+ and a running PostgreSQL 14+.

| OS | Install Postgres |
|---|---|
| macOS | `brew install postgresql@16 && brew services start postgresql@16` |
| Ubuntu/Debian | `sudo apt install postgresql && sudo systemctl start postgresql` |
| Windows | EDB installer from postgresql.org |

A hosted Postgres works too. Only the connection URL matters.

Create three local databases (the integration tests **drop and recreate tables** in
`recruiter_bot_test`; never point `TEST_DATABASE_URL` at data you need):

```text
createdb recruiter_bot
createdb recruiter_bot_test
createdb hiring_ops
```

Copy `.env.example` to `.env` and set `DATABASE_URL` and `TEST_DATABASE_URL` to
your local connection URLs. The checked-in example uses sample local connection URLs
and contains no real credentials.

**Windows PowerShell** (run from the project directory; PostgreSQL command-line tools
must be on `PATH`):

```powershell
Copy-Item .env.example .env
# Edit .env and set the two local database URLs.
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.init_db
python -m uvicorn app.main:app --reload
python -m pytest -q
```

If PowerShell blocks virtual-environment activation, use the Python executable directly:
`.venv\Scripts\python.exe -m pip install -r requirements.txt`, then replace `python`
with `.venv\Scripts\python.exe` in the remaining commands.

**macOS/Linux:**

```bash
cp .env.example .env
# Edit .env and set the two local database URLs.
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db
python -m uvicorn app.main:app --reload
python -m pytest -q
```

`python -m scripts.init_db` applies the schema and loads the transcribed seed in one
transaction. It is safe to rerun. The API docs are at
`http://localhost:8000/docs`.

Integration tests wipe and reseed `TEST_DATABASE_URL`, so never point it at real data.
If the test database is unavailable, those tests are reported as skipped.

### SQL Detective (Part 2)

The dataset loads unchanged into its own database:

```bash
psql hiring_ops -f sql/detective_data.sql
psql hiring_ops -f sql_detective.sql
```

The five queries return open postings with their recruiter (Q1); distinct applicants
reaching a Final interview per posting, including zero-count postings (Q2); people
associated with multiple distinct postings (Q3); recruiter Final-stage pass rates for
recruiters with at least three Final interviews (Q4); and each department's top
recruiter(s) by passed Final interviews (Q5). There is no applications table, so Q3
infers posting associations from interviews and groups people by normalized email.
Null and blank emails are excluded because they cannot reliably identify a person.
Repeated interviews for the same posting count once in Q3.

---

## API examples

```bash
curl localhost:8000/jobs/1/matches
curl "localhost:8000/jobs/1/matches?min_skill_coverage=50&availability=immediate"
curl "localhost:8000/jobs/6/matches?availability=immediate&availability=two_weeks&min_score=40"
curl localhost:8000/candidates/1/matches
curl -i localhost:8000/jobs/999/matches          # 404 JOB_NOT_FOUND
curl localhost:8000/jobs                         # v2: all jobs
curl "localhost:8000/candidates?availability=immediate"   # v2: candidates, optional availability filter
curl -i localhost:8000/health                    # v2: 200 ok, or 503 when the database is down
curl -i "localhost:8000/jobs/1/matches?min_score=150"   # 422 VALIDATION_ERROR
```

Abridged response for `GET /jobs/1/matches`:

```json
{
  "job": {"id": 1, "title": "Backend Detective", "min_experience_years": 3.0,
          "required_skills": ["deduction", "forensics", "pattern-recognition"],
          "culture_keywords": ["analytical", "autonomous"],
          "tagline": "We have a bug. We have no leads. We have you."},
  "filters_applied": {"min_score": 0.0, "min_skill_coverage": 0.0, "availability": null},
  "total": 15,
  "matches": [{
    "rank": 1,
    "candidate": {"id": 1, "name": "Sherlock H.", "experience_years": 8.0,
                  "availability": "immediate", "quirk": "Solves problems by eliminating the impossible; ..."},
    "score": 92.5,
    "skill_coverage": 100.0,
    "matched_required_skill_count": 3,
    "required_skill_count": 3,
    "components": {
      "skills":     {"score": 100.0, "weight_applied": 0.6, "matched": ["deduction", "forensics", "pattern-recognition"], "missing": []},
      "experience": {"score": 100.0, "weight_applied": 0.25, "candidate_years": 8.0, "required_years": 3.0, "meets_minimum": true},
      "culture":    {"status": "scored", "score": 50.0, "weight_applied": 0.15, "matched": ["analytical"], "missing": ["autonomous"]}
    },
    "explanation": "Has all 3 required skills; 8 yrs meets the 3-yr minimum; matches 1 of 2 culture keywords (analytical)."
  }]
}
```

`GET /candidates/{id}/matches` uses the same shape. It has a `candidate` block at the top, and each match carries a `job` summary instead of a candidate.

An abridged `GET /candidates/1/matches` response starts with a candidate block and
contains ranked job summaries:

```json
{
  "candidate": {
    "id": 1, "name": "Sherlock H.", "experience_years": 8.0,
    "availability": "immediate", "quirk": "display-only text",
    "skills": ["deduction", "forensics", "pattern-recognition"],
    "traits": ["analytical", "blunt"]
  },
  "filters_applied": {"min_score": 0.0, "min_skill_coverage": 0.0},
  "total": 6,
  "matches": [{
    "rank": 1,
    "job": {
      "id": 1, "title": "Backend Detective",
      "min_experience_years": 3.0, "tagline": "display-only text"
    },
    "score": 92.5,
    "skill_coverage": 100.0,
    "matched_required_skill_count": 3,
    "required_skill_count": 3,
    "components": {
      "skills": {
        "score": 100.0, "weight_applied": 0.6,
        "matched": ["deduction", "forensics", "pattern-recognition"], "missing": []
      },
      "experience": {
        "score": 100.0, "weight_applied": 0.25,
        "candidate_years": 8.0, "required_years": 3.0, "meets_minimum": true
      },
      "culture": {
        "status": "scored", "score": 50.0, "weight_applied": 0.15,
        "matched": ["analytical"], "missing": ["autonomous"]
      }
    },
    "explanation": "Has all 3 required skills; 8 yrs meets the 3-yr minimum; matches 1 of 2 culture keywords (analytical)."
  }]
}
```

**Query parameters**

| Param | Endpoints | Rules |
|---|---|---|
| `min_score` | both | decimal 0–100, default 0 |
| `min_skill_coverage` | both | decimal 0–100, default 0 |
| `availability` | jobs only | repeatable; `immediate`, `two_weeks`, `not_looking`, `unknown` |

**Errors.** Every error has the form `{"error": {"code", "message", "details"}}`.

| Situation | Status | Code |
|---|---|---|
| Bad path or query value (`/jobs/abc`, `min_score=150`, bad enum, NaN) | 422 | `VALIDATION_ERROR` (`details` lists the fields) |
| Unknown job or candidate | 404 | `JOB_NOT_FOUND` / `CANDIDATE_NOT_FOUND` |
| Unknown route or wrong method | 404 / 405 | `ROUTE_NOT_FOUND` / `METHOD_NOT_ALLOWED` |
| Database unreachable, pool timeout, or statement timeout | 503 | `DATABASE_UNAVAILABLE` |
| Any other error | 500 | `INTERNAL_ERROR` (generic message; details only in server logs) |

---

## Scoring

```
score = 0.60·S + 0.25·E + 0.15·C        (each component 0–100, score 0–100)
```

| Component | Rule |
|---|---|
| **Skills (S)** | matched required skills ÷ required skills × 100. Extra skills earn nothing. A job with no required skills gives 100, and the explanation says so. |
| **Experience (E)** | 100 if the job's minimum is 0, otherwise 100 × min(years ÷ minimum, 1). |
| **Culture (C)** | matched culture keywords ÷ job's keywords × 100, comparing the candidate's traits to the job's culture keywords. |

**Culture has three states**, reported in `components.culture.status`:

| Situation | `status` | Effect |
|---|---|---|
| Job has keywords and candidate's traits are known | `scored` | Normal score. Known-but-empty traits score 0. |
| Candidate's traits are unknown | `unknown_candidate_traits` | Culture dropped, weights renormalized |
| Job has no culture keywords | `no_job_keywords` | Culture dropped, weights renormalized |

Renormalization divides the remaining weights by their sum. Dropping culture therefore gives skills 0.60/0.85 = **70.59%** and experience **29.41%**. Every match reports its effective `weight_applied`, and the explanation names the rescaled weights.

**Ranking** (identical in both directions): highest score → highest skill coverage → highest experience score → availability (`immediate` < `two_weeks` < unknown < `not_looking`) → lowest ID. Ranks run 1..n over the filtered list, and `total` = n. An empty result is `200` with `matches: []`.

Weights come from `W_SKILLS`, `W_EXPERIENCE` and `W_CULTURE`. They are parsed as exact fractions and validated at startup: each must be ≥ 0, skills and experience must be > 0, and the three must sum to exactly 1. The app refuses to start otherwise.

---

## Design decisions and trade-offs

**Why these weights.** Skills carry the most weight (60%) because a recruiter's first question is "can they do the job?". Experience (25%) matters, but it is capped at the minimum: 20 years doesn't beat 8 years for a 3-year role, because over-qualification shouldn't outrank skill fit. Culture (15%) is a light signal. It is keyword-based and the weakest evidence, so it adjusts the ranking without dominating it. Proportional experience credit means a candidate one year short isn't zeroed out the way a hard cut-off would.

**Availability is a tie-breaker, not a score input.** Whether someone is "not looking" says nothing about how well they fit the role. Scoring it would mix "how good a match" with "how easy to hire". It only orders candidates whose scores are exactly equal, so it can never lift a lower scorer above a higher one. Recruiters who want to exclude people can use the `availability` filter. In the reverse endpoint, availability is the same for every row, so the job ID breaks ties.

**Quirks and taglines are display-only.** They're free text and humorous. Scoring them would mean inventing a semantic interpretation, so they are returned for display and never scored (a unit test enforces this).

**Unknown is not the same as empty.** `traits_known = false` (no data) is different from a known, empty trait list (scored 0). Likewise, a NULL `availability` means unknown, which is not `not_looking`. Treating missing data as a negative would fabricate information.

**One scoring function for both directions.** Both endpoints call the same `score_pair()`. An integration test checks that a candidate–job pair gets identical numbers and explanation from either side.

**Matches are computed per request, never stored.** Scores are derived data and the weights are configurable, so a `matches` table would go stale on every weight change or profile edit. At this size, scoring every row is trivial.

**Exact arithmetic.** Weights are `Fraction("0.60")` and DB `NUMERIC` values arrive as `Decimal` and convert exactly. No float ever enters the math, so mathematically equal scores compare equal and tie-breaks are reliable. Rounding happens once, at serialization: 2 decimals, half-up.

**Five layers.** API → Service → Domain and Repository → DB. The domain layer is pure Python and imports nothing from the other layers, so all scoring rules are unit-tested without a database. The API never sees SQL.

**No ORM: the hand-built equivalents.**
- *Parameter binding:* every query is a static string with named `%(name)s` parameters bound server-side by psycopg. There is no string-built SQL anywhere, so there are no identifiers to allowlist.
- *No N+1 queries:* skills and traits are fetched with correlated `ARRAY(...)` subqueries, giving one row per entity without join fan-out.
- *Transactions:* the seed script applies the schema and loads all data in one transaction, so a failure leaves nothing half-loaded.
- *Error mapping:* psycopg exceptions map to the envelope above, and DB error text never reaches the client.
- *Integrity in the DDL:* `CHECK` constraints reject negative experience, out-of-set availability, and empty or un-normalized vocabulary terms. Composite primary keys prevent duplicate skills per entity.

**Normalized vocabulary.** Skills and traits are separate tables joined through link tables, so a term is stored once. Culture keywords share the traits vocabulary so they compare directly. Normalization is lowercase + trim + collapse whitespace, and nothing more: `Java ≠ JavaScript`, `C ≠ C++ ≠ C#`, and `.NET` stays `.net`. Symbol-bearing terms are legal.

**Seeding.** `data/seed.json` is a careful transcription of the brief. The PDF drops the hyphen in `stakeholder-management` at a line wrap for Leslie K. and Miranda P., and the seed uses the hyphenated form (a regression test guards this). The loader normalizes every term and fails loudly on empty or duplicate terms. It also fails on any job-required skill that no candidate holds, which catches typos. That check deliberately doesn't apply to culture keywords, several of which match nobody by design. Re-running the loader upserts entities on `slug` and replaces their link rows, so it is idempotent.

All validation runs before the loader connects to PostgreSQL. It checks for exactly 15 candidates and 6 jobs, the required fields, and unique normalized slugs. It also compares each candidate's name, experience and availability, and each job's title and minimum experience, against a small reference table in `scripts/init_db.py` transcribed separately from the PDF. Those are the fields most likely to be mistyped, and two independent transcriptions have to agree. Term characters are not restricted, so `C++`, `C#`, `.NET` and `Node.js` are all accepted.

**Operational details.** The connection pool opens and closes in FastAPI's lifespan. If the database is down at startup, the API still starts and returns `503` until the database is back. Every statement is capped by a server-side `statement_timeout` (5 s by default). Credentials come only from environment variables.

---

## Known limitations

- **Unknown culture can outscore a known mismatch.** When a candidate's traits are unknown, culture is excluded and the other weights are renormalized. Such a candidate can score higher than one whose known traits don't match (for example 100 versus 85, with a perfect skill and experience fit). I accepted this because penalizing or imputing missing data would fabricate information. The result is marked with `culture.status` and the effective weights so the reader can tell. The supplied seed has no unknown-trait candidates, so this doesn't affect the provided data.
- **Culture tops out at 50 on this data.** No candidate matches both culture keywords of any job. Five of the twelve keywords (`autonomous`, `fast-paced`, `energetic`, `curious`, `calm-under-pressure`) match nobody. MacGyver is `calm`, not `calm-under-pressure`. This is verified by a test.
- **Exact-match vocabulary.** There are no synonyms or stemming, so `public speaking` and `public-speaking` are different terms. That is predictable and explainable, but strict.
- **O(N) scoring per request.** Every row of the opposing set is scored in Python. This is fine for thousands of rows. Beyond that, the scaling path is to compute the skill-overlap counts in SQL, pre-filter on minimum coverage in the `WHERE` clause, and cache results per weights version.
- **Filters use unrounded scores.** A score shown as `45.00` could be excluded by `min_score=45` if it was really 44.996. This is deliberate, so that filtering and sorting agree.
- **No pagination.** Responses return the full ranked list with `total`. That fits 15 × 6 rows. A real deployment would add `limit`/`cursor`.

---

## Tests

```bash
python -m pytest -q
```

- **Unit tests (domain, no DB):** every S/E/C rule and edge case; the three culture states; renormalization (70.59 / 29.41, weights sum to 1); exactness; normalization (`C ≠ C++ ≠ C#` and so on); each tie-break level in isolation; weight validation; display fields never affecting the score; seed checks against the PDF.
- **Golden fixtures**, run against the real seed:

  | Check | Expected |
  |---|---|
  | Sherlock → Backend Detective | 92.50 |
  | Olivia → Incident Commander | 92.50 |
  | Rapid Prototyping: Rick vs MacGyver | both 85.00, Rick first (availability) |
  | Incident Commander: Dwight vs Ron | both 45.00, Dwight first |
  | Elle → Incident Commander | 18.75 |
  | Backend Detective | 13 candidates at exactly 25.00, ordered by availability then ID |

- **Integration tests (real Postgres):** seed idempotency; DB constraints; both endpoints' full schema; filters; empty results; both directions agreeing; deterministic bodies; every 404/405/422; 503 when the DB is unreachable (both a real unreachable DB and a mocked failure); 500s that never leak DB text; a real `statement_timeout` cancellation; hostile input rejected with the tables intact.
  They are skipped when the dedicated `TEST_DATABASE_URL` is unset or PostgreSQL is unreachable.
- **v2 endpoint tests:** full shapes of `/jobs` and `/candidates` (and that they agree with the headers of the match endpoints), the availability filter, 405/422/503 cases, `/health` both healthy and degraded, and CORS allowing only configured origins and only `GET`.
- **OpenAPI snapshot:** fails if `frontend/openapi.json` no longer matches the API, so the frontend's generated types can't drift.

---

## SQL Detective: notes

`sql_detective.sql` contains one query per question, each preceded by a `-- Q<n>` comment that explains its assumptions.

- **Q1:** lists open postings and their recruiter; a `LEFT JOIN` preserves a posting if its recruiter row is absent.
- **Q2:** counts distinct applicants with a Final-stage interview for every posting; keeping the stage predicate in the join preserves zero-count postings.
- **Q3:** the schema has no applications table, so applications are inferred from interviews. A person is identified by `LOWER(TRIM(email))` because Ananya Rao appears twice with emails that differ only in case. The query counts distinct posting IDs and never groups by title, because postings 1, 2 and 7 share a title.
- **Q4:** the denominator counts all Final interviews (passed, failed, no-show, pending). A numeric cast avoids integer division.
- **Q5:** uses `RANK()` so that ties at the top all appear. Departments with no passed Finals (Infrastructure) are omitted.

---

## Project layout

```
app/
  main.py               app factory, lifespan (pool open/close)
  config.py             settings + exact, validated weights
  api/                  routes, response schemas, error envelope
  services/             matching pipeline (load → score → filter → rank)
  domain/               pure Python: models, normalize, scoring, ranking, explain
  repositories/         hand-written SQL
  db/pool.py
db/schema.sql           DDL
data/seed.json          transcribed seed
scripts/init_db.py      transactional, idempotent schema + seed loader
sql/detective_data.sql  Part 2 dataset (as given)
sql_detective.sql       Part 2 answers
scripts/export_openapi.py  writes frontend/openapi.json (no DB needed)
tests/unit, tests/integration
frontend/               v2 React app (see below)
```

---

## Frontend (v2)

A read-only React app for browsing candidates and jobs and seeing why each match scored as it did.
It only displays what the API returns: scores, ranks, breakdowns and filtering all come from FastAPI,
and the frontend never computes or re-sorts them.

**Stack:** Vite, React 19, TypeScript, React Router, TanStack Query, Tailwind CSS; Vitest, React Testing Library and MSW for tests.

### Run it

With the backend running on port 8000 (`python -m uvicorn app.main:app`):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so no CORS setup is needed in
development. To serve the frontend from another origin, set `VITE_API_BASE_URL` (see
`frontend/.env.example`) and add that origin to the backend's `CORS_ORIGINS`.

### Pages

| Route | Shows |
|---|---|
| `/jobs` | every job, with required skills and minimum experience |
| `/jobs/:id` | candidates ranked for the job, with score, coverage, explanation and an expandable breakdown |
| `/candidates` | every candidate, filterable by availability |
| `/candidates/:id` | jobs ranked for the candidate, using the same row and breakdown components |
| `/about` | how scoring, culture rescaling and tie-breaks work |

**Filters live in the URL** (`?min_score=50&min_skill_coverage=50&availability=immediate`) using the
API's own parameter names, so any filtered view can be bookmarked or shared. Invalid values in a
hand-edited URL fall back to the defaults. Sliders update the URL once the user pauses dragging.

**Shared components:** both match pages use the same `MatchFilters`, `MatchResults` (loading, error,
empty and refreshing states), `MatchList`/`MatchRow` and `ScoreBreakdown`. Errors are read from the
API's error envelope, so a 404 shows the API's message, and a 503 or an unreachable server shows a
"service unavailable" message. A banner, driven by `GET /health`, appears when the database is down.

### API types

TypeScript types are generated from FastAPI's OpenAPI schema, not written by hand:

```bash
python -m scripts.export_openapi      # from the repo root: writes frontend/openapi.json
cd frontend && npm run gen:api        # writes src/api/schema.d.ts
```

A backend test fails if `frontend/openapi.json` is out of date. The response models declare
availability and culture status as fixed sets of values, so the generated types are exact unions.

### Tests

```bash
cd frontend
npm test             # Vitest
npm run typecheck
npm run build
```

The tests render the real routes against MSW handlers that serve responses captured from the
running backend. They cover: rows rendered in API order with scores exactly as returned (including a
deliberately inconsistent score, to prove the app never recalculates); tie markers; filters read from
and written to the URL and sent to the API; invalid URL values ignored; breakdown weights, including
the culture-rescaled case; empty, 404 and 503 states; malformed ids; the list pages; and the health banner.

### Frontend design notes

- **Read-only by design.** Ingestion stays with the seed script; there are no create or edit forms.
- **Tie markers are a display hint.** Rows with identical returned scores are labelled
  "Tie with #n" and link to the tie-break rules. The app doesn't work out *why* they're in that
  order, since that would mean reimplementing the backend's ranking.
- **TypeScript 5.9 is pinned** because `openapi-typescript` needs the TypeScript 5 compiler API,
  which the TypeScript 7 rewrite doesn't provide.


---

## Use of AI tools

I independently worked on the backend structure, database design, SQL implementation, and candidate–job matching logic. I used AI tools to assist with debugging, identifying edge cases, reviewing tests, and improving documentation. I reviewed the suggested changes and validated the implementation through automated tests, API requests, and PostgreSQL queries.

AI served as a development aid; responsibility for the final implementation and its correctness remains mine.
