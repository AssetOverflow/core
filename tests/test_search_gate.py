from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from generate.contract_residuals import (
    ContractResidual,
    ResidualKind,
    ResidualSourceAxis,
)
from generate.kernel_facts import SourceSpan
from generate.search_gate import (
    SearchGateDecision,
    SearchGateStatus,
    decide_search_gate,
)


def _span(
    text: str = "test",
    start: int = 0,
    end: int = 4,
    sentence_index: int | None = None,
) -> SourceSpan:
    return SourceSpan(
        text=text,
        start=start,
        end=end,
        sentence_index=sentence_index,
    )


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
        # Generate a deterministic ID based on fields
        payload = {
            "candidate_organ": candidate_organ,
            "residual_kind": residual_kind.value,
            "residual_code": residual_code,
            "evidence_spans": [
                {
                    "text": s.text,
                    "start": s.start,
                    "end": s.end,
                    "sentence_index": s.sentence_index,
                }
                for s in evidence_spans
            ],
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        residual_id = hashlib.sha256(encoded).hexdigest()

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

    assert hasattr(sg, "__all__")
    assert sorted(sg.__all__) == sorted(
        [
            "SearchGateStatus",
            "SearchGateDecision",
            "decide_search_gate",
        ]
    )


def test_non_authority_fields() -> None:
    fields = {f.name for f in dataclasses.fields(SearchGateDecision)}
    forbidden = {
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
    intersection = fields.intersection(forbidden)
    assert not intersection, f"Forbidden authority/action fields found: {intersection}"


def test_empty_context() -> None:
    decisions = decide_search_gate(())
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.status is SearchGateStatus.UNASSESSABLE
    assert dec.reason_code == "unassessable_empty_context"
    assert dec.candidate_organ is None
    assert dec.residual_ids == ()
    assert dec.evidence_spans == ()
    assert dec.explanation == "Empty residual context."

    # Verify ID is deterministic
    decisions2 = decide_search_gate(())
    assert decisions[0].decision_id == decisions2[0].decision_id


def test_mixed_candidate_organs() -> None:
    r1 = _residual(
        candidate_organ="organ_a",
        residual_kind=ResidualKind.MISSING_ROLE,
        evidence_spans=(_span("aaa", 0, 3),),
    )
    r2 = _residual(
        candidate_organ="organ_b",
        residual_kind=ResidualKind.MISSING_ROLE,
        evidence_spans=(_span("bbb", 4, 7),),
    )
    decisions = decide_search_gate((r1, r2))
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.status is SearchGateStatus.UNASSESSABLE
    assert dec.reason_code == "unassessable_mixed_candidate_organs"
    assert dec.candidate_organ is None
    assert dec.residual_ids == tuple(sorted([r1.residual_id, r2.residual_id]))
    # Sorted by residual ID, spans preserved
    expected_spans = tuple(
        sorted([r1, r2], key=lambda r: r.residual_id)
    )[0].evidence_spans + tuple(
        sorted([r1, r2], key=lambda r: r.residual_id)
    )[1].evidence_spans
    assert dec.evidence_spans == expected_spans


def test_all_eligible_prioritization() -> None:
    # missing_relation has higher priority (2) than missing_role (3)
    r1 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
    )
    r2 = _residual(
        residual_kind=ResidualKind.MISSING_RELATION,
        residual_code="local_binding_relation_unbound",
    )
    decisions = decide_search_gate((r1, r2))
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.status is SearchGateStatus.ELIGIBLE
    assert dec.reason_code == "eligible_missing_relation"
    assert dec.candidate_organ == "unary_delta_transition"


def test_mixed_blocker_fails_closed() -> None:
    r1 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
    )
    r2 = _residual(
        residual_kind=ResidualKind.AMBIGUOUS_ROLE,
        residual_code="quantity_ambiguous",
    )
    decisions = decide_search_gate((r1, r2))
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.status is SearchGateStatus.BLOCKED
    assert dec.reason_code == "blocked_ambiguous_role"


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
def test_residual_kind_mapping(
    kind: ResidualKind,
    expected_status: SearchGateStatus,
    expected_reason: str,
) -> None:
    r = _residual(residual_kind=kind)
    decisions = decide_search_gate((r,))
    assert len(decisions) == 1
    assert decisions[0].status is expected_status
    assert decisions[0].reason_code == expected_reason


