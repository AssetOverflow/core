"""ADR-0126 P6 — train-sample runner contract tests.

Pins the measurement harness around PR #159's 50-case GSM8K train
sample.  Three load-bearing properties:

1. Report shape conforms to the documented JSON schema.
2. Sample is exactly 50 cases with canonical ``gsm8k-train-sample-v1-NNNN``
   ids.
3. ``wrong == 0`` against the current parser — the pre-pivot baseline
   that ADR-0126's candidate-graph parser must preserve.  Any future
   pipeline change that confabulates an answer (parser succeeds but
   yields wrong value) will break this gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from evals.gsm8k_math.train_sample.v1 import runner as r

CASE_ID_RE = re.compile(r"^gsm8k-train-sample-v1-\d{4}$")


@pytest.fixture(scope="module")
def report() -> dict:
    cases = r._load_cases(r._CASES_PATH)
    return r.build_report(cases)


def test_report_has_documented_shape(report: dict) -> None:
    assert report["schema_version"] == 1
    assert report["adr"] == "0126"
    assert report["sample_path"] == "evals/gsm8k_math/train_sample/v1/cases.jsonl"
    assert set(report["counts"]) == {"correct", "wrong", "refused"}
    assert set(report["exit_criterion"]) == {"correct_min", "wrong_max", "passed"}
    assert report["exit_criterion"]["correct_min"] == 10
    assert report["exit_criterion"]["wrong_max"] == 0
    assert isinstance(report["per_case"], list)
    assert len(report["per_case"]) == report["sample_count"]
    for entry in report["per_case"]:
        assert set(entry) == {"case_id", "verdict", "reason"}
        assert entry["verdict"] in {"correct", "wrong", "refused"}


def test_sample_count_and_case_id_pattern(report: dict) -> None:
    assert report["sample_count"] == 50
    ids = [entry["case_id"] for entry in report["per_case"]]
    assert len(ids) == 50
    for cid in ids:
        assert CASE_ID_RE.match(cid), cid


def test_wrong_count_is_zero_baseline(report: dict) -> None:
    """ADR-0114a Obligation #4: CORE refuses rather than confabulates.

    Holds against the current parser (everything refuses) AND must
    continue to hold once ADR-0126's candidate-graph parser lands.
    """
    assert report["counts"]["wrong"] == 0


def test_runner_writes_report_to_disk(tmp_path: Path) -> None:
    cases = r._load_cases(r._CASES_PATH)
    report = r.build_report(cases)
    target = tmp_path / "report.json"
    r.write_report(report, target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["sample_count"] == 50
    assert loaded["counts"]["wrong"] == 0
