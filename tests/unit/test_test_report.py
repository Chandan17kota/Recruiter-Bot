import json
import subprocess
from datetime import datetime

import pytest

from scripts.test_report import OUT_PATH, ROOT, _file_of, parse_junit

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="1" failures="1" skipped="1" tests="5" time="2.5">
    <testcase classname="tests.unit.test_scoring" name="test_ok" time="0.010"/>
    <testcase classname="tests.unit.test_scoring" name="test_param[a-1]" time="0.002"/>
    <testcase classname="tests.integration.test_api" name="test_bad" time="0.5">
      <failure message="assert 1 == 2">E   assert 1 == 2
tests/integration/test_api.py:10: AssertionError</failure>
    </testcase>
    <testcase classname="tests.integration.test_api" name="test_skip" time="0">
      <skipped type="pytest.skip" message="Postgres not reachable">skip details</skipped>
    </testcase>
    <testcase classname="tests.integration.test_api.TestGroup" name="test_err" time="0.1">
      <error message="fixture failed">boom</error>
    </testcase>
  </testsuite>
</testsuites>
"""


def test_summary_counts_every_outcome():
    report = parse_junit(JUNIT)
    assert report["summary"] == {"total": 5, "passed": 2, "failed": 1, "error": 1, "skipped": 1}
    assert report["duration_s"] == 2.5


def test_tests_grouped_by_file_sorted():
    report = parse_junit(JUNIT)
    assert [f["path"] for f in report["files"]] == ["tests/integration/test_api.py", "tests/unit/test_scoring.py"]
    api = report["files"][0]
    assert api["counts"] == {"passed": 0, "failed": 1, "error": 1, "skipped": 1}
    assert [t["name"] for t in api["tests"]] == ["test_bad", "test_skip", "test_err"]


def test_messages_kept_for_problems_only():
    tests = {t["name"]: t for f in parse_junit(JUNIT)["files"] for t in f["tests"]}
    assert tests["test_ok"]["message"] is None
    assert "assert 1 == 2" in tests["test_bad"]["message"] and "test_api.py:10" in tests["test_bad"]["message"]
    assert tests["test_skip"]["message"] == "Postgres not reachable"
    assert tests["test_err"]["message"] == "boom"


def test_file_of_strips_class_names():
    assert _file_of("tests.unit.test_x") == "tests/unit/test_x.py"
    assert _file_of("tests.unit.test_x.TestThing") == "tests/unit/test_x.py"


def test_rejects_junit_whose_totals_disagree():
    tampered = JUNIT.replace('tests="5"', 'tests="6"')
    with pytest.raises(ValueError, match="disagree"):
        parse_junit(tampered)


# ---- The committed report (frontend/public/test-report.json) ---------------------
# These can't prove the file wasn't hand-edited, but any edit that changes a number
# without regenerating the whole report breaks one of these invariants.
@pytest.fixture
def committed_report():
    if not OUT_PATH.exists():
        pytest.skip("no committed report; run python -m scripts.test_report")
    return json.loads(OUT_PATH.read_text(encoding="utf-8"))


def test_committed_report_comes_from_the_script(committed_report):
    r = committed_report
    assert r["generator"] == "scripts/test_report.py"
    datetime.fromisoformat(r["generated_at"])
    assert r["pytest_version"] and r["python_version"]


def test_committed_report_is_internally_consistent(committed_report):
    r = committed_report
    tests = [t for f in r["files"] for t in f["tests"]]
    assert r["summary"]["total"] == len(tests)
    for status in ("passed", "failed", "error", "skipped"):
        assert r["summary"][status] == sum(t["status"] == status for t in tests), status
    for f in r["files"]:
        assert f["counts"] == {s: sum(t["status"] == s for t in f["tests"]) for s in f["counts"]}, f["path"]
    # pytest exits 0 only when nothing failed or errored.
    assert (r["pytest_exit_code"] == 0) == (r["summary"]["failed"] + r["summary"]["error"] == 0)


def test_committed_report_names_a_real_commit(committed_report):
    commit = committed_report["git_commit"]
    if commit is None:
        pytest.skip("report was generated outside a git checkout")
    sha = commit.removesuffix("-dirty")
    try:
        found = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT, capture_output=True).returncode == 0
    except OSError:
        pytest.skip("git not available")
    assert found, f"report names commit {sha}, which is not in this repository"
