"""Generative wrong=0 hardening for the comprehension organ (anti-overfit).

The end-to-end lane tests prove wrong=0 on the 8-case staged gold lanes. This file
proves the same invariant GENERALIZES: over hundreds of randomly generated
single-word problems, the reader is FAITHFUL — it either refuses, or it reproduces
the exact verdict the independent oracle gives on the ground-truth structure the
prose encodes. It NEVER changes the answer.

Why this is non-circular: the generated structure ``S`` is the ground truth. We
render prose ``P(S)`` with a trivial single-word renderer, then run the
comprehension path ``oracle(project(comprehend(P(S))))`` and compare it to
``oracle(S)`` computed directly. The oracle is independent of the reader; agreement
means the reader carried the meaning losslessly, refusal means it declined — both
are wrong=0. A reader that silently mis-read would commit a DIFFERENT verdict and
the test would bite.

Single-word vocab on purpose: multi-word NPs are a known gold-canonicalization wall
(the reader refuses them), so the generator stays in the readable single-word
regime where faithfulness is the whole claim.
"""

from __future__ import annotations

import random

from evals.set_membership.oracle import OracleError as SetError
from evals.set_membership.oracle import oracle_answer as set_oracle
from evals.syllogism.oracle import OracleError as SylError
from evals.syllogism.oracle import oracle_answer as syl_oracle
from evals.total_ordering.oracle import OracleError as OrdError
from evals.total_ordering.oracle import oracle_answer as ord_oracle
from generate.meaning_graph.projectors import (
    to_set_membership,
    to_syllogism,
    to_total_ordering,
)
from generate.meaning_graph.reader import Refusal, comprehend

_TERMS = [f"t{i}" for i in range(8)]  # single-word identifiers -> trivial plurals


def _committed(comp_or_refusal, projector, oracle, error):
    """Run the comprehension path; return the committed oracle answer or None
    (None == refused / unprojectable / oracle-refused — all wrong=0-safe)."""
    if isinstance(comp_or_refusal, Refusal):
        return None
    projected = projector(comp_or_refusal)
    if projected is None:
        return None
    try:
        return oracle(*projected)
    except error:
        return None


# --------------------------------------------------------------------------- #
# Syllogism — the richest grammar (A/E/I/O premises + therefore-conclusion)
# --------------------------------------------------------------------------- #

_FORM_PREMISE = {
    "A": lambda s, p: f"All {s}s are {p}s.",
    "E": lambda s, p: f"No {s}s are {p}s.",
    "I": lambda s, p: f"Some {s}s are {p}s.",
    "O": lambda s, p: f"Some {s}s are not {p}s.",
}
_FORM_CONCLUSION = {
    "A": lambda s, p: f"Therefore all {s}s are {p}s.",
    "E": lambda s, p: f"Therefore no {s}s are {p}s.",
    "I": lambda s, p: f"Therefore some {s}s are {p}s.",
    "O": lambda s, p: f"Therefore some {s}s are not {p}s.",
}


def test_syllogism_reader_is_faithful_or_refuses() -> None:
    rng = random.Random(20260605)
    checked = committed = 0
    for _ in range(400):
        a, b, c = rng.sample(_TERMS, 3)
        # Two premises + a conclusion over the three terms; random forms.
        (s1, p1), (s2, p2), (sc, pc) = (
            rng.sample([a, b, c], 2),
            rng.sample([a, b, c], 2),
            rng.sample([a, b, c], 2),
        )
        f1, f2, fc = (rng.choice("AEIO"), rng.choice("AEIO"), rng.choice("AEIO"))
        prose = " ".join(
            [_FORM_PREMISE[f1](s1, p1), _FORM_PREMISE[f2](s2, p2), _FORM_CONCLUSION[fc](sc, pc)]
        )
        structure = {
            "terms": sorted({a, b, c}),
            "domain_size": 3,
            "premises": [
                {"form": f1, "subject": s1, "predicate": p1},
                {"form": f2, "subject": s2, "predicate": p2},
            ],
        }
        query = {"kind": "validity", "conclusion": {"form": fc, "subject": sc, "predicate": pc}}
        try:
            expected = syl_oracle(structure, query)
        except SylError:
            expected = None  # inconsistent premises -> ground truth refuses
        got = _committed(comprehend(prose), to_syllogism, syl_oracle, SylError)
        checked += 1
        if got is not None:
            committed += 1
            assert got == expected, (prose, got, expected)
    assert committed > 50  # the generator actually exercises the committed path


