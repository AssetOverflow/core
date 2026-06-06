from __future__ import annotations

import json

from core.cli import main
from evals.environment_falsification import build_environment_falsification_report


def test_environment_falsification_report_passes_expected_fixtures():
    report = build_environment_falsification_report()
    assert report["lane"] == "environment-falsification"
    assert report["failed"] == 0
    assert report["expected_report_hash_ok"] is True
    assert {case["actual_verdict"] for case in report["cases"]} == {"SUPPORTED", "FALSIFIED"}


def test_core_eval_environment_falsification_json(capsys):
    assert main(["eval", "environment-falsification", "--json"]) == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["lane"] == "environment-falsification"
    assert report["failed"] == 0


def test_core_eval_environment_falsification_text_summary(capsys):
    assert main(["eval", "environment-falsification"]) == 0
    out = capsys.readouterr().out
    assert "lane           : environment-falsification" in out
    assert "failed         : 0" in out
