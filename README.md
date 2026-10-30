# Recruiter Bot

Backend service that stores candidates and job openings in PostgreSQL and ranks matches both ways (candidates for a job, and jobs for a candidate). Every score comes with an explanation of how it was calculated. All SQL is hand-written, no ORM or query builder.

Main endpoints:

- `GET /jobs/{id}/matches` - ranked candidates for a job
- `GET /candidates/{id}/matches` - ranked jobs for a candidate

Each match has a score, skill coverage, a breakdown per component (with the weights that were actually used) and a one-line reason. Optional filters are `min_score`, `min_skill_coverage` and `availability` (repeatable, job endpoint only). All errors use the same JSON format.

Part 2 (SQL Detective) is in `sql_detective.sql`.

**v2:** I later added a read-only React frontend in `frontend/` and three small endpoints for it: `GET /jobs`, `GET /candidates` and `GET /health` (see [Frontend](#frontend-v2)). The backend-only submission is tagged `v1.0.0`.

**Stack:** Python 3.11+, FastAPI, PostgreSQL 14+, psycopg 3 + psycopg_pool, pytest.

## Scope and structure

What the assignment asked for: a PostgreSQL-backed matching API in both directions, deterministic and explainable scores, the sample data from the brief, tests, and the five SQL Detective queries.

The code is split into layers:

| Layer | What it does |
|---|---|
| API | FastAPI routes, request validation, response schemas, error envelope |
| Service | Loads the records, then runs scoring, filtering and ranking |
| Domain | Plain Python: profiles, normalization, scoring, ranking, explanations |
| Repository | Parameterized SQL queries |
| Database | Tables, constraints, indexes, seed data |

Both endpoints use the same scoring function. Only the repository layer runs SQL, and the domain layer doesn't import FastAPI or psycopg, so it can be tested without a database.

---

## Setup and run

You need Python 3.11+ and PostgreSQL 14+ running.

| OS | Install Postgres |
|---|---|
| macOS | `brew install postgresql@16 && brew services start postgresql@16` |
| Ubuntu/Debian | `sudo apt install postgresql && sudo systemctl start postgresql` |
| Windows | EDB installer from postgresql.org |

A hosted Postgres also works, only the connection URL matters.

Create three databases:

```text
createdb recruiter_bot
createdb recruiter_bot_test
createdb hiring_ops
```

**Warning:** the integration tests drop and recreate tables in `recruiter_bot_test`, so don't point `TEST_DATABASE_URL` at anything you care about.

Copy `.env.example` to `.env` and set `DATABASE_URL` and `TEST_DATABASE_URL`. The example file only has local sample URLs, no real credentials.

**Windows (PowerShell)**, from the project folder, with the Postgres tools on `PATH`:

```powershell
Copy-Item .env.example .env
# edit .env and set the two database URLs
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.init_db
python -m uvicorn app.main:app --reload
python -m pytest -q
```

If PowerShell won't let you activate the venv, call `.venv\Scripts\python.exe` directly instead of `python`.

**macOS/Linux:**

```bash
cp .env.example .env
# edit .env and set the two database URLs
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db
python -m uvicorn app.main:app --reload
python -m pytest -q
```

`scripts.init_db` creates the schema and loads the seed data in a single transaction, and it's safe to run again. Swagger docs are at `http://localhost:8000/docs`.

If the test database isn't reachable, the integration tests are skipped instead of failing.

### SQL Detective (Part 2)

The given dataset goes into its own database:

```bash
psql hiring_ops -f sql/detective_data.sql
psql hiring_ops -f sql_detective.sql
```

Notes on each query are in [SQL Detective notes](#sql-detective-notes) below.

---

## API examples

```bash
curl localhost:8000/jobs/1/matches
curl "localhost:8000/jobs/1/matches?min_skill_coverage=50&availability=immediate"
curl "localhost:8000/jobs/6/matches?availability=immediate&availability=two_weeks&min_score=40"
curl localhost:8000/candidates/1/matches
curl -i localhost:8000/jobs/999/matches                  # 404 JOB_NOT_FOUND
curl -i "localhost:8000/jobs/1/matches?min_score=150"    # 422 VALIDATION_ERROR
curl localhost:8000/jobs                                 # v2: all jobs
curl "localhost:8000/candidates?availability=immediate"  # v2: candidates, optional filter
curl -i localhost:8000/health                            # v2: 200, or 503 if the DB is down
```

Shortened response for `GET /jobs/1/matches`:

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

`GET /candidates/{id}/matches` returns the same structure the other way round: a `candidate` block at the top, and each match has a `job` summary instead of a candidate.

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
    "job": {"id": 1, "title": "Backend Detective", "min_experience_years": 3.0, "tagline": "display-only text"},
    "score": 92.5,
    "skill_coverage": 100.0,
    "matched_required_skill_count": 3,
    "required_skill_count": 3,
    "components": { "...": "same as above" },
    "explanation": "Has all 3 required skills; 8 yrs meets the 3-yr minimum; matches 1 of 2 culture keywords (analytical)."
  }]
}
```

**Query parameters**

| Param | Endpoints | Rules |
|---|---|---|
| `min_score` | both | number 0-100, default 0 |
| `min_skill_coverage` | both | number 0-100, default 0 |
| `availability` | jobs only | repeatable: `immediate`, `two_weeks`, `not_looking`, `unknown` |

**Errors** always look like `{"error": {"code", "message", "details"}}`.

| Case | Status | Code |
|---|---|---|
| Bad path or query value (`/jobs/abc`, `min_score=150`, bad enum, NaN) | 422 | `VALIDATION_ERROR` (`details` lists the fields) |
| Job or candidate doesn't exist | 404 | `JOB_NOT_FOUND` / `CANDIDATE_NOT_FOUND` |
| Unknown route / wrong method | 404 / 405 | `ROUTE_NOT_FOUND` / `METHOD_NOT_ALLOWED` |
| DB down, pool timeout or statement timeout | 503 | `DATABASE_UNAVAILABLE` |
| Anything else | 500 | `INTERNAL_ERROR` (generic message, real error only in server logs) |

---

## Scoring

```
score = 0.60·S + 0.25·E + 0.15·C        (each part is 0-100, so the score is 0-100)
```

| Part | Rule |
|---|---|
| **Skills (S)** | matched required skills / required skills × 100. Extra skills don't add anything. If a job has no required skills, S is 100 and the explanation mentions it. |
| **Experience (E)** | 100 if the job's minimum is 0, otherwise 100 × min(years / minimum, 1). |
| **Culture (C)** | matched culture keywords / job's culture keywords × 100 (candidate traits compared against the job's keywords). |

Culture can be in one of three states (`components.culture.status`):

| Case | `status` | Effect |
|---|---|---|
| Job has keywords and the candidate's traits are known | `scored` | Normal. If the known traits list is empty, culture = 0. |
| Candidate's traits are unknown | `unknown_candidate_traits` | Culture is dropped and the other weights are rescaled |
| Job has no culture keywords | `no_job_keywords` | Same as above |

Rescaling divides the remaining weights by their sum, so without culture skills become 0.60/0.85 = 70.59% and experience 29.41%. The response always shows the weights that were really used (`weight_applied`), and the explanation mentions the rescale.

**Ranking** is the same in both directions: higher score first, then higher skill coverage, then higher experience score, then availability (`immediate` < `two_weeks` < unknown < `not_looking`), then lower ID. Ranks are 1..n over the filtered list and `total` is n. No matches gives `200` with `matches: []`.

The weights come from `W_SKILLS`, `W_EXPERIENCE` and `W_CULTURE` in `.env`. They're checked at startup: each must be >= 0, skills and experience must be > 0, and they must add up to exactly 1, otherwise the app won't start.

---

## Design decisions

**Weights.** Skills get 60% because the first question is whether the person can actually do the job. Experience gets 25% but is capped at the job's minimum, so 20 years doesn't beat 8 years for a 3-year role. I didn't want over-qualification to outrank skill fit. Culture is only 15% because it's just keyword matching and the weakest signal. Experience gives partial credit, so someone one year short isn't scored zero like with a hard cut-off.

**Availability only breaks ties.** "Not looking" doesn't say anything about how well someone fits a role, so I kept it out of the score. It only orders candidates whose scores are exactly equal. If a recruiter wants to hide unavailable people they can use the `availability` filter. For the candidate endpoint availability is the same for every row, so the job ID decides ties.

**Quirks and taglines aren't scored.** They're funny free text, and scoring them would mean making up some interpretation of them. They're returned for display only (there's a unit test for this).

**Unknown vs empty.** `traits_known = false` (we don't know) is treated differently from a known but empty list of traits (scores 0). Same for a NULL `availability`: it means unknown, not `not_looking`. I didn't want missing data to count against anyone.

**Same scoring function both ways.** Both endpoints call `score_pair()`. An integration test checks that a candidate-job pair gets exactly the same numbers and explanation from either side.

**Matches aren't stored.** They're calculated on each request. Since the weights can be changed, a stored `matches` table would go out of date, and with this amount of data scoring everything per request costs nothing.

**No floats.** Weights are parsed as `Fraction("0.60")`, and Postgres `NUMERIC` values come in as `Decimal`, so the math is exact. That way equal scores really are equal and the tie-breaks behave. Scores are rounded only when the response is built (2 decimals, half-up).

**What replaces the ORM:**
- Every query is a fixed string with named `%(name)s` parameters that psycopg binds. No SQL is built from strings anywhere.
- Skills and traits are loaded with `ARRAY(...)` subqueries, so it's one row per entity and no N+1 queries.
- The seed script loads the schema and data in one transaction, so a failure leaves nothing half-loaded.
- psycopg errors are mapped to the error envelope, and DB error text is never sent to the client.
- `CHECK` constraints in the schema reject negative experience, invalid availability values and empty or non-normalized terms. Composite primary keys stop duplicate skills per person or job.

**Vocabulary.** Skills and traits each have their own table with link tables, so each term is stored once. Culture keywords use the traits table so they can be compared directly. Normalization is just lowercase, trim and collapse spaces. So `Java ≠ JavaScript`, `C ≠ C++ ≠ C#`, and `.NET` becomes `.net`.