def test_unknown_residual_kind_fails_closed() -> None:
    # Create a residual with a mocked residual_kind that is not in the Enum/dict
    r = _residual()
    object.__setattr__(r, "residual_kind", "UNKNOWN_FUTURE_KIND")
    decisions = decide_search_gate((r,))
    assert len(decisions) == 1
    assert decisions[0].status is SearchGateStatus.INELIGIBLE
    assert decisions[0].reason_code == "blocked_unclassified_gap"


def test_determinism_and_hashing() -> None:
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

    decisions_forward = decide_search_gate((r1, r2))
    decisions_backward = decide_search_gate((r2, r1))

    # Same decisions, same IDs, regardless of input order
    assert decisions_forward[0].decision_id == decisions_backward[0].decision_id
    assert decisions_forward[0].residual_ids == decisions_backward[0].residual_ids
    assert decisions_forward[0].evidence_spans == decisions_backward[0].evidence_spans

    # Hashing vector verification: changing explanation does not change ID
    r1_diff_exp = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("aaa", 0, 3), _span("bbb", 5, 8)),
        explanation="explanation DIFFERENT",
    )
    decisions_diff_exp = decide_search_gate((r1_diff_exp, r2))
    assert decisions_diff_exp[0].decision_id == decisions_forward[0].decision_id

    # Changing span details does change ID
    r1_diff_span = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("aaa", 0, 3), _span("bbb", 5, 9)),  # end=9 instead of 8
        explanation="explanation A",
    )
    decisions_diff_span = decide_search_gate((r1_diff_span, r2))
    assert decisions_diff_span[0].decision_id != decisions_forward[0].decision_id

    # Changing span order changes ID
    r1_diff_span_order = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="quantity_unbound",
        evidence_spans=(_span("bbb", 5, 8), _span("aaa", 0, 3)),  # reversed spans
        explanation="explanation A",
    )
    decisions_diff_span_order = decide_search_gate((r1_diff_span_order, r2))
    assert decisions_diff_span_order[0].decision_id != decisions_forward[0].decision_id


def test_span_preservation() -> None:
    span_a = _span("aaa", 0, 3)
    span_b = _span("bbb", 5, 8)
    r1 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        evidence_spans=(span_a,),
    )
    r2 = _residual(
        residual_kind=ResidualKind.MISSING_ROLE,
        evidence_spans=(span_b,),
    )

    decisions = decide_search_gate((r1, r2))
    assert len(decisions) == 1
    # Check that spans are exactly equal to source spans, in deterministic residual ID order
    sorted_res = sorted([r1, r2], key=lambda r: r.residual_id)
    expected_spans = tuple(sorted_res[0].evidence_spans) + tuple(sorted_res[1].evidence_spans)
    assert decisions[0].evidence_spans == expected_spans
    assert not any(s.text == "" for s in decisions[0].evidence_spans)  # No synthetic empty span


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
        "urllib",
        "requests",
        "http",
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
                    p in forbidden_imports for p in parts
                ), f"Forbidden import: {name.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                assert not any(
                    p in forbidden_imports for p in parts
                ), f"Forbidden import: {node.module}"
            for name in node.names:
                assert (
                    name.name not in forbidden_calls
                ), f"Forbidden import of function: {name.name}"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert (
                    node.func.id not in forbidden_calls
                ), f"Forbidden call: {node.func.id}"
            elif isinstance(node.func, ast.Attribute):
                assert (
                    node.func.attr not in forbidden_calls
                ), f"Forbidden call/method: {node.func.attr}"
