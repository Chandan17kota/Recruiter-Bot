"""Write the API's OpenAPI schema to frontend/openapi.json (no database needed).

Usage:  python -m scripts.export_openapi
Then:   cd frontend && npm run gen:api      (regenerates src/api/schema.d.ts)

tests/unit/test_openapi_snapshot.py fails if the committed file is out of date,
so frontend types cannot silently drift from the backend.
"""
import json
import sys
from pathlib import Path

from app.config import DEFAULT_WEIGHTS, Settings
from app.main import create_app

OUT_PATH = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"


def build_schema() -> dict:
    # The lifespan (and so the pool) never runs; app.openapi() only reads the routes.
    app = create_app(Settings(database_url="postgresql://unused", weights=DEFAULT_WEIGHTS))
    return app.openapi()


def render() -> str:
    return json.dumps(build_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
