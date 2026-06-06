"""Projector unit tests — MeaningGraph -> each oracle's input shape.

Projectors hold NO decision logic; they only re-shape. These tests pin the shape
(so a drift that mis-maps a form or drops a fact bites) and the None-on-
unprojectable contract (so the runner treats "nothing to ask" as a refusal, not a
silent wrong).
"""

from __future__ import annotations

from generate.meaning_graph.projectors import (
    to_deductive_logic,
    to_syllogism,
    to_total_ordering,
)
from generate.meaning_graph.reader import Comprehension, comprehend


def _comp(text: str) -> Comprehension:
    comp = comprehend(text)
    assert isinstance(comp, Comprehension), text
    return comp


# --------------------------------------------------------------------------- #
# to_syllogism
# --------------------------------------------------------------------------- #


def test_to_syllogism_maps_premises_and_conclusion() -> None:
    comp = _comp(
        "All mammals are animals. All whales are mammals. "
        "Therefore all whales are animals."
    )
    projected = to_syllogism(comp)
    assert projected is not None
    structure, query = projected
    assert structure["terms"] == ["animal", "mammal", "whale"]
    assert structure["domain_size"] == 3
    assert {"form": "A", "subject": "mammal", "predicate": "animal"} in structure["premises"]
    assert {"form": "A", "subject": "whale", "predicate": "mammal"} in structure["premises"]
    assert query == {
        "kind": "validity",
        "conclusion": {"form": "A", "subject": "whale", "predicate": "animal"},
    }


def test_to_syllogism_maps_e_i_o_forms() -> None:
    comp = _comp(
        "No reptiles are mammals. Some pets are reptiles. "
        "Therefore some pets are not mammals."
    )
    projected = to_syllogism(comp)
    assert projected is not None
    structure, query = projected
    forms = {(p["form"], p["subject"], p["predicate"]) for p in structure["premises"]}
    assert ("E", "reptile", "mammal") in forms
    assert ("I", "pet", "reptile") in forms
    assert query["conclusion"]["form"] == "O"


def test_to_syllogism_none_when_no_conclusion() -> None:
    # Premises but no "therefore" conclusion -> nothing askable -> None.
    assert to_syllogism(_comp("All mammals are animals.")) is None


def test_to_syllogism_none_for_membership_only() -> None:
    assert to_syllogism(_comp("Rhea is a raven.")) is None


# --------------------------------------------------------------------------- #
# to_total_ordering
# --------------------------------------------------------------------------- #


def test_to_total_ordering_sort_shape() -> None:
    comp = _comp(
        "Bronze is below silver, and silver is below gold. "
        "Sort them from lowest to highest."
    )
    projected = to_total_ordering(comp)
    assert projected is not None
    structure, query = projected
    assert structure["items"] == ["bronze", "gold", "silver"]
    assert {"less": "bronze", "greater": "silver"} in structure["relations"]
    assert {"less": "silver", "greater": "gold"} in structure["relations"]
    assert query == {"kind": "sort", "order": "ascending"}


def test_to_total_ordering_compare_shape() -> None:
    comp = _comp("A is earlier than B. Compare a with b.")
    projected = to_total_ordering(comp)
    assert projected is not None
    structure, query = projected
    assert structure["items"] == ["a", "b"]
    assert query == {"kind": "compare", "left": "a", "right": "b"}


def test_to_total_ordering_none_without_query() -> None:
    assert to_total_ordering(_comp("Bronze is below silver.")) is None


# --------------------------------------------------------------------------- #
# Cross-projector neutrality — one MeaningGraph, distinct oracle shapes
# --------------------------------------------------------------------------- #


def test_one_graph_projects_only_to_its_domain() -> None:
    # A categorical-with-conclusion comprehension projects to syllogism but not to
    # total_ordering (no ordering query) — the interlingua is neutral, the
    # projector decides applicability.
    comp = _comp("All mammals are animals. Therefore all mammals are animals.")
    assert to_syllogism(comp) is not None
    assert to_total_ordering(comp) is None
    assert to_deductive_logic(comp) is None  # categorical relations -> not propositional


# --------------------------------------------------------------------------- #
# to_deductive_logic
# --------------------------------------------------------------------------- #


def test_to_deductive_logic_serializes_formulas() -> None:
    comp = _comp("If p then q. p. Therefore q.")
    projected = to_deductive_logic(comp)
    assert projected is not None
    premises, query = projected
    assert set(premises) == {"p implies q", "p"}
    assert query == "q"


def test_to_deductive_logic_serializes_negation_and_disjunction() -> None:
    comp = _comp("p or q. Not q. Therefore p.")
    projected = to_deductive_logic(comp)
    assert projected is not None
    premises, query = projected
    assert set(premises) == {"p or q", "not q"}
    assert query == "p"


def test_to_deductive_logic_none_for_categorical_comprehension() -> None:
    # No propositional relations / query -> nothing askable of the entailment oracle.
    assert to_deductive_logic(_comp("All mammals are animals.")) is None
