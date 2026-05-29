"""ADR-0178 GB-3 — the referent guard (wrong=0-first lookback increment).

The GB-2 lookback review (audit docs/handoff/AUDIT-ADR-0178-GB1-GB2.md) found that
``compose_sequential`` summed same-unit quantities from the *whole problem*,
silently merging unrelated referents/scopes — admitting wrong structures whose
value happened to ground (hazards H1/H2/H3). GB-3's first, wrong=0-first slice is
the *defensive refusal*: the list-sum structure must be licensed within a single
clause; cross-clause aggregation refuses (referent-aware chaining is GB-3b).

These tests would FAIL against the pre-GB-3 whole-problem composer (which returned
12 / 20 / 13 respectively), so the obligation is proven, not decorative.
"""

from __future__ import annotations

from generate.derivation import compose_sequential


class TestReferentGuardRefuses:
    def test_h1_unrelated_same_unit_across_sentences(self) -> None:
        # Tom's apples are a different referent; the whole-problem composer summed
        # 6+4+2=12. Two quantity-bearing clauses -> refuse.
        text = (
            "Alice has 6 apples and 4 apples. Tom has 2 apples. "
            "How many apples does Alice have?"
        )
        assert compose_sequential(text) is None

    def test_h2_comparative_bound_to_other_referent(self) -> None:
        # "twice" modifies Tom, not Alice's list; the whole-problem composer applied
        # it to Alice's sum -> (6+4)*2 = 20. The comparative lives outside the list
        # clause -> refuse.
        text = (
            "Alice picked 6 apples and 4 apples. Tom picked twice as many apples. "
            "How many apples did Alice pick?"
        )
        assert compose_sequential(text) is None

    def test_h3_later_depletion_outside_asked_scope(self) -> None:
        # The "gave 3 away" event is a different scope; the whole-problem composer
        # summed 6+4+3 = 13. Two quantity-bearing clauses -> refuse.
        text = (
            "Alice picked 6 apples and 4 apples. Later she gave 3 apples away. "
            "How many apples did she pick before giving any away?"
        )
        assert compose_sequential(text) is None


class TestSingleClauseStructuresStillResolve:
    """The guard must not regress the legitimate single-clause GB-2 structures."""

    def test_single_clause_list_sum(self) -> None:
        res = compose_sequential("She picked 6 apples and 4 apples.")
        assert res is not None and res.answer == 10.0

    def test_single_clause_sum_then_scale(self) -> None:
        # list + comparative in the SAME clause (comma, not a sentence break).
        res = compose_sequential("She picked 6 apples and 4 apples, then doubled her apples.")
        assert res is not None and res.answer == 20.0


class TestDeterminism:
    def test_deterministic(self) -> None:
        t = "Alice has 6 apples and 4 apples. Tom has 2 apples. How many?"
        assert compose_sequential(t) == compose_sequential(t)
