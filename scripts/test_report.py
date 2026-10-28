"""Run the backend test suite and save the results for the frontend's Tests page.

Usage:  python -m scripts.test_report

Runs pytest with a JUnit XML report, converts it to JSON and writes
frontend/public/test-report.json. The report is written even when tests fail
(that is when it matters most). The exit code is pytest's.

The web app only ever reads this file; nothing in the API can start a test run.
"""
import json
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "frontend" / "public" / "test-report.json"
MAX_MESSAGE_CHARS = 2000   # keep the report small; the full output is in the terminal


def _file_of(classname: str) -> str:
    """'tests.integration.test_api' or 'tests.unit.test_x.TestClass' -> 'tests/integration/test_api.py'."""
    parts = classname.split(".")
    while parts and not parts[-1].startswith("test_"):
        parts.pop()   # drop class names such as TestSomething
    return "/".join(parts) + ".py" if parts else classname


def _outcome(case: ET.Element) -> tuple[str, str | None]:
    for tag, status in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
        node = case.find(tag)
        if node is not None:
            text = (node.get("message") or "").strip()
            if status != "skipped" and node.text:
                text = node.text.strip()
            return status, (text[:MAX_MESSAGE_CHARS] or None)
    return "passed", None


def parse_junit(xml_text: str) -> dict:
    """Turn pytest's JUnit XML into {summary, duration_s, files: [...]}, grouped by test file."""
    root = ET.fromstring(xml_text)
    files: dict[str, list[dict]] = {}
    for case in root.iter("testcase"):
        status, message = _outcome(case)
        files.setdefault(_file_of(case.get("classname", "")), []).append({
            "name": case.get("name", ""),
            "status": status,
            "duration_s": round(float(case.get("time", 0) or 0), 3),
            "message": message,
        })

    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    out_files = []
    for path in sorted(files):
        tests = files[path]
        file_counts = {k: sum(t["status"] == k for t in tests) for k in counts}
        for k, v in file_counts.items():
            counts[k] += v
        out_files.append({"path": path, "counts": file_counts,
                          "duration_s": round(sum(t["duration_s"] for t in tests), 3), "tests": tests})

    # Cross-check against pytest's own totals so a parsing mistake can't misreport results.
    suites = list(root.iter("testsuite"))
    declared = {
        "total": sum(int(s.get("tests", 0)) for s in suites),
        "failed": sum(int(s.get("failures", 0)) for s in suites),
        "error": sum(int(s.get("errors", 0)) for s in suites),
        "skipped": sum(int(s.get("skipped", 0)) for s in suites),
    }
    parsed = {"total": sum(counts.values()), "failed": counts["failed"], "error": counts["error"], "skipped": counts["skipped"]}
    if parsed != declared:
        raise ValueError(f"JUnit totals {declared} disagree with the parsed test cases {parsed}")

    suite_times = [float(s.get("time", 0) or 0) for s in suites]
    return {
        "summary": {"total": sum(counts.values()), **counts},
        "duration_s": round(sum(suite_times), 2),
        "files": out_files,
    }


def _git_commit() -> str | None:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        # The report itself is excluded, or regenerating it would always look dirty.
        report = OUT_PATH.relative_to(ROOT).as_posix()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", f":(exclude){report}"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "junit.xml"
        # Read the commit before the run so the report names the code that was tested.
        commit = _git_commit()
        code = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={xml_path}", *argv], cwd=ROOT).returncode
        if not xml_path.exists():
            print("pytest produced no report (see output above); nothing written.", file=sys.stderr)
            return code or 1
        report = parse_junit(xml_path.read_text(encoding="utf-8"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": commit,
        "generator": "scripts/test_report.py",
        "python_version": platform.python_version(),
        "pytest_version": pytest.__version__,
        "pytest_exit_code": code,
        **report,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    s = report["summary"]
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {s['passed']} passed, {s['failed']} failed, "
          f"{s['error']} errors, {s['skipped']} skipped")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
