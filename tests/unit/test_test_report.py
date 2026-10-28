from scripts.test_report import _file_of, parse_junit

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
