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
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
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
# A rule whose head contains a variable not bound in its body (non-range-restricted /
# "unsafe" in Datalog terms). It grounds soundly, but it is outside the clean regime
# real rule benchmarks use; refuse rather than silently widen scope.
UNSAFE_RULE: Final[str] = "unsafe_rule"
# The independent gold is a truth-table oracle, O(2^atoms); the grounding refuses a
# problem whose distinct-atom count (or entity/variable count) would make that gold
# intractable, rather than emit something the wrong=0 arbiter cannot decide.
GROUNDING_BOUND_EXCEEDED: Final[str] = "grounding_bound_exceeded"

GROUNDING_REASONS: Final[frozenset[str]] = frozenset({
    UNSUPPORTED_PREDICATE_ARITY,
    UNSUPPORTED_QUANTIFIER,
    UNSAFE_SYMBOL,
    UNKNOWN_ENTITY,
    UNKNOWN_VARIABLE,
    MALFORMED_CASE,
    EMPTY_CASE,
    UNSAFE_RULE,
    GROUNDING_BOUND_EXCEEDED,
})

# ---------------------------------------------------------------------------
# Bounds (v1.5: binary relations + multi-variable rules by finite grounding).
# ---------------------------------------------------------------------------
# Arity ceiling — unary + binary only; arity >= 3 refuses (functions never).
MAX_ARITY: Final[int] = 2
# A rule grounds over n^k assignments (n entities, k distinct variables). These two
# bound n and k so n^k cannot blow up before the atom bound below is even checked.
MAX_ENTITIES: Final[int] = 8
MAX_VARS_PER_RULE: Final[int] = 3
# THE binding constraint: the independent truth-table oracle is O(2^atoms). The
# lowered problem's distinct-atom count must stay small or the gold is intractable.
# 2^20 ~ 1e6 assignments — decidable; binary relations therefore cap at ~4 entities
# per predicate. This is the honest coverage ceiling of the binary extension.
MAX_GROUND_ATOMS: Final[int] = 20

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


def atom_n(predicate: Any, entity_slugs: Sequence[str]) -> str:
    """``predicate(arg1, ..., argk)`` → the canonical propositional atom.

    Arity 1 is byte-identical to :func:`atom` (``predicate__entity``), so every
    pre-existing unary problem lowers unchanged. The ``__`` separator between args
    cannot collide with a slug (slugs reject ``__``), so the atom is injective in
    ``(predicate, args)`` and arity-1 vs arity-2 atoms never alias.
    """
    return _ATOM_SEPARATOR.join([slug(predicate), *(slug(e) for e in entity_slugs)])


def _lit_str(atom_str: str, polarity: Any) -> str:
    if not isinstance(polarity, bool):
        raise GroundingError(MALFORMED_CASE, f"polarity must be a bool, got {polarity!r}")
    return atom_str if polarity else f"~{atom_str}"


def _require(condition: bool, reason: str, detail: str = "") -> None:
    if not condition:
        raise GroundingError(reason, detail)


# A term is ("entity", name) or ("var", name) — name is the raw case string.
_Term = tuple[str, str]
_NormLiteral = tuple[Any, tuple[_Term, ...], bool]


def _normalize_term(arg: Any, *, allow_var: bool) -> _Term:
    _require(isinstance(arg, dict), MALFORMED_CASE, f"arg not a mapping: {arg!r}")
    extra = set(arg) - {"entity", "var"}
    _require(not extra, MALFORMED_CASE, f"unexpected arg keys {sorted(extra)}")
    has_entity, has_var = "entity" in arg, "var" in arg
    _require(has_entity ^ has_var, MALFORMED_CASE, "arg needs exactly one of entity/var")
    if has_var:
        _require(allow_var, UNKNOWN_VARIABLE, "free variable outside a rule")
        v = arg["var"]
        _require(isinstance(v, str) and bool(v.strip()), MALFORMED_CASE, "empty variable")
        return ("var", v)
    return ("entity", arg["entity"])


