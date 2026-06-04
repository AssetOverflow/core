"""Finite-entity grounding — compile a typed finite-entity problem to
propositional atoms (Phase 2 of the universal-structure plan; the deductive-logic
runway doc's PR-1).

This is the first **comprehension compiler**: it lowers a structured, finite-entity
problem (finite named entities, unary predicates, single-variable universal rules)
into the propositional regime the ADR-0206 entailment operator already decides —
exactly where `wrong == 0` is structural. A grounded finite-entity problem (each
``predicate(entity)`` pair → one atom) IS propositional and in scope; anything
outside the narrow v1 grammar refuses with a typed reason rather than guessing.

Lowering law (deterministic):

    predicate(entity)            -> ``predicate_slug__entity_slug``  (atom)
    negative literal             -> ``~atom``
    rule body (∧ of literals)    -> conjunction of lowered body literals
    universal rule ∀x. B(x)->H(x)-> for each entity e: ``lower(B[e]) -> lower(H[e])``
    query                        -> the lowered query literal

The lowered ``(premises, query)`` is decided by **two independent procedures**
(the ROBDD engine and the truth-table oracle); a case counts only when both agree
with the gold (INV-25). v1 keeps the grammar intentionally narrow — that narrowness
is the firewall, not a weakness.

Sealed: no ``chat`` import, no serving path. Deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

# Closed refusal vocabulary for the grounding layer — distinct from the entailment
# operator's reasons so a malformed case never leaks into an ambiguous failure.
UNSUPPORTED_PREDICATE_ARITY: Final[str] = "unsupported_predicate_arity"
UNSUPPORTED_QUANTIFIER: Final[str] = "unsupported_quantifier"
UNSAFE_SYMBOL: Final[str] = "unsafe_symbol"
UNKNOWN_ENTITY: Final[str] = "unknown_entity"
UNKNOWN_VARIABLE: Final[str] = "unknown_variable"
MALFORMED_CASE: Final[str] = "malformed_case"
EMPTY_CASE: Final[str] = "empty_case"

GROUNDING_REASONS: Final[frozenset[str]] = frozenset({
    UNSUPPORTED_PREDICATE_ARITY,
    UNSUPPORTED_QUANTIFIER,
    UNSAFE_SYMBOL,
    UNKNOWN_ENTITY,
    UNKNOWN_VARIABLE,
    MALFORMED_CASE,
    EMPTY_CASE,
})

_ATOM_SEPARATOR: Final[str] = "__"
# A slug component: lowercase ASCII letters/digits/single underscores, no leading
# digit, no empty, no double-underscore (would collide with the separator).
_SLUG_RE: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


class GroundingError(ValueError):
    """A finite-entity case outside the v1 grammar. Carries a typed reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in GROUNDING_REASONS:
            raise ValueError(f"unknown grounding reason: {reason!r}")
        self.reason = reason
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True, slots=True)
class GroundedProblem:
    """The lowered finite-entity problem: propositional premises + query."""

    premises: tuple[str, ...]
    query: str


def slug(token: Any) -> str:
    """Deterministic, collision-safe slug. Rejects (never silently repairs)
    anything outside ``[a-z][a-z0-9]*(_[a-z0-9]+)*`` — including the separator,
    leading digits, empties, and double underscores."""
    if not isinstance(token, str):
        raise GroundingError(UNSAFE_SYMBOL, f"non-string symbol {token!r}")
    s = token.strip().lower()
    if not s:
        raise GroundingError(UNSAFE_SYMBOL, "empty symbol")
    if _ATOM_SEPARATOR in s:
        raise GroundingError(UNSAFE_SYMBOL, f"symbol {token!r} contains separator '{_ATOM_SEPARATOR}'")
    if not _SLUG_RE.fullmatch(s):
        raise GroundingError(UNSAFE_SYMBOL, f"symbol {token!r} is not a safe slug")
    return s


def atom(predicate: Any, entity: Any) -> str:
    """``predicate(entity)`` → the canonical propositional atom."""
    return f"{slug(predicate)}{_ATOM_SEPARATOR}{slug(entity)}"


def _literal(predicate: Any, entity: Any, polarity: Any) -> str:
    if not isinstance(polarity, bool):
        raise GroundingError(MALFORMED_CASE, f"polarity must be a bool, got {polarity!r}")
    a = atom(predicate, entity)
    return a if polarity else f"~{a}"


def _require(condition: bool, reason: str, detail: str = "") -> None:
    if not condition:
        raise GroundingError(reason, detail)


