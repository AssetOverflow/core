"""Tests for generate/kernel_facts.py."""
from __future__ import annotations

from fractions import Fraction
import pytest

from generate.kernel_facts import (
    SourceSpan,
    KernelProvenance,
    KernelHazard,
    GroundedScalar,
    GroundedUnit,
    RelationRole,
    CandidateRelation,
    SubstrateFact,
)


def test_source_span_validation() -> None:
    # Valid span
    span = SourceSpan("half", 0, 4, sentence_index=0)
    assert span.text == "half"
    assert span.start == 0
    assert span.end == 4
    assert span.sentence_index == 0

    # Invalid start
    with pytest.raises(ValueError, match="SourceSpan.start must be >= 0"):
        SourceSpan("half", -1, 4)

    # Invalid end
    with pytest.raises(ValueError, match="must be >= start"):
        SourceSpan("half", 4, 3)


def test_kernel_provenance_validation() -> None:
    # Invalid kind
    with pytest.raises(ValueError, match="must be one of"):
        KernelProvenance(kind="unknown_kind")

    # problem_text requires spans
    with pytest.raises(ValueError, match="requires non-empty source_spans"):
        KernelProvenance(kind="problem_text")

    # derived requires input_fact_ids
    with pytest.raises(ValueError, match="requires non-empty input_fact_ids"):
        KernelProvenance(kind="derived")

    # pack/world must not carry source spans
    span = SourceSpan("cent", 0, 4)
    with pytest.raises(ValueError, match="must not carry source_spans"):
        KernelProvenance(kind="kernel_unit", source_spans=(span,))

    # Valid combinations
    prov_text = KernelProvenance(kind="problem_text", source_spans=(SourceSpan("half", 0, 4),))
    assert prov_text.kind == "problem_text"

    prov_derived = KernelProvenance(kind="derived", input_fact_ids=("fact-1",))
    assert prov_derived.kind == "derived"

    prov_unit = KernelProvenance(kind="kernel_unit", pack_id="en_units_v1")
    assert prov_unit.kind == "kernel_unit"


def test_immutability() -> None:
    span = SourceSpan("half", 0, 4)
    with pytest.raises(AttributeError):
        span.start = 1  # type: ignore

    prov = KernelProvenance(kind="problem_text", source_spans=(span,))
    with pytest.raises(AttributeError):
        prov.kind = "derived"  # type: ignore


def test_substrate_fact_construction() -> None:
    span = SourceSpan("half", 0, 4)
    prov = KernelProvenance(kind="problem_text", source_spans=(span,))
    hazard = KernelHazard("haz-1", "unbound_base_quantity", "half", "unbound")

    # 1. GroundedScalar
    scalar = GroundedScalar("fact-1", "half", Fraction(1, 2), prov, (hazard,))
    fact_scalar = SubstrateFact("fact-1", "grounded_scalar", scalar, prov, (hazard,))
    assert fact_scalar.fact_type == "grounded_scalar"
    assert fact_scalar.content == scalar
    assert not fact_scalar.is_speculative

    # Type check for value
    with pytest.raises(TypeError, match="must be Fraction"):
        GroundedScalar("fact-1", "half", 0.5, prov)  # type: ignore

    # 2. GroundedUnit
    unit = GroundedUnit("fact-2", "dollar", "money", "dollar", prov)
    fact_unit = SubstrateFact("fact-2", "grounded_unit", unit, prov)
    assert fact_unit.fact_type == "grounded_unit"
    assert fact_unit.content == unit

    # 3. CandidateRelation
    role = RelationRole("buyer", True, "The buyer")
    rel = CandidateRelation("rel-1", "transaction", (role,), prov, (hazard,))
    fact_rel = SubstrateFact("rel-1", "candidate_relation", rel, prov)
    assert fact_rel.fact_type == "candidate_relation"
    assert fact_rel.content == rel

    # Mismatched fact_type and content
    with pytest.raises(TypeError, match="expects GroundedScalar content"):
        SubstrateFact("fact-1", "grounded_scalar", unit, prov)  # type: ignore


def test_speculative_fact() -> None:
    prov = KernelProvenance(kind="speculative")
    unit = GroundedUnit("fact-2", "dollar", "money", "dollar", prov)
    fact = SubstrateFact("fact-2", "grounded_unit", unit, prov)
    assert fact.is_speculative
