"""Regression tests for ``core eval`` failure-printer scope.

Before this fix the failure-printer in ``cmd_eval`` hardcoded the
cognition-lane field names (``intent_correct`` / ``versor_closure``) into
``result.case_details`` lookup.  Any non-cognition lane that returned clean
``case_details`` without those keys then triggered a spurious
``failures (N): <case_id>: intent, versor=0.00e+00`` block at the end of the
human-readable output, even though all metrics passed.

The fix gates that printer on ``lane_name == "cognition"``, mirroring the
gate already used for the worker preamble.  These tests pin the corrected
behavior so the printer cannot regress to a generic, lane-blind condition.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import pytest

import core.cli as cli_module


@dataclass(frozen=True)
class _StubLaneResult:
    """Mimics ``evals.framework.LaneResult.as_dict``-shaped output."""

    lane: str
    version: str
    split: str
    metrics: dict[str, Any]
    case_details: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "version": self.version,
            "split": self.split,
            "metrics": self.metrics,
            "case_details": self.case_details,
        }


@dataclass(frozen=True)
class _StubLane:
    name: str
    versions: tuple[str, ...] = ("v1",)


def _eval_args(lane: str, **overrides: Any) -> argparse.Namespace:
    defaults = dict(
        list_lanes=False,
        lane=lane,
        version=None,
        split="public",
        workers=None,
        json=False,
        save=False,
        report=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _install_stub_framework(
    monkeypatch: pytest.MonkeyPatch,
    *,
    lane_name: str,
    metrics: dict[str, Any],
    case_details: list[dict[str, Any]],
) -> None:
    """Replace ``evals.framework`` with deterministic stubs."""
    import evals.framework as framework

    stub_lane = _StubLane(name=lane_name)
    stub_result = _StubLaneResult(
        lane=lane_name,
        version="v1",
        split="public",
        metrics=metrics,
        case_details=case_details,
    )
    monkeypatch.setattr(framework, "get_lane", lambda name: stub_lane)
    monkeypatch.setattr(
        framework,
        "run_lane",
        lambda lane, version, split, workers: stub_result,
    )


def test_non_cognition_lane_does_not_emit_failures_block(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A clean non-cognition lane must not produce a 'failures' tail."""
    _install_stub_framework(
        monkeypatch,
        lane_name="contemplation_quality",
        metrics={
            "total": 9,
            "passed": 9,
            "failed": 0,
            "pass_rate": 1.0,
            "all_passed": True,
            "source_digest": "deadbeef",
        },
        case_details=[
            {
                "case_id": "learning_arc_demo",
                "source": "core demo learning-arc --json",
                "passed": True,
                "source_digest": "deadbeef",
                "metrics": [],
            }
        ],
    )

    rc = cli_module.cmd_eval(_eval_args("contemplation_quality"))
    captured = capsys.readouterr()

    assert rc == 0
    assert "failures (" not in captured.out
    assert "intent, versor=" not in captured.out
    # The clean human-readable summary must still emit lane metadata.
    assert "lane           : contemplation_quality" in captured.out
    assert "pass_rate      : 100.0%" in captured.out


def test_cognition_lane_still_prints_real_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The cognition-specific printer must still fire for cognition cases."""
    _install_stub_framework(
        monkeypatch,
        lane_name="cognition",
        metrics={"total": 2, "intent_accuracy": 0.5},
        case_details=[
            {
                "case_id": "case_pass",
                "intent_correct": True,
                "versor_closure": True,
            },
            {
                "case_id": "case_fail",
                "intent_correct": False,
                "versor_closure": False,
                "versor_condition": 1.2e-5,
            },
        ],
    )
    # ``cmd_eval`` calls ``load_cases`` and ``normalize_workers`` for the
    # cognition preamble; stub them too so the test stays hermetic.
    import evals.framework as framework
    import evals._parallel as parallel

    monkeypatch.setattr(framework, "load_cases", lambda path: [None, None])
    monkeypatch.setattr(parallel, "normalize_workers", lambda w, n: 1)
    # ``lane.public_cases_path(version)`` must not blow up; stub on the
    # _StubLane instance.
    stub_lane = framework.get_lane("cognition")  # picks up the monkeypatched stub
    setattr(stub_lane.__class__, "public_cases_path", lambda self, v: "<stub>")
    setattr(stub_lane.__class__, "dev_cases_path", lambda self: "<stub>")
    setattr(stub_lane.__class__, "holdout_cases_path", lambda self, v: "<stub>")

    rc = cli_module.cmd_eval(_eval_args("cognition"))
    captured = capsys.readouterr()

    assert rc == 0
    assert "failures (1):" in captured.out
    assert "case_fail" in captured.out
    assert "intent" in captured.out
    assert "versor=1.20e-05" in captured.out
    # The passing case must not appear in the failures tail.
    assert "case_pass:" not in captured.out


def test_cognition_lane_with_no_failures_omits_failures_block(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The failures block must not emit a hollow header when nothing failed."""
    _install_stub_framework(
        monkeypatch,
        lane_name="cognition",
        metrics={"total": 1, "intent_accuracy": 1.0},
        case_details=[
            {
                "case_id": "case_ok",
                "intent_correct": True,
                "versor_closure": True,
            },
        ],
    )
    import evals.framework as framework
    import evals._parallel as parallel

    monkeypatch.setattr(framework, "load_cases", lambda path: [None])
    monkeypatch.setattr(parallel, "normalize_workers", lambda w, n: 1)
    stub_lane = framework.get_lane("cognition")
    setattr(stub_lane.__class__, "public_cases_path", lambda self, v: "<stub>")
    setattr(stub_lane.__class__, "dev_cases_path", lambda self: "<stub>")
    setattr(stub_lane.__class__, "holdout_cases_path", lambda self, v: "<stub>")

    rc = cli_module.cmd_eval(_eval_args("cognition"))
    captured = capsys.readouterr()

    assert rc == 0
    assert "failures (" not in captured.out


def test_json_mode_skips_printer_entirely(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--json`` output must not be polluted by the human printer."""
    _install_stub_framework(
        monkeypatch,
        lane_name="contemplation_quality",
        metrics={"total": 9, "all_passed": True},
        case_details=[{"case_id": "learning_arc_demo", "passed": True}],
    )

    rc = cli_module.cmd_eval(_eval_args("contemplation_quality", json=True))
    captured = capsys.readouterr()

    assert rc == 0
    assert "failures (" not in captured.out
    assert "lane           :" not in captured.out  # no human preamble in --json
