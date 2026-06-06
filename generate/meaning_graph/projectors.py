"""Projectors — map a comprehended ``MeaningGraph`` into a reasoner's input shape.

The comprehension reader produces a neutral ``MeaningGraph``; a projector adapts
it to a specific independent-gold reasoner so the reader can be scored end-to-end
(prose -> MeaningGraph -> projection -> oracle -> answer vs gold). Projectors hold
NO decision logic — they only re-shape; the verdict is the independent oracle's.
"""

from __future__ import annotations

from typing import Any

from generate.meaning_graph.reader import Comprehension


def to_set_membership(comp: Comprehension) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project into ``(structure, query)`` for ``evals.set_membership.oracle``.

    Returns ``None`` when the comprehension does not carry exactly one membership
    question (nothing to ask the oracle) — the caller treats that as a refusal.
    """
    graph = comp.meaning_graph
    individuals = sorted({e.entity_id for e in graph.entities if e.kind == "individual"})
    classes = sorted({e.entity_id for e in graph.entities if e.kind == "class"})

    member_facts = [
        (r.arguments[0], r.arguments[1])
        for r in graph.relations
        if r.predicate == "member" and not r.negated
    ]
    subset_facts = [
        (r.arguments[0], r.arguments[1])
        for r in graph.relations
        if r.predicate == "subset" and not r.negated
    ]

    member_queries = [q for q in comp.queries if q.predicate == "member" and not q.negated]
    subset_queries = [q for q in comp.queries if q.predicate == "subset" and not q.negated]
    if len(member_queries) + len(subset_queries) != 1:
        return None

    sets = [
        {"id": cid, "members": sorted({ind for ind, cls in member_facts if cls == cid})}
        for cid in classes
    ]
    structure = {
        "elements": individuals,
        "sets": sets,
        "subsets": [{"subset": a, "superset": b} for a, b in subset_facts],
    }
    if member_queries:
        q = member_queries[0]
        query = {"kind": "member", "element": q.arguments[0], "set": q.arguments[1]}
    else:
        q = subset_queries[0]
        query = {"kind": "subset", "subset": q.arguments[0], "superset": q.arguments[1]}
    return structure, query


#: Categorical predicate -> Aristotelian form for the syllogism oracle.
_PRED_FORM = {"subset": "A", "disjoint": "E", "intersects": "I", "some_not": "O"}

#: Finite-model domain size for syllogism validity (matches the gold lane).
_SYLLOGISM_DOMAIN_SIZE = 3


def to_syllogism(comp: Comprehension) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project into ``(structure, query)`` for ``evals.syllogism.oracle``.

    Premises are the categorical relations (subset/disjoint/intersects/some_not);
    the single categorical query is the conclusion. Returns ``None`` when the
    comprehension is not exactly one categorical conclusion over >=1 premise — the
    caller treats that as a refusal (nothing honestly askable of this oracle).
    """
    graph = comp.meaning_graph
    premises = [
        {"form": _PRED_FORM[r.predicate], "subject": r.arguments[0], "predicate": r.arguments[1]}
        for r in graph.relations
        if r.predicate in _PRED_FORM and not r.negated
    ]
    conclusions = [q for q in comp.queries if q.predicate in _PRED_FORM and not q.negated]
    if not premises or len(comp.queries) != 1 or len(conclusions) != 1:
        return None

    c = conclusions[0]
    terms = sorted({e.entity_id for e in graph.entities if e.kind == "class"})
    if len(terms) < 2:
        return None
    structure = {
        "terms": terms,
        "domain_size": _SYLLOGISM_DOMAIN_SIZE,
        "premises": premises,
    }
    query = {
        "kind": "validity",
        "conclusion": {
            "form": _PRED_FORM[c.predicate],
            "subject": c.arguments[0],
            "predicate": c.arguments[1],
        },
    }
    return structure, query


def to_total_ordering(comp: Comprehension) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project into ``(structure, query)`` for ``evals.total_ordering.oracle``.

    Facts are ``less(lo, hi)`` relations; the single query is a sort or compare.
    Returns ``None`` when the comprehension does not carry exactly one ordering
    query — the caller treats that as a refusal.
    """
    graph = comp.meaning_graph
    less_facts = [
        (r.arguments[0], r.arguments[1])
        for r in graph.relations
        if r.predicate == "less" and not r.negated
    ]
    order_queries = [q for q in comp.queries if q.predicate in ("sort", "compare")]
    if len(comp.queries) != 1 or len(order_queries) != 1:
        return None

    q = order_queries[0]
    item_set = {item for pair in less_facts for item in pair}
    if q.predicate == "compare":
        item_set.update(q.arguments)
    structure = {
        "items": sorted(item_set),
        "relations": [{"less": lo, "greater": hi} for lo, hi in less_facts],
    }
    if q.predicate == "sort":
        query = {"kind": "sort", "order": q.arguments[0]}
    else:
        query = {"kind": "compare", "left": q.arguments[0], "right": q.arguments[1]}
    return structure, query


#: Propositional predicates serialized into formula strings for the ROBDD oracle.
_PROP_PREDICATES = frozenset({"implies", "or", "asserted"})


def _formula(predicate: str, args: tuple[str, ...], negated: bool) -> str | None:
    """Serialize a propositional relation/query into a deductive_logic formula
    string (keyword operators the oracle tokenizer accepts)."""
    if predicate == "asserted":
        return f"not {args[0]}" if negated else args[0]
    if predicate == "implies":
        return f"{args[0]} implies {args[1]}"
    if predicate == "or":
        return f"{args[0]} or {args[1]}"
    return None


def to_deductive_logic(comp: Comprehension) -> tuple[tuple[str, ...], str] | None:
    """Project into ``(premises, query)`` formula strings for
    ``evals.deductive_logic.oracle.oracle_entailment``.

    Returns ``None`` (treated as a refusal) unless the comprehension is purely
    propositional with >=1 premise and exactly one propositional query — so a
    categorical/ordering comprehension never leaks into the entailment oracle.
    """
    graph = comp.meaning_graph
    premises: list[str] = []
    for r in graph.relations:
        if r.predicate not in _PROP_PREDICATES:
            return None  # a non-propositional relation -> not this domain
        formula = _formula(r.predicate, r.arguments, r.negated)
        if formula is None:
            return None
        premises.append(formula)

    prop_queries = [q for q in comp.queries if q.predicate in _PROP_PREDICATES]
    if not premises or len(comp.queries) != 1 or len(prop_queries) != 1:
        return None
    query = _formula(prop_queries[0].predicate, prop_queries[0].arguments, prop_queries[0].negated)
    if query is None:
        return None
    return tuple(premises), query
