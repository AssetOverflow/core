"""Tests for generate/problem_frame_builder.py."""
from __future__ import annotations

from fractions import Fraction

from generate.problem_frame_builder import build_problem_frame
from language_packs.scalar_equivalence import extract_scalar_candidates, list_unsupported_surfaces


def _frame_names(text: str) -> tuple[str, ...]:
    return tuple(f.name for f in build_problem_frame(text).process_frames)


def _hazard_categories(text: str) -> tuple[str, ...]:
    return tuple(sorted({h.category for h in build_problem_frame(text).hazards}))


def test_percent_text_produces_scalar_facts_and_hazards_without_solving() -> None:
    text = "Mia spent 50% of her money."
    frame = build_problem_frame(text)

    assert frame.scalars
    assert any(s.canonical == Fraction(1, 2) for s in frame.scalars)
    assert "percent_change_vs_percent_of" in _hazard_categories(text)
    assert frame.question_target is None


def test_transfer_text_produces_transfer_process_frame_without_solving() -> None:
    text = "Tom gave Ana 3 marbles."
    frame = build_problem_frame(text)

    assert "transfer" in _frame_names(text)
    assert any(r.relation_type == "transfer" for r in frame.candidate_relations)
    assert not frame.question_target


def test_container_text_produces_container_process_frame_without_solving() -> None:
    text = "There are 4 full boxes and 3 loose crayons."
    frame = build_problem_frame(text)

    assert "container_packing" in _frame_names(text)
    assert frame.units or frame.scalars


def test_travel_text_produces_travel_process_frame_without_solving() -> None:
    text = "A car drove 30 miles each way."
    frame = build_problem_frame(text)

    assert "travel" in _frame_names(text)


def test_ambiguous_quarter_surfaces_carry_hazards() -> None:
    text = "A quarter of the class left."
    frame = build_problem_frame(text)

    categories = _hazard_categories(text)
    assert "unbound_base_quantity" in categories
    assert any(
        h.surface == "quarter" or h.category.startswith("quarter_")
        for h in frame.hazards
    )


def test_third_ordinal_carries_hazard() -> None:
    text = "Sam finished in third place."
    frame = build_problem_frame(text)

    assert "third_ordinal" in _hazard_categories(text)
    assert not any(s.canonical == Fraction(1, 3) for s in frame.scalars)


def test_unsupported_scalar_surfaces_do_not_broaden_adr_0128() -> None:
    text = "The remaining amount is .5 of the total."
    frame = build_problem_frame(text)

    assert frame.scalars == ()
    assert ".5" in list_unsupported_surfaces()
    assert extract_scalar_candidates(text) == ()


def test_exact_spans_slice_original_text() -> None:
    text = "Mia spent 50% of her money."
    frame = build_problem_frame(text)

    for scalar in frame.scalars:
        assert scalar.source_span is not None
        assert scalar.source_surface is not None
        start, end = scalar.source_span
        assert text[start:end] == scalar.source_surface

    for quantity in frame.quantities:
        span = quantity.provenance.source_spans[0]
        assert text[span.start:span.end] == span.text


def test_deterministic_ordering_across_repeated_runs() -> None:
    text = "Tom gave Ana 3 marbles and spent 50% of her money."
    frame_a = build_problem_frame(text)
    frame_b = build_problem_frame(text)

    assert frame_a.scalars == frame_b.scalars
    assert frame_a.units == frame_b.units
    assert frame_a.process_frames == frame_b.process_frames
    assert frame_a.hazards == frame_b.hazards
    assert frame_a.candidate_relations == frame_b.candidate_relations
    assert frame_a.mentions == frame_b.mentions
    assert frame_a.bindings == frame_b.bindings
    assert frame_a.bound_relations == frame_b.bound_relations


def test_mentions_bind_quantities_and_units_with_exact_spans() -> None:
    text = "A runner traveled 5 miles in 2 hours. How many miles?"
    frame = build_problem_frame(text)

    assert any(binding.binding_type == "quantity_entity" for binding in frame.bindings)
    assert any(binding.binding_type == "quantity_unit" for binding in frame.bindings)
    for mention in frame.mentions:
        assert text[mention.span.start:mention.span.end] == mention.span.text


def test_transfer_roles_and_question_target_are_bound() -> None:
    frame = build_problem_frame(
        "Tom gave Ana 3 marbles. How many marbles does Ana have?"
    )
    relation = next(item for item in frame.bound_relations if item.relation_type == "transfer")
    assert {role.role for role in relation.roles} == {"agent", "patient", "quantity", "object"}
    assert frame.bound_question_target is not None
    assert frame.bound_question_target.grounded


def test_question_target_is_explicitly_unbound_when_not_groundable() -> None:
    frame = build_problem_frame("What is the answer?")
    assert frame.bound_question_target is not None
    assert not frame.bound_question_target.grounded


def test_decrease_to_fraction_binds_state_base_scale_and_delta_target() -> None:
    text = (
        "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
        "If the current temperature of the mountain is 84 degrees, what will the temperature "
        "decrease by?"
    )
    frame = build_problem_frame(text)

    relation = next(item for item in frame.bound_relations if item.relation_type == "decrease_to_fraction")
    assert {role.role for role in relation.roles} == {
        "base_quantity",
        "scale",
        "state_entity",
        "transition",
        "unit",
    }
    assert frame.bound_question_target is not None
    assert frame.bound_question_target.grounded
    assert frame.bound_question_target.target_type == "difference"
    assert frame.bound_question_target.target_operator == "difference"
    assert frame.bound_question_target.target_state == "delta"
    assert frame.bound_question_target.target_direction == "decrease"


def test_decrease_relation_preserves_exact_source_spans() -> None:
    text = (
        "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
        "If the current temperature of the mountain is 84 degrees, what will the temperature "
        "decrease by?"
    )
    frame = build_problem_frame(text)
    relation = next(item for item in frame.bound_relations if item.relation_type == "decrease_to_fraction")

    for span in relation.evidence_spans:
        assert text[span.start:span.end] == span.text

    assert any(span.text == "decrease to" for span in relation.evidence_spans)
    assert any(span.text == "3/4" for span in relation.evidence_spans)
    assert any(span.text == "84" for span in relation.evidence_spans)
    assert any(span.text == "temperature" for span in relation.evidence_spans)
