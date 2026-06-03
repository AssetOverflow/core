"""ADR-0201 — Propositional canonicalizer (the ``proof_chain`` keystone).

Boolean-logic twin of :mod:`generate.math_symbolic_normalizer` /
:mod:`generate.math_symbolic_equivalence`. Where the algebra side normalizes an
expression to a canonical *polynomial string* and compares by byte-equality, this
module canonicalizes a propositional formula to a **Reduced Ordered Binary Decision
Diagram (ROBDD)** under a fixed (sorted) variable ordering and emits a canonical
*string* serialization of the reduced diagram.

Why ROBDD, not CNF/DNF: for a fixed variable ordering the ROBDD is canonical —
two formulas are logically equivalent **iff** their reduced diagrams are
isomorphic. CNF/DNF are merely normal (standardized shape), not canonical, and
have no poly-time equivalence-preserving transform. The reduced diagram collapses
logically-irrelevant variables, so ``P`` and ``P ∧ (Q ∨ ¬Q)`` produce the same key.

``wrong == 0`` discipline (mirrors the sibling): the canonicalizer **refuses**
rather than guesses. Out-of-grammar input raises :class:`LogicError`; a diagram
that would exceed the node budget raises :class:`LogicBudgetError` (a subclass, so
callers catching :class:`LogicError` refuse on both) rather than churning. There is
no approximate path — an answer is either the exact canonical form or a refusal.

Honesty boundary: this is **propositional** logic only (finite Boolean variables —
decidable, canonical). It does NOT canonicalize quantifiers/predicate logic and
must not be used to claim ``wrong == 0`` for first-order reasoning.

Hand-rolled (no external BDD library) to stay in CORE's idiom: deterministic by
construction, fully inspectable, zero opaque dependencies — the same posture as the
hand-rolled symbolic normalizer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Errors (twin of math_symbolic_normalizer.SymbolicError)
# ---------------------------------------------------------------------------


class LogicError(ValueError):
    """Raised when a formula cannot be canonicalized. Refusal-first; never
    coerces a malformed or out-of-regime input into a guess."""


class LogicBudgetError(LogicError):
    """Raised when the ROBDD would exceed the node budget (the exponential-blowup
    guard). A subclass of :class:`LogicError` so callers that refuse on
    ``LogicError`` refuse on budget-exceeded too — the proof-domain analog of the
    math gate refusing rather than churning."""


class LogicRegimeError(LogicError):
    """Raised when the input is outside the decidable **propositional** regime —
    quantified or predicate logic (ADR-0201.1; the typed refusal ADR-0202 §3
    names). A subclass of :class:`LogicError` so callers that refuse on
    ``LogicError`` refuse here too, but it carries the typed
    :data:`OUT_OF_DECIDABLE_REGIME` reason so the regime boundary is
    distinguishable from a generic malformed-formula grammar error.

    Crucially, the boundary is enforced **by design** (see
    :func:`_reject_out_of_regime_text` / :func:`_reject_out_of_regime_tokens`),
    not by the tokenizer incidentally choking on an out-of-grammar character —
    the latter is the by-luck-not-by-design refusal the ``wrong == 0``
    discipline rejects."""


# ---------------------------------------------------------------------------
# Public defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_NODES: Final[int] = 100_000
"""Default cap on reduced-diagram nodes. Bounded proof-step propositions relate a
handful of atoms; this is generous for that regime and refuses on adversarial
blowup rather than hanging."""

# Terminal node ids. 0 = constant false, 1 = constant true. Non-terminal ids >= 2.
_FALSE: Final[int] = 0
_TRUE: Final[int] = 1


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Multi-character / unicode operator spellings, longest first so the scanner is
# unambiguous. Each maps to a canonical token kind.
_OPERATOR_SPELLINGS: Final[tuple[tuple[str, str], ...]] = (
    ("<->", "IFF"),
    ("↔", "IFF"),
    ("≡", "IFF"),
    ("->", "IMPLIES"),
    ("→", "IMPLIES"),
    ("⊃", "IMPLIES"),
    ("∧", "AND"),
    ("&&", "AND"),
    ("&", "AND"),
    ("∨", "OR"),
    ("||", "OR"),
    ("|", "OR"),
    ("¬", "NOT"),
    ("~", "NOT"),
    ("!", "NOT"),
    ("(", "LPAREN"),
    (")", "RPAREN"),
)

# Keyword operators / constants (matched on word boundaries, case-insensitive).
_KEYWORDS: Final[dict[str, str]] = {
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "implies": "IMPLIES",
    "iff": "IFF",
    "true": "TRUE",
    "false": "FALSE",
}


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Scan ``text`` into ``(kind, lexeme)`` tokens. Raises :class:`LogicError`
    on any character that is not part of the propositional grammar."""
    tokens: list[tuple[str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch.isspace():
            pos += 1
            continue
        # Symbolic operators (longest spelling first).
        matched = False
        for spelling, kind in _OPERATOR_SPELLINGS:
            if text.startswith(spelling, pos):
                tokens.append((kind, spelling))
                pos += len(spelling)
                matched = True
                break
        if matched:
            continue
        # Identifiers / keywords.
        if _is_ident_start(ch):
            start = pos
            pos += 1
            while pos < n and _is_ident_char(text[pos]):
                pos += 1
            word = text[start:pos]
            kind = _KEYWORDS.get(word.lower())
            if kind is not None:
                tokens.append((kind, word))
            else:
                tokens.append(("ATOM", word))
            continue
        raise LogicError(f"unexpected character {ch!r} at position {pos}")
    return tokens


# ---------------------------------------------------------------------------
# Parser  (recursive descent — twin of math_symbolic_normalizer._Parser)
#
# Precedence, lowest to highest:  IFF < IMPLIES < OR < AND < NOT < atom/paren.
# IMPLIES is right-associative; the rest left-associative (associativity is
# semantically irrelevant under ROBDD but a fixed parse keeps errors crisp).
#
# The AST is a nested tuple, e.g. ('and', ('atom','P'), ('not',('atom','Q'))).
# ---------------------------------------------------------------------------

_Ast = tuple


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> tuple[str, str] | None:
        return None if self._pos >= len(self._tokens) else self._tokens[self._pos]

    def _consume(self) -> tuple[str, str]:
        if self._pos >= len(self._tokens):
            raise LogicError("unexpected end of formula")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> _Ast:
        if not self._tokens:
            raise LogicError("empty formula")
        ast = self._iff()
        if self._pos != len(self._tokens):
            raise LogicError(f"unexpected trailing token {self._tokens[self._pos]!r}")
        return ast

    def _iff(self) -> _Ast:
        node = self._implies()
        while (tok := self._peek()) is not None and tok[0] == "IFF":
            self._consume()
            node = ("iff", node, self._implies())
        return node

    def _implies(self) -> _Ast:
        node = self._or()
        if (tok := self._peek()) is not None and tok[0] == "IMPLIES":
            self._consume()
            # right-associative: recurse into _implies for the RHS
            node = ("implies", node, self._implies())
        return node

    def _or(self) -> _Ast:
        node = self._and()
        while (tok := self._peek()) is not None and tok[0] == "OR":
            self._consume()
            node = ("or", node, self._and())
        return node

    def _and(self) -> _Ast:
        node = self._not()
        while (tok := self._peek()) is not None and tok[0] == "AND":
            self._consume()
            node = ("and", node, self._not())
        return node

    def _not(self) -> _Ast:
        tok = self._peek()
        if tok is not None and tok[0] == "NOT":
            self._consume()
            return ("not", self._not())
        return self._atom()

    def _atom(self) -> _Ast:
        tok = self._consume()
        kind, lexeme = tok
        if kind == "ATOM":
            return ("atom", lexeme)
        if kind == "TRUE":
            return ("const", True)
        if kind == "FALSE":
            return ("const", False)
        if kind == "LPAREN":
            inner = self._iff()
            close = self._consume()
            if close[0] != "RPAREN":
                raise LogicError(f"expected ')'; got {close[1]!r}")
            return inner
        raise LogicError(f"unexpected token {lexeme!r}")


def _collect_atoms(ast: _Ast) -> set[str]:
    kind = ast[0]
    if kind == "atom":
        return {ast[1]}
    if kind == "const":
        return set()
    if kind == "not":
        return _collect_atoms(ast[1])
    # binary
    return _collect_atoms(ast[1]) | _collect_atoms(ast[2])


# ---------------------------------------------------------------------------
# ROBDD manager (hand-rolled, minimal: mk + apply + negate + unique table)
# ---------------------------------------------------------------------------


class _Bdd:
    """A single-formula ROBDD builder. Variables are addressed by index into a
    fixed (sorted) ordering; ``var_count`` is the terminal sentinel level."""

    __slots__ = ("var_count", "max_nodes", "_nodes", "_unique", "_and_c", "_or_c", "_neg_c")

    def __init__(self, var_count: int, max_nodes: int) -> None:
        self.var_count = var_count
        self.max_nodes = max_nodes
        # node id -> (var_index, low_id, high_id); ids 0/1 are terminals (absent here).
        self._nodes: list[tuple[int, int, int]] = []
        self._unique: dict[tuple[int, int, int], int] = {}
        self._and_c: dict[tuple[int, int], int] = {}
        self._or_c: dict[tuple[int, int], int] = {}
        self._neg_c: dict[int, int] = {}

    def _var(self, node: int) -> int:
        # Terminals sit "below" every variable: use var_count as +inf sentinel.
        if node <= _TRUE:
            return self.var_count
        return self._nodes[node - 2][0]

    def _low(self, node: int) -> int:
        return self._nodes[node - 2][1]

    def _high(self, node: int) -> int:
        return self._nodes[node - 2][2]

    def mk(self, var: int, low: int, high: int) -> int:
        """Make-or-reuse a node, applying the two reduction rules. This is the
        only node-creation site, so the budget is enforced here."""
        if low == high:
            return low  # redundant-node rule
        key = (var, low, high)
        existing = self._unique.get(key)
        if existing is not None:
            return existing  # shared-subgraph rule (hash-cons)
        if len(self._nodes) >= self.max_nodes:
            raise LogicBudgetError(
                f"ROBDD exceeded node budget ({self.max_nodes}); refusing rather "
                f"than churn"
            )
        node_id = len(self._nodes) + 2
        self._nodes.append(key)
        self._unique[key] = node_id
        return node_id

    def var_node(self, var: int) -> int:
        """The diagram for a bare variable: if var then true else false."""
        return self.mk(var, _FALSE, _TRUE)

    def negate(self, f: int) -> int:
        if f == _FALSE:
            return _TRUE
        if f == _TRUE:
            return _FALSE
        cached = self._neg_c.get(f)
        if cached is not None:
            return cached
        result = self.mk(self._var(f), self.negate(self._low(f)), self.negate(self._high(f)))
        self._neg_c[f] = result
        return result

    def conj(self, f: int, g: int) -> int:
        if f == _FALSE or g == _FALSE:
            return _FALSE
        if f == _TRUE:
            return g
        if g == _TRUE:
            return f
        if f == g:
            return f
        key = (f, g) if f <= g else (g, f)  # commutative -> canonical cache key
        cached = self._and_c.get(key)
        if cached is not None:
            return cached
        result = self._apply(self.conj, f, g)
        self._and_c[key] = result
        return result

    def disj(self, f: int, g: int) -> int:
        if f == _TRUE or g == _TRUE:
            return _TRUE
        if f == _FALSE:
            return g
        if g == _FALSE:
            return f
        if f == g:
            return f
        key = (f, g) if f <= g else (g, f)
        cached = self._or_c.get(key)
        if cached is not None:
            return cached
        result = self._apply(self.disj, f, g)
        self._or_c[key] = result
        return result

    def _apply(self, op, f: int, g: int) -> int:
        """Shannon expansion on the top variable of ``f``/``g`` (Bryant apply)."""
        v = min(self._var(f), self._var(g))
        f0, f1 = self._cofactor(f, v)
        g0, g1 = self._cofactor(g, v)
        return self.mk(v, op(f0, g0), op(f1, g1))

    def _cofactor(self, f: int, v: int) -> tuple[int, int]:
        if self._var(f) == v:
            return self._low(f), self._high(f)
        return f, f  # v does not occur at the top of f

    def compile(self, ast: _Ast, index_of: dict[str, int]) -> int:
        kind = ast[0]
        if kind == "atom":
            return self.var_node(index_of[ast[1]])
        if kind == "const":
            return _TRUE if ast[1] else _FALSE
        if kind == "not":
            return self.negate(self.compile(ast[1], index_of))
        left = self.compile(ast[1], index_of)
        right = self.compile(ast[2], index_of)
        if kind == "and":
            return self.conj(left, right)
        if kind == "or":
            return self.disj(left, right)
        if kind == "implies":
            return self.disj(self.negate(left), right)
        if kind == "iff":
            # (a -> b) ∧ (b -> a)
            return self.conj(self.disj(self.negate(left), right),
                             self.disj(self.negate(right), left))
        raise LogicError(f"unknown AST node {kind!r}")  # pragma: no cover

    def serialize(self, root: int, names: tuple[str, ...]) -> str:
        """Canonical, construction-order-independent serialization of the reduced
        diagram reachable from ``root``. Post-order DFS (low subtree fully before
        high subtree) assigns canonical indices; nodes reference variable *names*
        so diagrams over different atoms never collide, while terminals collapse
        (every tautology -> 'T', every contradiction -> 'F'). Because the diagram
        is reduced and the ordering fixed, isomorphic diagrams emit identical
        strings."""
        if root == _TRUE:
            return "T"
        if root == _FALSE:
            return "F"
        order: dict[int, int] = {}
        lines: list[str] = []

        def ref(node: int) -> str:
            if node == _TRUE:
                return "T"
            if node == _FALSE:
                return "F"
            return f"@{order[node]}"

        def visit(node: int) -> None:
            if node in order or node <= _TRUE:
                return
            visit(self._low(node))
            visit(self._high(node))
            idx = len(order)
            order[node] = idx
            lines.append(
                f"{idx}:{names[self._var(node)]}?{ref(self._high(node))}:{ref(self._low(node))}"
            )

        visit(root)
        return ";".join(lines)

    def support(self, root: int) -> set[int]:
        """The set of variable indices that occur in the reduced diagram —
        i.e. the atoms that survive reduction (irrelevant ones are absent)."""
        seen: set[int] = set()
        out: set[int] = set()

        def visit(node: int) -> None:
            if node <= _TRUE or node in seen:
                return
            seen.add(node)
            out.add(self._var(node))
            visit(self._low(node))
            visit(self._high(node))

        visit(root)
        return out


# ---------------------------------------------------------------------------
# Public API  (twin of math_symbolic_equivalence)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CanonicalProposition:
    """The canonical form of a propositional formula.

    ``canonical_key`` is the byte-equality discriminator — two formulas are
    logically equivalent iff their keys are equal. ``atoms`` are the variables
    that *survive* reduction (logically-irrelevant ones are dropped), so it can be
    a strict subset of the atoms written in the input."""

    canonical_key: str
    atoms: tuple[str, ...]
    is_tautology: bool
    is_contradiction: bool


# ---------------------------------------------------------------------------
# Out-of-regime detection (ADR-0201.1)
#
# Propositional logic is the only regime with a canonical form + decidable
# equivalence. Quantified / predicate input must REFUSE with the typed
# `out_of_decidable_regime` reason (ADR-0202 §3) — by DESIGN, recognized as
# out-of-regime, not by accident of the tokenizer choking on an out-of-grammar
# character. These checks run BEFORE the generic grammar error so the regime
# boundary is principled, typed, and inspectable.
# ---------------------------------------------------------------------------

OUT_OF_DECIDABLE_REGIME: Final[str] = "out_of_decidable_regime"

# Quantifier markers: ASCII keywords (word-boundary, case-insensitive) and the
# logic symbols ∀ / ∃. Their presence means first-order/predicate reasoning,
# which has no ROBDD canonical form and is undecidable in general. `forall` and
# `exists` are therefore reserved — not usable as atom ids.
_QUANTIFIER_WORD_RE: Final[re.Pattern[str]] = re.compile(r"\b(forall|exists)\b", re.IGNORECASE)
_QUANTIFIER_SYMBOLS: Final[frozenset[str]] = frozenset({"∀", "∃"})  # ∀ ∃


def _reject_out_of_regime_text(formula: str) -> None:
    """Refuse raw input that carries a quantifier marker. Runs before tokenizing
    so quantifier symbols (∀/∃) and the ``forall x. …`` / ``exists x. …`` shape
    refuse with the typed regime reason rather than a generic 'unexpected
    character' grammar error from the trailing ``.``/predicate syntax."""
    for sym in sorted(_QUANTIFIER_SYMBOLS):
        if sym in formula:
            raise LogicRegimeError(f"{OUT_OF_DECIDABLE_REGIME}: quantifier symbol {sym!r}")
    match = _QUANTIFIER_WORD_RE.search(formula)
    if match is not None:
        raise LogicRegimeError(f"{OUT_OF_DECIDABLE_REGIME}: quantifier {match.group(0)!r}")


def _reject_out_of_regime_tokens(tokens: list[tuple[str, str]]) -> None:
    """Refuse predicate-application shape — an atom immediately applied to an
    argument list, e.g. ``rains(x)``. In the propositional grammar an atom is
    never followed by ``(`` (grouping only follows an operator or opens an
    expression), so ``ATOM (`` is a predicate, not a well-formed propositional
    formula. Runs before the parser's generic trailing-token error so the regime
    boundary is the reason that surfaces. (Keyword operators such as ``not`` are
    NOT ``ATOM`` tokens, so ``not (P)`` is unaffected.)"""
    for (kind, lexeme), (next_kind, _next_lexeme) in zip(tokens, tokens[1:]):
        if kind == "ATOM" and next_kind == "LPAREN":
            raise LogicRegimeError(
                f"{OUT_OF_DECIDABLE_REGIME}: predicate application {lexeme!r}(…)"
            )


def canonicalize(formula: str, *, max_nodes: int = DEFAULT_MAX_NODES) -> CanonicalProposition:
    """Canonicalize ``formula`` to its ROBDD identity under the sorted-atom
    ordering. Refusal-first:

    * :class:`LogicRegimeError` (``out_of_decidable_regime``) if the input is
      quantified / predicate logic — checked *before* grammar, so the regime
      boundary is principled, not an incidental tokenizer failure;
    * :class:`LogicError` on out-of-grammar (malformed propositional) input;
    * :class:`LogicBudgetError` if the diagram exceeds ``max_nodes``.
    """
    _reject_out_of_regime_text(formula)
    tokens = _tokenize(formula)
    _reject_out_of_regime_tokens(tokens)
    ast = _Parser(tokens).parse()
    declared = tuple(sorted(_collect_atoms(ast)))  # fixed variable ordering
    index_of = {name: i for i, name in enumerate(declared)}
    bdd = _Bdd(var_count=len(declared), max_nodes=max_nodes)
    root = bdd.compile(ast, index_of)
    key = bdd.serialize(root, declared)
    # Atoms that actually occur in the reduced diagram (irrelevant ones dropped).
    support_idx = bdd.support(root)
    surviving = tuple(name for i, name in enumerate(declared) if i in support_idx)
    return CanonicalProposition(
        canonical_key=key,
        atoms=surviving,
        is_tautology=(root == _TRUE),
        is_contradiction=(root == _FALSE),
    )
