"""B2 — the transitive-chain lowering, in isolation.

``lower_transitive_chain`` proposes the propositional theory for a same-predicate
strict-order chain; the caller routes it through the UNCHANGED ``evaluate_entailment``
ROBDD. These pin the EXACT theory it emits (so a wrong lowering is caught) and its
soundness-by-construction refusals — a path that is empty, mislabeled, wrong-arity,
non-contiguous, or does not reach the target lowers to ``None`` (refuse), so a corrupted
path can never be confirmed as a wrong assertion.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.composition.lower_transitive import lower_transitive_chain


@dataclass(frozen=True)
class _Fact:
    """Minimal duck-typed relational fact (the lowering reads only these two)."""

    relation_predicate: str
    relation_arguments: tuple[str, ...]


def test_two_hop_chain_lowers_to_transitivity_theory() -> None:
    # less_than(a,b) ∘ less_than(b,c) → less_than(a,c) by p∘p→p.
    path = (_Fact("less_than", ("a", "b")), _Fact("less_than", ("b", "c")))
    lowered = lower_transitive_chain("less_than", "a", "c", path)
    assert lowered is not None
    premises, query = lowered
    # p(a,b)=x0, p(b,c)=x1, rule (p∘p→p): (x0 & x1) -> p(a,c)=x2.
    assert premises == ("x0", "x1", "(x0 & x1) -> x2")
    assert query == "x2"


def test_three_hop_chain_lowers_linearly() -> None:
    path = (
        _Fact("before_event", ("a", "b")),
        _Fact("before_event", ("b", "c")),
        _Fact("before_event", ("c", "d")),
    )
    lowered = lower_transitive_chain("before_event", "a", "d", path)
    assert lowered is not None
    premises, query = lowered
    # x0=p(a,b), x1=p(b,c), (x0&x1)->x2=p(a,c), x3=p(c,d), (x2&x3)->x4=p(a,d).
    assert premises == ("x0", "x1", "(x0 & x1) -> x2", "x3", "(x2 & x3) -> x4")
    assert query == "x4"


def test_empty_path_refuses() -> None:
    assert lower_transitive_chain("less_than", "a", "c", ()) is None


def test_mislabeled_edge_refuses() -> None:
    # an edge whose predicate is not the queried predicate must not be lowered (a
    # cross-predicate edge cannot be laundered into a same-predicate transitive chain).
    path = (_Fact("less_than", ("a", "b")), _Fact("greater_than", ("b", "c")))
    assert lower_transitive_chain("less_than", "a", "c", path) is None


def test_wrong_arity_refuses() -> None:
    path = (_Fact("less_than", ("a", "b", "extra")),)  # arity 3
    assert lower_transitive_chain("less_than", "a", "c", path) is None


def test_non_contiguous_path_refuses() -> None:
    # the second edge does not continue from the first edge's endpoint (b != c).
    path = (_Fact("less_than", ("a", "b")), _Fact("less_than", ("c", "d")))
    assert lower_transitive_chain("less_than", "a", "d", path) is None


def test_path_not_reaching_target_refuses() -> None:
    # a contiguous chain a→b but the target is c — the chain does not reach it.
    path = (_Fact("less_than", ("a", "b")),)
    assert lower_transitive_chain("less_than", "a", "c", path) is None
