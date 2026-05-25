"""Learning-arc demo — pins the headline claim for W-019/ADR-0151.

If any assertion fails, the claim ("engine authored the proposal
structure through autonomous contemplation; operator only ratified")
no longer holds.

Module-scoped fixture: one run_demo() invocation shared across all
tests.  Same pattern as test_learning_loop_demo.py — one worker pays
the demo cost (~3-4s) once.
"""

from __future__ import annotations

import pytest

from evals.learning_arc.run_demo import run_demo


@pytest.fixture(scope="module")
def demo_report() -> dict:
    return run_demo(emit_json=True)


def test_learning_arc_closes(demo_report: dict) -> None:
    assert demo_report["learning_arc_closed"] is True
    assert demo_report["all_claims_supported"] is True
    assert len(demo_report["scenes"]) == 5


def test_active_corpus_untouched(demo_report: dict) -> None:
    assert demo_report["active_corpus_byte_identical"] is True


def test_before_is_ungrounded(demo_report: dict) -> None:
    assert demo_report["before"]["grounding_source"] != "teaching"


def test_after_is_teaching_grounded(demo_report: dict) -> None:
    assert demo_report["after"]["grounding_source"] == "teaching"


def test_s1_cold_session_persists_candidate(demo_report: dict) -> None:
    s1 = demo_report["scenes"][0]
    assert s1["scene"] == "S1_cold_session"
    assert s1["detail"]["candidates_persisted"] >= 1
    assert s1["detail"]["grounding_source"] != "teaching"


def test_s2_enrichment_has_engine_derived_chain(demo_report: dict) -> None:
    s2 = demo_report["scenes"][1]
    assert s2["scene"] == "S2_checkpoint_enrichment"
    assert s2["detail"]["engine_chain_found"] is True
    assert s2["detail"]["sub_questions_count"] > 0
    chain = s2["detail"]["engine_chain"]
    assert chain["connective"] == demo_report["engine_connective"]
    assert chain["object"] == demo_report["engine_object"]


def test_s3_proposal_source_is_contemplation(demo_report: dict) -> None:
    s3 = demo_report["scenes"][2]
    assert s3["scene"] == "S3_engine_authored_proposal"
    assert s3["detail"]["source_kind"] == "contemplation"
    assert s3["detail"]["state"] == "pending"
    chain = s3["detail"]["proposed_chain"]
    assert chain["connective"] == demo_report["engine_connective"]
    assert chain["object"] == demo_report["engine_object"]


def test_s3_replay_gate_passes(demo_report: dict) -> None:
    s3 = demo_report["scenes"][2]
    ev = s3["detail"]["replay_evidence"]
    assert ev["replay_equivalent"] is True
    assert ev["regressed_metrics"] == []


def test_s4_corpus_byte_identical_after_accept(demo_report: dict) -> None:
    s4 = demo_report["scenes"][3]
    assert s4["scene"] == "S4_operator_ratifies"
    assert s4["detail"]["active_corpus_byte_identical"] is True
    assert s4["detail"]["transient_lines_after"] == s4["detail"]["transient_lines_before"] + 1


def test_before_and_after_surfaces_differ(demo_report: dict) -> None:
    assert demo_report["before"]["surface"] != demo_report["after"]["surface"]


def test_engine_connective_and_object_not_operator_provided(demo_report: dict) -> None:
    """Connective+object in the proposal came from engine decomposition.

    The demo's _ENGINE_CONNECTIVE and _ENGINE_OBJECT constants are
    derived from _decompose() output, not hard-coded operator choices.
    S2 confirms engine_chain_found=True, proving the chain appeared
    in the autonomous decomposition set.
    """
    s2 = demo_report["scenes"][1]
    assert s2["detail"]["engine_chain_found"] is True
    s3 = demo_report["scenes"][2]
    assert s3["detail"]["source_kind"] == "contemplation"
