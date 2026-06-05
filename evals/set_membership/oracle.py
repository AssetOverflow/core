"""Independent set-membership oracle for the staged Phase 2 gold lane.

The oracle reads STRUCTURE only: finite elements, finite sets, direct membership
facts, and subset relations. It performs a plain transitive-closure decision
procedure and refuses malformed/out-of-grammar inputs. It imports no engine,
reader, algebra, field, or generation code; independence will live in a future
text reader, while this lane fixes the gold side.
"""

from __future__ import annotations

from typing import Any


class OracleError(ValueError):
    """Malformed or out-of-grammar case; the oracle refuses, never guesses."""


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise OracleError(f"{label} must be a non-empty string: {value!r}")
    return value


def _require_str_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise OracleError(f"{label} must be a list")
    out = [_require_str(v, label) for v in value]
    if len(set(out)) != len(out):
        raise OracleError(f"{label} contains duplicates")
    return out


def _closure(edges: dict[str, set[str]], sets: set[str]) -> dict[str, set[str]]:
    closed = {s: {s, *edges.get(s, set())} for s in sets}
    changed = True
    while changed:
        changed = False
        for left in sorted(sets):
            expanded = set(closed[left])
            for mid in tuple(closed[left]):
                expanded.update(closed.get(mid, {mid}))
            if expanded != closed[left]:
                closed[left] = expanded
                changed = True
    return closed


def oracle_answer(structure: dict[str, Any], query: dict[str, Any]) -> bool:
    """Return the closed-world membership/subsumption verdict.

    Supported query kinds:
    - ``member``: whether ``element`` is in ``set`` after subset propagation.
    - ``subset``: whether ``subset`` is included in ``superset`` transitively.
    """
    elements = set(_require_str_list(structure.get("elements"), "elements"))

    raw_sets = structure.get("sets")
    if not isinstance(raw_sets, list) or not raw_sets:
        raise OracleError("sets must be a non-empty list")

    members: dict[str, set[str]] = {}
    for raw in raw_sets:
        if not isinstance(raw, dict):
            raise OracleError(f"set entry must be an object: {raw!r}")
        sid = _require_str(raw.get("id"), "set.id")
        if sid in members:
            raise OracleError(f"duplicate set id: {sid!r}")
        direct = set(_require_str_list(raw.get("members", []), f"{sid}.members"))
        unknown = direct - elements
        if unknown:
            raise OracleError(f"set {sid!r} names unknown elements: {sorted(unknown)}")
        members[sid] = direct

    set_ids = set(members)
    edges: dict[str, set[str]] = {sid: set() for sid in set_ids}
    raw_subsets = structure.get("subsets", [])
    if not isinstance(raw_subsets, list):
        raise OracleError("subsets must be a list")
    for raw in raw_subsets:
        if not isinstance(raw, dict):
            raise OracleError(f"subset entry must be an object: {raw!r}")
        subset = _require_str(raw.get("subset"), "subset")
        superset = _require_str(raw.get("superset"), "superset")
        if subset not in set_ids or superset not in set_ids:
            raise OracleError(f"subset relation names unknown set: {raw!r}")
        edges[subset].add(superset)

    closed = _closure(edges, set_ids)
    kind = query.get("kind")
    if kind == "subset":
        subset = _require_str(query.get("subset"), "query.subset")
        superset = _require_str(query.get("superset"), "query.superset")
        if subset not in set_ids or superset not in set_ids:
            raise OracleError(f"query names unknown set: {query!r}")
        return superset in closed[subset]

    if kind == "member":
        element = _require_str(query.get("element"), "query.element")
        target = _require_str(query.get("set"), "query.set")
        if element not in elements:
            raise OracleError(f"query names unknown element: {element!r}")
        if target not in set_ids:
            raise OracleError(f"query names unknown set: {target!r}")
        element_sets = {sid for sid, direct in members.items() if element in direct}
        return any(target in closed[sid] for sid in element_sets)

    raise OracleError(f"unsupported query kind: {kind!r}")

