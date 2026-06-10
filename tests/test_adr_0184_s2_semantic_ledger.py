"""ADR-0184 S2 — semantic ledger model, builder, and replay tests.

The semantic ledger is the first explicit state-transition substrate.  These tests
pin the narrow S2 shape: SET_STATE plus same-key GAIN/LOSS transitions replay to the
same ``GroundedDerivation`` shape the existing verifier/pool already accepts, and the
model rejects structurally illegal states.

The wrong=0 obligations these tests must *non-vacuously* catch (CLAUDE.md
"Schema-Defined Proof Obligations"): a non-SET start, a cross-key mutation, a new
named actor, an absent/ambiguous change cue, and an out-of-vocabulary transition op.
Each has a test that fails if exactly that guard is removed.
"""

from __future__ import annotations

import pytest

from generate.derivation.accumulate import accumulation_candidates, compose_accumulation
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.model import (
    VALID_TRANSITION_OPS,
    SemanticLedger,
    SemanticQuantity,
    SemanticStateError,
    StateKey,
    StateTransition,
)
from generate.derivation.state.replay import replay_accumulation_ledger


class TestSemanticLedgerModel:
    def test_valid_transition_ops_are_the_closed_set(self) -> None:
        assert VALID_TRANSITION_OPS == frozenset({"set", "gain", "loss"})

    def test_rejects_unknown_transition_op(self) -> None:
        with pytest.raises(SemanticStateError):
            StateTransition(
                key=StateKey(entity="Sam", unit="apples"),
                op="multiply",
                quantity=SemanticQuantity(3.0, "apples", "3", 0),
                cue="times",
                clause_index=0,
            )

    def test_rejects_non_tuple_ledger(self) -> None:
        with pytest.raises(SemanticStateError):
            SemanticLedger(transitions=[])  # type: ignore[arg-type]

    def test_rejects_non_transition_entry(self) -> None:
        with pytest.raises(SemanticStateError):
            SemanticLedger(transitions=("not a transition",))  # type: ignore[arg-type]

    def test_unit_must_be_str_not_none(self) -> None:
        # ADR-0184 S2 tightening: units mirror the extractor's ``Quantity.unit``
        # contract exactly (a ``str``, ``""`` = unitless). ``None`` is rejected so a
        # ``None``-unit can never split key identity from a ``""``-unit transition.
        with pytest.raises(SemanticStateError):
            SemanticQuantity(3.0, None, "3", 0)  # type: ignore[arg-type]
        with pytest.raises(SemanticStateError):
            StateKey(entity="Sam", unit=None)  # type: ignore[arg-type]

    def test_unitless_empty_string_is_accepted(self) -> None:
        quantity = SemanticQuantity(9.0, "", "9", 1)
        assert quantity.unit == ""
        assert StateKey(entity=None, unit="").unit == ""

    def test_entity_may_be_none(self) -> None:
        assert StateKey(entity=None, unit="apples").entity is None


class TestAccumulationLedgerBuilder:
    def test_builds_set_and_gain_transitions(self) -> None:
        ledger = build_accumulation_ledger(
            ["Sam has 14 apples.", "He buys 9 more apples."],
            drop_isolated_foreign=False,
        )
        assert ledger is not None
        assert [t.op for t in ledger.transitions] == ["set", "gain"]
        assert ledger.transitions[0].key == StateKey(entity="Sam", unit="apples")
        assert ledger.transitions[1].cue == "more"

    def test_loss_transition(self) -> None:
        ledger = build_accumulation_ledger(
            ["Anna has 25 stickers.", "She gives 10 to her friend."],
            drop_isolated_foreign=False,
        )
        assert ledger is not None
        assert [t.op for t in ledger.transitions] == ["set", "loss"]
        assert ledger.transitions[1].cue == "gives"

    def test_new_named_actor_refuses(self) -> None:
        assert (
            build_accumulation_ledger(
                ["Sam has 14 apples.", "Tom buys 9 more apples."],
                drop_isolated_foreign=False,
            )
            is None
        )

    def test_no_change_cue_refuses(self) -> None:
        assert (
            build_accumulation_ledger(
                ["Lisa has 30 coins.", "She owns 15 coins."],
                drop_isolated_foreign=False,
            )
            is None
        )

    def test_multi_quantity_anchor_refuses(self) -> None:
        assert (
            build_accumulation_ledger(
                ["Sam has 14 apples and 3 pears.", "He buys 9 more apples."],
                drop_isolated_foreign=False,
            )
            is None
        )

    def test_drop_isolated_foreign_preserves_candidate_only_when_enabled(self) -> None:
        clauses = [
            "Kate has 20 pencils.",
            "She studies for 3 hours and then buys 5 more pencils.",
        ]
        assert build_accumulation_ledger(clauses, drop_isolated_foreign=False) is None
        ledger = build_accumulation_ledger(clauses, drop_isolated_foreign=True)
        assert ledger is not None
        assert [t.quantity.source_token for t in ledger.transitions] == ["20", "5"]


