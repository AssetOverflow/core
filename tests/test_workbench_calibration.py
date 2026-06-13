"""Wave M Phase B — calibration / serving-discipline readers (ADR-0175).

The load-bearing obligation: the workbench re-implements none of the engine's
calibration math. These tests prove the reader's numbers come from
``core.reliability_gate`` (``conservative_floor`` / ``license_for``), and that
the serving counts are read from the committed reports unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.reliability_gate import conservative_floor
from workbench import calibration
from workbench.api import WorkbenchApi
from workbench.readers import EvidenceUnavailableError


def _write_practice_report(tmp_path: Path, per_class: dict) -> Path:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps({"adr": "0175", "regime": "practice", "per_class": per_class}),
        encoding="utf-8",
    )
    return path


def test_serving_metrics_read_committed_counts_unchanged() -> None:
    metrics = {m.lane: m for m in calibration.read_serving_metrics()}
    assert "train_sample" in metrics
    # The live invariant: the committed serving lane commits zero wrong answers.
    assert metrics["train_sample"].wrong == 0
    assert metrics["train_sample"].correct >= 0
    assert metrics["train_sample"].source_digest.startswith("sha256:")


def test_calibration_classes_over_committed_report_are_honest() -> None:
    # The committed practice report's classes are all below N_MIN today, so
    # none has earned a license — the reader must show exactly that, not fake
    # a green light.
    rows = calibration.read_calibration_classes()
    assert rows, "expected the committed per_class ledger to yield rows"
    for row in rows:
        if row.committed < 10:  # N_MIN
            assert row.reliability_floor == 0.0
            assert row.propose_licensed is False
            assert row.serve_licensed is False


def test_reader_uses_the_engine_math_not_its_own(tmp_path) -> None:
    # A class that has earned PROPOSE (0.86 >= 0.85) but not SERVE (< 0.99).
    report = _write_practice_report(
        tmp_path,
        {
            "additive": {"correct": 95, "wrong": 5, "refused": 50},
            "novice": {"correct": 0, "wrong": 0, "refused": 4},
        },
    )
    rows = {r.class_name: r for r in calibration.read_calibration_classes(report)}

    earned = rows["additive"]
    # The reader's reliability is the engine's own Wilson floor, to the digit.
    assert earned.reliability_floor == round(conservative_floor(95, 100), 9)
    assert earned.committed == 100
    assert earned.propose_required == 0.85 and earned.propose_licensed is True
    assert earned.serve_required == 0.99 and earned.serve_licensed is False

    novice = rows["novice"]
    assert novice.reliability_floor == 0.0  # below N_MIN
    assert novice.propose_licensed is False


def test_calibration_classes_are_failures_first(tmp_path) -> None:
    report = _write_practice_report(
        tmp_path,
        {
            "earned": {"correct": 95, "wrong": 5, "refused": 0},
            "unearned": {"correct": 0, "wrong": 0, "refused": 9},
        },
    )
    rows = calibration.read_calibration_classes(report)
    # Un-licensed / lowest-reliability comes first.
    assert rows[0].class_name == "unearned"
    assert rows[-1].class_name == "earned"


def test_endpoints_return_items() -> None:
    api = WorkbenchApi()
    r1 = api.handle("GET", "/calibration/classes", b"")
    assert r1.status == 200 and isinstance(r1.payload["data"]["items"], list)
    r2 = api.handle("GET", "/serving/metrics", b"")
    assert r2.status == 200 and isinstance(r2.payload["data"]["items"], list)


def test_missing_practice_report_is_evidence_unavailable(tmp_path) -> None:
    with pytest.raises(EvidenceUnavailableError):
        calibration.read_calibration_classes(tmp_path / "nope.json")