def _normalize_literal(obj: Any, *, allow_var: bool) -> _NormLiteral:
    """Normalize a literal — legacy unary ``{entity|var}`` OR general
    ``{args:[{entity|var},...]}`` — to ``(predicate, terms, polarity)``. Refuses
    arity 0 / > :data:`MAX_ARITY` (functions and ternary relations) with a typed reason.
    """
    _require(isinstance(obj, dict), MALFORMED_CASE, f"literal not a mapping: {obj!r}")
    _require("predicate" in obj, MALFORMED_CASE, "literal missing predicate")
    polarity = obj.get("polarity", True)
    _require(isinstance(polarity, bool), MALFORMED_CASE, f"polarity must be bool: {polarity!r}")

    if "args" in obj:
        _require("entity" not in obj and "var" not in obj, MALFORMED_CASE,
                 "use 'args' OR 'entity'/'var', not both")
        extra = set(obj) - {"predicate", "args", "polarity"}
        _require(not extra, UNSUPPORTED_PREDICATE_ARITY, f"unexpected keys {sorted(extra)}")
        args = obj["args"]
        _require(isinstance(args, list) and bool(args), MALFORMED_CASE, "args must be a non-empty list")
        terms = tuple(_normalize_term(a, allow_var=allow_var) for a in args)
    else:
        extra = set(obj) - {"predicate", "entity", "var", "polarity"}
        _require(not extra, UNSUPPORTED_PREDICATE_ARITY, f"unexpected keys {sorted(extra)}")
        has_entity, has_var = "entity" in obj, "var" in obj
        _require(has_entity ^ has_var, MALFORMED_CASE, "unary literal needs exactly one of entity/var")
        if has_var:
            _require(allow_var, UNKNOWN_VARIABLE, "free variable outside a rule")
            v = obj["var"]
            _require(isinstance(v, str) and bool(v.strip()), MALFORMED_CASE, "empty variable")
            terms = (("var", v),)
        else:
            terms = (("entity", obj["entity"]),)

    _require(1 <= len(terms) <= MAX_ARITY, UNSUPPORTED_PREDICATE_ARITY,
             f"arity {len(terms)} outside 1..{MAX_ARITY}")
    if not allow_var:
        _require(all(k == "entity" for k, _ in terms), UNKNOWN_VARIABLE, "free variable outside a rule")
    return obj["predicate"], terms, polarity


def _collect_vars(literals: Sequence[_NormLiteral]) -> list[str]:
    """Distinct variable names across a rule's literals, in first-seen order."""
    names: list[str] = []
    for _pred, terms, _pol in literals:
        for kind, name in terms:
            if kind == "var" and name not in names:
                names.append(name)
    return names


