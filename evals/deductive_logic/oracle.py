"""Independent entailment oracle — the gold for the deductive-logic lane.

This is **deliberately a second, independent decision procedure**: a self-contained
recursive-descent parser plus brute-force truth-table model enumeration. It shares
**no code** with :mod:`generate.logic_canonical` (the ROBDD) or
:mod:`generate.proof_chain.entail` (the engine under test). Two independent sound
procedures agreeing on held-out random problems is real evidence the engine is
correct; a shared-code "oracle" would only prove the engine agrees with itself.

It is intentionally simple and slow (O(2^atoms)) — correctness by obviousness, not
performance. The lane keeps atom counts small so enumeration stays cheap.

Grammar / precedence match the ROBDD's so the same formula string means the same
thing in both procedures (the comparison is about the *decision*, not parsing):
    iff  <  implies  <  or  <  and  <  not        (implies right-associative)
"""

from __future__ import annotations

from itertools import product
from typing import Final

# --- independent tokenizer -------------------------------------------------

_OPS: Final[tuple[tuple[str, str], ...]] = (
    ("<->", "IFF"), ("↔", "IFF"), ("≡", "IFF"),
    ("->", "IMP"), ("→", "IMP"), ("⊃", "IMP"),
    ("∧", "AND"), ("&&", "AND"), ("&", "AND"),
    ("∨", "OR"), ("||", "OR"), ("|", "OR"),
    ("¬", "NOT"), ("~", "NOT"), ("!", "NOT"),
    ("(", "LP"), (")", "RP"),
)
_KW: Final[dict[str, str]] = {
    "and": "AND", "or": "OR", "not": "NOT", "implies": "IMP",
    "iff": "IFF", "true": "TRUE", "false": "FALSE",
}


class OracleError(ValueError):
    """Malformed formula — the oracle refuses to guess, same posture as the engine."""


def _tokenize(text: str) -> list[tuple[str, str]]:
    toks: list[tuple[str, str]] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        hit = False
        for spell, kind in _OPS:
            if text.startswith(spell, i):
                toks.append((kind, spell))
                i += len(spell)
                hit = True
                break
        if hit:
            continue
        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            toks.append((_KW.get(word.lower(), "ATOM"), word))
            i = j
            continue
        raise OracleError(f"unexpected character {c!r}")
    return toks


# --- independent recursive-descent parser ----------------------------------


class _P:
    def __init__(self, toks: list[tuple[str, str]]) -> None:
        self.toks = toks
        self.i = 0

    def _peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _eat(self) -> tuple[str, str]:
        if self.i >= len(self.toks):
            raise OracleError("unexpected end of formula")
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse(self) -> tuple:
        if not self.toks:
            raise OracleError("empty formula")
        ast = self._iff()
        if self.i != len(self.toks):
            raise OracleError("trailing tokens")
        return ast

    def _iff(self) -> tuple:
        node = self._imp()
        while (t := self._peek()) and t[0] == "IFF":
            self._eat()
            node = ("iff", node, self._imp())
        return node

    def _imp(self) -> tuple:
        node = self._or()
        if (t := self._peek()) and t[0] == "IMP":
            self._eat()
            node = ("imp", node, self._imp())  # right-assoc
        return node

    def _or(self) -> tuple:
        node = self._and()
        while (t := self._peek()) and t[0] == "OR":
            self._eat()
            node = ("or", node, self._and())
        return node

    def _and(self) -> tuple:
        node = self._not()
        while (t := self._peek()) and t[0] == "AND":
            self._eat()
            node = ("and", node, self._not())
        return node

    def _not(self) -> tuple:
        if (t := self._peek()) and t[0] == "NOT":
            self._eat()
            return ("not", self._not())
        return self._atom()

    def _atom(self) -> tuple:
        kind, lex = self._eat()
        if kind == "ATOM":
            return ("atom", lex)
        if kind == "TRUE":
            return ("const", True)
        if kind == "FALSE":
            return ("const", False)
        if kind == "LP":
            inner = self._iff()
            if self._eat()[0] != "RP":
                raise OracleError("expected ')'")
            return inner
        raise OracleError(f"unexpected token {lex!r}")


def _atoms(ast: tuple) -> set[str]:
    k = ast[0]
    if k == "atom":
        return {ast[1]}
    if k == "const":
        return set()
    if k == "not":
        return _atoms(ast[1])
    return _atoms(ast[1]) | _atoms(ast[2])


def _eval(ast: tuple, env: dict[str, bool]) -> bool:
    k = ast[0]
    if k == "atom":
        return env[ast[1]]
    if k == "const":
        return ast[1]
    if k == "not":
        return not _eval(ast[1], env)
    a = _eval(ast[1], env)
    b = _eval(ast[2], env)
    if k == "and":
        return a and b
    if k == "or":
        return a or b
    if k == "imp":
        return (not a) or b
    if k == "iff":
        return a == b
    raise OracleError(f"unknown node {k!r}")  # pragma: no cover


def _parse(formula: str) -> tuple:
    return _P(_tokenize(formula)).parse()


# --- the oracle verdict ----------------------------------------------------

# Verdict strings match generate.proof_chain.entail.Entailment values exactly so the
# runner can compare engine.outcome.value to the oracle verdict directly.
ENTAILED: Final[str] = "entailed"
REFUTED: Final[str] = "refuted"
UNKNOWN: Final[str] = "unknown"
REFUSED: Final[str] = "refused"


def oracle_entailment(premises: tuple[str, ...], query: str) -> str:
    """Brute-force entailment verdict over all truth assignments.

    Enumerates every assignment of the atoms appearing anywhere in premises+query;
    a *model* is an assignment satisfying every premise. Returns:
    ``entailed`` if query holds in all models, ``refuted`` if in none,
    ``unknown`` if in some-but-not-all, ``refused`` if there are no models
    (inconsistent premises) or anything fails to parse."""
    try:
        prem_asts = [_parse(p) for p in premises]
        q_ast = _parse(query)
    except OracleError:
        return REFUSED

    atoms = set(_atoms(q_ast))
    for a in prem_asts:
        atoms |= _atoms(a)
    ordered = sorted(atoms)

    models = 0
    q_true = 0
    for combo in product((False, True), repeat=len(ordered)):
        env = dict(zip(ordered, combo))
        if all(_eval(a, env) for a in prem_asts):
            models += 1
            if _eval(q_ast, env):
                q_true += 1

    if models == 0:
        return REFUSED  # inconsistent premises
    if q_true == models:
        return ENTAILED
    if q_true == 0:
        return REFUTED
    return UNKNOWN
