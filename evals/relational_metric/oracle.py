"""Independent arithmetic oracle — the gold for the relational-metric lane.

This is **deliberately a second, independent decision procedure**: it computes the
answer to a forward-substitutable quantitative-relational problem by plain integer
arithmetic over the *structured* relations. It never reads problem text, and it
shares **no code** with the geometric field reader under test
(``generate.relational_field_reader``) — it imports no ``algebra`` / ``field`` /
``generate`` module. Two independent procedures (the field reader off the TEXT, the
oracle off the STRUCTURE) agreeing is real evidence the field READ the text
correctly; a shared-code "gold" would only prove the reader agrees with itself
(INV-25).

Supported relation kinds (the v1 + PR-6b forward-substitutable grammar):

- ``fact``          : ``entity = value`` (a given quantity)
- ``more_than``     : ``entity = ref + delta``
- ``fewer_than``    : ``entity = ref - delta``
- ``times_as_many`` : ``entity = ref * factor`` (dimensionless integer scalar)
- ``divide_by``     : ``entity = ref // divisor`` (exact integer division only)
- ``sum_of``        : ``entity = sum(parts)``  (part-whole / total)

Every relation's references must already be resolved (forward-substitutable /
triangular). The oracle refuses anything else, never guesses.  PR-6b/6c keep this
off-serving: they let setup-correct R1 cases compute answers in the eval lane only.

``divide_by`` is exact-only: a non-exact division (``base % divisor != 0``, e.g. an
odd base halved) REFUSES rather than flooring to a wrong integer — the wrong=0 boundary
for the "half as many" frame (PR-6c).
"""

from __future__ import annotations

from typing import Any


class OracleError(ValueError):
    """Malformed or out-of-grammar case — the oracle refuses, never guesses."""


_SUPPORTED = frozenset(
    {"fact", "more_than", "fewer_than", "sum_of", "times_as_many", "divide_by"}
)


def oracle_answer(relations: list[dict[str, Any]], query: dict[str, Any]) -> int:
    """Compute the integer answer by forward substitution over the relations.

    Raises :class:`OracleError` on an unknown relation kind, a forward reference to
    an unresolved entity, a duplicate definition, malformed scalar, or a missing
    query entity.
    """
    values: dict[str, int] = {}

    for rel in relations:
        kind = rel.get("kind")
        entity = rel.get("entity")
        if kind not in _SUPPORTED:
            raise OracleError(f"unsupported relation kind: {kind!r}")
        if not isinstance(entity, str) or not entity:
            raise OracleError(f"relation missing entity: {rel!r}")
        if entity in values:
            raise OracleError(f"duplicate definition of {entity!r}")

        if kind == "fact":
            value = rel.get("value")
            if not isinstance(value, int) or isinstance(value, bool):
                raise OracleError(f"fact value must be int: {rel!r}")
            values[entity] = value
        elif kind in ("more_than", "fewer_than"):
            ref = rel.get("ref")
            delta = rel.get("delta")
            if ref not in values:
                raise OracleError(f"forward reference to unresolved {ref!r}")
            if not isinstance(delta, int) or isinstance(delta, bool):
                raise OracleError(f"delta must be int: {rel!r}")
            values[entity] = values[ref] + (delta if kind == "more_than" else -delta)
        elif kind == "times_as_many":
            ref = rel.get("ref")
            factor = rel.get("factor")
            if ref not in values:
                raise OracleError(f"forward reference to unresolved {ref!r}")
            if not isinstance(factor, int) or isinstance(factor, bool):
                raise OracleError(f"factor must be int: {rel!r}")
            values[entity] = values[ref] * factor
        elif kind == "divide_by":
            ref = rel.get("ref")
            divisor = rel.get("divisor")
            if ref not in values:
                raise OracleError(f"forward reference to unresolved {ref!r}")
            if not isinstance(divisor, int) or isinstance(divisor, bool) or divisor == 0:
                raise OracleError(f"divisor must be a nonzero int: {rel!r}")
            if values[ref] % divisor != 0:
                # Exact-only: refuse rather than floor to a wrong integer (wrong=0).
                raise OracleError(f"non-exact division {values[ref]}/{divisor}: {rel!r}")
            values[entity] = values[ref] // divisor
        else:  # sum_of
            parts = rel.get("parts")
            if not isinstance(parts, list) or not parts:
                raise OracleError(f"sum_of needs non-empty parts: {rel!r}")
            if any(p not in values for p in parts):
                raise OracleError(f"sum_of references unresolved part: {rel!r}")
            values[entity] = sum(values[p] for p in parts)

    target = query.get("entity")
    if target not in values:
        raise OracleError(f"query entity {target!r} not resolved")
    return values[target]
