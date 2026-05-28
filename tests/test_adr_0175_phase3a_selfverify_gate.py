"""ADR-0175 Phase 3a — the self-verification gate (built BEFORE the search).

The wrong=0-critical piece. A bounded derivation search (Phase 3b) will be
*allowed* to attempt freely in the sealed practice lane; what keeps it honest is
this gate, which decides whether an attempt is **self-verified**:

    grounded operands  ∧  grounded operation cues  ∧  unit-consistent  ∧  unique

Invariant #2 (CLAUDE.md §Schema-Defined Proof Obligations): the gate MUST refuse
to self-verify a derivation that is not grounded+unit-consistent+unique — even
when its value coincidentally matches gold (the `20/5 == 4` class). The proof is
``TestInvariant2_NoSpuriousSelfVerification`` — each test fails if the gate
admits a spurious derivation.
"""

from __future__ import annotations

import pytest

from generate.derivation import (
    GroundedDerivation,
    Quantity,
    Resolution,
    SelfVerification,
    Step,
    select_self_verified,
    self_verifies,
)

# Case 0021 text — a genuine in-clause multiplicative aggregate.
_T0021 = "He bench presses 15 pounds for 10 reps and does 3 sets."


def _q(v: float, unit: str, tok: str) -> Quantity:
    return Quantity(value=v, unit=unit, source_token=tok)


def _mult_0021() -> GroundedDerivation:
    # 15 pounds  × 10 (cue "reps")  × 3 (cue "sets")  = 450
    return GroundedDerivation(
        start=_q(15, "pounds", "15"),
        steps=(
            Step(op="multiply", operand=_q(10, "reps", "10"), cue="reps"),
            Step(op="multiply", operand=_q(3, "sets", "3"), cue="sets"),
        ),
    )


# ---------------------------------------------------------------------------
# Derivation arithmetic
# ---------------------------------------------------------------------------

class TestDerivationArithmetic:
    def test_left_fold_multiply(self) -> None:
        assert _mult_0021().answer == 450.0

    def test_answer_unit_is_primary_for_multiply(self) -> None:
        assert _mult_0021().answer_unit == "pounds"

    def test_add_same_unit(self) -> None:
        d = GroundedDerivation(
            start=_q(5, "apples", "5"),
            steps=(Step(op="add", operand=_q(3, "apples", "3"), cue="and"),),
        )
        assert d.answer == 8.0
        assert d.answer_unit == "apples"


# ---------------------------------------------------------------------------
# self_verifies — the per-derivation gate
# ---------------------------------------------------------------------------

class TestSelfVerifies:
    def test_grounded_multiplicative_self_verifies(self) -> None:
        sv = self_verifies(_mult_0021(), _T0021)
        assert isinstance(sv, SelfVerification)
        assert sv.verified is True

    def test_grounded_additive_self_verifies(self) -> None:
        text = "She has 5 apples and 3 apples."
        d = GroundedDerivation(
            start=_q(5, "apples", "5"),
            steps=(Step(op="add", operand=_q(3, "apples", "3"), cue="and"),),
        )
        assert self_verifies(d, text).verified is True


# ---------------------------------------------------------------------------
# INVARIANT #2 — the gate refuses to self-verify spurious derivations
# ---------------------------------------------------------------------------