**Seed data.** `data/seed.json` is typed up from the brief. The PDF loses the hyphen in `stakeholder-management` at a line break for Leslie K. and Miranda P.; I used the hyphenated version and added a test for it. The loader normalizes all terms and fails on empty or duplicate terms. It also fails if a job needs a skill that no candidate has, which catches typos. Culture keywords are excluded from that check because some of them don't match anyone in the data on purpose. Rerunning the loader updates rows by `slug` and replaces the link rows, so it's idempotent.

Before connecting to the DB, the loader also checks: exactly 15 candidates and 6 jobs, required fields, unique slugs, and a small reference table in `scripts/init_db.py` (names, experience, availability, job titles and minimum experience) that I typed separately from the PDF. Those are the fields I was most likely to mistype, so both copies have to match.

**Runtime.** The connection pool is opened and closed in FastAPI's lifespan. If the DB is down when the app starts, the app still starts and returns `503` until the DB is back. Every query has a `statement_timeout` (5 s by default). Credentials only come from environment variables.

---

## Known limitations

- **An unknown culture can score higher than a known mismatch.** If a candidate's traits are unknown, culture is dropped and the weights are rescaled, so they can end up above someone whose known traits don't match (e.g. 100 vs 85 with perfect skills and experience). I left it like this because guessing missing data seemed worse, and the response shows `culture.status` and the weights used. None of the seed candidates have unknown traits, so it doesn't affect the given data.
- **Culture never goes above 50 on this data.** No candidate matches both culture keywords of any job, and 5 of the 12 keywords (`autonomous`, `fast-paced`, `energetic`, `curious`, `calm-under-pressure`) don't match anyone. For example, MacGyver is `calm`, not `calm-under-pressure`. There's a test for this.
- **Exact matching only.** No synonyms or stemming, so `public speaking` and `public-speaking` are different. Easy to explain, but strict.
- **Every row is scored in Python on each request.** That's fine for thousands of rows. For more, I'd count skill overlap in SQL, filter on coverage in the `WHERE` clause and cache results per set of weights.
- **Filters compare the unrounded score.** A score shown as `45.00` can be excluded by `min_score=45` if it's actually 44.996. I kept it this way so filtering and sorting use the same number.
- **No pagination.** The whole ranked list is returned with `total`. That's fine for 15 × 6, but a real version would need `limit`/cursor.

