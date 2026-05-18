"""Learning-loop demo — pins the load-bearing before/after claim.

If any assertion fails, the headline claim ("CORE learned a new chain
from a cold turn and the same prompt is now teaching-grounded with
provenance") no longer holds.
"""

from __future__ import annotations

from evals.learning_loop.run_demo import run_demo


def test_demo_closes_the_full_loop() -> None:
    report = run_demo(emit_json=True)
    assert report["learning_loop_closed"] is True
    assert report["active_corpus_byte_identical"] is True
    assert len(report["scenes"]) == 5


def test_before_is_ungrounded_disclosure() -> None:
    report = run_demo(emit_json=True)
    assert report["before"]["grounding_source"] == "none"
    assert "insufficient grounding" in report["before"]["surface"].lower()


def test_after_is_teaching_grounded_with_new_chain_atoms() -> None:
    report = run_demo(emit_json=True)
    assert report["after"]["grounding_source"] == "teaching"
    surface = report["after"]["surface"].lower()
    # The accepted chain is (narrative, cause, reveals, meaning).
    # ``thought`` was the original cold subject; cognition saturation
    # v2 (commit ``a0edbb4``) added ``cause_thought_reveals_meaning``
    # to the active corpus so the demo switched to ``narrative`` —
    # same shape, still cold.
    assert "narrative" in surface
    assert "reveal" in surface  # humanised connective
    assert "meaning" in surface
    assert "teaching-grounded" in surface


def test_s1_emits_one_discovery_candidate() -> None:
    report = run_demo(emit_json=True)
    s1 = report["scenes"][0]
    assert s1["scene"] == "S1_cold_turn"
    assert s1["detail"]["discovery_candidates_emitted"] >= 1


def test_s3_replay_gate_reports_no_regression() -> None:
    report = run_demo(emit_json=True)
    s3 = report["scenes"][2]
    assert s3["scene"] == "S3_propose_replay_pass"
    ev = s3["detail"]["replay_evidence"]
    assert ev["replay_equivalent"] is True
    assert ev["regressed_metrics"] == []
    assert s3["detail"]["state"] == "pending"


def test_s4_active_corpus_byte_identical_after_accept() -> None:
    report = run_demo(emit_json=True)
    s4 = report["scenes"][3]
    assert s4["scene"] == "S4_accept_against_transient"
    assert s4["detail"]["active_corpus_byte_identical"] is True
    assert s4["detail"]["transient_lines_after"] == s4["detail"]["transient_lines_before"] + 1


def test_same_prompt_drives_before_and_after() -> None:
    """The same input string drives both sides of the before/after pair.
    Different surfaces emerge from the corpus state change alone, not
    from any prompt variation or stochastic sampling."""
    report = run_demo(emit_json=True)
    assert report["prompt"] == "Why does narrative exist?"
    # And the two surfaces are observably different — the loop changed
    # the response, not merely the metadata.
    assert report["before"]["surface"] != report["after"]["surface"]