def _check_unary(obj: dict[str, Any], *, allow_var: bool) -> None:
    """Reject any non-unary / relational / functional shape (v1 is unary only)."""
    keys = set(obj)
    # A binary relation / function would carry extra argument keys.
    extra = keys - {"predicate", "entity", "var", "polarity"}
    _require(not extra, UNSUPPORTED_PREDICATE_ARITY, f"unexpected keys {sorted(extra)}")
    has_entity = "entity" in obj
    has_var = "var" in obj
    if allow_var:
        _require(has_entity ^ has_var, MALFORMED_CASE, "literal needs exactly one of entity/var")
    else:
        _require(has_entity and not has_var, UNKNOWN_VARIABLE, "free variable outside a rule")


def lower_case(case: dict[str, Any]) -> GroundedProblem:
    """Lower a finite-entity case to ``(premises, query)``. Refuse-first.

    Schema (v1):
        {"entities": [str, ...],
         "facts": [{"predicate": str, "entity": str, "polarity": bool}, ...],
         "rules": [{"if": [<unary literal with var>, ...],
                    "then": <unary literal with var>}, ...],
         "query": {"predicate": str, "entity": str, "polarity": bool}}
    """
    if not isinstance(case, dict) or not case:
        raise GroundingError(EMPTY_CASE, "case is empty or not a mapping")

    entities = case.get("entities")
    if not (isinstance(entities, list) and entities):
        raise GroundingError(EMPTY_CASE, "no entities")
    entity_set = {slug(e) for e in entities}  # also validates each entity slug
    _require(len(entity_set) == len(entities), MALFORMED_CASE, "duplicate entities after slugging")

    if "query" not in case:
        raise GroundingError(MALFORMED_CASE, "no query")

    premises: list[str] = []

    facts = case.get("facts", []) or []
    rules = case.get("rules", []) or []
    _require(isinstance(facts, list), MALFORMED_CASE, "facts must be a list")
    _require(isinstance(rules, list), MALFORMED_CASE, "rules must be a list")

    # Facts — ground unary literals over named entities.
    for fact in facts:
        _require(isinstance(fact, dict), MALFORMED_CASE, f"fact is not a mapping: {fact!r}")
        _check_unary(fact, allow_var=False)
        _require(slug(fact["entity"]) in entity_set, UNKNOWN_ENTITY, str(fact.get("entity")))
        premises.append(_literal(fact["predicate"], fact["entity"], fact.get("polarity", True)))

    # Rules — single-variable universal rules, grounded by explicit entity expansion.
    for rule in rules:
        _require(isinstance(rule, dict), MALFORMED_CASE, f"rule is not a mapping: {rule!r}")
        _require("quantifier" not in rule and "exists" not in rule,
                 UNSUPPORTED_QUANTIFIER, "only implicit single-var universal rules in v1")
        body = rule.get("if")
        head = rule.get("then")
        if not (isinstance(body, list) and body):
            raise GroundingError(MALFORMED_CASE, "rule body must be a non-empty list")
        if not isinstance(head, dict):
            raise GroundingError(MALFORMED_CASE, "rule head must be a literal")
        var = _rule_variable(body, head)
        for ent in entities:
            body_atoms = [_literal(lit["predicate"], ent, lit.get("polarity", True)) for lit in body]
            head_atom = _literal(head["predicate"], ent, head.get("polarity", True))
            body_conj = " & ".join(f"({b})" for b in body_atoms)
            premises.append(f"({body_conj}) -> ({head_atom})")
        _ = var  # validated; grounding is by explicit entity expansion, not by name

    query = case["query"]
    _require(isinstance(query, dict), MALFORMED_CASE, "query must be a literal")
    _check_unary(query, allow_var=False)
    _require(slug(query["entity"]) in entity_set, UNKNOWN_ENTITY, str(query.get("entity")))
    query_lit = _literal(query["predicate"], query["entity"], query.get("polarity", True))

    return GroundedProblem(premises=tuple(premises), query=query_lit)


def _rule_variable(body: list[dict[str, Any]], head: dict[str, Any]) -> str:
    """Confirm the rule is single-variable: every literal uses one shared var,
    no named entities (those would make it not universal). Returns the var name."""
    seen: set[str] = set()
    for lit in (*body, head):
        _require(isinstance(lit, dict), MALFORMED_CASE, f"rule literal not a mapping: {lit!r}")
        _check_unary(lit, allow_var=True)
        _require("var" in lit, MALFORMED_CASE, "rule literals must use a variable, not a named entity")
        v = lit["var"]
        _require(isinstance(v, str) and bool(v.strip()), MALFORMED_CASE, "empty variable")
        seen.add(v)
    _require(len(seen) == 1, UNSUPPORTED_QUANTIFIER, f"v1 allows one variable per rule, saw {sorted(seen)}")
    return seen.pop()
