"""ADR-0176 MS-2 — multi-step chain model: text + comparative operands.

Extends the derivation model so a chain can mix text-quantity operands and
**comparative-scalar** operands (twice -> x2, 'N times' -> xN, half -> x0.5),
self-verifying the whole chain with completeness over body+question and
question-target matching.

Covers the multi-step shapes the gold structures show:
- 0021: all-text multiplicative chain.
- 0024: text sum, then a comparative scale ('three times').
- 0033 father-chain: digit-comparative ('7 times') + fixed-comparative ('half')
  + text add — the mixed chain mechanics (full 0033 DAG with quantity reuse is
  deferred; here we verify the chain composes and is complete over its own body).
"""

from __future__ import annotations

from generate.derivation import (
    GroundedDerivation,
    Quantity,
    Step,
    comparative_step,
    extract_comparative_scalars,
    select_self_verified,
    self_verifies,
)


def _q(v: float, unit: str, tok: str) -> Quantity:
    return Quantity(value=v, unit=unit, source_token=tok)


# ---------------------------------------------------------------------------
# comparative_step bridge
# ---------------------------------------------------------------------------

class TestComparativeStep:
    def test_word_times_bridges_to_multiply_step(self) -> None:
        (cs,) = extract_comparative_scalars("three times as many")
        step = comparative_step(cs)
        assert step.op == "multiply" and step.comparative is True
        assert step.operand.value == 3.0
        assert step.cue == "times"
        assert step.operand.source_token == "three"  # number_token, for completeness

    def test_digit_times_carries_number_token(self) -> None:
        (cs,) = extract_comparative_scalars("7 times her age")
        step = comparative_step(cs)
        assert step.operand.value == 7.0
        assert step.operand.source_token == "7"  # so completeness counts body "7"

    def test_fixed_lexeme_has_no_number_token(self) -> None:
        (cs,) = extract_comparative_scalars("half of it")
        step = comparative_step(cs)
        assert step.operand.value == 0.5
        assert step.operand.source_token == "half"


# ---------------------------------------------------------------------------
# mixed text + comparative chains self-verify
# ---------------------------------------------------------------------------

class TestMixedChains:
    def test_0024_sum_then_comparative_scale(self) -> None:
        # "Sidney does 20, 36, 40, 50 jumping jacks. Brooke does three times as many."
        text = (
            "Sidney does 20 jacks on Monday, 36 on Tuesday, 40 on Wednesday, "
            "and 50 on Thursday. Brooke does three times as many jacks as Sidney."
        )
        (cs,) = extract_comparative_scalars(text)
        chain = GroundedDerivation(
            start=_q(20, "jacks", "20"),
            steps=(
                Step("add", _q(36, "jacks", "36"), cue="and"),
                Step("add", _q(40, "jacks", "40"), cue="and"),
                Step("add", _q(50, "jacks", "50"), cue="and"),
                comparative_step(cs),  # x3
            ),
        )
        assert chain.answer == 438.0
        sv = self_verifies(chain, text)
        assert sv.verified is True, sv.reasons

    def test_0033_father_chain_digit_and_fixed_comparatives(self) -> None:
        # father's current age: 12 x 7 (= grandfather) / 2 (mother=half) + 5
        # (the body alone; the full 0033 also uses the question's 25 -> DAG, deferred)
        body = "Rachel is 12. Her grandfather is 7 times her age. Her mother is half that. Her father is 5 years older."
        scalars = {c.cue: c for c in extract_comparative_scalars(body)}
        chain = GroundedDerivation(
            start=_q(12, "years", "12"),
            steps=(
                comparative_step(scalars["times"]),   # x7  (digit comparative)
                comparative_step(scalars["half"]),     # x0.5
                Step("add", _q(5, "years", "5"), cue="older"),
            ),
        )
        assert chain.answer == 47.0
        sv = self_verifies(chain, body)
        assert sv.verified is True, sv.reasons


# ---------------------------------------------------------------------------
# completeness over body (digit comparative consumes its body quantity)
# ---------------------------------------------------------------------------

class TestCompletenessWithComparatives:
    def test_digit_comparative_consumes_body_quantity(self) -> None:
        # "7 times" consumes body "7" -> chain using 12 + (x7) is complete over {12,7}
        body = "Rachel is 12. Her grandfather is 7 times her age."
        (cs,) = extract_comparative_scalars(body)
        chain = GroundedDerivation(
            start=_q(12, "years", "12"),
            steps=(comparative_step(cs),),
        )
        assert self_verifies(chain, body).verified is True

    def test_ignoring_a_body_quantity_is_incomplete(self) -> None:
        body = "Rachel is 12 years old. Her grandfather is 7 times her age. She has 30 coins."
        (cs,) = extract_comparative_scalars(body)
        chain = GroundedDerivation(  # ignores the stated "30 coins"
            start=_q(12, "years", "12"),
            steps=(comparative_step(cs),),
        )
        sv = self_verifies(chain, body)
        assert sv.verified is False
        assert any("incomplete" in r for r in sv.reasons)

    def test_comparative_cue_absent_refuses(self) -> None:
        # a comparative step whose cue is not in the text -> ungrounded
        chain = GroundedDerivation(
            start=_q(12, "years", "12"),
            steps=(Step("multiply", _q(3.0, "", "three"), cue="times", comparative=True),),
        )
        sv = self_verifies(chain, "Rachel is 12.")  # no "times"
        assert sv.verified is False
        assert any("cue" in r for r in sv.reasons)


# ---------------------------------------------------------------------------
# question-target matching (MS-2)
# ---------------------------------------------------------------------------

class TestTargetMatch:
    def test_target_unit_match_resolves(self) -> None:
        text = "He has 6 boxes for 50 each."
        chain = GroundedDerivation(
            start=_q(6, "boxes", "6"),
            steps=(Step("multiply", _q(50, "each", "50"), cue="for"),),
        )
        res = select_self_verified([chain], text, target_units=("boxes",))
        assert res is not None and res.answer == 300.0

    def test_target_unit_mismatch_refuses(self) -> None:
        # chain answers in "boxes" but the question asked for "reps" -> refuse
        text = "He has 6 boxes for 50 each."
        chain = GroundedDerivation(
            start=_q(6, "boxes", "6"),
            steps=(Step("multiply", _q(50, "each", "50"), cue="for"),),
        )
        assert select_self_verified([chain], text, target_units=("reps",)) is None

    def test_empty_target_imposes_no_constraint(self) -> None:
        text = "He has 6 boxes for 50 each."
        chain = GroundedDerivation(
            start=_q(6, "boxes", "6"),
            steps=(Step("multiply", _q(50, "each", "50"), cue="for"),),
        )
        assert select_self_verified([chain], text, target_units=()) is not None
