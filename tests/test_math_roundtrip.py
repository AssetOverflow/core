"""ADR-0126 — tests for the round-trip admissibility filter.

Exercises every rejection criterion. If a single test here fails, the
wrong-answer firewall has a hole and the whole candidate-graph
architecture is unsound — these are the load-bearing assertions.
"""

from __future__ import annotations

import pytest

from generate.math_problem_graph import (
    Comparison,
    Operation,
    Quantity,
    Rate,
)
from generate.math_roundtrip import (
    ADD_VERBS,
    KIND_TO_VERBS,
    SUBTRACT_VERBS,
    CandidateOperation,
    _tokens,
    roundtrip_admissible,
)


# ---------------------------------------------------------------------------
# Sanity: verb registry contracts.
# ---------------------------------------------------------------------------

class TestVerbRegistry:
    def test_kind_to_verbs_covers_all_operation_kinds(self) -> None:
        from generate.math_problem_graph import VALID_OPERATION_KINDS
        for kind in VALID_OPERATION_KINDS:
            assert kind in KIND_TO_VERBS, f"{kind} missing from KIND_TO_VERBS"

    def test_add_subtract_disjoint_modulo_known_overlaps(self) -> None:
        # The two ambiguous overlap groups (give/send/return) are
        # intentional — they fire as both subtract candidates and
        # transfer candidates; the filter rejects whichever does not
        # match the grounded slots.
        intentional_overlap = {"give", "gives", "gave", "send", "sends", "sent",
                               "return", "returns", "returned"}
        unintentional = (ADD_VERBS & SUBTRACT_VERBS) - intentional_overlap
        assert unintentional == frozenset()

    def test_tokenization_word_boundary(self) -> None:
        toks = _tokens("Sam ate three apples.")
        assert "ate" in toks
        assert "states" not in toks
        assert "apples" in toks  # plural NOT stemmed
        assert "apple" not in toks


# ---------------------------------------------------------------------------
# Positive cases — every operation kind admits a clean candidate.
# ---------------------------------------------------------------------------

class TestPositiveAdmission:
    def test_add_with_digit(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)

    def test_add_with_word_number(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys three apples.",
            matched_verb="buys",
            matched_value_token="three",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)

    def test_subtract_past_tense(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="subtract",
                         operand=Quantity(value=2, unit="apples")),
            source_span="Sam ate 2 apples.",
            matched_verb="ate",
            matched_value_token="2",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)

    def test_transfer(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="transfer",
                         operand=Quantity(value=4, unit="apples"),
                         target="Tom"),
            source_span="Sam gives 4 apples to Tom.",
            matched_verb="gives",
            matched_value_token="4",
            matched_unit_token="apples",
            matched_actor_token="Sam",
            matched_target_token="Tom",
        )
        assert roundtrip_admissible(c)

    def test_apply_rate(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="apply_rate",
                         operand=Rate(value=2.0, numerator_unit="dollars",
                                      denominator_unit="apple")),
            source_span="Apples cost 2 dollars per apple.",
            matched_verb="per",
            matched_value_token="2",
            matched_unit_token="dollars",
            matched_actor_token="Apples",
        )
        assert roundtrip_admissible(c)

    def test_compare_additive(self) -> None:
        c = CandidateOperation(
            op=Operation(
                actor="Sam", kind="compare_additive",
                operand=Comparison(
                    reference_actor="Tom",
                    delta=Quantity(value=3, unit="apples"),
                    factor=None, direction="more",
                ),
            ),
            source_span="Sam has 3 more apples than Tom.",
            matched_verb="more",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="Sam",
            matched_reference_actor_token="Tom",
        )
        assert roundtrip_admissible(c)

    def test_compare_multiplicative_anchor(self) -> None:
        c = CandidateOperation(
            op=Operation(
                actor="Sam", kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor="Tom", delta=None, factor=2.0,
                    direction="times",
                ),
            ),
            source_span="Sam has twice as many apples as Tom.",
            matched_verb="twice",
            matched_value_token="twice",  # anchor carries the factor
            matched_unit_token="apples",
            matched_actor_token="Sam",
            matched_reference_actor_token="Tom",
        )
        assert roundtrip_admissible(c)

    def test_compare_multiplicative_implicit_unit(self) -> None:
        # "Sam has twice as many as Tom" — no unit token in source
        c = CandidateOperation(
            op=Operation(
                actor="Sam", kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor="Tom", delta=None, factor=2.0,
                    direction="times",
                ),
            ),
            source_span="Sam has twice as many as Tom.",
            matched_verb="twice",
            matched_value_token="twice",
            matched_unit_token="",  # empty allowed for comparisons
            matched_actor_token="Sam",
            matched_reference_actor_token="Tom",
        )
        assert roundtrip_admissible(c)


