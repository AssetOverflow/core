"""Edge-deployment budget gate (A2) — deterministic per-turn persistence cost.

Three obligations:
  - EDGE REQUIREMENT (xfail today, strict): per-turn checkpoint bytes must stay under a
    fixed budget regardless of session length — what a constrained offline device can
    afford for an indefinitely-running life. The current O(n) snapshot breaches it, so
    this is an EXPECTED failure that documents the cliff; it flips to a hard failure
    (xpass, strict) the moment incremental/append-only persistence (O(Δ)/turn) lands,
    forcing us to retire the xfail. This is the gate that makes the fix falsifiable.
  - REGRESSION CEILING (passes today): catches a change that makes the cliff worse.
  - DETERMINISM: the byte metric is reproducible (same corpus → identical series), which
    is why it is a valid gate rather than a flaky wall-clock measurement.

Each pipeline turn is ~3s, so the soak runs ONCE (module-scoped) and is kept short —
the cliff already breaches the 16 KiB edge budget by turn ~4. The full 24-turn measured
series lives in ``evals/edge_budget/contract.md``.
"""

from __future__ import annotations

import pytest

from evals.edge_budget.runner import (
    EDGE_PER_TURN_CEILING_BYTES,
    REGRESSION_PER_TURN_CEILING_BYTES,
    REGRESSION_TOTAL_CEILING_BYTES,
    measure,
    run,
)

_TURNS = 8


@pytest.fixture(scope="module")
def report() -> dict:
    return run(_TURNS)  # one soak, shared across the cost assertions


@pytest.mark.xfail(
    strict=True,
    reason=(
        "O(n) per-turn persistence cliff: save_session_state re-serializes the FULL "
        "snapshot every turn, so per-turn bytes grow with the accumulated life. Flips "
        "green when incremental/append-only persistence lands (O(Δ)/turn). See "
        "evals/edge_budget/contract.md."
    ),
)
def test_per_turn_checkpoint_cost_is_within_edge_budget(report) -> None:
    # The edge requirement: bounded per-turn write cost on a constrained device.
    assert report["max_per_turn_bytes"] <= EDGE_PER_TURN_CEILING_BYTES, (
        f"per-turn checkpoint peaked at {report['max_per_turn_bytes']} bytes "
        f"(budget {EDGE_PER_TURN_CEILING_BYTES}); growth_ratio={report['growth_ratio']}"
    )


def test_persistence_cost_regression_ceiling(report) -> None:
    # Passes today; guards against making the cliff materially worse before the fix.
    assert report["max_per_turn_bytes"] <= REGRESSION_PER_TURN_CEILING_BYTES
    assert report["total_bytes_written"] <= REGRESSION_TOTAL_CEILING_BYTES


def test_cost_grows_with_accumulated_state_today(report) -> None:
    # Documents the CURRENT defect: per-turn cost is NOT bounded — it tracks vault
    # growth. (When the fix lands this becomes ~flat; update the assertion then.)
    assert report["final_per_turn_bytes"] > report["first_per_turn_bytes"]
    assert report["growth_ratio"] > 1.0
    assert report["edge_budget_met"] is False  # the cliff is real, on the record


def test_cost_metric_is_deterministic() -> None:
    # The whole point of measuring BYTES (not latency): reproducible → a valid gate.
    a = [c.checkpoint_bytes for c in measure(2)]
    b = [c.checkpoint_bytes for c in measure(2)]
    assert a == b and len(a) == 2
