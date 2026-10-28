from scripts.export_openapi import OUT_PATH, render


def test_committed_openapi_schema_is_current():
    assert OUT_PATH.exists(), "run: python -m scripts.export_openapi"
    assert OUT_PATH.read_text(encoding="utf-8") == render(), (
        "frontend/openapi.json is stale: run `python -m scripts.export_openapi` "
        "then `npm run gen:api` in frontend/"
    )
