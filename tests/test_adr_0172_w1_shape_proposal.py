"""ADR-0172 Tier 1 / W1 — MathReaderRefusalShapeProposal schema tests.

Verifies the eight obligations specified in the ADR-0172 brief:

1. evidence floor: ≥2 evidence rows required.
2. canonical_bytes stability across independent calls.
3. proposal_id determinism.
4. change_kind Literal enforced.
5. JSON-serializable payload enforced.
6. wrong_zero_assertion non-empty (≥40 chars) enforced.
7. reasoning_trace required (None rejected).
8. all four change_kinds round-trip cleanly.

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
# Test 8 — all four change_kinds round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", [
    "matcher_extension",
    "injector_sub_shape",
    "vocabulary_addition",
    "frame_reclassification",
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
