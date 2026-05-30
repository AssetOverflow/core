"""ADR-0184 — distinct-unit product rule.

A pure multiplicative product that revisits a non-empty dimension (``unit²``:
``apples × apples``, ``cards × cards``) is the over-eager product-of-all multiplying
independent groups — never a real quantity. It is classified **commit-ineligible**
(``exempt``), *not removed*: it still enters the pool to force a disagreement refusal
(the disguised-polarity confusers depend on the ``coins × coins`` product disagreeing
with the ``coins + coins`` accumulation reading). Dropping it instead of downgrading
would unmask the additive reading as a unique wrong commit — that regression is pinned
below.

Sealed lane: ``chat/`` does not import these; serving ``3/47/0`` cannot move.
"""

from __future__ import annotations

from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.pool import pooled_candidates, resolve_pooled
from generate.derivation.verify import _is_repeated_unit_product, classify_derivation


def _q(v: float, unit: str, tok: str) -> Quantity:
    return Quantity(value=v, unit=unit, source_token=tok)


class TestIsRepeatedUnitProduct:
    def test_same_unit_multiply_is_repeated(self) -> None:
        d = GroundedDerivation(
            start=_q(4, "apples", "4"),
            steps=(Step(op="multiply", operand=_q(5, "apples", "5"), cue="each"),),
        )
        assert _is_repeated_unit_product(d) is True

    def test_distinct_units_multiply_is_not_repeated(self) -> None:
        # boxes × erasers — a genuine rate-chain, distinct dimensions.
        d = GroundedDerivation(
            start=_q(48, "boxes", "48"),
            steps=(Step(op="multiply", operand=_q(24, "erasers", "24"), cue="each"),),
        )
        assert _is_repeated_unit_product(d) is False

    def test_empty_unit_repeat_is_exempt(self) -> None:
        # blank units cannot be shown to collide (a correct rate-chain may carry a
        # blank-unit scalar like $0.75).
        d = GroundedDerivation(
            start=_q(48, "boxes", "48"),
            steps=(
                Step(op="multiply", operand=_q(24, "erasers", "24"), cue="each"),
                Step(op="multiply", operand=_q(0.75, "", "0.75"), cue="each"),
            ),
        )
        assert _is_repeated_unit_product(d) is False

    def test_same_unit_divide_is_exempt(self) -> None:
        # feet / feet is a legitimate dimensionless count, not unit².
        d = GroundedDerivation(
            start=_q(1000, "feet", "1000"),
            steps=(Step(op="divide", operand=_q(25, "feet", "25"), cue="per"),),
        )
        assert _is_repeated_unit_product(d) is False

    def test_additive_chain_is_not_a_product(self) -> None:
        d = GroundedDerivation(
            start=_q(20, "apples", "20"),
            steps=(Step(op="add", operand=_q(20, "apples", "5"), cue="more"),),
        )
        assert _is_repeated_unit_product(d) is False


class TestClassifyDowngrade:
    def test_repeated_unit_product_is_exempt_not_complete(self) -> None:
        text = "There are 4 bags with 20 apples each and 6 bags with 25 apples each."
        d = GroundedDerivation(
            start=_q(4, "bags", "4"),
            steps=(
                Step(op="multiply", operand=_q(20, "apples", "20"), cue="each"),
                Step(op="multiply", operand=_q(6, "bags", "6"), cue="each"),
                Step(op="multiply", operand=_q(25, "apples", "25"), cue="each"),
            ),
        )
        # complete (uses all 4 quantities) but dimensionally impossible -> exempt.
        assert classify_derivation(d, text) == "exempt"

    def test_distinct_unit_product_stays_complete(self) -> None:
        text = "There are 48 boxes with 24 erasers each."
        d = GroundedDerivation(
            start=_q(48, "boxes", "48"),
            steps=(Step(op="multiply", operand=_q(24, "erasers", "24"), cue="each"),),
        )
        assert classify_derivation(d, text) == "complete"


class TestPoolBehaviour:
    _PRODUCT_OF_ALL_0042 = (
        "Ella has 4 bags with 20 apples in each bag and six bags with 25 apples in "
        "each bag. If Ella sells 200 apples, how many apples does Ella have left?"
    )
    # confuser 0001 — the regression guard pair.
    _DISGUISED = "Dan has 50 coins. He buys a toy for 30 coins. How many coins does Dan have left?"

    def test_unopposed_repeated_unit_product_refuses(self) -> None:
        # 0042 used to commit 2,400,000 (4×20×6×25); now the product is exempt and
        # (being commit-ineligible and otherwise unopposed) the pool refuses.
        assert resolve_pooled(self._PRODUCT_OF_ALL_0042) is None

    def test_downgrade_not_removal_preserves_disagreement_refusal(self) -> None:
        # THE regression guard. The disguised-polarity case refuses because the
        # coins×coins product (exempt) DISAGREES with the coins+coins accumulation
        # reading (complete). If the rule *dropped* the repeated-unit product instead
        # of downgrading it, the additive reading would be unique and commit (wrong).
        cands = [
            (classify_derivation(d, self._DISGUISED), round(d.answer, 6))
            for d in pooled_candidates(self._DISGUISED)
        ]
        # both a commit-eligible additive AND a commit-ineligible product are present:
        assert ("complete", 80.0) in cands, f"expected additive 80 (complete): {cands}"
        assert any(k == "exempt" for k, a in cands if a == 1500.0), (
            f"expected the coins×coins product (1500) to be exempt, not dropped: {cands}"
        )
        # and therefore the case refuses (disagreement), never commits 80:
        assert resolve_pooled(self._DISGUISED) is None
