from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from generate.contract_residuals import (
    ContractResidual,
    ResidualKind,
    ResidualSourceAxis,
    project_contract_residuals,
)
from generate.kernel_facts import SourceSpan
from generate.problem_frame_contracts import ContractAssessment


def _assessment(
    *,
    candidate_organ: str = "unary_delta_transition",
    missing_bindings: tuple[str, ...] = (),
    unresolved_hazards: tuple[str, ...] = (),
    runnable: bool = False,
    explanation: str = "diagnostic candidate is not runnable",
    evidence_spans: tuple[SourceSpan, ...] = (),
) -> ContractAssessment:
    return ContractAssessment(
        candidate_organ=candidate_organ,
        missing_bindings=missing_bindings,
        unresolved_hazards=unresolved_hazards,
        runnable=runnable,
        explanation=explanation,
        evidence_spans=evidence_spans,
    )


def _entries(
    kind: ResidualKind,
    axis: ResidualSourceAxis,
    *labels: str,
) -> tuple[tuple[str, ResidualKind, ResidualSourceAxis], ...]:
    return tuple((label, kind, axis) for label in labels)


EXPECTED_LABEL_MAP: tuple[
    tuple[str, ResidualKind, ResidualSourceAxis],
    ...,
] = (
    *_entries(
        ResidualKind.MISSING_PROPOSAL,
        ResidualSourceAxis.PROPOSAL,
        "quantity_entity_proposal_required",
        "unary_delta_proposal_required",
    ),
    *_entries(
        ResidualKind.MISSING_RELATION,
        ResidualSourceAxis.RELATION,
        "local_binding_relation_unbound",
    ),
    *_entries(
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
        "quantity_unbound",
        "entity_unbound",
        "quantity_kind_unresolved",
        "base_quantity_unbound",
        "scale_unbound",
        "state_entity_unbound",
        "grounded_partition_subgroup",
        "grounded_whole_entity",
        "original_whole_unbound",
        "action_cue_unbound",
        "delta_quantity_unbound",
        "changed_object_unbound",
        "direction_unbound",
    ),
    *_entries(
        ResidualKind.AMBIGUOUS_RELATION,
        ResidualSourceAxis.RELATION,
        "local_binding_relation_ambiguous",
        "decrease_relation_ambiguous",
        "unary_delta_relation_ambiguous",
    ),
    *_entries(
        ResidualKind.AMBIGUOUS_ROLE,
        ResidualSourceAxis.ROLE,
        "quantity_ambiguous",
        "entity_ambiguous",
        "multiple_original_whole_candidates",
        "delta_quantity_ambiguous",
        "changed_object_ambiguous",
    ),
    *_entries(
        ResidualKind.INEXACT_PROVENANCE,
        ResidualSourceAxis.PROVENANCE,
        "provenance_span_inexact",
        "base_quantity_provenance_missing",
        "scale_provenance_missing",
    ),
    *_entries(
        ResidualKind.NONLOCAL_BINDING,
        ResidualSourceAxis.LOCALITY,
        "quantity_entity_nonlocal",
        "pronoun_antecedent_unresolved",
    ),
    *_entries(
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
        "percent_subgroup_links_incomplete",
        "inverse_topology_unlicensed",
        "event_assertion_unlicensed",
        "passive_voice_unsupported",
        "multiple_actor_surface",
    ),
    *_entries(
        ResidualKind.UNIT_OBJECT_CONFLICT,
        ResidualSourceAxis.UNIT_OBJECT,
        "unit_kind_conflict",
        "unit_continuity_unproven",
        "unit_object_conflict",
    ),
    *_entries(
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
        "competing_family_context",
        "percent_change_vs_percent_of",
        "state_entity_continuity_unproven",
        "scale_out_of_range",
        "partition_subgroups_not_distinct",
    ),
    *_entries(
        ResidualKind.TARGET_UNBOUND,
        ResidualSourceAxis.TARGET,
        "delta_decrease_target_unbound",
        "delta_decrease_target_required",
        "grounded_question_target",
        "forward_aggregate_target_required",
    ),
    *_entries(
        ResidualKind.CONTRACT_GAP_UNCLASSIFIED,
        ResidualSourceAxis.UNKNOWN,
        "unbound_base_quantity",
        "container",
        "content",
        "count_per",
        "worker",
        "rate",
        "duration",
    ),
)


@pytest.mark.parametrize(("label", "kind", "axis"), EXPECTED_LABEL_MAP)
def test_contract_residual_exact_label_mapping(
    label: str,
    kind: ResidualKind,
    axis: ResidualSourceAxis,
) -> None:
    residuals = project_contract_residuals(
        (_assessment(missing_bindings=(label,)),)
    )

    assert len(residuals) == 1
    residual = residuals[0]
    assert residual.residual_kind is kind
    assert residual.source_axis is axis
    assert residual.residual_code == label


