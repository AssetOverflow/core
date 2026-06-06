"""Structure preservation — the reader recovers the EXACT structure, not just a
verdict-equivalent one (closes the coincidental-correctness gap).

`test_comprehension_wrong_zero_property.py` proves ANSWER preservation: the
comprehension path yields the same oracle verdict as the ground-truth structure. But
a *misread* graph can coincidentally yield the same verdict and pass that test. This
module proves the stronger property: over randomly generated structures rendered to
prose, the projected structure (and query) the reader recovers equals the
ground-truth structure exactly — or the reader refuses. Verdict agreement then
follows for free; here we assert STRUCTURE, separately.

Each generator renders prose that FULLY determines its structure (every term /
class / item / atom it claims is actually stated), so projected == ground truth is
the honest bar. A reader that drops, adds, swaps, or mis-roles any element fails
here even when the final verdict happens to match.
"""

from __future__ import annotations

import random

from generate.meaning_graph.projectors import (
    to_deductive_logic,
    to_set_membership,
    to_syllogism,
    to_total_ordering,
)
from generate.meaning_graph.reader import Refusal, comprehend
from generate.quantitative_comprehension import comprehend_quantitative, to_relational_metric

_TERMS = [f"t{i}" for i in range(8)]


def _canon(value):
    """Order-insensitive canonicalization (lists/tuples are sets here, since the
    reasoning structures are order-free) for exact structure comparison."""
    if isinstance(value, dict):
        return tuple(sorted((k, _canon(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(sorted((_canon(v) for v in value), key=repr))
    return value


def _project(comp_or_refusal, projector):
    if isinstance(comp_or_refusal, Refusal):
        return None
    return projector(comp_or_refusal)


# --------------------------------------------------------------------------- #
# Syllogism
# --------------------------------------------------------------------------- #

_PREM = {
    "A": lambda s, p: f"All {s}s are {p}s.",
    "E": lambda s, p: f"No {s}s are {p}s.",
    "I": lambda s, p: f"Some {s}s are {p}s.",
    "O": lambda s, p: f"Some {s}s are not {p}s.",
}
_CONCL = {
    "A": lambda s, p: f"Therefore all {s}s are {p}s.",
    "E": lambda s, p: f"Therefore no {s}s are {p}s.",
    "I": lambda s, p: f"Therefore some {s}s are {p}s.",
    "O": lambda s, p: f"Therefore some {s}s are not {p}s.",
}


def test_syllogism_structure_is_preserved_exactly() -> None:
    rng = random.Random(11)
    committed = 0
    for _ in range(400):
        pool = rng.sample(_TERMS, 3)
        prem = [(rng.choice("AEIO"), *rng.sample(pool, 2)) for _ in range(2)]
        cc = (rng.choice("AEIO"), *rng.sample(pool, 2))
        used = sorted({t for _, s, p in prem for t in (s, p)} | {cc[1], cc[2]})
        prose = " ".join([_PREM[f](s, p) for f, s, p in prem] + [_CONCL[cc[0]](cc[1], cc[2])])
        structure = {
            "terms": used,
            "domain_size": 3,
            "premises": [{"form": f, "subject": s, "predicate": p} for f, s, p in prem],
        }
        query = {"kind": "validity", "conclusion": {"form": cc[0], "subject": cc[1], "predicate": cc[2]}}
        proj = _project(comprehend(prose), to_syllogism)
        if proj is None:
            continue
        committed += 1
        pstruct, pquery = proj
        assert _canon(pstruct) == _canon(structure), (prose, pstruct, structure)
        assert pquery == query, (prose, pquery, query)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Total ordering
# --------------------------------------------------------------------------- #


def test_total_ordering_structure_is_preserved_exactly() -> None:
    rng = random.Random(22)
    committed = 0
    for _ in range(300):
        n = rng.randint(2, 5)
        chain = rng.sample(_TERMS, n)
        rels = [{"less": chain[i], "greater": chain[i + 1]} for i in range(n - 1)]
        facts = ", and ".join(f"{lo} is below {hi}" for lo, hi in zip(chain, chain[1:])) + "."
        if rng.random() < 0.5:
            order = rng.choice(["ascending", "descending"])
            prose = f"{facts} Sort {order}."
            query = {"kind": "sort", "order": order}
        else:
            x, y = rng.sample(chain, 2)
            prose = f"{facts} Compare {x} with {y}."
            query = {"kind": "compare", "left": x, "right": y}
        structure = {"items": sorted(chain), "relations": rels}
        proj = _project(comprehend(prose), to_total_ordering)
        if proj is None:
            continue
        committed += 1
        pstruct, pquery = proj
        assert _canon(pstruct) == _canon(structure), (prose, pstruct, structure)
        assert pquery == query, (prose, pquery, query)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Set membership — classes derived from stated facts (so prose fully determines it)
# --------------------------------------------------------------------------- #


def test_set_membership_structure_is_preserved_exactly() -> None:
    rng = random.Random(33)
    committed = 0
    for _ in range(300):
        pool = rng.sample(_TERMS, rng.randint(2, 4))
        individuals = [f"e{i}" for i in range(rng.randint(1, 3))]
        member_facts = [(ind, rng.choice(pool)) for ind in individuals]
        subset_facts = [
            (pool[i], pool[i + 1]) for i in range(len(pool) - 1) if rng.random() < 0.7
        ]
        # Classes that are actually STATED (member class or either side of a subset).
        used_classes = sorted(
            {c for _, c in member_facts} | {a for a, _ in subset_facts} | {b for _, b in subset_facts}
        )
        member_lines = [f"{ind} is a {cls}." for ind, cls in member_facts]
        subset_lines = [f"All {a}s are {b}s." for a, b in subset_facts]
        sets = [
            {"id": c, "members": sorted({i for i, cl in member_facts if cl == c})}
            for c in used_classes
        ]
        structure = {
            "elements": sorted(individuals),
            "sets": sets,
            "subsets": [{"subset": a, "superset": b} for a, b in subset_facts],
        }
        # Query over stated entities only.
        if rng.random() < 0.5 and individuals:
            ind = rng.choice(individuals)
            target = rng.choice(used_classes)
            prose = " ".join(member_lines + subset_lines + [f"Is {ind} a {target}?"])
            query = {"kind": "member", "element": ind, "set": target}
        elif len(used_classes) >= 2:
            a, b = rng.sample(used_classes, 2)
            prose = " ".join(member_lines + subset_lines + [f"Are all {a}s {b}s?"])
            query = {"kind": "subset", "subset": a, "superset": b}
        else:
            continue
        proj = _project(comprehend(prose), to_set_membership)
        if proj is None:
            continue
        committed += 1
        pstruct, pquery = proj
        assert _canon(pstruct) == _canon(structure), (prose, pstruct, structure)
        assert pquery == query, (prose, pquery, query)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Propositional logic — premises (as a set of formula strings) + query string
# --------------------------------------------------------------------------- #

_ATOMS = [f"p{i}" for i in range(5)]


def _prop_fact(rng):
    kind = rng.choice(["implies", "or", "atom", "not_atom"])
    if kind == "implies":
        a, b = rng.sample(_ATOMS, 2)
        return f"If {a} then {b}.", f"{a} implies {b}"
    if kind == "or":
        a, b = rng.sample(_ATOMS, 2)
        return f"{a} or {b}.", f"{a} or {b}"
    if kind == "not_atom":
        a = rng.choice(_ATOMS)
        return f"Not {a}.", f"not {a}"
    a = rng.choice(_ATOMS)
    return f"{a}.", a


def _prop_query(rng):
    kind = rng.choice(["atom", "not_atom", "implies"])
    if kind == "implies":
        a, b = rng.sample(_ATOMS, 2)
        return f"Therefore if {a} then {b}.", f"{a} implies {b}"
    if kind == "not_atom":
        a = rng.choice(_ATOMS)
        return f"Therefore not {a}.", f"not {a}"
    a = rng.choice(_ATOMS)
    return f"Therefore {a}.", a


def test_propositional_structure_is_preserved_exactly() -> None:
    rng = random.Random(44)
    committed = 0
    for _ in range(400):
        facts = [_prop_fact(rng) for _ in range(rng.randint(1, 3))]
        concl_prose, query_formula = _prop_query(rng)
        prose = " ".join(p for p, _ in facts) + " " + concl_prose
        premises = frozenset(f for _, f in facts)
        proj = _project(comprehend(prose), to_deductive_logic)
        if proj is None:
            continue
        committed += 1
        pprem, pquery = proj
        assert frozenset(pprem) == premises, (prose, pprem, premises)
        assert pquery == query_formula, (prose, pquery, query_formula)
    assert committed > 50


# --------------------------------------------------------------------------- #
# Perturbation invariance — meaning-preserving surface changes (premise/clause
# reordering, capitalization, extra whitespace) must yield the SAME structure.
# --------------------------------------------------------------------------- #


def _struct(prose, projector):
    proj = _project(comprehend(prose), projector)
    return None if proj is None else (_canon(proj[0]), proj[1])


def test_syllogism_invariant_to_premise_reorder_and_caps() -> None:
    # Same two premises in either order + capitalized variant -> identical structure.
    base = "All mammals are animals. All whales are mammals. Therefore all whales are animals."
    swapped = "All whales are mammals. All mammals are animals. Therefore all whales are animals."
    caps = "ALL MAMMALS ARE ANIMALS. All Whales Are Mammals. Therefore all whales are animals."
    s_base = _struct(base, to_syllogism)
    assert s_base is not None
    assert _struct(swapped, to_syllogism) == s_base
    assert _struct(caps, to_syllogism) == s_base


def test_total_ordering_invariant_to_clause_reorder_and_whitespace() -> None:
    base = "a is below b, and b is below c. Sort ascending."
    reordered = "b is below c, and a is below b. Sort ascending."
    spaced = "a   is below b,  and b is below   c.  Sort ascending."
    s_base = _struct(base, to_total_ordering)
    assert s_base is not None
    assert _struct(reordered, to_total_ordering) == s_base
    assert _struct(spaced, to_total_ordering) == s_base


def test_propositional_invariant_to_premise_reorder() -> None:
    base = "If p then q. p. Therefore q."
    swapped = "p. If p then q. Therefore q."
    s_base = _struct(base, to_deductive_logic)
    assert s_base is not None
    assert _struct(swapped, to_deductive_logic) == s_base


# --------------------------------------------------------------------------- #
# Arithmetic (binding_graph) — projected relations + query preserved exactly.
# --------------------------------------------------------------------------- #


def test_arithmetic_structure_is_preserved_exactly() -> None:
    rng = random.Random(55)
    committed = 0
    for _ in range(300):
        ents = rng.sample([f"e{i}" for i in range(6)], rng.randint(2, 4))
        base, base_val = ents[0], rng.randint(1, 20)
        relations = [{"kind": "fact", "entity": base, "value": base_val}]
        lines = [f"{base} has {base_val} things."]
        prev = base
        for e in ents[1:]:
            delta = rng.randint(1, 15)
            kind = rng.choice(["more_than", "fewer_than"])
            word = "more" if kind == "more_than" else "fewer"
            relations.append({"kind": kind, "entity": e, "ref": prev, "delta": delta})
            lines.append(f"{e} has {delta} {word} things than {prev}.")
            prev = e
        ask = rng.choice(ents)
        lines.append(f"How many things does {ask} have?")
        prose = " ".join(lines)
        expected_query = {"entity": ask, "unit": "item"}  # "things" -> item dimension

        comp = comprehend_quantitative(prose)
        if isinstance(comp, Refusal):
            continue
        proj = to_relational_metric(comp)
        if proj is None:
            continue
        committed += 1
        prelations, pquery = proj
        assert _canon(prelations) == _canon(relations), (prose, prelations, relations)
        assert pquery == expected_query, (prose, pquery, expected_query)
    assert committed > 50
