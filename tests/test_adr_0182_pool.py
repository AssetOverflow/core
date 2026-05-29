"""ADR-0182 — cross-composer disagreement pooling (distractor refusal).

Two surfaces under test:

* :func:`generate.derivation.verify.classify_derivation` — the commit-eligibility
  class (``complete`` / ``exempt`` / ``None``) and, critically, that the
  isolated-foreign exemption is *narrow* (an empty-unit or same-unit unused
  quantity is never exempt — it is real signal, not a distractor).
* :func:`generate.derivation.pool.resolve_pooled` — the pooled resolution: a clean
  reading commits, a distractor problem's product-vs-additive disagreement refuses,
  and (the wrong=0-critical property) an ``exempt``-only answer **never commits**.

Sealed lane: ``chat/`` does not import these; serving ``3/47/0`` cannot move.
"""

from __future__ import annotations

from generate.derivation.accumulate import accumulation_candidates
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.pool import resolve_pooled
from generate.derivation.verify import classify_derivation

_DISTRACTOR_0014 = (
    "Kate has 20 pencils. She studies for 3 hours and then buys 5 more pencils. "
    "How many pencils does Kate have?"
)
# A distractor with NO multiplicative cue: the only candidate is the exempt additive
# reading (no complete product exists). The commit-ineligibility rule must refuse it.
_EXEMPT_ONLY = (
    "Kate has 20 pencils. She rests for 3 hours and buys 5 more pencils."
)
_CLEAN_ACCUMULATION = "Sam has 14 apples. He buys 9 more apples."


class TestClassifyDerivation:
    def test_complete_reading_is_commit_eligible(self) -> None:
        # uses every quantity -> complete
        derivation = accumulation_candidates(_CLEAN_ACCUMULATION)[0]
        assert classify_derivation(derivation, _CLEAN_ACCUMULATION) == "complete"

    def test_isolated_foreign_unused_is_exempt(self) -> None:
        # the additive reading of 0014 leaves "3 hours" unused; hours is foreign to
        # the used unit (pencils) -> exempt (commit-ineligible).
        derivation = GroundedDerivation(
            start=Quantity(20.0, "pencils", "20"),
            steps=(Step(op="add", operand=Quantity(5.0, "pencils", "5"), cue="more"),),
        )
        assert classify_derivation(derivation, _DISTRACTOR_0014) == "exempt"

    def test_same_unit_unused_is_not_exempt(self) -> None:
        # a quantity sharing the reading's unit is real signal, never a distractor:
        # leaving it unused must NOT be exempted (it stays invalid -> None).
        text = "Sam has 14 apples. He buys 9 more apples. He eats 2 apples."
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(9.0, "apples", "9"), cue="more"),),
        )
        assert classify_derivation(derivation, text) is None

    def test_empty_unit_unused_is_not_exempt(self) -> None:
        # an unused quantity with an unknown (empty) unit cannot be shown foreign,
        # so it is never exempt — completeness still rejects the reading.
        text = "Sam has 14 apples. He buys 9 more apples. He had 2."
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(9.0, "apples", "9"), cue="more"),),
        )
        assert classify_derivation(derivation, text) is None

    def test_ungrounded_operand_is_invalid(self) -> None:
        derivation = GroundedDerivation(
            start=Quantity(14.0, "apples", "14"),
            steps=(Step(op="add", operand=Quantity(999.0, "apples", "999"), cue="more"),),
        )
        assert classify_derivation(derivation, _CLEAN_ACCUMULATION) is None


class TestResolvePooled:
    def test_clean_accumulation_commits(self) -> None:
        resolution = resolve_pooled(_CLEAN_ACCUMULATION)
        assert resolution is not None
        assert resolution.answer == 23.0

    def test_distractor_0014_refuses_via_disagreement(self) -> None:
        # product 300 (complete) vs additive 25 (exempt) disagree -> refuse.
        assert resolve_pooled(_DISTRACTOR_0014) is None

    def test_exempt_only_never_commits(self) -> None:
        # THE wrong=0-critical obligation. The only verifying reading here is the
        # exempt additive one (no multiplicative cue -> no competing product), so a
        # commit would be on an incomplete reading. The commit-ineligibility rule
        # must refuse. Flipping `exempt` to commit-eligible makes this commit 25 and
        # this test fails loudly.
        assert accumulation_candidates(_EXEMPT_ONLY), "expected an exempt candidate"
        assert classify_derivation(
            accumulation_candidates(_EXEMPT_ONLY)[-1], _EXEMPT_ONLY
        ) == "exempt"
        assert resolve_pooled(_EXEMPT_ONLY) is None

    def test_deterministic(self) -> None:
        assert resolve_pooled(_DISTRACTOR_0014) == resolve_pooled(_DISTRACTOR_0014)
        a = resolve_pooled(_CLEAN_ACCUMULATION)
        b = resolve_pooled(_CLEAN_ACCUMULATION)
        assert a is not None and b is not None and a.answer == b.answer