class TestInvariant2_NoSpuriousSelfVerification:
    def test_invented_operand_not_in_text_refused(self) -> None:
        # 15 × 8 = 120, but "8" is not in the problem -> operand ungrounded
        d = GroundedDerivation(
            start=_q(15, "pounds", "15"),
            steps=(Step(op="multiply", operand=_q(8, "things", "8"), cue="reps"),),
        )
        sv = self_verifies(d, _T0021)
        assert sv.verified is False
        assert any("operand" in r for r in sv.reasons)

    def test_operation_cue_not_in_text_refused(self) -> None:
        # 20 / 5 = 4 with operands present, but cue "divided" is NOT in the text.
        # Even though 4 might match gold, an ungrounded op cannot self-verify.
        text = "Martha has 20 apples and 5 friends."
        d = GroundedDerivation(
            start=_q(20, "apples", "20"),
            steps=(Step(op="divide", operand=_q(5, "friends", "5"), cue="divided"),),
        )
        sv = self_verifies(d, text)
        assert sv.verified is False
        assert any("cue" in r for r in sv.reasons)

    def test_value_coincidence_does_not_rescue_ungrounded_op(self) -> None:
        # The `20/5 == 4` coincidence: gold is 4, the derivation computes 4, the
        # operands are in text — but division is not licensed by any present cue.
        text = "Martha has 20 apples and 5 friends."  # no division cue
        d = GroundedDerivation(
            start=_q(20, "apples", "20"),
            steps=(Step(op="divide", operand=_q(5, "friends", "5"), cue="per"),),
        )  # cue "per" is also absent from the text
        assert d.answer == 4.0  # coincides with a plausible gold
        assert self_verifies(d, text).verified is False  # but does NOT self-verify

    def test_add_across_units_refused(self) -> None:
        # 5 pounds + 10 reps is unit-incoherent even if both tokens are present.
        d = GroundedDerivation(
            start=_q(5, "pounds", "15"),
            steps=(Step(op="add", operand=_q(10, "reps", "10"), cue="and"),),
        )
        sv = self_verifies(d, _T0021)
        assert sv.verified is False
        assert any("unit" in r for r in sv.reasons)

    def test_division_by_zero_refused(self) -> None:
        text = "There are 6 boxes and 0 shelves."
        d = GroundedDerivation(
            start=_q(6, "boxes", "6"),
            steps=(Step(op="divide", operand=_q(0, "shelves", "0"), cue="per"),),
        )
        assert self_verifies(d, text).verified is False


# ---------------------------------------------------------------------------
# select_self_verified — uniqueness / refuse-on-disagreement
# ---------------------------------------------------------------------------

class TestSelectUnique:
    def test_unique_self_verified_resolves(self) -> None:
        res = select_self_verified([_mult_0021()], _T0021)
        assert isinstance(res, Resolution)
        assert res.answer == 450.0
        assert res.answer_unit == "pounds"

    def test_zero_self_verified_refuses(self) -> None:
        # only a spurious derivation present -> nothing self-verifies -> refuse
        spurious = GroundedDerivation(
            start=_q(20, "apples", "20"),
            steps=(Step(op="divide", operand=_q(5, "friends", "5"), cue="divided"),),
        )
        assert select_self_verified([spurious], "Martha has 20 apples and 5 friends.") is None

    def test_disagreeing_self_verified_refuses(self) -> None:
        # two grounded derivations that disagree on the answer -> refuse (wrong=0)
        text = "He bench presses 15 pounds for 10 reps and does 3 sets."
        d1 = _mult_0021()  # 450
        d2 = GroundedDerivation(  # 15 x 10 = 150 (grounded but different answer)
            start=_q(15, "pounds", "15"),
            steps=(Step(op="multiply", operand=_q(10, "reps", "10"), cue="reps"),),
        )
        assert d1.answer != d2.answer
        assert select_self_verified([d1, d2], text) is None

    def test_agreeing_self_verified_resolves(self) -> None:
        # two self-verifying derivations that AGREE -> resolve (convergent evidence)
        text = "He bench presses 15 pounds for 10 reps and does 3 sets."
        d1 = _mult_0021()
        d2 = _mult_0021()
        res = select_self_verified([d1, d2], text)
        assert res is not None and res.answer == 450.0


# ---------------------------------------------------------------------------
# Determinism (invariant #3)
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_self_verifies_is_deterministic(self) -> None:
        a = self_verifies(_mult_0021(), _T0021)
        b = self_verifies(_mult_0021(), _T0021)
        assert a == b

    def test_frozen_types(self) -> None:
        import dataclasses
        q = _q(1, "x", "1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            q.value = 9.0  # type: ignore[misc]
