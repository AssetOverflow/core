"""Span-free structural signatures for the setup-oracle.

A *signature* is a deterministic, order-independent, span-free projection of the
mathematical SETUP — what the reader claims the problem says, stripped of input
offsets and surface tokens. Two readings are setup-equivalent iff their signatures
are equal. Used to compare the reader's comprehended structure against the
independent gold structure (the relational_metric cases' own `relations`/`query`).

v2 (PR-5a) grades: facts (entity, value), equations (the typed relation shape), the
question target (symbol, state-index, question-form, **unit**), and the **per-symbol
unit** — read from the binding-graph itself, not the answer projection. A reading whose
structure matches but whose units diverge from the independent expected-unit gold now
FAILS (``setup_wrong``). The ruler must be unit-aware before it judges real GSM8K frames.
"""

from __future__ import annotations

from typing import Any

from generate.binding_graph.model import SemanticSymbolicBindingGraph


def symbol_unit_signature(units: dict[str, str | None]) -> tuple[tuple[str, str], ...]:
    """Canonicalize a per-symbol unit map into a sorted, order-independent signature.

    Used for BOTH sides: the reader's units come from the binding-graph's symbols; the
    gold's from the independent ``expected_units`` fixture. A ``None`` unit (a symbol the
    reader left unmodelled) canonicalizes to ``"unset"`` so it can never silently match a
    declared gold unit.
    """
    return tuple(
        sorted((sid, unit if unit is not None else "unset") for sid, unit in units.items())
    )


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
    relations: list[dict[str, Any]],
    query: dict[str, Any],
    expected_units: dict[str, str],
) -> tuple[str, str, str, str]:
    """The expected question-target signature, derived from the INDEPENDENT gold.

    A query whose target is an aggregate (the gold contains a ``sum_of`` producing it)
    is a ``total`` form; otherwise a ``count``. All current cases ask the terminal state.
    The expected target unit comes from the independent ``expected_units`` fixture.
    """
    form = "total" if any(r["kind"] == "sum_of" for r in relations) else "count"
    entity = query["entity"]
    return (entity, "terminal", form, expected_units.get(entity, "unset"))


def _state_token(state_index: Any) -> str:
    if isinstance(state_index, str):
        return state_index
    # An Operation state-index (ADR-0135) — name it by its operation index.
    return f"op{getattr(state_index, 'operation_index', '?')}"


def reader_unknown_signature(
    graph: SemanticSymbolicBindingGraph,
) -> tuple[str, str, str, str]:
    """The reader's question-target signature from ``graph.unknowns`` (PR-1), now with
    the target's ``expected_unit`` (PR-5a).

    A graph that does not carry exactly one unknown is itself a structural defect — it
    is reported as a distinguished ``MALFORMED`` signature so it can never silently
    compare equal to a well-formed gold target.
    """
    unknowns = graph.unknowns
    if len(unknowns) != 1:
        return ("MALFORMED", str(len(unknowns)), "", "")
    u = unknowns[0]
    return (
        u.symbol_id,
        _state_token(u.state_index),
        u.question_form,
        u.expected_unit if u.expected_unit is not None else "unset",
    )


def reader_symbol_units(graph: SemanticSymbolicBindingGraph) -> tuple[tuple[str, str], ...]:
    """The reader's per-symbol unit signature, read from the BINDING-GRAPH (not the
    answer projection) — the unit each symbol was modelled with."""
    return symbol_unit_signature({s.symbol_id: s.unit for s in graph.symbols})


__all__ = [
    "gold_unknown_signature",
    "reader_symbol_units",
    "reader_unknown_signature",
    "relation_signature",
    "symbol_unit_signature",
]
