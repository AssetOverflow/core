"""Independent OWA label oracle for the ProofWriter-OWA refusal-floor lane (B1).

This computes the open-world-assumption gold label (`True` / `Unknown` / `False`) for
each fixture item, DISJOINTLY from the engine: it does NOT import `determine`,
`comprehend`/MeaningGraph realization, or any production predicate-entailment helper
(INV-25 / INV-27). It has its own tiny parser for the closed B1 fixture grammar and its
own minimal relational algebra. The fixture's hand-authored `expected` field is pinned
equal to this oracle's output by the lane test, so the oracle is itself verified.

Grammar (closed — anything else raises):
    facts:  "<X> is a[n] <Y>."                 -> member(x, y)
            "All <Xs> are <Ys>."               -> subset(x, y)        (regular plurals)
            "No <X> is a[n] <Y>."              -> disjoint(x, y)
            "<A> is [the] <connective> <B>."   -> rel(lemma, a, b)
    query:  "Is <X> a[n] <Y>?"                  -> member?(x, y)
            "Are all <Xs> <Ys>?"               -> subset?(x, y)
            "Is <A> [the] <connective> <B>?"   -> rel?(lemma, a, b)

OWA semantics:
    member?(x, y): True if y is in the is-a closure of x's classes; False if some class
        in that closure is declared disjoint from y; else Unknown.
    subset?(x, y): True if y is in x's superclass closure; False if some class in that
        closure is disjoint from y; else Unknown.
    rel?(lemma, a, b): True on a direct edge, a declared INVERSE edge (b,a), or a declared
        SYMMETRIC edge (b,a) — ONE hop only. Else Unknown. (No transitive relational
        chains in B1; no relational negation in this grammar.)
"""

from __future__ import annotations

import re

# The oracle's OWN relational ontology — declared here, NOT imported from
# generate.meaning_graph.relational, so the gold producer stays disjoint from the
# solver. (It mirrors the pack's algebra for the predicates this fixture uses.)
_INVERSE: dict[str, str] = {
    "less_than": "greater_than", "greater_than": "less_than",
    "parent_of": "child_of", "child_of": "parent_of",
    "left_of": "right_of", "right_of": "left_of",
    "before_event": "after_event", "after_event": "before_event",
}
_SYMMETRIC: frozenset[str] = frozenset({
    "sibling_of", "spouse_of", "equal_to", "distinct_from", "adjacent_to",
})
_CONNECTIVE: dict[str, str] = {
    "parent of": "parent_of", "child of": "child_of", "sibling of": "sibling_of",
    "spouse of": "spouse_of", "less than": "less_than", "greater than": "greater_than",
    "equal to": "equal_to", "distinct from": "distinct_from",
    "left of": "left_of", "right of": "right_of", "inside of": "inside_of",
    "adjacent to": "adjacent_to",
}
# longest connective first so "parent of" wins before any single-token prefix
_CONN_ALT = "|".join(re.escape(k) for k in sorted(_CONNECTIVE, key=len, reverse=True))

_MEMBER = re.compile(r"^(\w+) is an? (\w+)\.$")
_SUBSET = re.compile(r"^All (\w+) are (\w+)\.$")
_DISJOINT = re.compile(r"^No (\w+) is an? (\w+)\.$")
_REL = re.compile(rf"^(\w+) is (?:the )?({_CONN_ALT}) (\w+)\.$")

_Q_MEMBER = re.compile(r"^Is (\w+) an? (\w+)\?$")
_Q_SUBSET = re.compile(r"^Are all (\w+) (\w+)\?$")
_Q_REL = re.compile(rf"^Is (\w+) (?:the )?({_CONN_ALT}) (\w+)\?$")


class OracleParseError(ValueError):
    """A fixture string is outside the closed B1 grammar — fail loudly, never guess."""


def _sing(word: str) -> str:
    """Singularize a regular plural class noun ('dogs' -> 'dog'). Used ONLY in the
    explicitly-plural slots of the subset patterns, so 'species'/'Socrates' (which only
    appear in singular `is a` slots) are never mangled."""
    w = word.lower()
    return w[:-1] if w.endswith("s") and not w.endswith("ss") else w


def parse_fact(text: str) -> tuple:
    t = text.strip()
    if (m := _DISJOINT.match(t)):
        return ("disjoint", m.group(1).lower(), m.group(2).lower())
    if (m := _SUBSET.match(t)):
        return ("subset", _sing(m.group(1)), _sing(m.group(2)))
    if (m := _REL.match(t)):
        return ("rel", _CONNECTIVE[m.group(2)], m.group(1).lower(), m.group(3).lower())
    if (m := _MEMBER.match(t)):
        return ("member", m.group(1).lower(), m.group(2).lower())
    raise OracleParseError(f"unparseable fact: {text!r}")


def parse_query(text: str) -> tuple:
    t = text.strip()
    if (m := _Q_REL.match(t)):
        return ("rel?", _CONNECTIVE[m.group(2)], m.group(1).lower(), m.group(3).lower())
    if (m := _Q_SUBSET.match(t)):
        return ("subset?", _sing(m.group(1)), _sing(m.group(2)))
    if (m := _Q_MEMBER.match(t)):
        return ("member?", m.group(1).lower(), m.group(2).lower())
    raise OracleParseError(f"unparseable query: {text!r}")


def _closure(start: str, supers: dict[str, set[str]]) -> set[str]:
    """`start` plus every superclass reachable over subset edges (BFS, deterministic)."""
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for sup in sorted(supers.get(node, ())):
            if sup not in seen:
                seen.add(sup)
                stack.append(sup)
    return seen


def label(facts: list[str], query: str) -> str:
    """The OWA gold label for `query` given `facts`: 'True' | 'Unknown' | 'False'."""
    members: dict[str, set[str]] = {}
    supers: dict[str, set[str]] = {}
    disjoint: set[frozenset[str]] = set()
    rels: set[tuple[str, str, str]] = set()
    for text in facts:
        f = parse_fact(text)
        if f[0] == "member":
            members.setdefault(f[1], set()).add(f[2])
        elif f[0] == "subset":
            supers.setdefault(f[1], set()).add(f[2])
        elif f[0] == "disjoint":
            disjoint.add(frozenset((f[1], f[2])))
        else:  # rel
            rels.add((f[1], f[2], f[3]))

    q = parse_query(query)
    if q[0] == "member?":
        _, subj, cls = q
        reach: set[str] = set()
        for c0 in members.get(subj, ()):
            reach |= _closure(c0, supers)
        if cls in reach:
            return "True"
        if any(frozenset((d, cls)) in disjoint for d in reach):
            return "False"
        return "Unknown"
    if q[0] == "subset?":
        _, x, y = q
        clo = _closure(x, supers)
        if y in clo:
            return "True"
        if any(frozenset((d, y)) in disjoint for d in clo):
            return "False"
        return "Unknown"
    # rel?
    _, lemma, a, b = q
    if (lemma, a, b) in rels:
        return "True"
    inv = _INVERSE.get(lemma)
    if inv is not None and (inv, b, a) in rels:
        return "True"
    if lemma in _SYMMETRIC and (lemma, b, a) in rels:
        return "True"
    return "Unknown"
