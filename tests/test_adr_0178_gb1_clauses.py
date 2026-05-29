"""ADR-0178 GB-1 — clause segmentation + clause-local sub-derivation.

The first slice of the comprehension-guided composer: read the problem clause by
clause and derive each clause's local contribution (GB-2 combines them). Covers
segmentation, the leaf/context/local-search cases, and the refuse-preferring hold
on ambiguous clauses.
"""

from __future__ import annotations

from generate.derivation import (
    ClauseResult,
    clause_local_results,
    segment_clauses,
)


class TestSegmentClauses:
    def test_sentence_level_split(self) -> None:
        clauses = segment_clauses(
            "Sidney does 20 jacks. Brooke does three times as many. How many?"
        )
        assert len(clauses) == 3
        assert clauses[0] == "Sidney does 20 jacks."

    def test_collapses_whitespace_and_drops_empty(self) -> None:
        assert segment_clauses("  A.   B.  ") == ("A.", "B.")

    def test_deterministic(self) -> None:
        t = "He has 6 boxes. Each holds 50 apples."
        assert segment_clauses(t) == segment_clauses(t)


class TestClauseLocalResults:
    def test_single_clause_local_product(self) -> None:
        # 0021: one clause, all quantities multiply locally -> 450
        results = clause_local_results(
            "He bench presses 15 pounds for 10 reps and does 3 sets."
        )
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, ClauseResult)
        assert r.resolved is True
        assert r.value == 450.0

    def test_single_quantity_clause_is_a_leaf(self) -> None:
        (r,) = clause_local_results("There are 48 boxes.")
        assert r.resolved is True
        assert r.value == 48.0
        assert r.unit == "boxes"

    def test_zero_quantity_clause_is_context(self) -> None:
        (r,) = clause_local_results("John is lifting weights.")
        assert r.resolved is False
        assert r.value is None
        assert r.quantities == ()

    def test_ambiguous_multi_quantity_clause_holds(self) -> None:
        # two quantities, no licensed local op (no mult cue / aggregation hint)
        # -> the local search refuses -> unresolved hold (not guessed)
        (r,) = clause_local_results("There are 6 rows and 50 seats.")
        assert r.resolved is False
        assert r.value is None
        assert len(r.quantities) == 2

    def test_per_clause_structure_of_a_multi_sentence_problem(self) -> None:
        # 0003-shape: each sentence contributes a local piece; GB-1 reports them
        # per clause (GB-2 will chain them: 48 -> x24 -> x2). Each sentence here
        # has a single quantity -> three leaves (48, 24, 2).
        results = clause_local_results(
            "There are 48 boxes. There are 24 erasers in each box. "
            "They sell for 2 dollars each."
        )
        assert [r.resolved for r in results] == [True, True, True]
        assert [r.value for r in results] == [48.0, 24.0, 2.0]

    def test_deterministic(self) -> None:
        t = "He bench presses 15 pounds for 10 reps and does 3 sets."
        assert clause_local_results(t) == clause_local_results(t)