## What I'd improve with more time

- Synonym/alias support for skills (e.g. `js` → `javascript`) with a mapping table.
- Pagination on the match and list endpoints.
- Moving the skill-overlap calculation into SQL for larger datasets.
- Create/edit endpoints for candidates and jobs, since right now data only comes in through the seed script.

---

## Tests

```bash
python -m pytest -q
```

- **Unit tests (no DB):** every scoring rule and edge case, the three culture states, the rescaling (70.59 / 29.41), exact arithmetic, normalization (`C ≠ C++ ≠ C#` etc.), each tie-break on its own, weight validation, display fields not affecting the score, and seed checks against the PDF.
- **Expected values on the real seed:**

  | Check | Expected |
  |---|---|
  | Sherlock → Backend Detective | 92.50 |
  | Olivia → Incident Commander | 92.50 |
  | Rapid Prototyping: Rick vs MacGyver | both 85.00, Rick first (availability) |
  | Incident Commander: Dwight vs Ron | both 45.00, Dwight first |
  | Elle → Incident Commander | 18.75 |
  | Backend Detective | 13 candidates at exactly 25.00, ordered by availability then ID |

- **Integration tests (real Postgres):** rerunning the seed, DB constraints, full response shape of both endpoints, filters, empty results, both directions agreeing, same response every time, all the 404/405/422 cases, 503 when the DB is unreachable (real and mocked), 500s not leaking DB errors, a real `statement_timeout`, and malicious input being rejected without touching the tables. These are skipped if `TEST_DATABASE_URL` isn't set or Postgres isn't reachable.
- **v2 endpoints:** `/jobs` and `/candidates` responses (and that they match the headers of the match endpoints), the availability filter, 405/422/503, `/health` healthy and degraded, and CORS only allowing configured origins and `GET`.
- **OpenAPI snapshot:** fails if `frontend/openapi.json` doesn't match the API anymore, so the frontend types can't silently drift.

