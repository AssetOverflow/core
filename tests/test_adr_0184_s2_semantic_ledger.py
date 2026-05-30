"""ADR-0184 S2 — semantic ledger replay tests.

The semantic ledger is the first explicit state-transition substrate.  These tests
pin the narrow S2 shape: SET_STATE plus same-key GAIN/LOSS transitions replay to
the same ``GroundedDerivation`` shape the existing verifier/pool already accepts.
"""

from __future__ import annotations

import pytest

from generate.derivation.accumulate import accumulation_candidates, compose_accumulation
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.model import (
    SemanticLedger,
    SemanticQuantity,
    SemanticStateError,
    StateKey,
    StateTransition,
)
from generate.derivation.state.replay import replay_accumulation_ledger


class TestSemanticLedgerModel:
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
    def test_compose_accumulation_still_commits_clean_gain(self) -> None:
        result = compose_accumulation(
            "Sam has 14 apples. He buys 9 more. How many apples does Sam have now?"
        )
        assert result is not None
        assert result.answer == 23.0

    def test_anchor_skip_still_emits_exempt_candidate_shape(self) -> None:
        text = (
            "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
            "he buys 4 more tickets. How many tickets does Tom have?"
        )
        assert any(d.answer == 12.0 for d in accumulation_candidates(text))