# --------------------------------------------------------------------------- #
# Total ordering — random strict chains, sort + compare queries
# --------------------------------------------------------------------------- #


def test_total_ordering_reader_is_faithful_or_refuses() -> None:
    rng = random.Random(7)
    committed = 0
    for _ in range(300):
        n = rng.randint(2, 5)
        chain = rng.sample(_TERMS, n)  # chain[0] < chain[1] < ... (strict)
        rels = [{"less": chain[i], "greater": chain[i + 1]} for i in range(n - 1)]
        # Render the chain as comparative clauses joined into one sentence.
        clauses = [f"{lo} is below {hi}" for lo, hi in zip(chain, chain[1:])]
        facts = ", and ".join(clauses) + "."
        if rng.random() < 0.5:
            order = rng.choice(["ascending", "descending"])
            prose = f"{facts} Sort {order}."
            query = {"kind": "sort", "order": order}
        else:
            x, y = rng.sample(chain, 2)
            prose = f"{facts} Compare {x} with {y}."
            query = {"kind": "compare", "left": x, "right": y}
        structure = {"items": sorted(set(chain)), "relations": rels}
        try:
            expected = ord_oracle(structure, query)
        except OrdError:
            expected = None
        got = _committed(comprehend(prose), to_total_ordering, ord_oracle, OrdError)
        if got is not None:
            committed += 1
            assert got == expected, (prose, got, expected)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Set membership — random members + subset chains, member + subset queries
# --------------------------------------------------------------------------- #


def test_set_membership_reader_is_faithful_or_refuses() -> None:
    rng = random.Random(99)
    committed = 0
    for _ in range(300):
        classes = rng.sample(_TERMS, rng.randint(2, 4))
        individuals = [f"e{i}" for i in range(rng.randint(1, 3))]
        member_facts = [(ind, rng.choice(classes)) for ind in individuals]
        # a short subset chain over a prefix of the classes
        subset_facts = [
            (classes[i], classes[i + 1]) for i in range(len(classes) - 1) if rng.random() < 0.7
        ]
        member_lines = [f"{ind} is a {cls}." for ind, cls in member_facts]
        subset_lines = [f"All {a}s are {b}s." for a, b in subset_facts]
        sets = [
            {"id": c, "members": sorted({i for i, cl in member_facts if cl == c})} for c in classes
        ]
        structure = {
            "elements": sorted(individuals),
            "sets": sets,
            "subsets": [{"subset": a, "superset": b} for a, b in subset_facts],
        }
        if rng.random() < 0.5 and individuals:
            ind = rng.choice(individuals)
            target = rng.choice(classes)
            prose = " ".join(member_lines + subset_lines + [f"Is {ind} a {target}?"])
            query = {"kind": "member", "element": ind, "set": target}
        else:
            a, b = rng.sample(classes, 2)
            prose = " ".join(member_lines + subset_lines + [f"Are all {a}s {b}s?"])
            query = {"kind": "subset", "subset": a, "superset": b}
        try:
            expected = set_oracle(structure, query)
        except SetError:
            expected = None
        got = _committed(comprehend(prose), to_set_membership, set_oracle, SetError)
        if got is not None:
            committed += 1
            assert got == expected, (prose, got, expected)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Multi-word NP chunking — faithful under the canonicalization contract
# --------------------------------------------------------------------------- #


def _class_term(rng):
    """Return (canonical_id, plural_surface) for a class NP, sometimes multi-word.

    "t1" -> ("t1", "t1s");  "t1 t2" -> ("t1_t2", "t1 t2s")  (head pluralized).
    """
    w1 = rng.choice(_TERMS)
    if rng.random() < 0.5:
        head = rng.choice([t for t in _TERMS if t != w1])
        return f"{w1}_{head}", f"{w1} {head}s"
    return w1, f"{w1}s"


