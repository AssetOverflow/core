"""Learning-loop demo — pins the load-bearing before/after claim.

If any assertion fails, the headline claim ("CORE learned a new chain
from a cold turn and the same prompt is now teaching-grounded with
provenance") no longer holds.

Performance: ``run_demo()`` exercises the full pipeline including the
replay-equivalence gate (which itself runs the cognition public split
twice).  Each invocation costs ~2-3s.  A module-scoped fixture caches
the report so every assertion in this file shares one demo run —
reduces this file's runtime from ~15s (7 × 2s) to ~2s.

Compatibility with pytest-xdist: pytest-xdist distributes by test, not
by module; module-scoped fixtures are re-evaluated per worker that
picks up a test from this file.  Worst case one worker takes the
whole file's 2s; xdist still parallelises across the rest of the
suite.
"""

from __future__ import annotations

import pytest

from evals.learning_loop.run_demo import run_demo


@pytest.fixture(scope="module")
def demo_report() -> dict:
    """One ``run_demo()`` invocation shared across every test in this
    module.  Module-scoped so pytest-xdist's per-worker isolation
    still applies (a worker that picks up any test in this file pays
    the demo cost once)."""
    return run_demo(emit_json=True)


def test_demo_closes_the_full_loop(demo_report: dict) -> None:
    assert demo_report["learning_loop_closed"] is True
    assert demo_report["active_corpus_byte_identical"] is True
    assert len(demo_report["scenes"]) == 5


def test_before_is_ungrounded_disclosure(demo_report: dict) -> None:
    assert demo_report["before"]["grounding_source"] == "none"
    assert "insufficient grounding" in demo_report["before"]["surface"].lower()


def test_after_is_teaching_grounded_with_new_chain_atoms(demo_report: dict) -> None:
    assert demo_report["after"]["grounding_source"] == "teaching"
    surface = demo_report["after"]["surface"].lower()
    # The accepted chain is (narrative, cause, reveals, meaning).
    # ``thought`` was the original cold subject; cognition saturation
    # v2 (commit ``a0edbb4``) added ``cause_thought_reveals_meaning``
    # to the active corpus so the demo switched to ``narrative`` —
    # same shape, still cold.
    assert "narrative" in surface
    assert "reveal" in surface  # humanised connective
    assert "meaning" in surface
    assert "teaching-grounded" in surface


def test_s1_emits_one_discovery_candidate(demo_report: dict) -> None:
    s1 = demo_report["scenes"][0]
    assert s1["scene"] == "S1_cold_turn"
    assert s1["detail"]["discovery_candidates_emitted"] >= 1


def test_s3_replay_gate_reports_no_regression(demo_report: dict) -> None:
    s3 = demo_report["scenes"][2]
    assert s3["scene"] == "S3_propose_replay_pass"
    ev = s3["detail"]["replay_evidence"]
    assert ev["replay_equivalent"] is True
    assert ev["regressed_metrics"] == []
    assert s3["detail"]["state"] == "pending"


def test_s4_active_corpus_byte_identical_after_accept(demo_report: dict) -> None:
    s4 = demo_report["scenes"][3]
    assert s4["scene"] == "S4_accept_against_transient"
    assert s4["detail"]["active_corpus_byte_identical"] is True
    assert s4["detail"]["transient_lines_after"] == s4["detail"]["transient_lines_before"] + 1


def test_same_prompt_drives_before_and_after(demo_report: dict) -> None:
    """The same input string drives both sides of the before/after pair.
    Different surfaces emerge from the corpus state change alone, not
    from any prompt variation or stochastic sampling."""
    assert demo_report["prompt"] == "Why does narrative exist?"
    # And the two surfaces are observably different — the loop changed
    # the response, not merely the metadata.
    assert demo_report["before"]["surface"] != demo_report["after"]["surface"]
