"""ADR-0178 GB-2 — sequential composition: list-structure + comparative-scale.

First GB-2 increment: the `sum-then-scale` family the blunt MS-3 shapes couldn't
reach. A same-unit list (additive cue) sums; trailing comparatives scale. Gated by
self-verification + uniqueness; refuse-preferring on ambiguity.
"""

from __future__ import annotations

from generate.derivation import compose_sequential


class TestListSum:
    def test_same_unit_list_sums(self) -> None:
        # a list of like quantities joined by "and" -> sum
        res = compose_sequential("She picked 6 apples and 4 apples.")
        assert res is not None and res.answer == 10.0

    def test_three_item_list(self) -> None:
        res = compose_sequential("He has 2 coins and 3 coins and 5 coins.")
        assert res is not None and res.answer == 10.0


class TestListThenScale:
    def test_sum_then_double(self) -> None:
        # 0024-family: list sums, then a comparative scales it
        res = compose_sequential("She picked 6 apples and 4 apples, then doubled her apples.")
        assert res is not None and res.answer == 20.0  # (6+4)*2

    def test_sum_then_triple(self) -> None:
        # use "tripled" (a fixed comparative, not a 'times' that also reads as a
        # multiplicative cue) so the base op is unambiguous
        res = compose_sequential("He ran 2 miles and 3 miles, then tripled it.")
        assert res is not None and res.answer == 15.0  # (2+3)*3


class TestRefusePreferring:
    def test_mixed_units_no_list_sum(self) -> None:
        # different units -> not a same-unit list -> no list-sum candidate
        # (no other licensed shape either) -> refuse
        assert compose_sequential("He has 6 boxes and 50 apples.") is None

    def test_ambiguous_disagreement_refuses(self) -> None:
        # same-unit list (sum=10) AND a multiplicative cue "each" (product=24) both
        # self-verify and disagree -> uniqueness refuses (cue precision resolves later)
        assert compose_sequential("He has 6 apples and 4 apples in each basket.") is None

    def test_too_few_quantities(self) -> None:
        assert compose_sequential("She has 6 apples.") is None


class TestDeterminism:
    def test_deterministic(self) -> None:
        t = "She picked 6 apples and 4 apples, then doubled her apples."
        assert compose_sequential(t) == compose_sequential(t)