def _item_term(rng, pool):
    """Return (canonical_id, surface) for an item NP, sometimes multi-word (no
    pluralization for items): "t1" or "t1 t2" -> "t1_t2"."""
    w1 = pool.pop()
    if rng.random() < 0.5 and pool:
        w2 = pool.pop()
        return f"{w1}_{w2}", f"{w1} {w2}"
    return w1, w1


_MW_PREMISE = {
    "A": lambda s, p: f"All {s} are {p}.",
    "E": lambda s, p: f"No {s} are {p}.",
    "I": lambda s, p: f"Some {s} are {p}.",
    "O": lambda s, p: f"Some {s} are not {p}.",
}
_MW_CONCLUSION = {
    "A": lambda s, p: f"Therefore all {s} are {p}.",
    "E": lambda s, p: f"Therefore no {s} are {p}.",
    "I": lambda s, p: f"Therefore some {s} are {p}.",
    "O": lambda s, p: f"Therefore some {s} are not {p}.",
}


def test_multiword_syllogism_is_faithful_or_refuses() -> None:
    rng = random.Random(31337)
    committed = 0
    for _ in range(400):
        meta = []
        seen = set()
        while len(meta) < 3:
            canon, plural = _class_term(rng)
            if canon not in seen:
                seen.add(canon)
                meta.append((canon, plural))
        surf = dict(meta)
        canons = [c for c, _ in meta]
        (s1, p1), (s2, p2), (sc, pc) = (
            rng.sample(canons, 2),
            rng.sample(canons, 2),
            rng.sample(canons, 2),
        )
        f1, f2, fc = rng.choice("AEIO"), rng.choice("AEIO"), rng.choice("AEIO")
        prose = " ".join(
            [_MW_PREMISE[f1](surf[s1], surf[p1]), _MW_PREMISE[f2](surf[s2], surf[p2]),
             _MW_CONCLUSION[fc](surf[sc], surf[pc])]
        )
        structure = {
            "terms": sorted(canons),
            "domain_size": 3,
            "premises": [
                {"form": f1, "subject": s1, "predicate": p1},
                {"form": f2, "subject": s2, "predicate": p2},
            ],
        }
        query = {"kind": "validity", "conclusion": {"form": fc, "subject": sc, "predicate": pc}}
        try:
            expected = syl_oracle(structure, query)
        except SylError:
            expected = None
        got = _committed(comprehend(prose), to_syllogism, syl_oracle, SylError)
        if got is not None:
            committed += 1
            assert got == expected, (prose, got, expected)
    assert committed > 50


def test_multiword_total_ordering_is_faithful_or_refuses() -> None:
    rng = random.Random(2718)
    committed = 0
    for _ in range(300):
        pool = list(_TERMS)
        rng.shuffle(pool)
        n = rng.randint(2, 4)
        chain, surf = [], {}
        for _ in range(n):
            canon, s = _item_term(rng, pool)
            chain.append(canon)
            surf[canon] = s
        rels = [{"less": chain[i], "greater": chain[i + 1]} for i in range(n - 1)]
        facts = ", and ".join(f"{surf[lo]} is below {surf[hi]}" for lo, hi in zip(chain, chain[1:])) + "."
        if rng.random() < 0.5:
            order = rng.choice(["ascending", "descending"])
            prose = f"{facts} Sort {order}."
            query = {"kind": "sort", "order": order}
        else:
            x, y = rng.sample(chain, 2)
            prose = f"{facts} Compare {surf[x]} with {surf[y]}."
            query = {"kind": "compare", "left": x, "right": y}
        structure = {"items": sorted(chain), "relations": rels}
        try:
            expected = ord_oracle(structure, query)
        except OrdError:
            expected = None
        got = _committed(comprehend(prose), to_total_ordering, ord_oracle, OrdError)
        if got is not None:
            committed += 1
            assert got == expected, (prose, got, expected)
    assert committed > 50
