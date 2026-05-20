from __future__ import annotations

import json
from pathlib import Path

from evals.frontier_compare.__main__ import main
from evals.frontier_compare.runner import (
    BenchmarkReport,
    SuiteReport,
    format_human_report,
    run_all,
    run_suite,
    write_report,
)


def test_frontier_compare_run_all_report_shape() -> None:
    report = run_all()

    assert isinstance(report, BenchmarkReport)
    assert report.benchmark_family == "frontier_compare_wave1"
    assert report.model == "core"
    assert report.mode == "native"
    assert {suite.suite for suite in report.suites} == {
        "determinism",
        "truth_lock",
        "axis_orthogonality",
    }
    assert report.case_count > 0
    payload = report.as_dict()
    assert payload["summary"]["suite_count"] == 3
    assert payload["summary"]["case_count"] == report.case_count
    assert 0.0 <= payload["summary"]["primary_score"] <= 1.0


def test_frontier_compare_individual_suites_are_json_stable() -> None:
    for suite_name in ("determinism", "truth_lock", "axis_orthogonality"):
        report = run_suite(suite_name)
        assert isinstance(report, SuiteReport)
        assert report.suite == suite_name
        payload = report.as_dict()
        encoded = json.dumps(payload, sort_keys=True)
        assert suite_name in encoded
        assert payload["case_count"] == len(payload["cases"])
        assert 0.0 <= payload["primary_score"] <= 1.0


def test_frontier_compare_write_report(tmp_path: Path) -> None:
    report = run_suite("truth_lock")
    target = tmp_path / "frontier_wave1.json"

    write_report(report, target)

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["suite"] == "truth_lock"
    assert loaded["case_count"] == len(loaded["cases"])


def test_frontier_compare_human_report_contains_suite_status() -> None:
    report = run_suite("determinism")
    text = format_human_report(report)

    assert "frontier_compare_wave1" in text
    assert "determinism" in text
    assert "score=" in text


def test_frontier_compare_cli_json_and_report(tmp_path: Path, capsys) -> None:
    target = tmp_path / "report.json"
    code = main(["--suite", "truth_lock", "--json", "--report", str(target)])
    out = capsys.readouterr().out

    assert code in {0, 1}
    printed = json.loads(out)
    written = json.loads(target.read_text(encoding="utf-8"))
    assert printed == written
    assert printed["suite"] == "truth_lock"


def test_frontier_compare_report_viewer_exists() -> None:
    viewer = Path("evals/frontier_compare/ui/report_viewer.html")
    text = viewer.read_text(encoding="utf-8")

    assert "Frontier Compare" in text
    assert "Drop report JSON" in text
    assert "No network calls" in text
    assert "fetch(" not in text
    assert "XMLHttpRequest" not in text
