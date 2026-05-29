"""ADR-0178 GB-3b.1 — single-referent accumulation chaining.

The first cross-clause comprehension reading. These tests prove the obligations
from the GB-3b scope: the accumulation flips the gain/loss cases, and the wrong=0
guards (multi-actor, absent/ambiguous change cue, the GB-3a hazards) each REFUSE.
Every refusal test would *fail* if the guard it covers were removed.
"""

from __future__ import annotations

from generate.derivation.accumulate import compose_accumulation


def _answer(text: str):
    res = compose_accumulation(text)
    return None if res is None else res.answer


class TestAccumulationFlips:
    def test_gain_with_more(self) -> None:
        assert _answer("Sam has 14 apples. He buys 9 more. How many apples does Sam have now?") == 23.0

    def test_gain_verb_no_more(self) -> None:
        assert _answer("Ben has 20 marbles. He finds 7 on the playground. How many marbles?") == 27.0

    def test_gain_giver_to_subject_reads_as_more(self) -> None:
        # "Her teacher gives her 5 more" — subject (pronoun) is the recipient -> +5.
        assert _answer("Kate has 18 pencils. Her teacher gives her 5 more. How many pencils?") == 23.0

    def test_loss_verb(self) -> None:
        assert _answer("Sam has 30 apples. He eats 8. How many apples does Sam have left?") == 22.0

    def test_loss_gives_to_recipient(self) -> None:
        assert _answer("Anna has 25 stickers. She gives 10 to her friend. How many stickers left?") == 15.0


class TestReferentGuardRefuses:
    def test_new_named_actor_refuses(self) -> None:
        # The Alice/Tom hazard: a new named subject -> refuse (not Sam's 14+9).
        assert _answer("Sam has 14 apples. Tom buys 9 more. How many apples does Sam have?") is None

    def test_h1_unrelated_same_unit_across_sentences(self) -> None:
        assert _answer("Alice has 6 apples. Tom has 2 apples. How many apples does Alice have?") is None


class TestChangeCueGuardRefuses:
    def test_no_change_cue_refuses(self) -> None:
        # two quantities, no gain/loss verb and no "more" -> no licensed change -> refuse.
        assert _answer("Lisa has 30 coins. She has 15 stickers. How many coins does Lisa have?") is None

    def test_anchor_must_be_single_quantity(self) -> None:
        # a list anchor is GB-2a's job, not accumulation -> refuse here.
        assert _answer("Sam has 6 apples and 4 apples. He buys 5 more. How many?") is None

    def test_multi_change_in_one_clause_refuses(self) -> None:
        # "gets 5 more from Tom and 3 more from Lisa" is multi-change (GB-3b.2) -> refuse.
        assert _answer("Sam has 10 apples. He gets 5 more and 3 more. How many?") is None


class TestDeterminism:
    def test_deterministic(self) -> None:
        t = "Sam has 14 apples. He buys 9 more. How many?"
        assert compose_accumulation(t) == compose_accumulation(t)


class TestPracticeLaneFlip:
    def test_accumulation_flips_a_chunk_with_no_new_wrong(self) -> None:
        from evals.gsm8k_math.practice.v1.accumulation_runner import build_accumulation_report
        from evals.gsm8k_math.practice.v1.runner import build_practice_report

        before = build_practice_report().counts
        after = build_accumulation_report().counts
        # accumulation fires only on refusals: it adds correct, never a new wrong.
        assert after["correct"] >= 55
        assert after["wrong"] == before["wrong"]
        assert after["correct"] + after["wrong"] + after["refused"] == sum(before.values())
