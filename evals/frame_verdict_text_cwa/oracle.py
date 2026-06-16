"""Independent text-CWA oracle — a truth-table propositional checker.

Authored DISJOINT from ``generate.frame_verdict`` (INV-25 / INV-27): it imports NO engine
module, does NOT call ``evaluate_frame_verdict`` / ``determine`` / ``response_governance``,
and decides entailment by its OWN recursive-descent parser + brute-force truth-table
enumeration — NOT the production ROBDD. If the ROBDD evaluator and this truth-table oracle
ever disagree, the lane fails (so the lane's gold is a real independent check, not the
engine's echo).

Scope note (honest): the FRAME GATING (OPEN / undeclared closure / non-TEXT => SCOPE_BOUNDARY)
is the frame CONTRACT, shared by both; independence is in the SOLVING (entailment), which is
the wrong=0-critical part. The grammar is the closed propositional grammar of
``proof_chain.entail`` (atoms, ``~``, ``&``, ``->``, parens); ``~`` > ``&`` > ``->`` (``->``
right-assoc). Anything outside it is reported ``SCOPE_BOUNDARY`` (out of regime), matching the
evaluator's refusal-first posture.
"""

from __future__ import annotations

import itertools
import re

_TOKEN = re.compile(r"\s*(->|[&~()]|[A-Za-z_][A-Za-z0-9_]*)")


class _Bad(Exception):
    """Malformed / out-of-regime formula."""


def _tokens(s: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i].isspace():
            i += 1
            continue
        m = _TOKEN.match(s, i)
        if not m:
            raise _Bad(f"bad token at {s[i:]!r}")
        out.append(m.group(1))
        i = m.end()
    return out


def _parse(formula: str):
    toks = _tokens(formula)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def eat(t=None):
        nonlocal pos
        cur = peek()
        if cur is None or (t is not None and cur != t):
            raise _Bad(f"expected {t!r}, got {cur!r}")
        pos += 1
        return cur

    def imp():  # lowest precedence, right-assoc
        left = conj()
        if peek() == "->":
            eat("->")
            return ("imp", left, imp())
        return left

    def conj():
        left = neg()
        while peek() == "&":
            eat("&")
            left = ("and", left, neg())
        return left

    def neg():
        if peek() == "~":
            eat("~")
            return ("not", neg())
        return atom()

    def atom():
        cur = peek()
        if cur == "(":
            eat("(")
            inner = imp()
            eat(")")
            return inner
        if cur is None or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cur):
            raise _Bad(f"expected atom, got {cur!r}")
        eat()
        return ("var", cur)

    tree = imp()
    if pos != len(toks):
        raise _Bad("trailing tokens")
    return tree


def _vars(tree, acc: set[str]) -> None:
    tag = tree[0]
    if tag == "var":
        acc.add(tree[1])
    elif tag == "not":
        _vars(tree[1], acc)
    else:
        _vars(tree[1], acc)
        _vars(tree[2], acc)


def _eval(tree, env: dict[str, bool]) -> bool:
    tag = tree[0]
    if tag == "var":
        return env[tree[1]]
    if tag == "not":
        return not _eval(tree[1], env)
    if tag == "and":
        return _eval(tree[1], env) and _eval(tree[2], env)
    if tag == "imp":
        return (not _eval(tree[1], env)) or _eval(tree[2], env)
    raise _Bad(f"unknown node {tag}")


def cwa_verdict(premises: list[str], query: str) -> str:
    """The independent closed-world verdict over the propositional ``premises`` + ``query``:
    ``ENTAILED_TRUE`` | ``ENTAILED_FALSE`` | ``UNDETERMINED`` | ``CONTRADICTION`` |
    ``SCOPE_BOUNDARY`` (malformed / out of regime). Truth-table enumeration, ROBDD-disjoint."""
    try:
        trees = [_parse(p) for p in premises]
        q = _parse(query)
    except _Bad:
        return "SCOPE_BOUNDARY"

    names: set[str] = set()
    for t in trees:
        _vars(t, names)
    _vars(q, names)
    names_sorted = sorted(names)

    models = []
    for bits in itertools.product([False, True], repeat=len(names_sorted)):
        env = dict(zip(names_sorted, bits))
        if all(_eval(t, env) for t in trees):
            models.append(env)

    if not models:
        return "CONTRADICTION"  # premises unsatisfiable — decline, never assert
    q_vals = {_eval(q, env) for env in models}
    if q_vals == {True}:
        return "ENTAILED_TRUE"
    if q_vals == {False}:
        return "ENTAILED_FALSE"
    return "UNDETERMINED"


def oracle_frame_verdict(
    propositions, query: str, *, frame_kind: str, world_assumption: str, closure_declared: bool
) -> str:
    """The full independent verdict for a case: the shared frame-gating CONTRACT (OPEN /
    undeclared / non-TEXT => SCOPE_BOUNDARY) composed with the DISJOINT truth-table solver.
    Independence is in the solving (``cwa_verdict``), not the gating contract."""
    if frame_kind != "text" or world_assumption == "open" or not closure_declared:
        return "SCOPE_BOUNDARY"
    return cwa_verdict(list(propositions), query)
