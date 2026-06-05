"""Phase 2a-r1 — the general comprehension reader (disciplined Path β).

Reads S-P-O structure SYMBOLICALLY from the token sequence via domain-agnostic
templates keyed on FUNCTION WORDS + ORDER (the field provably cannot recover
structure — see the α-falsification in the Phase 2 scope doc). Content is the
filler; structure is the template. Parse-or-refuse → wrong=0 at the comprehension
layer. Each test bites under its named violation.
"""

from __future__ import annotations

from generate.meaning_graph.reader import (
    Comprehension,
    Query,
    Refusal,
    comprehend,
)


def _rel(comp: Comprehension, predicate: str) -> tuple:
    return tuple(
        (r.predicate, r.arguments) for r in comp.meaning_graph.relations if r.predicate == predicate
    )


def _entity_kind(comp: Comprehension, entity_id: str) -> str | None:
    for e in comp.meaning_graph.entities:
        if e.entity_id == entity_id:
            return e.kind
    return None


# --------------------------------------------------------------------------- #
# Single-clause templates
# --------------------------------------------------------------------------- #


def test_membership_clause() -> None:
    comp = comprehend("Rhea is a raven.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "member") == (("member", ("rhea", "raven")),)
    assert _entity_kind(comp, "rhea") == "individual"
    assert _entity_kind(comp, "raven") == "class"
    assert comp.queries == ()


def test_membership_clause_an() -> None:
    comp = comprehend("Ada is an engineer.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "member") == (("member", ("ada", "engineer")),)


def test_subsumption_clause_pluralized() -> None:
    comp = comprehend("All ravens are birds.")
    assert isinstance(comp, Comprehension)
    # plural surfaces normalize to the singular class ids the oracle expects.
    assert _rel(comp, "subset") == (("subset", ("raven", "bird")),)
    assert _entity_kind(comp, "raven") == "class"
    assert _entity_kind(comp, "bird") == "class"


def test_query_clause() -> None:
    comp = comprehend("Is Rhea a bird?")
    assert isinstance(comp, Comprehension)
    assert len(comp.queries) == 1
    q = comp.queries[0]
    assert isinstance(q, Query)
    assert q.predicate == "member"
    assert q.arguments == ("rhea", "bird")


def test_subset_query_clause() -> None:
    comp = comprehend("Are all squares polygons?")
    assert isinstance(comp, Comprehension)
    assert len(comp.queries) == 1
    q = comp.queries[0]
    assert q.predicate == "subset"
    assert q.arguments == ("square", "polygon")


def test_definite_np_membership_clause() -> None:
    comp = comprehend("The mug is a cup.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "member") == (("member", ("mug", "cup")),)
    assert _entity_kind(comp, "mug") == "individual"


def test_definite_np_membership_query() -> None:
    comp = comprehend("Is the mug a tool?")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "member"
    assert comp.queries[0].arguments == ("mug", "tool")


# --------------------------------------------------------------------------- #
# Categorical forms (syllogism) — neutral predicates the projector maps to A/E/I/O
# --------------------------------------------------------------------------- #


def test_categorical_no_is_disjoint() -> None:
    comp = comprehend("No reptiles are mammals.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "disjoint") == (("disjoint", ("reptile", "mammal")),)


def test_categorical_some_is_intersects() -> None:
    comp = comprehend("Some students are poets.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "intersects") == (("intersects", ("student", "poet")),)


def test_categorical_some_not_is_some_not() -> None:
    comp = comprehend("Some pets are not reptiles.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "some_not") == (("some_not", ("pet", "reptile")),)


def test_therefore_is_a_conclusion_query() -> None:
    comp = comprehend("Therefore all whales are animals.")
    assert isinstance(comp, Comprehension)
    assert comp.meaning_graph.relations == ()  # a conclusion is a query, not a fact
    assert comp.queries[0].predicate == "subset"
    assert comp.queries[0].arguments == ("whale", "animal")


def test_full_syllogism_premises_and_conclusion() -> None:
    comp = comprehend(
        "All mammals are animals. All whales are mammals. Therefore all whales are animals."
    )
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "subset") == (
        ("subset", ("mammal", "animal")),
        ("subset", ("whale", "mammal")),
    )
    assert comp.queries[0].arguments == ("whale", "animal")


# --------------------------------------------------------------------------- #
# Ordering — comparatives carry DIRECTION (wrong direction would flip the sort)
# --------------------------------------------------------------------------- #


def test_comparative_below_is_less() -> None:
    comp = comprehend("Bronze is below silver.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("bronze", "silver")),)
    assert _entity_kind(comp, "bronze") == "item"


def test_comparative_taller_reverses_direction() -> None:
    # "Oak is taller than birch" => oak > birch => less(birch, oak).
    comp = comprehend("Oak is taller than birch.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("birch", "oak")),)


def test_comparative_elided_copula() -> None:
    comp = comprehend("Silver below gold.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("silver", "gold")),)


def test_comma_joined_clauses() -> None:
    comp = comprehend("Bronze is below silver, and silver is below gold.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (
        ("less", ("bronze", "silver")),
        ("less", ("silver", "gold")),
    )


def test_sort_query_from_low_to_high_is_ascending() -> None:
    comp = comprehend("Sort them from lowest to highest.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "sort"
    assert comp.queries[0].arguments == ("ascending",)


def test_compare_query() -> None:
    comp = comprehend("Compare alpha with delta.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "compare"
    assert comp.queries[0].arguments == ("alpha", "delta")


# --------------------------------------------------------------------------- #
# Full multi-clause problem
# --------------------------------------------------------------------------- #


def test_full_membership_problem() -> None:
    comp = comprehend("Rhea is a raven. All ravens are birds. Is Rhea a bird?")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "member") == (("member", ("rhea", "raven")),)
    assert _rel(comp, "subset") == (("subset", ("raven", "bird")),)
    assert len(comp.queries) == 1
    assert comp.queries[0].arguments == ("rhea", "bird")


def test_irregular_plural_people_person_is_consistent() -> None:
    # The wrong=0 wrinkle: 'people' must normalize to the same id as 'person'.
    comp = comprehend("All scientists are people. Is Ada a person?")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "subset") == (("subset", ("scientist", "person")),)
    assert comp.queries[0].arguments == ("ada", "person")


# --------------------------------------------------------------------------- #
# Generality — SAME template, DISTINCT domains (anti-overfit)
# --------------------------------------------------------------------------- #


def test_membership_template_generalizes_across_domains() -> None:
    # One template, three distinct content domains -> all produce member().
    for text, ind, cls in [
        ("Rex is a dog.", "rex", "dog"),          # animals
        ("Ada is a botanist.", "ada", "botanist"),  # professions
        ("Paris is a city.", "paris", "city"),    # geography
    ]:
        comp = comprehend(text)
        assert isinstance(comp, Comprehension), text
        assert _rel(comp, "member") == (("member", (ind, cls)),), text


# --------------------------------------------------------------------------- #
# Parse-or-refuse — refuse, never guess (wrong=0)
# --------------------------------------------------------------------------- #


def test_refuses_unmatched_clause() -> None:
    comp = comprehend("The weather changed quickly yesterday.")
    assert isinstance(comp, Refusal)
    assert comp.reason == "no_template_match"


def test_refuses_when_any_clause_unmatched() -> None:
    # If ONE clause cannot be read, the whole problem refuses (no partial guess).
    comp = comprehend("Rhea is a raven. Rhea flew over the mountain.")
    assert isinstance(comp, Refusal)


def test_refuses_non_identifier_filler() -> None:
    # A filler that is not a clean identifier cannot become an entity id -> refuse.
    comp = comprehend("Rhea is a co-pilot.")
    assert isinstance(comp, Refusal)


def test_empty_input_refuses() -> None:
    assert isinstance(comprehend(""), Refusal)
    assert isinstance(comprehend("   "), Refusal)
