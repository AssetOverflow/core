"""Independent transitive-closure oracle — BFS reachability over STRUCTURED edges.

Authored DISJOINT from ``generate.determine`` / ``generate.meaning_graph.relational``
(INV-25 / INV-27): it imports NO engine module. It computes the gold from each case's
structured edge set, so the lane's expected labels are an independent check, not the
engine's echo. It carries its OWN declaration of which predicates are transitive (from
order semantics, not imported) and its OWN BFS — so if the engine ever made a different
predicate transitive, or composed inverse/cross-predicate edges, this oracle would still
say those chains are not entailed and the disagreement (wrong>0) would surface.

Scope — same-predicate transitive closure over the declared STRICT ORDERS, the exact
capability B2 implements. It is deliberately NOT a fuller semantic reasoner: it does not
compose inverse/symmetric/cross-predicate edges, so an inverse+transitive query is
``False`` here (matching B2's deliberate scope). The independence is in the SEPARATE
authoring, not in being a richer solver.
"""

from __future__ import annotations

from collections import deque

#: The strict orders whose same-predicate transitive closure is sound. Declared HERE,
#: independently of the engine's ``TRANSITIVE_PREDICATES`` — two independent authorings of
#: the same order-theoretic fact (INV-25/27). A predicate NOT here is non-transitive: its
#: chain is reachable as a graph but NOT entailed.
_TRANSITIVE: frozenset[str] = frozenset(
    {"less_than", "greater_than", "before_event", "after_event"}
)


def transitively_entails(
    edges: list[list[str]], predicate: str, subject: str, target: str
) -> bool:
    """``True`` iff ``predicate(subject, target)`` is in the same-predicate transitive
    closure of ``edges`` — BFS reachability ``subject → … → target`` over the edges whose
    predicate is exactly ``predicate``.

    ``False`` (not entailed) for: a non-transitive ``predicate`` (reachability ≠
    entailment), an unreachable ``target`` (a gap or a cross-predicate/disjoint chain), or
    a reflexive query (``subject == target`` — strict orders are irreflexive). ``edges`` is
    a list of ``[predicate, a, b]`` triples; only ``predicate``'s own edges are walked.
    """
    if predicate not in _TRANSITIVE:
        return False  # reachability is NOT entailment for a non-transitive predicate
    if subject == target:
        return False  # strict orders are irreflexive

    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        p, a, b = edge
        if p == predicate:
            adjacency.setdefault(a, []).append(b)

    seen = {subject}
    queue: deque[str] = deque([subject])
    while queue:
        node = queue.popleft()
        for nxt in adjacency.get(node, ()):
            if nxt == target:
                return True
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False