def lower_case(case: dict[str, Any]) -> GroundedProblem:
    """Lower a finite-entity case to ``(premises, query)``. Refuse-first.

    Schema (v1.5 — extends v1 with binary relations + multi-variable rules):
        {"entities": [str, ...],
         "facts":    [<ground literal>, ...],
         "rules":    [{"if": [<literal-with-vars>, ...], "then": <literal-with-vars>}, ...],
         "query":    <ground literal>}

    A literal is either legacy unary ``{"predicate","entity"|"var","polarity"}`` or
    general ``{"predicate","args":[{"entity"|"var": str}, ...],"polarity"}`` of arity
    1..2. Universal rules are grounded by enumerating every assignment of their
    variables to named entities (``n^k``). Unary single-var problems lower
    byte-identically to v1. Anything outside the regime or above the bounds refuses.
    """
    _require(isinstance(case, dict) and bool(case), EMPTY_CASE, "case is empty or not a mapping")

    entities = case.get("entities")
    if not (isinstance(entities, list) and entities):  # narrows for the type checker
        raise GroundingError(EMPTY_CASE, "no entities")
    _require(len(entities) <= MAX_ENTITIES, GROUNDING_BOUND_EXCEEDED,
             f"{len(entities)} entities > {MAX_ENTITIES}")
    entity_slugs = [slug(e) for e in entities]  # validates each entity slug
    entity_set = set(entity_slugs)
    _require(len(entity_set) == len(entities), MALFORMED_CASE, "duplicate entities after slugging")
    _require("query" in case, MALFORMED_CASE, "no query")

    facts = case.get("facts", []) or []
    rules = case.get("rules", []) or []
    _require(isinstance(facts, list), MALFORMED_CASE, "facts must be a list")
    _require(isinstance(rules, list), MALFORMED_CASE, "rules must be a list")

    premises: list[str] = []
    atoms_seen: set[str] = set()

    def emit(predicate: Any, resolved: list[str], polarity: bool) -> str:
        a = atom_n(predicate, resolved)
        atoms_seen.add(a)
        _require(len(atoms_seen) <= MAX_GROUND_ATOMS, GROUNDING_BOUND_EXCEEDED,
                 f"{len(atoms_seen)} distinct atoms > {MAX_GROUND_ATOMS} "
                 "(the independent truth-table gold is O(2^atoms))")
        return _lit_str(a, polarity)

    def resolve(terms: tuple[_Term, ...], sigma: dict[str, str]) -> list[str]:
        out: list[str] = []
        for kind, name in terms:
            if kind == "var":
                out.append(sigma[name])  # already a validated entity slug
            else:
                s = slug(name)
                _require(s in entity_set, UNKNOWN_ENTITY, str(name))
                out.append(s)
        return out

    # Facts — ground literals (no variables).
    for fact in facts:
        predicate, terms, polarity = _normalize_literal(fact, allow_var=False)
        premises.append(emit(predicate, resolve(terms, {}), polarity))

    # Rules — universal, grounded over every assignment of variables to entities.
    for rule in rules:
        _require(isinstance(rule, dict), MALFORMED_CASE, f"rule is not a mapping: {rule!r}")
        _require("quantifier" not in rule and "exists" not in rule,
                 UNSUPPORTED_QUANTIFIER, "only implicit universal rules are supported")
        body = rule.get("if")
        head = rule.get("then")
        _require(isinstance(body, list) and bool(body), MALFORMED_CASE, "rule body must be a non-empty list")
        _require(isinstance(head, dict), MALFORMED_CASE, "rule head must be a literal")
        body_norm = [_normalize_literal(lit, allow_var=True) for lit in body]
        head_norm = _normalize_literal(head, allow_var=True)
        var_names = _collect_vars([*body_norm, head_norm])
        _require(bool(var_names), UNSUPPORTED_QUANTIFIER,
                 "a rule must contain at least one variable (a variable-free rule is just a fact)")
        _require(len(var_names) <= MAX_VARS_PER_RULE, GROUNDING_BOUND_EXCEEDED,
                 f"{len(var_names)} variables > {MAX_VARS_PER_RULE}")
        # Range-restriction (safety): every head variable must be bound in the body.
        unbound = set(_collect_vars([head_norm])) - set(_collect_vars(body_norm))
        _require(not unbound, UNSAFE_RULE, f"head variable(s) {sorted(unbound)} not bound in the body")
        for assignment in product(entity_slugs, repeat=len(var_names)):
            sigma = dict(zip(var_names, assignment, strict=True))
            body_lits = [emit(p, resolve(ts, sigma), pol) for (p, ts, pol) in body_norm]
            hp, hts, hpol = head_norm
            head_lit = emit(hp, resolve(hts, sigma), hpol)
            body_conj = " & ".join(f"({b})" for b in body_lits)
            premises.append(f"({body_conj}) -> ({head_lit})")

    # Query — a ground literal.
    qpred, qterms, qpol = _normalize_literal(case["query"], allow_var=False)
    query_lit = emit(qpred, resolve(qterms, {}), qpol)

    return GroundedProblem(premises=tuple(premises), query=query_lit)
