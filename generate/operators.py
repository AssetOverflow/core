"""Typed deterministic operators over CORE's typed state (ADR-0018).

Two operators land here as the Phase 3 v2 inference-depth bundle.  Both
are pure functions; both are bounded by a ``max_hops`` cap so they
cannot diverge; both produce outputs that round-trip through the
existing pipeline (entities, vault entries).

Operator-invocation records are folded into ``trace_hash`` (see
``core/cognition/trace.py``) so any turn that calls an operator stays
bit-for-bit replay-deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_MAX_HOPS = 5


@dataclass(frozen=True, slots=True)
class WalkResult:
    """A typed relation-walk result.

    ``path`` is the sequence of entities visited, starting from the head
    and ending at the deepest entity reachable under the requested
    relation.  Length 1 means no edges were found.  Length > 1 means a
    chain was traversed.

    ``relation`` and ``head`` are echoed back so the result is self-
    describing for downstream wiring and trace_hash inclusion.

    ``truncated`` is True when the walk hit the max_hops bound before
    exhausting the path; consumers should treat that as a soft signal
    that a longer chain may exist in the underlying store.
    """
    head: str
    relation: str
    path: tuple[str, ...]
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "head": self.head,
            "relation": self.relation,
            "path": list(self.path),
            "truncated": self.truncated,
        }


def _normalize(token: str) -> str:
    return token.strip().lower()


def transitive_walk(
    triples: tuple[tuple[str, str, str], ...],
    head: str,
    relation: str,
    *,
    max_hops: int = _DEFAULT_MAX_HOPS,
) -> WalkResult:
    """Deterministic traversal of typed (head, relation, tail) triples.

    Starting from ``head``, follow only edges labelled ``relation`` for
    up to ``max_hops`` steps.  Returns a ``WalkResult`` whose ``path``
    is the chain of visited entities.

    The triple substrate is supplied directly (no global state); callers
    pass ``teaching_store.triples()`` or any equivalent.  Comparisons are
    case-insensitive and whitespace-trimmed.

    Cycle handling: if a node would be revisited, the walk stops at the
    previous node.  This keeps the operator total over arbitrary
    teaching-store contents.

    Determinism: pure function over its arguments; no hidden state.
    """
    if max_hops < 1:
        return WalkResult(head=head, relation=relation, path=(head,), truncated=False)

    head_lc = _normalize(head)
    relation_lc = _normalize(relation)
    edges: dict[str, str] = {}
    for h, r, t in triples:
        if _normalize(r) != relation_lc:
            continue
        h_lc = _normalize(h)
        t_lc = _normalize(t)
        # First-write-wins keeps the operator deterministic when the same
        # head appears more than once under the same relation.
        edges.setdefault(h_lc, t_lc)

    path: list[str] = [head_lc]
    visited = {head_lc}
    cursor = head_lc
    truncated = False
    for _ in range(max_hops):
        nxt = edges.get(cursor)
        if nxt is None:
            break
        if nxt in visited:
            break
        path.append(nxt)
        visited.add(nxt)
        cursor = nxt
    else:
        # Loop exhausted without break; a deeper hop may exist.
        truncated = edges.get(cursor) is not None

    return WalkResult(
        head=head_lc,
        relation=relation_lc,
        path=tuple(path),
        truncated=truncated,
    )


def path_recall(
    triples: tuple[tuple[str, str, str], ...],
    entity: str,
    relation_chain: tuple[str, ...],
    *,
    max_hops: int = _DEFAULT_MAX_HOPS,
) -> tuple[str, ...]:
    """Recall the sequence of entities along a named relation chain.

    A single-element ``relation_chain`` (e.g. ``("is",)``) reduces to
    ``transitive_walk``.  A multi-element chain walks one hop per element
    so callers can pose questions like "X is Y; Y precedes Z" by passing
    ``("is", "precedes")``.

    Returns the path of entities visited.  Empty chain returns just the
    starting entity.  Determinism and case-insensitivity inherit from
    ``transitive_walk``.
    """
    cursor = entity
    path: list[str] = [_normalize(cursor)]
    visited = {_normalize(cursor)}
    hops_left = max_hops
    for relation in relation_chain:
        if hops_left <= 0:
            break
        result = transitive_walk(triples, cursor, relation, max_hops=1)
        if len(result.path) < 2:
            break
        next_entity = result.path[1]
        if next_entity in visited:
            break
        path.append(next_entity)
        visited.add(next_entity)
        cursor = next_entity
        hops_left -= 1
    return tuple(path)
