"""ADR-0172 Tier 2 / W5 — MathReaderInferenceProposal schema tests.

11 obligations tested:

1.  evidence floor: ≥3 evidence rows required.
2.  canonical_bytes stability across independent calls.
3.  inference_id determinism.
4.  ratification_effect_kind Literal enforced ("canonicalization_bridge" only).
5.  both arms cannot simultaneously be REJECT at construction.
6.  arm2 PASS requires cases_changed_answer == 0.
7.  reasoning_trace must carry ≥6 steps.
8.  reasoning_trace must include {abstraction, test_design, test_application,
    test_result}.
9.  wrong_zero_assertion ≥40 chars enforced.
10. proposal is frozen (immutable dataclass).
11. to_jsonl_record / from_jsonl_record self-contained round-trip.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

import pytest

from generate.comprehension.audit import AuditRow
from teaching.math_evidence import MathReaderRefusalEvidence, from_audit_row
from teaching.math_reasoning_trace import ReasoningStep, build_trace
from teaching.math_inference_proposal import (
    ArmResult,
    MathReaderInferenceProposal,
    build_arm_result,
    build_inference_proposal,
    canonical_bytes,
    from_jsonl_record,
    to_jsonl_record,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _make_audit_row(case_id: str = "test-001", token_text: str = "stub") -> AuditRow:
    return AuditRow(
        case_id=case_id,
        sentence_index=0,
        token_index=0,
        token_text=token_text,
        recognized_terms=(),
        skipped_frame=None,
        missing_operator="lexicon_entry",
        refusal_reason="unknown_word",
        refusal_detail=f"unknown word: {token_text}",
    )


def _make_evidence(
    case_id: str = "test-001",
    token_text: str = "stub",
) -> MathReaderRefusalEvidence:
    return from_audit_row(
        _make_audit_row(case_id=case_id, token_text=token_text),
        "lexical",
    )


def _three_evidences() -> tuple[MathReaderRefusalEvidence, ...]:
    return (
        _make_evidence("ev-001", "collected"),
        _make_evidence("ev-002", "acquired"),
        _make_evidence("ev-003", "received"),
    )


_STEP_KINDS_TIER2 = (
    "observation",
    "grouping",
    "abstraction",
    "hypothesis",
    "test_design",
    "test_application",
    "test_result",
    "conclusion",
)

_VALID_ASSERTION = (
    "Canonicalization bridge maps acquisition verbs to initial-state "
    "without altering admissibility gates; wrong=0 preserved."
)


def _make_trace(
    kinds: tuple[str, ...] = _STEP_KINDS_TIER2,
) -> Any:
    steps = tuple(
        ReasoningStep(
            step_index=i,
            step_kind=kind,  # type: ignore[arg-type]
            input_pointers=("ev-001", "ev-002", "ev-003"),
            claim=f"step {i} claim",
            justification=f"step {i} justification",
            output_payload={"i": i},
        )
        for i, kind in enumerate(kinds)
    )
    return build_trace(steps)


def _pass_arm1() -> ArmResult:
    return build_arm_result(
        arm="arm1_held_out",
        outcome="PASS",
        cases_tested=10,
        cases_admitted=7,
        cases_changed_answer=0,
    )


def _pass_arm2() -> ArmResult:
    return build_arm_result(
        arm="arm2_known_good",
        outcome="PASS",
        cases_tested=20,
        cases_admitted=20,
        cases_changed_answer=0,
    )


def _build(**overrides: Any) -> MathReaderInferenceProposal:
    kwargs: dict[str, Any] = dict(
        structural_claim=(
            "'<ProperNoun> <acquisition-verb> <count> <noun>' "
            "canonicalizes to '<ProperNoun> has <count> <noun>'"
        ),
        evidence_pointers=_three_evidences(),
        arm1_result=_pass_arm1(),
        arm2_result=_pass_arm2(),
        ratification_effect_kind="canonicalization_bridge",
        ratification_effect_payload={"bridge": "acquisition_to_initial_state_v1"},
        wrong_zero_assertion=_VALID_ASSERTION,
        replay_equivalence_hash="c" * 64,
        reasoning_trace=_make_trace(),
    )
    kwargs.update(overrides)
    return build_inference_proposal(**kwargs)


# ---------------------------------------------------------------------------
# Test 1 — evidence floor: ≥3 rows required
# ---------------------------------------------------------------------------


def test_minimum_three_evidence_rows_rejects_two() -> None:
    """Passing exactly two evidence rows raises ValueError (floor is ≥3)."""
    two_ev = (
        _make_evidence("ev-001", "alpha"),
        _make_evidence("ev-002", "beta"),
    )
    with pytest.raises(ValueError, match="≥3"):
        _build(evidence_pointers=two_ev)


def test_minimum_three_evidence_rows_rejects_one() -> None:
    """Passing a single evidence row raises ValueError."""
    one_ev = (_make_evidence("ev-001", "alpha"),)
    with pytest.raises(ValueError, match="≥3"):
        _build(evidence_pointers=one_ev)


# ---------------------------------------------------------------------------
# Test 2 — canonical_bytes stability
# ---------------------------------------------------------------------------


def test_canonical_bytes_stable() -> None:
    """Same inputs produce byte-identical canonical_bytes across two calls."""
    p1 = _build()
    p2 = _build()
    assert canonical_bytes(p1) == canonical_bytes(p2)


# ---------------------------------------------------------------------------
# Test 3 — inference_id determinism
# ---------------------------------------------------------------------------


def test_inference_id_determinism() -> None:
    """Two independently built proposals from identical inputs share an inference_id."""
    p1 = _build()
    p2 = _build()
    assert p1.inference_id == p2.inference_id
    assert p1.inference_id == hashlib.sha256(canonical_bytes(p1)).hexdigest()


# ---------------------------------------------------------------------------
# Test 4 — ratification_effect_kind Literal enforced
# ---------------------------------------------------------------------------


def test_ratification_effect_kind_must_be_canonicalization_bridge() -> None:
    """Any value other than 'canonicalization_bridge' raises ValueError."""
    with pytest.raises(ValueError, match="canonicalization_bridge"):
        _build(ratification_effect_kind="matcher_extension")


def test_ratification_effect_kind_empty_rejected() -> None:
    """Empty string raises ValueError."""
    with pytest.raises(ValueError, match="canonicalization_bridge"):
        _build(ratification_effect_kind="")


# ---------------------------------------------------------------------------
# Test 5 — both arms cannot simultaneously be REJECT
# ---------------------------------------------------------------------------


def test_both_arms_reject_raises() -> None:
    """arm1=REJECT + arm2=REJECT raises ValueError."""
    reject_arm1 = build_arm_result(
        arm="arm1_held_out",
        outcome="REJECT",
        cases_tested=5,
        cases_admitted=2,
        cases_changed_answer=0,
    )
    reject_arm2 = build_arm_result(
        arm="arm2_known_good",
        outcome="REJECT",
        cases_tested=10,
        cases_admitted=1,
        cases_changed_answer=3,
    )
    with pytest.raises(ValueError, match="both arms"):
        _build(arm1_result=reject_arm1, arm2_result=reject_arm2)


def test_single_reject_arm_is_accepted() -> None:
    """arm1=REJECT with arm2=PASS is a valid construction."""
    reject_arm1 = build_arm_result(
        arm="arm1_held_out",
        outcome="REJECT",
        cases_tested=5,
        cases_admitted=2,
        cases_changed_answer=0,
    )
    # Should not raise — only both-REJECT is forbidden at schema level.
    proposal = _build(arm1_result=reject_arm1, arm2_result=_pass_arm2())
    assert proposal.arm1_result.outcome == "REJECT"
    assert proposal.arm2_result.outcome == "PASS"


# ---------------------------------------------------------------------------
# Test 6 — arm2 PASS requires cases_changed_answer == 0
# ---------------------------------------------------------------------------


def test_arm2_pass_with_changed_answers_raises() -> None:
    """arm2 outcome=PASS but cases_changed_answer>0 raises ValueError."""
    bad_arm2 = build_arm_result(
        arm="arm2_known_good",
        outcome="PASS",
        cases_tested=20,
        cases_admitted=20,
        cases_changed_answer=1,
    )
    with pytest.raises(ValueError, match="cases_changed_answer"):
        _build(arm2_result=bad_arm2)


def test_arm2_neutral_allows_changed_answers() -> None:
    """arm2 outcome=NEUTRAL with cases_changed_answer>0 is valid."""
    neutral_arm2 = build_arm_result(
        arm="arm2_known_good",
        outcome="NEUTRAL",
        cases_tested=20,
        cases_admitted=0,
        cases_changed_answer=2,
    )
    proposal = _build(arm2_result=neutral_arm2)
    assert proposal.arm2_result.outcome == "NEUTRAL"


# ---------------------------------------------------------------------------
# Test 7 — reasoning_trace must carry ≥6 steps
# ---------------------------------------------------------------------------


def test_reasoning_trace_fewer_than_six_steps_raises() -> None:
    """A trace with only 5 steps raises ValueError (floor is ≥6)."""
    five_step_kinds = (
        "observation",
        "abstraction",
        "test_design",
        "test_application",
        "test_result",
    )
    short_trace = _make_trace(kinds=five_step_kinds)
    with pytest.raises(ValueError, match="≥6"):
        _build(reasoning_trace=short_trace)


# ---------------------------------------------------------------------------
# Test 8 — reasoning_trace must include required step kinds
# ---------------------------------------------------------------------------


def test_reasoning_trace_missing_required_kind_raises() -> None:
    """Omitting 'abstraction' from the trace raises ValueError."""
    kinds_without_abstraction = (
        "observation",
        "grouping",
        "hypothesis",
        "test_design",
        "test_application",
        "test_result",
    )
    trace = _make_trace(kinds=kinds_without_abstraction)
    with pytest.raises(ValueError, match="abstraction"):
        _build(reasoning_trace=trace)


def test_reasoning_trace_missing_test_design_raises() -> None:
    """Omitting 'test_design' from the trace raises ValueError."""
    kinds_without_test_design = (
        "observation",
        "grouping",
        "abstraction",
        "hypothesis",
        "test_application",
        "test_result",
    )
    trace = _make_trace(kinds=kinds_without_test_design)
    with pytest.raises(ValueError, match="test_design"):
        _build(reasoning_trace=trace)


# ---------------------------------------------------------------------------
# Test 9 — wrong_zero_assertion ≥40 chars enforced
# ---------------------------------------------------------------------------


def test_wrong_zero_assertion_empty_raises() -> None:
    """Empty wrong_zero_assertion raises ValueError."""
    with pytest.raises(ValueError, match="wrong_zero_assertion"):
        _build(wrong_zero_assertion="")


def test_wrong_zero_assertion_too_short_raises() -> None:
    """An assertion shorter than 40 chars raises ValueError."""
    with pytest.raises(ValueError, match="wrong_zero_assertion"):
        _build(wrong_zero_assertion="short")


# ---------------------------------------------------------------------------
# Test 10 — proposal is frozen
# ---------------------------------------------------------------------------


def test_proposal_is_frozen() -> None:
    """MathReaderInferenceProposal instances are immutable."""
    p = _build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.inference_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 11 — JSONL self-contained round-trip
# ---------------------------------------------------------------------------


def test_to_jsonl_record_self_contained() -> None:
    """to_jsonl_record emits inference_id, full evidence_pointers, arm results,
    and full trace steps inline."""
    p = _build()
    record = to_jsonl_record(p)

    # inference_id present
    assert record["inference_id"] == p.inference_id

    # full evidence dicts (not just hashes)
    assert isinstance(record["evidence_pointers"], list)
    assert len(record["evidence_pointers"]) == 3
    assert isinstance(record["evidence_pointers"][0], dict)
    assert "evidence_hash" in record["evidence_pointers"][0]
    assert "audit_row" in record["evidence_pointers"][0]

    # arm results present
    assert record["arm1_result"]["arm"] == "arm1_held_out"
    assert record["arm2_result"]["arm"] == "arm2_known_good"

    # full trace steps
    assert isinstance(record["reasoning_trace"], dict)
    assert record["reasoning_trace"]["trace_id"] == p.reasoning_trace.trace_id
    assert len(record["reasoning_trace"]["steps"]) == len(_STEP_KINDS_TIER2)


def test_jsonl_record_round_trip() -> None:
    """to_jsonl_record → from_jsonl_record returns an equivalent proposal."""
    p = _build()
    record = to_jsonl_record(p)
    restored = from_jsonl_record(record)

    assert restored.inference_id == p.inference_id
    assert restored.domain == p.domain
    assert restored.structural_claim == p.structural_claim
    assert restored.ratification_effect_kind == p.ratification_effect_kind
    assert restored.replay_equivalence_hash == p.replay_equivalence_hash
    assert restored.reasoning_trace.trace_id == p.reasoning_trace.trace_id
    assert len(restored.evidence_pointers) == len(p.evidence_pointers)
    assert restored.arm1_result == p.arm1_result
    assert restored.arm2_result == p.arm2_result


def test_jsonl_record_byte_stability() -> None:
    """Same proposal → byte-identical JSON line across reruns."""
    p1 = _build()
    p2 = _build()
    line1 = json.dumps(
        to_jsonl_record(p1), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    line2 = json.dumps(
        to_jsonl_record(p2), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert line1 == line2


def test_jsonl_record_inference_id_mismatch_rejected() -> None:
    """A tampered inference_id in the persisted record raises ValueError."""
    p = _build()
    record = to_jsonl_record(p)
    record["inference_id"] = "0" * 64  # tamper

    with pytest.raises(ValueError, match="inference_id mismatch"):
        from_jsonl_record(record)


def test_canonical_bytes_excludes_inference_id() -> None:
    """canonical_bytes (the content-hash function) omits inference_id and
    uses hashes for evidence_pointers — not full dicts."""
    p = _build()
    raw = canonical_bytes(p)
    decoded = json.loads(raw.decode("utf-8"))
    assert "inference_id" not in decoded
    assert all(isinstance(ptr, str) for ptr in decoded["evidence_pointers"])
