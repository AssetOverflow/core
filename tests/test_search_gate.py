from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from generate.contract_residuals import ContractResidual, ResidualKind, ResidualSourceAxis
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus, decide_search_gate


def _span(text: str = "test", start: int = 0, end: int = 4, sentence_index: int | None = None) -> SourceSpan:
    return SourceSpan(text=text, start=start, end=end, sentence_index=sentence_index)


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _residual(
    *,
    residual_id: str | None = None,
    candidate_organ: str = "unary_delta_transition",
    family_id: str | None = "state_change.unary_delta",
    residual_kind: ResidualKind = ResidualKind.MISSING_ROLE,
    residual_code: str = "changed_object_unbound",
    source_axis: ResidualSourceAxis = ResidualSourceAxis.ROLE,
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "explanation text",
) -> ContractResidual:
    if residual_id is None:
        payload = {
            "candidate_organ": candidate_organ,
            "residual_kind": residual_kind.value,
            "residual_code": residual_code,
            "evidence_spans": [_span_payload(span) for span in evidence_spans],
        }
        residual_id = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return ContractResidual(
        residual_id=residual_id,
        candidate_organ=candidate_organ,
        family_id=family_id,
        residual_kind=residual_kind,
        residual_code=residual_code,
        source_axis=source_axis,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def test_public_api() -> None:
    import generate.search_gate as sg

    assert tuple(sg.__all__) == (
        "SearchGateStatus",
        "SearchGateDecision",
        "decide_search_gate",
    )


def test_decision_fields_are_diagnostic_only() -> None:
    fields = {field.name for field in dataclasses.fields(SearchGateDecision)}
    assert {"policy_version", "input_digest"}.issubset(fields)
    assert fields.isdisjoint(
        {
            "budget",
            "priority",
            "rank",
            "action",
            "repair",
            "candidate",
            "answer",
            "proof",
            "serving_allowed",
            "mutation",
            "runnable",
            "verdict",
            "search_run",
            "proposal",
            "promotion",
        }
    )


def test_empty_context_is_unassessable_and_replay_stable() -> None:
    first = decide_search_gate(())[0]
    second = decide_search_gate(())[0]

    assert first.status is SearchGateStatus.UNASSESSABLE
    assert first.reason_code == "unassessable_empty_context"
    assert first.candidate_organ is None
    assert first.residual_ids == ()
    assert first.evidence_spans == ()
    assert first.policy_version == "search_gate.v1"
    assert len(first.input_digest) == 64
    assert len(first.decision_id) == 64
    assert first == second


def test_mixed_candidate_organs_fail_closed_with_preserved_spans() -> None:
    r1 = _residual(candidate_organ="organ_a", evidence_spans=(_span("aaa", 0, 3),))
    r2 = _residual(candidate_organ="organ_b", evidence_spans=(_span("bbb", 4, 7),))

    decision = decide_search_gate((r1, r2))[0]
    sorted_residuals = tuple(sorted([r1, r2], key=lambda residual: residual.residual_id))

    assert decision.status is SearchGateStatus.UNASSESSABLE
    assert decision.reason_code == "unassessable_mixed_candidate_organs"
    assert decision.candidate_organ is None
    assert decision.residual_ids == tuple(residual.residual_id for residual in sorted_residuals)
    assert decision.evidence_spans == (
        sorted_residuals[0].evidence_spans + sorted_residuals[1].evidence_spans
    )


def test_context_with_only_eligible_residuals_is_eligible() -> None:
    r1 = _residual(residual_kind=ResidualKind.MISSING_ROLE, residual_code="quantity_unbound")
    r2 = _residual(
        residual_kind=ResidualKind.MISSING_RELATION,
        residual_code="local_binding_relation_unbound",
    )

    decision = decide_search_gate((r1, r2))[0]

    assert decision.status is SearchGateStatus.ELIGIBLE
    assert decision.reason_code == "eligible_missing_relation"
    assert decision.candidate_organ == "unary_delta_transition"


def test_context_with_any_blocker_fails_closed() -> None:
    r1 = _residual(residual_kind=ResidualKind.MISSING_ROLE, residual_code="quantity_unbound")
    r2 = _residual(
        residual_kind=ResidualKind.AMBIGUOUS_ROLE,
        residual_code="quantity_ambiguous",
    )

    decision = decide_search_gate((r1, r2))[0]

    assert decision.status is SearchGateStatus.BLOCKED
    assert decision.reason_code == "blocked_ambiguous_role"


@pytest.mark.parametrize(
    ("kind", "expected_status", "expected_reason"),
    [
        (ResidualKind.MISSING_PROPOSAL, SearchGateStatus.ELIGIBLE, "eligible_missing_proposal"),
        (ResidualKind.MISSING_RELATION, SearchGateStatus.ELIGIBLE, "eligible_missing_relation"),
        (ResidualKind.MISSING_ROLE, SearchGateStatus.ELIGIBLE, "eligible_missing_role"),
        (ResidualKind.TARGET_UNBOUND, SearchGateStatus.ELIGIBLE, "eligible_target_unbound"),
        (ResidualKind.AMBIGUOUS_RELATION, SearchGateStatus.BLOCKED, "blocked_ambiguous_relation"),
        (ResidualKind.AMBIGUOUS_ROLE, SearchGateStatus.BLOCKED, "blocked_ambiguous_role"),
        (ResidualKind.INEXACT_PROVENANCE, SearchGateStatus.BLOCKED, "blocked_inexact_provenance"),
        (ResidualKind.NONLOCAL_BINDING, SearchGateStatus.BLOCKED, "blocked_nonlocal_binding"),
        (ResidualKind.UNSUPPORTED_TOPOLOGY, SearchGateStatus.BLOCKED, "blocked_unsupported_topology"),
        (ResidualKind.UNIT_OBJECT_CONFLICT, SearchGateStatus.BLOCKED, "blocked_unit_object_conflict"),
        (ResidualKind.HAZARD_BLOCKED, SearchGateStatus.BLOCKED, "blocked_hazard"),
        (ResidualKind.CONTRACT_GAP_UNCLASSIFIED, SearchGateStatus.BLOCKED, "blocked_unclassified_gap"),
    ],
)
def test_every_residual_kind_has_explicit_policy(
    kind: ResidualKind,
    expected_status: SearchGateStatus,
    expected_reason: str,
) -> None:
    decision = decide_search_gate((_residual(residual_kind=kind),))[0]

    assert decision.status is expected_status
    assert decision.reason_code == expected_reason


def test_unknown_residual_kind_fails_closed() -> None:
    residual = _residual()
    object.__setattr__(residual, "residual_kind", "UNKNOWN_FUTURE_KIND")

    decision = decide_search_gate((residual,))[0]

    assert decision.status is SearchGateStatus.BLOCKED
    assert decision.reason_code == "blocked_unclassified_gap"


def test_decision_and_input_digest_are_deterministic() -> None:
    r1 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("aaa", 0, 3), _span("bbb", 5, 8)),
        explanation="explanation A",
    )
    r2 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="entity_unbound",
        evidence_spans=(_span("ccc", 10, 13),),
        explanation="explanation B",
    )

    forward = decide_search_gate((r1, r2))[0]
    backward = decide_search_gate((r2, r1))[0]

    assert forward.decision_id == backward.decision_id
    assert forward.input_digest == backward.input_digest
    assert forward.residual_ids == backward.residual_ids
    assert forward.evidence_spans == backward.evidence_spans

    r1_different_explanation = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("aaa", 0, 3), _span("bbb", 5, 8)),
        explanation="different explanation",
    )
    different_explanation = decide_search_gate((r1_different_explanation, r2))[0]
    assert different_explanation.decision_id == forward.decision_id
    assert different_explanation.input_digest == forward.input_digest

    r1_different_span = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("aaa", 0, 3), _span("bbb", 5, 9)),
        explanation="explanation A",
    )
    different_span = decide_search_gate((r1_different_span, r2))[0]
    assert different_span.decision_id != forward.decision_id
    assert different_span.input_digest != forward.input_digest


