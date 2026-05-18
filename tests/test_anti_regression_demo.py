"""Anti-regression demo — pins each scene's load-bearing claim.

These are the falsifiable assertions the demo would make to a viewer.
If any assertion fails, the demo's headline claim no longer holds.
"""

from __future__ import annotations

from evals.anti_regression.run_demo import run_demo


def test_demo_runs_to_completion_with_all_three_gates_holding() -> None:
    report = run_demo(emit_json=True)
    assert report["all_gates_held"] is True
    assert report["active_corpus_byte_identical"] is True
    assert len(report["scenes"]) == 3


def test_s1_eligibility_gate_rejects_pre_replay() -> None:
    report = run_demo(emit_json=True)
    s1 = report["scenes"][0]
    assert s1["scene"] == "S1_eligibility_gate"
    assert s1["outcome"] == "rejected_pre_replay"
    assert s1["proposal_id"] is None
    assert s1["replay_evidence"] is None
    assert "undetermined" in (s1["error"] or "")
    assert s1["corpus_byte_identical"] is True


def test_s2_replay_gate_auto_rejects_with_named_metrics() -> None:
    report = run_demo(emit_json=True)
    s2 = report["scenes"][1]
    assert s2["scene"] == "S2_replay_auto_reject"
    assert s2["outcome"] == "auto_rejected_on_regression"
    assert s2["review_state"] == "rejected"
    assert s2["replay_evidence"]["replay_equivalent"] is False
    assert "surface_groundedness" in s2["replay_evidence"]["regressed_metrics"]
    assert "term_capture_rate" in s2["replay_evidence"]["regressed_metrics"]
    # The operator note must name the regressed metrics.
    assert "surface_groundedness" in s2["operator_note"]
    assert "term_capture_rate" in s2["operator_note"]
    assert s2["corpus_byte_identical"] is True


def test_s3_real_gate_passes_to_pending_not_accepted() -> None:
    report = run_demo(emit_json=True)
    s3 = report["scenes"][2]
    assert s3["scene"] == "S3_real_gate_pass_through"
    assert s3["outcome"] == "pending_awaiting_operator"
    assert s3["review_state"] == "pending"
    assert s3["replay_evidence"]["replay_equivalent"] is True
    assert s3["replay_evidence"]["regressed_metrics"] == []
    assert s3["corpus_byte_identical"] is True


def test_active_corpus_never_touched_across_full_demo() -> None:
    """Defence-in-depth: even though each scene asserts byte-identity,
    re-confirm at the report level — the demo never writes to the
    production teaching corpus regardless of scene outcomes."""
    report = run_demo(emit_json=True)
    assert report["active_corpus_byte_identical"] is True
    for scene in report["scenes"]:
        assert scene["corpus_byte_identical"] is True
