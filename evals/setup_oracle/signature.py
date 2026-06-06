"""Span-free structural signatures for the setup-oracle.

A *signature* is a deterministic, order-independent, span-free projection of the
mathematical SETUP — what the reader claims the problem says, stripped of input
offsets and surface tokens. Two readings are setup-equivalent iff their signatures
are equal. Used to compare the reader's comprehended structure against the
independent gold structure (the relational_metric cases' own `relations`/`query`).

v1 grades: facts (entity, value), equations (the typed relation shape), and the
question target (symbol, state-index, question-form). Unit modelling is intentionally
NOT in the signature yet — it is covered by the admissibility tests, and a future
extension adds an expected-unit axis once the gold carries it.
"""

from __future__ import annotations

from typing import Any

from generate.binding_graph.model import SemanticSymbolicBindingGraph


def relation_signature(relations: list[dict[str, Any]]) -> tuple[tuple, ...]:
    """Canonicalize a list of relations (the ``to_relational_metric`` / gold shape)
    into a sorted, order-independent tuple of typed relation tuples."""
    out: list[tuple] = []
    for r in relations:
        kind = r["kind"]
        if kind == "fact":
            out.append(("fact", r["entity"], int(r["value"])))
        elif kind in ("more_than", "fewer_than"):
            out.append((kind, r["entity"], r["ref"], int(r["delta"])))
        elif kind == "sum_of":
            out.append(("sum_of", r["entity"], tuple(sorted(r["parts"]))))
        else:  # an unknown relation kind is itself a structural difference, not a crash
            out.append(("unhandled_kind", kind, r.get("entity", "")))
    return tuple(sorted(out, key=repr))


def gold_unknown_signature(
    relations: list[dict[str, Any]], query: dict[str, Any]
) -> tuple[str, str, str]:
    """The expected question-target signature, derived from the INDEPENDENT gold.

    A query whose target is an aggregate (the gold contains a ``sum_of`` producing it)
    is a ``total`` form; otherwise a ``count``. All current cases ask the terminal state.
    """
    form = "total" if any(r["kind"] == "sum_of" for r in relations) else "count"
    return (query["entity"], "terminal", form)


def _state_token(state_index: Any) -> str:
    if isinstance(state_index, str):
        return state_index
    # An Operation state-index (ADR-0135) — name it by its operation index.
    return f"op{getattr(state_index, 'operation_index', '?')}"


def reader_unknown_signature(graph: SemanticSymbolicBindingGraph) -> tuple[str, str, str]:
    """The reader's question-target signature from ``graph.unknowns`` (PR-1).

    A graph that does not carry exactly one unknown is itself a structural defect — it
    is reported as a distinguished ``MALFORMED`` signature so it can never silently
    compare equal to a well-formed gold target.
    """
    unknowns = graph.unknowns
    if len(unknowns) != 1:
        return ("MALFORMED", str(len(unknowns)), "")
    u = unknowns[0]
    return (u.symbol_id, _state_token(u.state_index), u.question_form)


__all__ = [
    "gold_unknown_signature",
    "reader_unknown_signature",
    "relation_signature",
]
