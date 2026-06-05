"""Independent finite-order oracle for the staged Phase 2 gold lane.

The oracle reads only structured pairwise ``less < greater`` facts over a finite
item set. It refuses cycles, incomparability for sort queries, unknown items, and
malformed relations. It imports no engine, reader, algebra, field, or generation
code.
"""

from __future__ import annotations

from typing import Any


class OracleError(ValueError):
    """Malformed or out-of-grammar case; the oracle refuses, never guesses."""


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise OracleError(f"{label} must be a non-empty string: {value!r}")
    return value


def _items(raw: object) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise OracleError("items must be a non-empty list")
    items = [_require_str(v, "item") for v in raw]
    if len(set(items)) != len(items):
        raise OracleError("items contains duplicates")
    return items


def _closure(items: list[str], relations: object) -> dict[str, set[str]]:
    item_set = set(items)
    if not isinstance(relations, list):
        raise OracleError("relations must be a list")
    less_than: dict[str, set[str]] = {item: set() for item in items}
    for rel in relations:
        if not isinstance(rel, dict):
            raise OracleError(f"relation must be an object: {rel!r}")
        less = _require_str(rel.get("less"), "relation.less")
        greater = _require_str(rel.get("greater"), "relation.greater")
        if less not in item_set or greater not in item_set:
            raise OracleError(f"relation names unknown item: {rel!r}")
        if less == greater:
            raise OracleError("irreflexive order cannot relate an item to itself")
        less_than[less].add(greater)

    changed = True
    while changed:
        changed = False
        for item in items:
            expanded = set(less_than[item])
            for mid in tuple(less_than[item]):
                expanded.update(less_than[mid])
            if item in expanded:
                raise OracleError("cycle in ordering relations")
            if expanded != less_than[item]:
                less_than[item] = expanded
                changed = True
    return less_than


def oracle_answer(structure: dict[str, Any], query: dict[str, Any]) -> list[str] | str:
    """Return a sort or comparison result from a finite strict total order."""
    items = _items(structure.get("items"))
    less_than = _closure(items, structure.get("relations", []))
    item_set = set(items)

    def compare(left: str, right: str) -> str:
        if left not in item_set or right not in item_set:
            raise OracleError(f"query names unknown item: {left!r}, {right!r}")
        if left == right:
            return "equal"
        if right in less_than[left]:
            return "less"
        if left in less_than[right]:
            return "greater"
        raise OracleError(f"items are incomparable: {left!r}, {right!r}")

    kind = query.get("kind")
    if kind == "compare":
        return compare(
            _require_str(query.get("left"), "query.left"),
            _require_str(query.get("right"), "query.right"),
        )
    if kind == "sort":
        order = query.get("order", "ascending")
        if order not in ("ascending", "descending"):
            raise OracleError(f"unsupported sort order: {order!r}")
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                compare(left, right)
        sorted_items = sorted(items, key=lambda item: (-len(less_than[item]), item))
        if order == "descending":
            sorted_items = list(reversed(sorted_items))
        return sorted_items
    raise OracleError(f"unsupported query kind: {kind!r}")