# ---------------------------------------------------------------------------
# Negative cases — the wrong-answer firewall.
# ---------------------------------------------------------------------------

class TestRejection:
    def test_rejects_verb_not_registered_for_kind(self) -> None:
        # Parser hallucinates: "loses" claimed as add. "loses" is in
        # SUBTRACT_VERBS, not ADD_VERBS, so this must reject.
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=2, unit="apples")),
            source_span="Sam loses 2 apples.",
            matched_verb="loses",  # wrong kind!
            matched_value_token="2",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(c)

    def test_rejects_verb_absent_from_source(self) -> None:
        # Parser hallucinates: "buys" claimed but source doesn't contain it.
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=2, unit="apples")),
            source_span="Sam has 2 apples.",  # no "buys"
            matched_verb="buys",
            matched_value_token="2",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(c)

    def test_rejects_value_absent_from_source(self) -> None:
        # Parser hallucinates: claims value 7 but source has 3.
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=7, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="7",  # not in source
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(c)

    def test_rejects_unit_absent_from_source(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="oranges")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="oranges",  # not in source
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(c)

    def test_rejects_actor_absent_from_source(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Tom", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="Tom",  # not in source
        )
        assert not roundtrip_admissible(c)

    def test_rejects_transfer_target_absent_from_source(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="transfer",
                         operand=Quantity(value=4, unit="apples"),
                         target="Alice"),
            source_span="Sam gives 4 apples to Tom.",
            matched_verb="gives",
            matched_value_token="4",
            matched_unit_token="apples",
            matched_actor_token="Sam",
            matched_target_token="Alice",  # not in source
        )
        assert not roundtrip_admissible(c)

    def test_rejects_comparison_reference_absent_from_source(self) -> None:
        c = CandidateOperation(
            op=Operation(
                actor="Sam", kind="compare_additive",
                operand=Comparison(
                    reference_actor="Alice",
                    delta=Quantity(value=3, unit="apples"),
                    factor=None, direction="more",
                ),
            ),
            source_span="Sam has 3 more apples than Tom.",
            matched_verb="more",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="Sam",
            matched_reference_actor_token="Alice",  # not in source
        )
        assert not roundtrip_admissible(c)

    def test_rejects_rate_denominator_unit_absent(self) -> None:
        # Rate claims "per banana" but source says "per apple".
        c = CandidateOperation(
            op=Operation(actor="Apples", kind="apply_rate",
                         operand=Rate(value=2.0, numerator_unit="dollars",
                                      denominator_unit="banana")),
            source_span="Apples cost 2 dollars per apple.",
            matched_verb="per",
            matched_value_token="2",
            matched_unit_token="dollars",
            matched_actor_token="Apples",
        )
        assert not roundtrip_admissible(c)

    def test_rejects_empty_unit_for_non_comparison(self) -> None:
        # Empty unit token is only legal for comparison operands.
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="",  # empty not allowed for add
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(c)


# ---------------------------------------------------------------------------
# Number-form grounding cross-equivalence.
# ---------------------------------------------------------------------------

