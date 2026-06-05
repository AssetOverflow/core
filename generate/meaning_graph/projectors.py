"""Projectors — map a comprehended ``MeaningGraph`` into a reasoner's input shape.

The comprehension reader produces a neutral ``MeaningGraph``; a projector adapts
it to a specific independent-gold reasoner so the reader can be scored end-to-end
(prose -> MeaningGraph -> projection -> oracle -> answer vs gold). Projectors hold
NO decision logic — they only re-shape; the verdict is the independent oracle's.
"""

from __future__ import annotations

from typing import Any

from generate.meaning_graph.reader import Comprehension

# Neutral categorical predicate -> Aristotelian syllogism form.
_SYLLOGISM_FORM = {"subset": "A", "disjoint": "E", "intersects": "I", "some_not": "O"}


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


def to_syllogism(
    comp: Comprehension, domain_size: int = 3
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project into ``(structure, query)`` for ``evals.syllogism.oracle``.

    Categorical relations become premises; the single 'Therefore' conclusion
    becomes the validity query. ``domain_size`` matches the v1 lane (categorical
    validity is stable for domain_size >= 2). Returns ``None`` when there is not
    exactly one categorical conclusion with at least one premise.
    """
    graph = comp.meaning_graph
    terms = sorted({e.entity_id for e in graph.entities if e.kind == "class"})
    premises = [
        {"form": _SYLLOGISM_FORM[r.predicate], "subject": r.arguments[0], "predicate": r.arguments[1]}
        for r in graph.relations
        if r.predicate in _SYLLOGISM_FORM and not r.negated
    ]
    conclusions = [q for q in comp.queries if q.predicate in _SYLLOGISM_FORM and not q.negated]
    if len(conclusions) != 1 or not premises or len(terms) < 2:
        return None
    q = conclusions[0]
    structure = {"terms": terms, "domain_size": domain_size, "premises": premises}
    query = {
        "kind": "validity",
        "conclusion": {
            "form": _SYLLOGISM_FORM[q.predicate],
            "subject": q.arguments[0],
            "predicate": q.arguments[1],
        },
    }
    return structure, query


def to_total_ordering(comp: Comprehension) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project into ``(structure, query)`` for ``evals.total_ordering.oracle``.

    ``less`` relations become ``{less, greater}`` edges; the single sort/compare
    question becomes the query. Returns ``None`` without exactly one such question
    or with no ordering relations.
    """
    graph = comp.meaning_graph
    items = sorted({e.entity_id for e in graph.entities if e.kind == "item"})
    edges = [
        {"less": r.arguments[0], "greater": r.arguments[1]}
        for r in graph.relations
        if r.predicate == "less" and not r.negated
    ]
    sort_queries = [q for q in comp.queries if q.predicate == "sort"]
    compare_queries = [q for q in comp.queries if q.predicate == "compare"]
    if len(sort_queries) + len(compare_queries) != 1 or not edges:
        return None

    structure = {"items": items, "relations": edges}
    if sort_queries:
        query = {"kind": "sort", "order": sort_queries[0].arguments[0]}
    else:
        q = compare_queries[0]
        query = {"kind": "compare", "left": q.arguments[0], "right": q.arguments[1]}
    return structure, query
