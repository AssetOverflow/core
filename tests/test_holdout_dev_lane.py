"""Held-out dev lane — the honest iteration metric (ADR-pending).

This lane is the instrument the 2026-06-04 sealed-breach post-mortem proved we never
had: 500 real GSM8K cases CORE was NOT built against. Two obligations:

* **Floor (forever):** `wrong == 0` — the engine refuses, never confabulates, on data it
  was not tuned to. This is the property the train_sample could not protect (it hid a
  5-wrong sealed breach).
* **Snapshot (the one a real lift updates):** correct=0 / refused=500 today. Refusing
  everything is the *failing* baseline, not a pass; a genuine capability gain moves
  `correct` up here AND holds wrong=0 on the sealed test.
"""
from __future__ import annotations

from evals.gsm8k_math.holdout_dev.v1.runner import _load_cases, build_report

_REPORT = build_report(_load_cases())


def test_holdout_dev_has_500_cases() -> None:
    assert _REPORT["n"] == 500


def test_wrong_is_zero_the_floor() -> None:
    """FOREVER: never confabulate on held-out data. If this ever fails, a committing
    path is wrong on real GSM8K — exactly the breach class that hid behind train_sample."""
    assert _REPORT["counts"]["wrong"] == 0


def test_current_baseline_snapshot() -> None:
    """Honest baseline: 0 correct / 500 refused. Real GSM8K capability is zero.

    This is the single assertion a genuine capability lift updates — and a lift only
    counts if it also holds wrong=0 on the sealed test (this lane is the dev signal,
    the sealed 1,319 is the arbiter). 'Refuse everything' is the baseline to BEAT.
    """
    assert (_REPORT["counts"]["correct"], _REPORT["counts"]["refused"]) == (0, 500), (
        f"holdout_dev moved to {_REPORT['counts']} — if a real capability change landed, "
        f"update this snapshot AND confirm wrong=0 on the sealed test before claiming lift"
    )