---

## SQL Detective notes

Each query in `sql_detective.sql` has a `-- Q<n>` comment above it explaining assumptions.

- **Q1:** open postings with their recruiter. `LEFT JOIN` so a posting still shows up if its recruiter row is missing.
- **Q2:** distinct applicants with a Final interview per posting. The stage condition is in the join so postings with zero still appear.
- **Q3:** there's no applications table, so applications are inferred from interviews. People are identified by `LOWER(TRIM(email))` because Ananya Rao appears twice with emails that only differ in case. Null/blank emails are left out since they can't identify anyone. It counts distinct posting IDs, not titles, because postings 1, 2 and 7 have the same title. Repeat interviews for the same posting count once.
- **Q4:** recruiter Final-stage pass rate, for recruiters with at least 3 Final interviews. The denominator is all Final interviews (passed, failed, no-show, pending), with a numeric cast to avoid integer division.
- **Q5:** top recruiter(s) per department by passed Finals. Uses `RANK()` so ties are all shown. Infrastructure has no passed Finals, so it doesn't appear.

---

## Project layout

```
app/
  main.py               app setup, lifespan (opens/closes the pool)
  config.py             settings + weight validation
  api/                  routes, response schemas, error envelope
  services/             matching flow (load → score → filter → rank)
  domain/               plain Python: models, normalize, scoring, ranking, explain
  repositories/         SQL queries
  db/pool.py
db/schema.sql           tables
data/seed.json          seed data from the brief
scripts/init_db.py      schema + seed loader
scripts/export_openapi.py  writes frontend/openapi.json
scripts/test_report.py  runs pytest and writes the report for the /tests page
sql/detective_data.sql  Part 2 dataset (as given)
sql_detective.sql       Part 2 answers
tests/unit, tests/integration
frontend/               v2 React app
```

