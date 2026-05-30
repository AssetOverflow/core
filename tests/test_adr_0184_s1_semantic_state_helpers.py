"""ADR-0184 S1 — semantic-state helper extraction tests.

S1 is intentionally behavior-equivalent: the helpers extracted from
``generate.derivation.accumulate`` must stay conservative and non-vacuous.  These
tests pin the referent and polarity guard surfaces directly so future semantic
state work composes on the same wrong=0-first floor.
"""

from __future__ import annotations

from generate.derivation.accumulate import accumulation_candidates, compose_accumulation
from generate.derivation.state.bind import (
    continues_anchor_referent,
    leading_subject_token,
)
from generate.derivation.state.change import (
    classify_change_polarity,
    select_change_cue,
)


class TestReferentBindingHelpers:
    def test_leading_subject_token_is_loose_signal_only(self) -> None:
        assert leading_subject_token("Sam has 14 apples.") == "Sam"
        assert leading_subject_token("   He buys 9 more apples.") == "He"
        assert leading_subject_token("123 + 4") is None

    def test_pronoun_continuation_allowed(self) -> None:
        assert continues_anchor_referent("He buys 9 more apples.", "Sam") is True
        assert continues_anchor_referent("she gets 4 more tickets", "Lisa") is True

    def test_same_named_subject_allowed(self) -> None:
        assert continues_anchor_referent("Sam buys 9 more apples.", "Sam") is True

    def test_new_named_actor_refuses(self) -> None:
        assert continues_anchor_referent("Tom buys 9 more apples.", "Sam") is False

    def test_lowercase_leading_token_is_not_a_new_named_actor(self) -> None:
        # Behavior-equivalent with the original accumulation helper: lowercase
        # leading words carry no named-actor signal, so they do not by themselves
        # trip the referent guard.
        assert continues_anchor_referent("then buys 9 more apples", "Sam") is True


class TestChangeCueHelpers:
    def test_more_takes_gain_precedence(self) -> None:
        clause = "Her teacher gives her 5 more pencils."
        assert classify_change_polarity(clause) == +1
        assert select_change_cue(clause, +1) == "more"

    def test_gain_verb_without_more(self) -> None:
        clause = "He finds 7 on the playground."
        assert classify_change_polarity(clause) == +1
        assert select_change_cue(clause, +1) == "finds"

    def test_loss_verb(self) -> None:
        clause = "She eats 8 apples."
        assert classify_change_polarity(clause) == -1
        assert select_change_cue(clause, -1) == "eats"

    def test_directional_gives_is_loss(self) -> None:
        clause = "She gives 10 to her friend."
        assert classify_change_polarity(clause) == -1
        assert select_change_cue(clause, -1) == "gives"

    def test_unlicensed_change_refuses(self) -> None:
        assert classify_change_polarity("She owns 4 tickets.") is None

    def test_mixed_gain_and_loss_refuses_without_more_override(self) -> None:
        # Both cue sets present and no 'more' override -> ambiguous, so refuse.
        assert classify_change_polarity("She buys and sells 4 apples.") is None


class TestAccumulationStillUsesEquivalentSemantics:
    def test_clean_accumulation_still_commits(self) -> None:
        result = compose_accumulation(
            "Sam has 14 apples. He buys 9 more. How many apples does Sam have now?"
        )
        assert result is not None
        assert result.answer == 23.0

    def test_new_actor_still_refuses(self) -> None:
        assert (
            compose_accumulation(
                "Sam has 14 apples. Tom buys 9 more. How many apples does Sam have?"
            )
            is None
        )

    def test_anchor_skip_referent_guard_still_blocks_new_actor(self) -> None:
        same_referent = (
            "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
            "he buys 4 more tickets. How many tickets does Tom have?"
        )
        new_actor = (
            "A train travels at 60 miles per hour for 2 hours. Tom has 8 tickets and "
            "Sara buys 4 more tickets. How many tickets does Tom have?"
        )
        assert any(d.answer == 12.0 for d in accumulation_candidates(same_referent))
        assert all(d.answer != 12.0 for d in accumulation_candidates(new_actor))
