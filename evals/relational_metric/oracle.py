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

Plus one narrow off-grammar extension — a reverse-solve (PR-7a): the base of a single
more_than/fewer_than whose other side is grounded (``Nia has 9 more than Omar. Nia has
15. -> Omar = 6``). It is deliberately tiny — single base constraint, base == query
target (no chains), base not otherwise grounded, non-negative count result, more/fewer
only (never times/divide). Everything wider refuses.

Every forward relation's references must already be resolved (forward-substitutable /
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

    Plus one narrow reverse-solve (PR-7a): a single more_than/fewer_than whose entity
    is grounded and whose ref is the (otherwise ungrounded) query target is inverted to
    that base — ``base = entity -/+ delta``. The reverse-solve refuses on anything wider:
    more than one inverse constraint, an inverse base that is not the query target (a
    chain), an already-grounded base, a negative result (count domain), or an inverse
    over times/divide. The +/- inversion is always integer-exact.

    Raises :class:`OracleError` on an unknown relation kind, a forward reference to
    an unresolved entity, a duplicate definition, malformed scalar, an out-of-contract
    reverse-solve, or a missing query entity.
    """
    values: dict[str, int] = {}
    # Deferred narrow inverse (PR-7a): a more_than/fewer_than whose ENTITY is already
    # grounded (by a prior fact) and whose REF is unresolved is NOT a duplicate
    # definition — it pins its ref (the unknown base). Collected here, resolved after
    # the forward pass so the single-base / no-chains guardrails apply to the whole set.
    inverse: list[tuple[str, str, str, int]] = []  # (kind, entity, ref, delta)

    for rel in relations:
        kind = rel.get("kind")
        entity = rel.get("entity")
        if kind not in _SUPPORTED:
            raise OracleError(f"unsupported relation kind: {kind!r}")
        if not isinstance(entity, str) or not entity:
            raise OracleError(f"relation missing entity: {rel!r}")

        if kind == "fact":
            if entity in values:
                raise OracleError(f"duplicate definition of {entity!r}")
            value = rel.get("value")
            if not isinstance(value, int) or isinstance(value, bool):
                raise OracleError(f"fact value must be int: {rel!r}")
            values[entity] = value
        elif kind in ("more_than", "fewer_than"):
            ref = rel.get("ref")
            delta = rel.get("delta")
            if not isinstance(ref, str) or not ref:
                raise OracleError(f"relation missing ref: {rel!r}")
            if not isinstance(delta, int) or isinstance(delta, bool):
                raise OracleError(f"delta must be int: {rel!r}")
            entity_known = entity in values
            ref_known = ref in values
            if entity_known and not ref_known:
                # INVERSE: the unknown is the ref (base). Solved in phase 2.
                inverse.append((kind, entity, ref, delta))
            elif not entity_known and ref_known:
                values[entity] = values[ref] + (delta if kind == "more_than" else -delta)
            elif not entity_known and not ref_known:
                raise OracleError(f"forward reference to unresolved {ref!r}")
            else:  # both sides grounded -> over-determined, refuse rather than ignore
                raise OracleError(f"over-determined relation (both sides known): {rel!r}")
        elif kind == "times_as_many":
            if entity in values:
                # Reverse-solve over times/divide is NOT in the PR-7a contract.
                raise OracleError(f"duplicate definition of {entity!r}")
            ref = rel.get("ref")
            factor = rel.get("factor")
            if ref not in values:
                raise OracleError(f"forward reference to unresolved {ref!r}")
            if not isinstance(factor, int) or isinstance(factor, bool):
                raise OracleError(f"factor must be int: {rel!r}")
            values[entity] = values[ref] * factor
        elif kind == "divide_by":
            if entity in values:
                raise OracleError(f"duplicate definition of {entity!r}")
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
            if entity in values:
                raise OracleError(f"duplicate definition of {entity!r}")
            parts = rel.get("parts")
            if not isinstance(parts, list) or not parts:
                raise OracleError(f"sum_of needs non-empty parts: {rel!r}")
            if any(p not in values for p in parts):
                raise OracleError(f"sum_of references unresolved part: {rel!r}")
            values[entity] = sum(values[p] for p in parts)

    target = query.get("entity")

    # Phase 2: narrow reverse-solve (PR-7a). The single unknown is the base of exactly
    # one more_than/fewer_than whose other side is grounded. Anything wider refuses.
    if inverse:
        if len(inverse) != 1:
            raise OracleError(
                f"reverse-solve supports a single base constraint only: {inverse!r}"
            )
        kind, ent, ref, delta = inverse[0]
        if target in values:
            raise OracleError("reverse-solve constraint present but target already determined")
        if ref != target:
            raise OracleError(
                f"reverse-solve base {ref!r} is not the query target {target!r} (no chains)"
            )
        if ref in values:
            raise OracleError(f"reverse-solve base {ref!r} is already grounded")
        # more_than: entity = base + delta -> base = entity - delta;
        # fewer_than: entity = base - delta -> base = entity + delta. (Always exact for +/-.)
        result = values[ent] - delta if kind == "more_than" else values[ent] + delta
        if result < 0:
            raise OracleError(f"reverse-solve base is negative (count domain): {result}")
        values[ref] = result

    if target not in values:
        raise OracleError(f"query entity {target!r} not resolved")
    return values[target]