def test_all_currently_emitted_labels_are_accounted_for() -> None:
    assert len(EXPECTED_LABEL_MAP) == 53
    assert len({label for label, _, _ in EXPECTED_LABEL_MAP}) == 53


@pytest.mark.parametrize(
    "label",
    ("Quantity_Unbound", "quantity_unbound ", "unknown_label"),
)
def test_arbitrary_and_case_altered_labels_fall_back_without_fuzzy_match(
    label: str,
) -> None:
    residuals = project_contract_residuals(
        (_assessment(missing_bindings=(label,)),)
    )

    assert len(residuals) == 1
    assert residuals[0].residual_code == label
    assert residuals[0].residual_kind is ResidualKind.CONTRACT_GAP_UNCLASSIFIED
    assert residuals[0].source_axis is ResidualSourceAxis.UNKNOWN


def test_duplicate_code_across_missing_and_hazard_fields_emits_once() -> None:
    residuals = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("quantity_unbound",),
                unresolved_hazards=("quantity_unbound",),
            ),
        )
    )

    assert len(residuals) == 1
    assert residuals[0].residual_code == "quantity_unbound"


def test_runnable_assessment_produces_no_residual_even_with_labels() -> None:
    residuals = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                unresolved_hazards=("unit_object_conflict",),
                runnable=True,
            ),
        )
    )

    assert residuals == ()


def test_refused_assessment_without_labels_produces_no_invented_residual() -> None:
    assert project_contract_residuals((_assessment(),)) == ()


def test_residual_preserves_code_spans_and_explanation_verbatim() -> None:
    span_a = SourceSpan("gained", 4, 10, 0)
    span_b = SourceSpan("3", 11, 12, 0)
    explanation = "diagnostic candidate is not runnable: changed_object_unbound"
    residuals = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                explanation=explanation,
                evidence_spans=(span_a, span_b),
            ),
        )
    )

    assert len(residuals) == 1
    residual = residuals[0]
    assert residual.residual_code == "changed_object_unbound"
    assert residual.evidence_spans == (span_a, span_b)
    assert residual.explanation == explanation


def test_family_id_is_resolved_from_candidate_organ() -> None:
    residual = project_contract_residuals(
        (
            _assessment(
                candidate_organ="unary_delta_transition",
                missing_bindings=("changed_object_unbound",),
            ),
        )
    )[0]

    assert residual.family_id == "state_change.unary_delta"


def test_unknown_candidate_organ_keeps_none_family_id() -> None:
    residual = project_contract_residuals(
        (
            _assessment(
                candidate_organ="future_unknown_organ",
                missing_bindings=("unknown_label",),
            ),
        )
    )[0]

    assert residual.family_id is None


def test_replay_stability_and_sorted_output_are_independent_of_input_order() -> None:
    assessment_a = _assessment(missing_bindings=("changed_object_unbound",))
    assessment_b = _assessment(
        candidate_organ="quantity_entity_binding",
        missing_bindings=("unit_kind_conflict",),
    )

    forward = project_contract_residuals((assessment_a, assessment_b))
    reversed_input = project_contract_residuals((assessment_b, assessment_a))

    assert forward == reversed_input
    assert tuple(residual.residual_id for residual in forward) == tuple(
        sorted(residual.residual_id for residual in forward)
    )


def test_known_sha256_vector_and_explanation_independence() -> None:
    span = SourceSpan("gained", 4, 10, 0)
    residual_a = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                explanation="first explanation",
                evidence_spans=(span,),
            ),
        )
    )[0]
    residual_b = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                explanation="second explanation",
                evidence_spans=(span,),
            ),
        )
    )[0]

    assert residual_a.residual_id == (
        "e56fa420ce0acc64071fc5ef819d740d54f1ab17f1a268728a0ef490784ffe32"
    )
    assert residual_a.residual_id == residual_b.residual_id


def test_evidence_span_order_and_sentence_index_participate_in_identity() -> None:
    span_a = SourceSpan("gained", 4, 10, 0)
    span_b = SourceSpan("3", 11, 12, 0)
    residual_ordered = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                evidence_spans=(span_a, span_b),
            ),
        )
    )[0]
    residual_reversed = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                evidence_spans=(span_b, span_a),
            ),
        )
    )[0]
    residual_no_sentence = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                evidence_spans=(SourceSpan("gained", 4, 10), span_b),
            ),
        )
    )[0]

    assert residual_ordered.residual_id != residual_reversed.residual_id
    assert residual_ordered.residual_id != residual_no_sentence.residual_id


