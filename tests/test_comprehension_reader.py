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


# --------------------------------------------------------------------------- #
# Categorical premises — E / I / O forms (syllogism shapes)
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


# --------------------------------------------------------------------------- #
# "Therefore <categorical>" -> conclusion QUERY (same neutral predicates)
# --------------------------------------------------------------------------- #


def test_therefore_conclusion_is_a_query_not_a_fact() -> None:
    comp = comprehend("All whales are mammals. Therefore all whales are mammals.")
    assert isinstance(comp, Comprehension)
    # the premise is a fact; the conclusion is a query of the same predicate.
    assert _rel(comp, "subset") == (("subset", ("whale", "mammal")),)
    assert len(comp.queries) == 1
    assert comp.queries[0].predicate == "subset"
    assert comp.queries[0].arguments == ("whale", "mammal")


def test_therefore_maps_each_quantifier_to_its_predicate() -> None:
    for tail, predicate in [
        ("all dogs are animals", "subset"),
        ("no dogs are cats", "disjoint"),
        ("some dogs are pets", "intersects"),
        ("some dogs are not cats", "some_not"),
    ]:
        comp = comprehend(f"Therefore {tail}.")
        assert isinstance(comp, Comprehension), tail
        assert comp.queries[0].predicate == predicate, tail


# --------------------------------------------------------------------------- #
# Ordering — comparative facts (total_ordering shapes)
# --------------------------------------------------------------------------- #


def test_comparative_less_direction() -> None:
    comp = comprehend("Bronze is below silver.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("bronze", "silver")),)
    assert _entity_kind(comp, "bronze") == "item"


def test_comparative_greater_direction_reverses() -> None:
    # "X is taller than Y" means X > Y, i.e. less(Y, X).
    comp = comprehend("Oak is taller than birch.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("birch", "oak")),)


def test_comparative_elided_verb() -> None:
    # "Venus closer than Earth" (no copula) still reads.
    comp = comprehend("Venus closer than Earth.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("venus", "earth")),)


def test_comparative_clause_splitting_on_comma_and() -> None:
    comp = comprehend("A is earlier than B, and B is earlier than C.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("a", "b")), ("less", ("b", "c")))


# --------------------------------------------------------------------------- #
# Ordering — sort / compare QUERIES
# --------------------------------------------------------------------------- #


def test_sort_query_lowest_to_highest_is_ascending() -> None:
    comp = comprehend("Sort them from lowest to highest.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "sort"
    assert comp.queries[0].arguments == ("ascending",)


def test_sort_query_explicit_descending() -> None:
    comp = comprehend("Sort descending.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].arguments == ("descending",)


def test_sort_query_order_question_form() -> None:
    comp = comprehend("Which is the height order from shortest to tallest?")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "sort"
    assert comp.queries[0].arguments == ("ascending",)


def test_compare_query() -> None:
    comp = comprehend("Compare north with south.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "compare"
    assert comp.queries[0].arguments == ("north", "south")


# --------------------------------------------------------------------------- #
# Generality — SAME comparative template, DISTINCT domains (anti-overfit)
# --------------------------------------------------------------------------- #


def test_comparative_template_generalizes_across_domains() -> None:
    for text, lo, hi in [
        ("Bronze is below silver.", "bronze", "silver"),   # metals
        ("Monday is earlier than tuesday.", "monday", "tuesday"),  # time
        ("Birch is shorter than oak.", "birch", "oak"),    # height
    ]:
        comp = comprehend(text)
        assert isinstance(comp, Comprehension), text
        assert _rel(comp, "less") == (("less", (lo, hi)),), text


# --------------------------------------------------------------------------- #
# Multi-word NP — CHUNK by the canonicalization contract (join tokens with "_")
# --------------------------------------------------------------------------- #


def test_multiword_np_in_categorical_chunks() -> None:
    comp = comprehend("No metal objects are soft objects.")
    assert isinstance(comp, Comprehension)
    # plural class head singularized, then joined: "metal objects" -> "metal_object"
    assert _rel(comp, "disjoint") == (("disjoint", ("metal_object", "soft_object")),)


def test_multiword_np_in_comparative_chunks() -> None:
    comp = comprehend("North station is below south.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "less") == (("less", ("north_station", "south")),)
    assert _entity_kind(comp, "north_station") == "item"


def test_multiword_item_in_compare_query_chunks() -> None:
    comp = comprehend("Compare north station with south.")
    assert isinstance(comp, Comprehension)
    assert comp.queries[0].predicate == "compare"
    assert comp.queries[0].arguments == ("north_station", "south")


def test_multiword_individual_in_membership_chunks() -> None:
    comp = comprehend("The red car is a vehicle.")
    assert isinstance(comp, Comprehension)
    assert _rel(comp, "member") == (("member", ("red_car", "vehicle")),)


def test_join_is_information_preserving_distinct_nps_stay_distinct() -> None:
    # WHY the contract JOINS instead of keeping the head word: distinct phrases must
    # not collapse into a false identity ("metal objects" vs "metal tools" both ->
    # "metal" would be a wrong=0 hazard).
    comp = comprehend("All metal objects are heavy items. All metal tools are sharp items.")
    assert isinstance(comp, Comprehension)
    ids = {e.entity_id for e in comp.meaning_graph.entities}
    assert {"metal_object", "metal_tool"} <= ids  # NOT collapsed to "metal"


# --------------------------------------------------------------------------- #
# Parse-or-refuse — still refuse where no honest reading exists (wrong=0)
# --------------------------------------------------------------------------- #


def test_adjectival_predicate_refuses_via_morphology() -> None:
    # "trained" is an adjective, not a pluralizable noun class -> cannot singularize.
    comp = comprehend("All pilots are trained.")
    assert isinstance(comp, Refusal)
    assert comp.reason == "unknown_morphology"


def test_trailing_prepositional_phrase_in_compare_refuses() -> None:
    # "...in the same order" leaks reserved words into the NP slot -> refuse, never
    # chunk "beta_in_the_same_order".
    comp = comprehend("Compare beta with beta in the same order.")
    assert isinstance(comp, Refusal)
    assert comp.reason == "reserved_word_in_np"


def test_ambiguous_two_np_subset_query_refuses() -> None:
    # Two adjacent multi-word class NPs with no separating function word -> the
    # boundary is unknown, so refuse rather than guess it.
    comp = comprehend("Are all metal objects soft objects?")
    assert isinstance(comp, Refusal)
    assert comp.reason == "ambiguous_subset_query"
