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