class TestNumberGrounding:
    def test_digit_grounds_when_source_uses_word(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys three apples.",
            matched_verb="buys",
            matched_value_token="3",  # source has "three"
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)

    def test_word_grounds_when_source_uses_digit(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="three",  # source has "3"
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)


class TestMultiWordUnitGrounding:
    """Multi-word units (e.g. 'Pokemon cards') ground when every
    component word appears in source. Conjunctive — missing one
    component refuses, preserving wrong=0."""

    def test_two_word_unit_grounds_when_both_components_present(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Nicole", kind="add",
                         operand=Quantity(value=400, unit="Pokemon cards")),
            source_span="Nicole collected 400 Pokemon cards.",
            matched_verb="collected",
            matched_value_token="400",
            matched_unit_token="Pokemon cards",
            matched_actor_token="Nicole",
        )
        assert roundtrip_admissible(c)

    def test_two_word_unit_refuses_when_one_component_missing(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Nicole", kind="add",
                         operand=Quantity(value=400, unit="Pokemon cards")),
            source_span="Nicole collected 400 cards.",  # 'Pokemon' missing
            matched_verb="collected",
            matched_value_token="400",
            matched_unit_token="Pokemon cards",
            matched_actor_token="Nicole",
        )
        assert not roundtrip_admissible(c)

    def test_single_word_unit_unaffected(self) -> None:
        c = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=3, unit="apples")),
            source_span="Sam buys 3 apples.",
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert roundtrip_admissible(c)


# ---------------------------------------------------------------------------
# Constructor validation — illegal CandidateOperation states are
# refused at construction (not at filter time).
# ---------------------------------------------------------------------------

class TestConstructorInvariants:
    def test_transfer_requires_target_token(self) -> None:
        with pytest.raises(ValueError, match="matched_target_token required"):
            CandidateOperation(
                op=Operation(actor="Sam", kind="transfer",
                             operand=Quantity(value=4, unit="apples"),
                             target="Tom"),
                source_span="Sam gives 4 apples to Tom.",
                matched_verb="gives",
                matched_value_token="4",
                matched_unit_token="apples",
                matched_actor_token="Sam",
                matched_target_token=None,  # missing
            )

    def test_non_transfer_must_not_carry_target_token(self) -> None:
        with pytest.raises(ValueError, match="matched_target_token only valid"):
            CandidateOperation(
                op=Operation(actor="Sam", kind="add",
                             operand=Quantity(value=3, unit="apples")),
                source_span="Sam buys 3 apples.",
                matched_verb="buys",
                matched_value_token="3",
                matched_unit_token="apples",
                matched_actor_token="Sam",
                matched_target_token="Tom",  # not allowed for add
            )

    def test_comparison_requires_reference_actor_token(self) -> None:
        with pytest.raises(ValueError, match="matched_reference_actor_token required"):
            CandidateOperation(
                op=Operation(
                    actor="Sam", kind="compare_additive",
                    operand=Comparison(
                        reference_actor="Tom",
                        delta=Quantity(value=3, unit="apples"),
                        factor=None, direction="more",
                    ),
                ),
                source_span="Sam has 3 more apples than Tom.",
                matched_verb="more",
                matched_value_token="3",
                matched_unit_token="apples",
                matched_actor_token="Sam",
                matched_reference_actor_token=None,  # missing
            )

    def test_non_comparison_must_not_carry_reference_actor_token(self) -> None:
        with pytest.raises(ValueError, match="matched_reference_actor_token only valid"):
            CandidateOperation(
                op=Operation(actor="Sam", kind="add",
                             operand=Quantity(value=3, unit="apples")),
                source_span="Sam buys 3 apples.",
                matched_verb="buys",
                matched_value_token="3",
                matched_unit_token="apples",
                matched_actor_token="Sam",
                matched_reference_actor_token="Tom",  # not allowed
            )
