"""ADR-0176 MS-3 — target-guided bounded multi-step search.

Composes MS-1 (Target) + MS-2 (comparative chains + completeness) + the gate.
Shape-based + bounded + deterministic + refuse-on-overflow. Uniqueness refuses
ambiguity (multiple shapes self-verify + disagree -> refuse) — safe-but-low-
coverage by design; coverage is gated on cue precision (the learning lever).

Honest practice measurement (sealed lane, this build): 4 correct / 9 wrong / 37
refused (baseline 3/0/47). The +1 flip is the unambiguous whole-problem product
(0021); the 9 wrongs are product-of-all eliminations on multi-step problems
(caught by gold). 0003-class flips are blocked by a decimal-grounding gap
(``$0.75`` tokenizes to ``0``/``75``) in the shared round-trip primitive —
deferred extraction-richness work, not a search bug.
"""

from __future__ import annotations

from generate.derivation import search_chain
from generate.derivation.target import Target


class TestFlipsCleanProduct:
    def test_unambiguous_product_resolves(self) -> None:
        # mult cue "each", no aggregation hint -> only the product shape -> unique
        res = search_chain("Maria packs 6 boxes with 50 apples each. How many apples?")
        assert res is not None and res.answer == 300.0


class TestRefusesAmbiguity:
    def test_product_and_sum_disagree_refuses(self) -> None:
        # same-unit quantities so both shapes self-verify: "each" licenses product
        # (300), "total" licenses sum (56); they disagree -> refuse (wrong=0).
        text = "Each box has 6 apples. There are 50 apples in total. How many apples?"
        assert search_chain(text) is None

    def test_no_licensed_op_refuses(self) -> None:
        # no multiplicative cue and no aggregation hint -> no candidate -> refuse
        # (the search does not fabricate an operation it cannot license)
        assert search_chain("A theater has 6 rows and 50 seats.") is None


class TestBounded:
    def test_too_few_quantities_refuses(self) -> None:
        assert search_chain("He has 6 boxes each.") is None

    def test_refuse_on_overflow(self) -> None:
        # > MAX_QUANTITIES (6) quantities -> refuse rather than enumerate
        text = (
            "1 apple, 2 pears, 3 plums, 4 figs, 5 dates, 6 limes, 7 kiwis each."
        )
        assert search_chain(text) is None


class TestDeterminism:
    def test_deterministic(self) -> None:
        text = "Maria packs 6 boxes with 50 apples each. How many apples?"
        assert search_chain(text) == search_chain(text)


class TestTargetThreading:
    def test_explicit_target_is_used(self) -> None:
        # passing a Target with no aggregation -> sum shape not attempted ->
        # unambiguous product resolves
        text = "Maria packs 6 boxes with 50 apples each."
        target = Target(quantities=(), aggregation=None, units=())
        assert search_chain(text, target).answer == 300.0


class TestDecimalGroundingResolves:
    def test_decimal_operand_grounds_and_resolves(self) -> None:
        # ADR-0179 EX-2 (#447) landed bare-decimal grounding in the shared round-trip
        # primitive, so "0.75" is now grounded and the (correct, 864) product
        # self-verifies. This previously refused (the decimal grounding gap); the
        # flip is the EX-2 acceptance signal.
        text = (
            "There are 48 boxes with 24 erasers in each box. "
            "They sell the erasers for $0.75 each. How much money will they make?"
        )
        res = search_chain(text)
        assert res is not None and res.answer == 864.0  # 48 * 24 * 0.75
