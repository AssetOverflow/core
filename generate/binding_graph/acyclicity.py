"""ADR-0203 — Acyclicity invariant for the binding-graph dependency structure.

Pure cycle detection over a ``{node: successors}`` adjacency, isolated from the
binding-graph model so it is testable against synthetic graphs with no
binding-graph construction. The model's ``__post_init__`` adapts its equations
into an adjacency and calls :func:`find_cycle`; a non-``None`` result is refused
with the typed reason :data:`CIRCULAR_DEPENDENCY`.

Why this exists (additive to ADR-0132, which it references): the ADR-0132 data
model enforces *referential integrity* (every dependency names a known symbol) but
not *acyclicity*. A cycle in the equation dependency structure is **circular
reasoning** — concluding ``P`` because ``Q`` because ``P`` — the proof-domain
analog of the ``20/5 == 4`` class: structurally well-formed, semantically invalid.
``proof_chain`` is the first consumer that can build such a structure, so the guard
lands at the shared construction boundary *before* that wiring exists (ADR-0201
phase 2.1).

On main today the only producer of binding graphs is the math adapter
(`generate/binding_graph/adapter.py`), which mints a fresh result symbol per
operation and depends only on symbols that already exist — edges point strictly
backward in construction order, so it is **acyclic by construction**. This guard
therefore refuses no existing graph; it protects the structure the moment a future
consumer could build a cycle.

Honesty boundary (carried by every phase-2 ADR, 0203–0205): through phase 2.3,
``proof_chain`` is **sound over its declared atoms**, not grounded in recognized
input. Atom→carrier grounding is phase 2.4. This module is structure-only and makes
no grounding claim.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

CIRCULAR_DEPENDENCY: Final[str] = "circular_dependency"


def find_cycle(adjacency: Mapping[str, frozenset[str]]) -> tuple[str, ...] | None:
    """Return a directed cycle as an ordered tuple ``(n0, …, nk, n0)``, or
    ``None`` if the graph is acyclic.

    ``adjacency`` maps a node to the set of nodes it points to (an equation's
    ``lhs_symbol_id`` → the symbols it reads). Nodes that appear only as
    successors (leaf dependencies defined by no equation) have no out-edges and
    cannot start a cycle.

    Deterministic: roots and successors are visited in sorted order, so the
    reported cycle is byte-stable across runs (the replay discipline). A node
    listing itself as a successor is reported as a length-1 self-cycle
    ``(n, n)``.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in adjacency}
    for succs in adjacency.values():
        for succ in succs:
            color.setdefault(succ, WHITE)

    def successors(node: str) -> list[str]:
        return sorted(adjacency.get(node, frozenset()))

    # Iterative three-colour DFS (iterative to avoid recursion limits on long
    # dependency chains). GREY = on the current DFS path; a GREY successor is a
    # back-edge, i.e. a cycle.
    for root in sorted(color):
        if color[root] != WHITE:
            continue
        path: list[str] = [root]
        stack: list[tuple[str, list[str]]] = [(root, successors(root))]
        color[root] = GREY
        while stack:
            node, succs = stack[-1]
            descended = False
            while succs:
                nxt = succs.pop(0)
                state = color[nxt]
                if state == GREY:
                    start = path.index(nxt)
                    return tuple(path[start:] + [nxt])
                if state == WHITE:
                    color[nxt] = GREY
                    path.append(nxt)
                    stack.append((nxt, successors(nxt)))
                    descended = True
                    break
                # BLACK: fully explored, no cycle through it — skip.
            if not descended:
                color[node] = BLACK
                path.pop()
                stack.pop()
    return None