---

## Frontend (v2)

A read-only React app to browse candidates and jobs and see why each match got its score. It only shows what the API returns. Scores, ranks, breakdowns and filtering all come from the backend, and the frontend never recalculates or re-sorts anything.

**Stack:** Vite, React 19, TypeScript, React Router, TanStack Query, Tailwind CSS. Tests use Vitest, React Testing Library and MSW.

### Run it

With the backend running on port 8000:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The Vite dev server forwards `/api/*` to `http://localhost:8000`, so you don't need CORS in development. To host the frontend somewhere else, set `VITE_API_BASE_URL` (see `frontend/.env.example`) and add that origin to `CORS_ORIGINS` in the backend.

### Pages

| Route | Shows |
|---|---|
| `/jobs` | all jobs with required skills and minimum experience |
| `/jobs/:id` | ranked candidates for the job: score, coverage, explanation, expandable breakdown |
| `/candidates` | all candidates, filterable by availability |
| `/candidates/:id` | ranked jobs for the candidate (same components) |
| `/about` | how scoring, culture rescaling and tie-breaks work |
| `/tests` | developer page (linked in the footer) showing the saved backend test report |

Filters are stored in the URL using the API's parameter names (`?min_score=50&min_skill_coverage=50&availability=immediate`), so a filtered view can be bookmarked. Invalid values in the URL fall back to defaults. Both match pages share the same filter, list and breakdown components. API errors are shown using the error envelope (e.g. the 404 message), and a banner appears when `/health` reports the DB is down.

### Test report page

`/tests` only **shows** a saved report, it can't run tests. Running tests from a web page would let anyone run code on the server, and the integration tests wipe the test database. To update the report:

```bash
python -m scripts.test_report     # from the repo root, writes frontend/public/test-report.json
```

The script runs pytest with JUnit XML output and converts it to JSON (totals, duration, Python/pytest version, git commit, and every test with its status). It double-checks its counts against pytest's totals and won't write the report if they don't match. If there were uncommitted changes, the commit is marked `-dirty`. A backend test also checks that the committed report is consistent with itself. The page shows when and on which commit the report was made, since it's a snapshot and not live.

### API types

The TypeScript types are generated from FastAPI's OpenAPI schema:

```bash
python -m scripts.export_openapi      # from the repo root, writes frontend/openapi.json
cd frontend && npm run gen:api        # writes src/api/schema.d.ts
```

A backend test fails if `frontend/openapi.json` is out of date.

### Frontend tests

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

The tests render the real pages against MSW mocks that return responses captured from the running backend. They check that rows appear in API order with scores exactly as returned (one test uses a deliberately wrong score to prove the app doesn't recalculate), tie labels, URL filters, invalid URL values, breakdown weights including the rescaled case, empty/404/503 states, the list pages and the health banner.

Notes:
- No create or edit forms, data comes from the seed script only.
- Rows with the same score are labelled "Tie with #n" and link to the tie-break rules. The app doesn't try to work out the tie-break itself.
- TypeScript is pinned to 5.9 because `openapi-typescript` needs the TypeScript 5 compiler API.

---

## Use of AI tools

I worked on the backend structure, database design, SQL and the candidate-job matching logic myself. I used AI tools to help with debugging, finding edge cases, reviewing tests and improving the documentation.

The v2 frontend (the React app in `frontend/`) was built with AI. I reviewed it and tested it against the running backend.

I checked all suggested changes with the automated tests, manual API requests and PostgreSQL queries. AI was a development aid; I'm responsible for the final implementation and whether it's correct.