def test_empty_evidence_is_lawful_and_does_not_synthesize_span() -> None:
    residual = project_contract_residuals(
        (
            _assessment(
                missing_bindings=("changed_object_unbound",),
                evidence_spans=(),
            ),
        )
    )[0]

    assert residual.evidence_spans == ()


def test_projection_leaves_assessment_unchanged() -> None:
    span = SourceSpan("lost", 8, 12, 0)
    assessment = _assessment(
        missing_bindings=("delta_quantity_unbound",),
        evidence_spans=(span,),
    )
    before = assessment

    project_contract_residuals((assessment,))

    assert assessment == before


def test_contract_residual_has_no_authority_fields() -> None:
    disallowed = {
        "runnable",
        "verdict",
        "answer",
        "proof",
        "search_eligible",
        "retryable",
        "priority",
        "budget",
        "action",
        "serving_allowed",
        "mutation",
        "recommended_migration_target",
    }

    assert disallowed.isdisjoint(
        {field.name for field in dataclasses.fields(ContractResidual)}
    )


def test_public_api_is_exactly_the_read_model_projection() -> None:
    import generate.contract_residuals as contract_residuals

    assert tuple(contract_residuals.__all__) == (
        "ResidualKind",
        "ResidualSourceAxis",
        "ContractResidual",
        "project_contract_residuals",
    )


def test_family_examples_project_expected_residuals() -> None:
    examples = (
        (
            _assessment(
                candidate_organ="unary_delta_transition",
                missing_bindings=(
                    "action_cue_unbound",
                    "direction_unbound",
                    "changed_object_unbound",
                ),
            ),
            {
                "action_cue_unbound": ResidualKind.MISSING_ROLE,
                "direction_unbound": ResidualKind.MISSING_ROLE,
                "changed_object_unbound": ResidualKind.MISSING_ROLE,
            },
        ),
        (
            _assessment(
                candidate_organ="quantity_entity_binding",
                missing_bindings=("quantity_kind_unresolved",),
                unresolved_hazards=("unit_kind_conflict",),
            ),
            {
                "quantity_kind_unresolved": ResidualKind.MISSING_ROLE,
                "unit_kind_conflict": ResidualKind.UNIT_OBJECT_CONFLICT,
            },
        ),
        (
            _assessment(
                candidate_organ="fraction_decrease",
                missing_bindings=("delta_decrease_target_unbound",),
            ),
            {"delta_decrease_target_unbound": ResidualKind.TARGET_UNBOUND},
        ),
        (
            _assessment(
                candidate_organ="percent_partition",
                missing_bindings=("percent_subgroup_links_incomplete",),
                unresolved_hazards=(
                    "partition_subgroups_not_distinct",
                    "percent_change_vs_percent_of",
                ),
            ),
            {
                "partition_subgroups_not_distinct": ResidualKind.HAZARD_BLOCKED,
                "percent_subgroup_links_incomplete": (
                    ResidualKind.UNSUPPORTED_TOPOLOGY
                ),
                "percent_change_vs_percent_of": ResidualKind.HAZARD_BLOCKED,
            },
        ),
    )

    for assessment, expected in examples:
        residuals = project_contract_residuals((assessment,))
        assert {residual.residual_code for residual in residuals} == set(expected)
        for residual in residuals:
            assert residual.residual_kind is expected[residual.residual_code]


def test_positive_family_controls_project_to_empty_tuple() -> None:
    runnable_assessments = (
        _assessment(candidate_organ="unary_delta_transition", runnable=True),
        _assessment(candidate_organ="quantity_entity_binding", runnable=True),
        _assessment(candidate_organ="fraction_decrease", runnable=True),
        _assessment(candidate_organ="percent_partition", runnable=True),
    )

    assert project_contract_residuals(runnable_assessments) == ()


def test_module_imports_are_leaf_read_model_allowlist() -> None:
    source = Path("generate/contract_residuals.py").read_text()
    tree = ast.parse(source)
    imports: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert imports <= {
        "__future__",
        "hashlib",
        "json",
        "dataclasses",
        "enum",
        "generate.kernel_facts",
        "generate.problem_frame_contracts",
    }

    forbidden_calls = {
        "build_problem_frame",
        "assess_contracts",
        "determine",
        "store",
        "write",
        "repair",
        "search",
        "serve",
        "SourceSpan",
    }
    assert forbidden_calls.isdisjoint(calls)


def test_no_reverse_imports_into_contract_residuals() -> None:
    for path in Path("generate").glob("*.py"):
        if path.name == "contract_residuals.py":
            continue
        assert "contract_residuals" not in path.read_text()


def test_enum_values_are_lower_snake_case() -> None:
    for enum_cls in (ResidualKind, ResidualSourceAxis):
        for member in enum_cls:
            assert member.value == member.value.lower()
            assert " " not in member.value
            assert "-" not in member.value
