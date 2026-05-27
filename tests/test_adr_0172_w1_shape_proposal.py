"""ADR-0172 Tier 1 / W1 — MathReaderRefusalShapeProposal schema tests.

Verifies the eight obligations specified in the ADR-0172 brief:

1. evidence floor: ≥2 evidence rows required.
2. canonical_bytes stability across independent calls.
3. proposal_id determinism.
4. change_kind Literal enforced.
5. JSON-serializable payload enforced.
6. wrong_zero_assertion non-empty (≥40 chars) enforced.
7. reasoning_trace required (None rejected).
8. all five change_kinds round-trip cleanly (including ADR-0169 CC-2's composition_reclassification).

W0 dependency: ``teaching/math_reasoning_trace.py`` (A1 branch) has not
landed yet.  Tests use a minimal stub that exposes the ``trace_id`` duck-
typing contract used by :func:`build_proposal`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.audit import AuditRow
from teaching.math_evidence import MathReaderRefusalEvidence, from_audit_row
from teaching.math_contemplation_proposal import (
    MathReaderRefusalShapeProposal,
    build_proposal,
    canonical_bytes,
)


# ---------------------------------------------------------------------------
# Stubs — W0 ReasoningTrace not yet merged; duck-type the trace_id contract.
# ---------------------------------------------------------------------------


class _StubReasoningTrace:
    """Minimal stand-in for teaching.math_reasoning_trace.ReasoningTrace.

    Carries only the attributes accessed by :func:`build_proposal` and
    :func:`canonical_bytes`.  Replaced by the real type when A1 lands.
    """

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id


# ---------------------------------------------------------------------------
# Shared fixtures
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
    return from_audit_row(_make_audit_row(case_id=case_id, token_text=token_text), "lexical")


def _two_evidences() -> tuple[MathReaderRefusalEvidence, ...]:
    return (
        _make_evidence("ev-001", "alpha"),
        _make_evidence("ev-002", "beta"),
    )


_VALID_TRACE = _StubReasoningTrace("a" * 64)
_VALID_ASSERTION = "This injector does not admit case 0050 or any ambiguous shape, preserving wrong=0."


def _build(**overrides: Any) -> MathReaderRefusalShapeProposal:
    """Build a valid proposal, optionally overriding fields."""
    kwargs: dict[str, Any] = dict(
        shape_category=ShapeCategory.RATE_WITH_CURRENCY,
        structural_commonality="subject earns currency per time-unit",
        evidence_pointers=_two_evidences(),
        proposed_change_kind="injector_sub_shape",
        proposed_change_payload={"narrow_form": "$<amount> per <unit>"},
        wrong_zero_assertion=_VALID_ASSERTION,
        replay_equivalence_hash="b" * 64,
        reasoning_trace=_VALID_TRACE,
    )
    kwargs.update(overrides)
    return build_proposal(**kwargs)


# ---------------------------------------------------------------------------
# Test 1 — evidence floor
# ---------------------------------------------------------------------------


def test_minimum_two_evidence_rows() -> None:
    """Passing a single evidence row raises ValueError."""
    single = (_make_evidence("ev-only", "x"),)
    with pytest.raises(ValueError, match="≥2"):
        _build(evidence_pointers=single)


# ---------------------------------------------------------------------------
# Test 2 — canonical_bytes stability
# ---------------------------------------------------------------------------


def test_canonical_bytes_stable() -> None:
    """Same inputs produce byte-identical canonical_bytes across two calls."""
    p1 = _build()
    p2 = _build()
    assert canonical_bytes(p1) == canonical_bytes(p2)


# ---------------------------------------------------------------------------
# Test 3 — proposal_id determinism
# ---------------------------------------------------------------------------


def test_proposal_id_determinism() -> None:
    """Two independently built proposals from identical inputs share a proposal_id."""
    p1 = _build()
    p2 = _build()
    assert p1.proposal_id == p2.proposal_id
    assert p1.proposal_id == hashlib.sha256(canonical_bytes(p1)).hexdigest()


# ---------------------------------------------------------------------------
# Test 4 — change_kind Literal enforced
# ---------------------------------------------------------------------------


def test_change_kind_literal_enforced() -> None:
    """An unrecognised change_kind string raises ValueError."""
    with pytest.raises(ValueError, match="proposed_change_kind"):
        _build(proposed_change_kind="totally_invented_kind")


# ---------------------------------------------------------------------------
# Test 5 — JSON-serializable payload enforced
# ---------------------------------------------------------------------------


def test_change_payload_must_be_json_serializable() -> None:
    """A set() payload is not JSON-serializable and must raise ValueError."""
    with pytest.raises(ValueError, match="JSON-serializable"):
        _build(proposed_change_payload={1, 2, 3})


# ---------------------------------------------------------------------------
# Test 6 — wrong_zero_assertion required
# ---------------------------------------------------------------------------


def test_wrong_zero_assertion_required_empty() -> None:
    """Empty wrong_zero_assertion raises ValueError."""
    with pytest.raises(ValueError, match="wrong_zero_assertion"):
        _build(wrong_zero_assertion="")


def test_wrong_zero_assertion_too_short() -> None:
    """An assertion shorter than 40 chars raises ValueError."""
    with pytest.raises(ValueError, match="wrong_zero_assertion"):
        _build(wrong_zero_assertion="too short")


# ---------------------------------------------------------------------------
# Test 7 — reasoning_trace required
# ---------------------------------------------------------------------------


def test_reasoning_trace_required_none() -> None:
    """Passing reasoning_trace=None raises ValueError."""
    with pytest.raises(ValueError, match="reasoning_trace"):
        _build(reasoning_trace=None)


def test_reasoning_trace_required_missing_trace_id() -> None:
    """An object without a trace_id attribute raises ValueError."""

    class _BadTrace:
        pass

    with pytest.raises(ValueError, match="trace_id"):
        _build(reasoning_trace=_BadTrace())


def test_reasoning_trace_required_empty_trace_id() -> None:
    """An object with an empty string trace_id raises ValueError."""
    with pytest.raises(ValueError, match="trace_id"):
        _build(reasoning_trace=_StubReasoningTrace(""))


# ---------------------------------------------------------------------------
# Test 8 — all five change_kinds round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", [
    "matcher_extension",
    "injector_sub_shape",
    "vocabulary_addition",
    "frame_reclassification",
    "composition_reclassification",  # ADR-0169 CC-2
])
def test_all_four_change_kinds_round_trip(kind: str) -> None:
    """Every valid change_kind is accepted and round-trips through the schema."""
    p = _build(proposed_change_kind=kind)
    assert p.proposed_change_kind == kind
    assert p.domain == "math"
    assert isinstance(p.shape_category, ShapeCategory)
    assert p.proposal_id != ""


# ---------------------------------------------------------------------------
# Bonus: proposal is frozen
# ---------------------------------------------------------------------------


def test_proposal_is_frozen() -> None:
    """MathReaderRefusalShapeProposal instances are immutable."""
    p = _build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.proposal_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Bonus: proposal_id changes when shape_category changes
# ---------------------------------------------------------------------------


def test_proposal_id_sensitive_to_shape_category() -> None:
    """Different shape_category values produce different proposal_ids."""
    p1 = _build(shape_category=ShapeCategory.RATE_WITH_CURRENCY)
    p2 = _build(shape_category=ShapeCategory.CURRENCY_AMOUNT)
    assert p1.proposal_id != p2.proposal_id


# ---------------------------------------------------------------------------
# ADR-0172 tightening follow-up #1 — self-contained JSONL round-trip
# ---------------------------------------------------------------------------


def _build_with_real_trace(**overrides: Any) -> MathReaderRefusalShapeProposal:
    """Build a proposal using a real ReasoningTrace (round-trip requires it)."""
    from teaching.math_reasoning_trace import ReasoningStep, build_trace

    steps = tuple(
        ReasoningStep(
            step_index=i,
            step_kind=kind,
            input_pointers=("ev-001", "ev-002"),
            claim=f"step {i} claim",
            justification=f"step {i} justification",
            output_payload={"i": i},
        )
        for i, kind in enumerate(
            ("observation", "grouping", "hypothesis", "conclusion")
        )
    )
    trace = build_trace(steps)
    kwargs: dict[str, Any] = dict(
        shape_category=ShapeCategory.RATE_WITH_CURRENCY,
        structural_commonality="subject earns currency per time-unit",
        evidence_pointers=_two_evidences(),
        proposed_change_kind="injector_sub_shape",
        proposed_change_payload={"narrow_form": "$<amount> per <unit>"},
        wrong_zero_assertion=_VALID_ASSERTION,
        replay_equivalence_hash="b" * 64,
        reasoning_trace=trace,
    )
    kwargs.update(overrides)
    return build_proposal(**kwargs)


def test_to_jsonl_record_self_contained() -> None:
    """to_jsonl_record emits proposal_id, full evidence_pointers, full trace steps."""
    from teaching.math_contemplation_proposal import to_jsonl_record

    proposal = _build_with_real_trace()
    record = to_jsonl_record(proposal)

    # proposal_id is present (canonical_bytes omits it; this is the difference)
    assert record["proposal_id"] == proposal.proposal_id

    # evidence_pointers are nested dicts (not just hashes)
    assert isinstance(record["evidence_pointers"], list)
    assert len(record["evidence_pointers"]) == 2
    assert isinstance(record["evidence_pointers"][0], dict)
    assert "evidence_hash" in record["evidence_pointers"][0]
    assert "audit_row" in record["evidence_pointers"][0]

    # reasoning_trace carries full steps inline (not just trace_id)
    assert isinstance(record["reasoning_trace"], dict)
    assert record["reasoning_trace"]["trace_id"] == proposal.reasoning_trace.trace_id
    assert len(record["reasoning_trace"]["steps"]) == 4


def test_jsonl_record_round_trip() -> None:
    """to_jsonl_record → from_jsonl_record returns an equivalent proposal."""
    from teaching.math_contemplation_proposal import from_jsonl_record, to_jsonl_record

    proposal = _build_with_real_trace()
    record = to_jsonl_record(proposal)
    restored = from_jsonl_record(record)

    assert restored.proposal_id == proposal.proposal_id
    assert restored.domain == proposal.domain
    assert restored.proposed_change_kind == proposal.proposed_change_kind
    assert restored.shape_category == proposal.shape_category
    assert restored.replay_equivalence_hash == proposal.replay_equivalence_hash
    assert restored.reasoning_trace.trace_id == proposal.reasoning_trace.trace_id
    assert len(restored.evidence_pointers) == len(proposal.evidence_pointers)


def test_jsonl_record_byte_stability() -> None:
    """Same proposal → byte-identical JSON line across reruns (sort_keys=True)."""
    from teaching.math_contemplation_proposal import to_jsonl_record

    p1 = _build_with_real_trace()
    p2 = _build_with_real_trace()
    line1 = json.dumps(
        to_jsonl_record(p1), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    line2 = json.dumps(
        to_jsonl_record(p2), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert line1 == line2


def test_jsonl_record_proposal_id_mismatch_rejected() -> None:
    """A tampered proposal_id in the persisted record raises ValueError."""
    from teaching.math_contemplation_proposal import from_jsonl_record, to_jsonl_record

    proposal = _build_with_real_trace()
    record = to_jsonl_record(proposal)
    record["proposal_id"] = "0" * 64  # tamper

    with pytest.raises(ValueError, match="proposal_id mismatch"):
        from_jsonl_record(record)


def test_canonical_bytes_unchanged_by_tightening() -> None:
    """canonical_bytes (the content-hash function) still omits proposal_id.

    Tightening follow-up #1 added to_jsonl_record as a SEPARATE serializer;
    canonical_bytes itself must remain stable so trace_id and proposal_id
    derivations don't shift.
    """
    proposal = _build_with_real_trace()
    raw = canonical_bytes(proposal)
    decoded = json.loads(raw.decode("utf-8"))
    assert "proposal_id" not in decoded
    # evidence_pointers in canonical_bytes are still hash strings, not dicts
    assert all(isinstance(p, str) for p in decoded["evidence_pointers"])
