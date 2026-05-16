"""Unit tests for the typed deterministic inference operators (ADR-0018)."""
from __future__ import annotations

import pytest

from generate.operators import (
    WalkResult,
    multi_relation_walk,
    path_recall,
    transitive_walk,
)
from teaching.relation_parse import parse_triple


# ---------------------------------------------------------------------------
# relation_parse
# ---------------------------------------------------------------------------

class TestRelationParse:
    def test_basic_is_triple(self):
        assert parse_triple("Actually wisdom is judgment.") == (
            "wisdom", "is", "judgment",
        )

    def test_precedes_triple(self):
        assert parse_triple("No, creation precedes order.") == (
            "creation", "precedes", "order",
        )

    def test_grounds_triple(self):
        assert parse_triple("Actually truth grounds knowledge.") == (
            "truth", "grounds", "knowledge",
        )

    def test_belongs_to_triple(self):
        assert parse_triple("Actually question belongs_to inquiry.") == (
            "question", "belongs_to", "inquiry",
        )

    def test_causes_triple(self):
        assert parse_triple("Actually light causes clarity.") == (
            "light", "causes", "clarity",
        )

    def test_articles_stripped(self):
        assert parse_triple("Actually the wisdom is the judgment.") == (
            "wisdom", "is", "judgment",
        )

    def test_no_relation_returns_none(self):
        assert parse_triple("Actually that's an interesting point.") is None

    def test_empty_returns_none(self):
        assert parse_triple("") is None

    def test_compound_relation_not_split(self):
        # "belongs_to" must not be parsed as "belongs" leaving "_to" behind
        result = parse_triple("Actually X belongs_to Y.")
        assert result == ("x", "belongs_to", "y")


# ---------------------------------------------------------------------------
# transitive_walk
# ---------------------------------------------------------------------------

class TestTransitiveWalk:
    def test_single_hop(self):
        triples = (("a", "is", "b"),)
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b")
        assert not r.truncated

    def test_two_hop_chain(self):
        triples = (("a", "is", "b"), ("b", "is", "c"))
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b", "c")
        assert not r.truncated

    def test_three_hop_chain(self):
        triples = (
            ("a", "is", "b"),
            ("b", "is", "c"),
            ("c", "is", "d"),
        )
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b", "c", "d")

    def test_relation_filter_excludes_other_relations(self):
        triples = (
            ("a", "is", "b"),
            ("b", "precedes", "c"),  # different relation, must be skipped
        )
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b")

    def test_unrelated_head_returns_singleton(self):
        triples = (("a", "is", "b"),)
        r = transitive_walk(triples, "x", "is")
        assert r.path == ("x",)
        assert not r.truncated

    def test_empty_triples_returns_singleton(self):
        r = transitive_walk((), "a", "is")
        assert r.path == ("a",)

    def test_cycle_terminates(self):
        triples = (("a", "is", "b"), ("b", "is", "a"))
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b")
        assert not r.truncated

    def test_max_hops_truncates(self):
        triples = (
            ("a", "is", "b"),
            ("b", "is", "c"),
            ("c", "is", "d"),
        )
        r = transitive_walk(triples, "a", "is", max_hops=2)
        assert r.path == ("a", "b", "c")
        assert r.truncated

    def test_case_insensitive(self):
        triples = (("A", "Is", "B"),)
        r = transitive_walk(triples, "a", "is")
        assert r.path == ("a", "b")

    def test_deterministic_under_repeated_calls(self):
        triples = (("a", "is", "b"), ("b", "is", "c"))
        r1 = transitive_walk(triples, "a", "is")
        r2 = transitive_walk(triples, "a", "is")
        assert r1 == r2

    def test_first_write_wins_on_duplicate_head(self):
        triples = (("a", "is", "b"), ("a", "is", "z"))
        r = transitive_walk(triples, "a", "is")
        # First triple wins; "z" is ignored under "is" from "a"
        assert r.path[1] == "b"


# ---------------------------------------------------------------------------
# multi_relation_walk
# ---------------------------------------------------------------------------

class TestMultiRelationWalk:
    def test_single_relation_chain_still_walks(self):
        triples = (("a", "is", "b"), ("b", "is", "c"))
        r = multi_relation_walk(triples, "a")
        assert r.path == ("a", "b", "c")
        assert r.relation == "<mixed>"

    def test_walks_across_relation_types(self):
        triples = (
            ("light", "grounds", "clarity"),
            ("clarity", "causes", "recognition"),
            ("recognition", "precedes", "naming"),
        )
        r = multi_relation_walk(triples, "light")
        assert r.path == ("light", "clarity", "recognition", "naming")
        assert not r.truncated

    def test_unrelated_head_returns_singleton(self):
        triples = (("a", "is", "b"),)
        assert multi_relation_walk(triples, "x").path == ("x",)

    def test_cycle_terminates(self):
        triples = (("a", "is", "b"), ("b", "precedes", "a"))
        r = multi_relation_walk(triples, "a")
        assert r.path == ("a", "b")

    def test_max_hops_truncates(self):
        triples = (
            ("a", "is", "b"),
            ("b", "causes", "c"),
            ("c", "precedes", "d"),
        )
        r = multi_relation_walk(triples, "a", max_hops=2)
        assert r.path == ("a", "b", "c")
        assert r.truncated

    def test_deterministic(self):
        triples = (("a", "is", "b"), ("b", "grounds", "c"))
        assert multi_relation_walk(triples, "a") == multi_relation_walk(triples, "a")


# ---------------------------------------------------------------------------
# path_recall
# ---------------------------------------------------------------------------

class TestPathRecall:
    def test_single_relation_chain(self):
        triples = (("a", "is", "b"), ("b", "is", "c"))
        assert path_recall(triples, "a", ("is",)) == ("a", "b")

    def test_two_relation_mixed_chain(self):
        triples = (
            ("a", "is", "b"),
            ("b", "precedes", "c"),
        )
        assert path_recall(triples, "a", ("is", "precedes")) == ("a", "b", "c")

    def test_empty_chain_returns_singleton(self):
        assert path_recall((), "a", ()) == ("a",)

    def test_broken_chain_stops_early(self):
        triples = (("a", "is", "b"),)  # second relation absent
        assert path_recall(triples, "a", ("is", "precedes")) == ("a", "b")

    def test_chain_respects_cycle(self):
        triples = (
            ("a", "is", "b"),
            ("b", "is", "a"),
        )
        assert path_recall(triples, "a", ("is", "is")) == ("a", "b")


# ---------------------------------------------------------------------------
# WalkResult shape
# ---------------------------------------------------------------------------

class TestWalkResultShape:
    def test_as_dict_round_trip(self):
        r = WalkResult(head="a", relation="is", path=("a", "b"), truncated=False)
        d = r.as_dict()
        assert d == {"head": "a", "relation": "is", "path": ["a", "b"], "truncated": False}

    def test_frozen(self):
        r = WalkResult(head="a", relation="is", path=("a",), truncated=False)
        with pytest.raises(AttributeError):
            r.head = "b"  # type: ignore[misc]