def test_duplicate_evidence_spans_are_preserved_per_residual() -> None:
    span = _span("same", 0, 4, 0)
    r1 = _residual(residual_id="a", evidence_spans=(span,))
    r2 = _residual(residual_id="b", residual_code="entity_unbound", evidence_spans=(span,))

    decision = decide_search_gate((r2, r1))[0]

    assert decision.residual_ids == ("a", "b")
    assert decision.evidence_spans == (span, span)


def test_input_digest_uses_complete_context_without_explanation() -> None:
    span = _span("aaa", 0, 3, 0)
    residual = _residual(
        residual_id="residual-a",
        candidate_organ="unary_delta_transition",
        family_id="state_change.unary_delta",
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="changed_object_unbound",
        source_axis=ResidualSourceAxis.ROLE,
        evidence_spans=(span,),
        explanation="excluded explanation",
    )

    decision = decide_search_gate((residual,))[0]
    expected_payload = {
        "residuals": [
            {
                "residual_id": "residual-a",
                "candidate_organ": "unary_delta_transition",
                "family_id": "state_change.unary_delta",
                "residual_kind": "missing_role",
                "residual_code": "changed_object_unbound",
                "source_axis": "role",
                "evidence_spans": [_span_payload(span)],
            }
        ]
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            expected_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    assert decision.input_digest == expected_digest


def test_coupling_guards() -> None:
    path = Path(__file__).parent.parent / "generate" / "search_gate.py"
    tree = ast.parse(path.read_text("utf-8"))

    forbidden_imports = {
        "runtime",
        "serving",
        "workbench",
        "teaching",
        "eval",
        "report",
        "vault",
        "recall",
        "field",
        "algebra",
        "subprocess",
        "socket",
        "random",
        "datetime",
        "time",
    }
    forbidden_calls = {
        "assess_contracts",
        "project_contract_residuals",
        "build_problem_frame",
        "determine",
        "search",
        "repair",
        "serve",
        "store",
        "write",
        "open",
        "write_text",
        "write_bytes",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                parts = name.name.split(".")
                assert not any(
                    part in forbidden_imports for part in parts
                ), f"Forbidden import: {name.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                assert not any(
                    part in forbidden_imports for part in parts
                ), f"Forbidden import: {node.module}"
            for name in node.names:
                assert name.name not in forbidden_calls, (
                    f"Forbidden import of function: {name.name}"
                )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls, (
                    f"Forbidden call: {node.func.id}"
                )
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls, (
                    f"Forbidden call/method: {node.func.attr}"
                )