class TestLedgerReplay:
    def test_replays_gain_to_grounded_derivation(self) -> None:
        ledger = build_accumulation_ledger(
            ["Sam has 14 apples.", "He buys 9 more apples."],
            drop_isolated_foreign=False,
        )
        assert ledger is not None
        derivation = replay_accumulation_ledger(ledger)
        assert derivation is not None
        assert derivation.start.value == 14.0
        assert derivation.steps[0].op == "add"
        assert derivation.steps[0].operand.value == 9.0
        assert derivation.answer == 23.0

    def test_replays_loss_to_grounded_derivation(self) -> None:
        ledger = build_accumulation_ledger(
            ["Sam has 30 apples.", "He eats 8 apples."],
            drop_isolated_foreign=False,
        )
        assert ledger is not None
        derivation = replay_accumulation_ledger(ledger)
        assert derivation is not None
        assert derivation.steps[0].op == "subtract"
        assert derivation.answer == 22.0

    def test_change_operand_inherits_anchor_unit(self) -> None:
        # "9 more" extracts unitless ("") but accumulates in the anchor's dimension.
        ledger = build_accumulation_ledger(
            ["Sam has 14 apples.", "He buys 9 more."],
            drop_isolated_foreign=False,
        )
        assert ledger is not None
        derivation = replay_accumulation_ledger(ledger)
        assert derivation is not None
        assert derivation.start.unit == "apples"
        assert derivation.steps[0].operand.unit == "apples"

    def test_replay_refuses_non_set_start(self) -> None:
        ledger = SemanticLedger(
            transitions=(
                StateTransition(
                    key=StateKey(entity="Sam", unit="apples"),
                    op="gain",
                    quantity=SemanticQuantity(9.0, "apples", "9", 0),
                    cue="more",
                    clause_index=0,
                ),
            )
        )
        assert replay_accumulation_ledger(ledger) is None

    def test_replay_refuses_cross_key_mutation(self) -> None:
        ledger = SemanticLedger(
            transitions=(
                StateTransition(
                    key=StateKey(entity="Sam", unit="apples"),
                    op="set",
                    quantity=SemanticQuantity(14.0, "apples", "14", 0),
                    cue="set",
                    clause_index=0,
                ),
                StateTransition(
                    key=StateKey(entity="Tom", unit="apples"),
                    op="gain",
                    quantity=SemanticQuantity(9.0, "apples", "9", 1),
                    cue="more",
                    clause_index=1,
                ),
            )
        )
        assert replay_accumulation_ledger(ledger) is None


class TestAccumulationComposerEquivalence:
    """The composer surfaces still produce the proven accumulation answers; the
    ledger is purely an internal re-expression."""

    def test_compose_accumulation_still_commits_clean_gain(self) -> None:
        result = compose_accumulation(
            "Sam has 14 apples. He buys 9 more. How many apples does Sam have now?"
        )
        assert result is not None
        assert result.answer == 23.0

    def test_compose_accumulation_still_commits_clean_loss(self) -> None:
        result = compose_accumulation(
            "Anna has 25 stickers. She gives 10 away. How many stickers does Anna have?"
        )
        assert result is not None
        assert result.answer == 15.0

    def test_new_actor_problem_still_refuses(self) -> None:
        assert (
            compose_accumulation(
                "Sam has 14 apples. Tom buys 9 more. How many apples does Sam have?"
            )
            is None
        )

    def test_anchor_skip_still_emits_exempt_candidate_shape(self) -> None:
        text = (
            "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
            "he buys 4 more tickets. How many tickets does Tom have?"
        )
        assert any(d.answer == 12.0 for d in accumulation_candidates(text))
