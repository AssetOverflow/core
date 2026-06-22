from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generate.compute_budget import (
    COMPUTE_BUDGET_POLICY_VERSION,
    ComputeBudgetDecision,
    ComputeBudgetStatus,
    decide_compute_budget,
    decide_compute_budget_for_gate,
)
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus


def _gate(
    *,
    decision_id: str = "gate-a",
    policy_version: str = "search_gate.v1",
    input_digest: str = "a" * 64,
    status: SearchGateStatus = SearchGateStatus.ELIGIBLE,
    reason_code: str = "eligible_missing_role",
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "gate explanation",
) -> SearchGateDecision:
    return SearchGateDecision(
        decision_id=decision_id,
        policy_version=policy_version,
        input_digest=input_digest,
        residual_ids=("residual-a",),
        candidate_organ="unary_delta_transition",
        status=status,
        reason_code=reason_code,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _canonical_budget_id(decision: ComputeBudgetDecision) -> str:
    payload = {
        "policy_version": decision.policy_version,
        "gate_decision_id": decision.gate_decision_id,
        "gate_policy_version": decision.gate_policy_version,
        "gate_input_digest": decision.gate_input_digest,
        "status": decision.status.value,
        "reason_code": decision.reason_code,
        "max_candidates": decision.max_candidates,
        "max_depth": decision.max_depth,
        "max_steps": decision.max_steps,
        "max_parallelism": decision.max_parallelism,
        "evidence_spans": [
            _span_payload(span) for span in decision.evidence_spans
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assert_zero_limits(decision: ComputeBudgetDecision) -> None:
    assert decision.max_candidates == 0
    assert decision.max_depth == 0
    assert decision.max_steps == 0
    assert decision.max_parallelism == 0
    assert decision.max_wallclock_ms is None


def test_public_api_exports_are_exact() -> None:
    import generate.compute_budget as compute_budget

    assert COMPUTE_BUDGET_POLICY_VERSION == "compute_budget.v1"
    assert tuple(compute_budget.__all__) == (
        "COMPUTE_BUDGET_POLICY_VERSION",
        "ComputeBudgetStatus",
        "ComputeBudgetDecision",
        "decide_compute_budget",
        "decide_compute_budget_for_gate",
    )


def test_batch_is_one_to_one_ordered_and_does_not_aggregate() -> None:
    first_gate = _gate(decision_id="gate-first", input_digest="1" * 64)
    second_gate = _gate(
        decision_id="gate-second",
        input_digest="2" * 64,
        reason_code="eligible_missing_proposal",
    )

    decisions = decide_compute_budget((first_gate, second_gate))

    assert len(decisions) == 2
    assert tuple(decision.gate_decision_id for decision in decisions) == (
        "gate-first",
        "gate-second",
    )
    assert decisions[0].max_candidates == 5
    assert decisions[1].max_candidates == 3
    assert decide_compute_budget(()) == ()


@pytest.mark.parametrize(
    "gate_status",
    (
        SearchGateStatus.BLOCKED,
        SearchGateStatus.INELIGIBLE,
        SearchGateStatus.UNASSESSABLE,
    ),
)
def test_valid_noneligible_gates_receive_blocked_zero_budget(
    gate_status: SearchGateStatus,
) -> None:
    decision = decide_compute_budget_for_gate(
        _gate(status=gate_status, reason_code="any_gate_reason")
    )

    assert decision.status is ComputeBudgetStatus.BUDGET_BLOCKED
    assert decision.reason_code == "budget_blocked_gate_not_eligible"
    _assert_zero_limits(decision)


@pytest.mark.parametrize(
    "malformed_gate",
    (
        SimpleNamespace(
            decision_id="gate-a",
            policy_version="search_gate.v1",
            input_digest="a" * 64,
            status="eligible",
            reason_code="eligible_missing_role",
            evidence_spans=(),
        ),
        SimpleNamespace(
            decision_id="gate-a",
            policy_version="search_gate.v1",
            input_digest="a" * 64,
            reason_code="eligible_missing_role",
            evidence_spans=(),
        ),
    ),
)
def test_unknown_or_missing_status_fails_closed(malformed_gate: object) -> None:
    decision = decide_compute_budget_for_gate(malformed_gate)  # type: ignore[arg-type]

    assert decision.status is ComputeBudgetStatus.BUDGET_UNASSESSABLE
    assert decision.reason_code == "budget_unassessable_unknown_gate_status"
    _assert_zero_limits(decision)


@pytest.mark.parametrize(
    ("reason_code", "expected_reason", "expected_limits"),
    (
        (
            "eligible_missing_role",
            "budget_allowed_missing_role",
            (5, 2, 10, 1),
        ),
        (
            "eligible_missing_relation",
            "budget_allowed_missing_relation",
            (5, 2, 10, 1),
        ),
        (
            "eligible_missing_proposal",
            "budget_allowed_missing_proposal",
            (3, 1, 5, 1),
        ),
        (
            "eligible_target_unbound",
            "budget_allowed_target_unbound",
            (5, 2, 10, 1),
        ),
    ),
)
def test_eligible_reason_code_table_is_closed(
    reason_code: str,
    expected_reason: str,
    expected_limits: tuple[int, int, int, int],
) -> None:
    decision = decide_compute_budget_for_gate(_gate(reason_code=reason_code))

    assert decision.status is ComputeBudgetStatus.BUDGET_ALLOWED
    assert decision.reason_code == expected_reason
    assert (
        decision.max_candidates,
        decision.max_depth,
        decision.max_steps,
        decision.max_parallelism,
    ) == expected_limits
    assert decision.max_wallclock_ms is None


@pytest.mark.parametrize("reason_code", ("eligible_future_reason", [], None))
def test_unknown_eligible_reason_fails_closed(reason_code: object) -> None:
    gate = SimpleNamespace(
        decision_id="gate-a",
        policy_version="search_gate.v1",
        input_digest="a" * 64,
        status=SearchGateStatus.ELIGIBLE,
        reason_code=reason_code,
        evidence_spans=(),
    )
    decision = decide_compute_budget_for_gate(
        gate  # type: ignore[arg-type]
    )

    assert decision.status is ComputeBudgetStatus.BUDGET_UNASSESSABLE
    assert decision.reason_code == "budget_unassessable_unknown_gate_reason"
    _assert_zero_limits(decision)


def test_budget_zero_is_reserved_and_unreachable_in_v1() -> None:
    assert ComputeBudgetStatus.BUDGET_ZERO.value == "budget_zero"

    gates = tuple(
        _gate(status=status, reason_code=reason_code)
        for status, reason_code in (
            (SearchGateStatus.ELIGIBLE, "eligible_missing_role"),
            (SearchGateStatus.ELIGIBLE, "eligible_future_reason"),
            (SearchGateStatus.BLOCKED, "blocked_hazard"),
            (SearchGateStatus.INELIGIBLE, "ineligible_reason"),
            (SearchGateStatus.UNASSESSABLE, "unassessable_reason"),
        )
    )

    assert all(
        decision.status is not ComputeBudgetStatus.BUDGET_ZERO
        for decision in decide_compute_budget(gates)
    )


def test_budget_id_is_canonical_deterministic_and_structurally_sensitive() -> None:
    span = SourceSpan("gained", 4, 10, 0)
    gate = _gate(evidence_spans=(span,))
    first = decide_compute_budget_for_gate(gate)
    second = decide_compute_budget_for_gate(gate)
    changed_digest = decide_compute_budget_for_gate(
        dataclasses.replace(gate, input_digest="b" * 64)
    )
    changed_policy_row = decide_compute_budget_for_gate(
        dataclasses.replace(gate, reason_code="eligible_missing_proposal")
    )

    assert first.budget_id == second.budget_id
    assert first.budget_id == _canonical_budget_id(first)
    assert len(first.budget_id) == 64
    assert first.budget_id == first.budget_id.lower()
    assert changed_digest.budget_id != first.budget_id
    assert changed_policy_row.budget_id != first.budget_id


def test_gate_explanation_and_budget_prose_do_not_participate_in_identity() -> None:
    first = decide_compute_budget_for_gate(_gate(explanation="first prose"))
    second = decide_compute_budget_for_gate(_gate(explanation="second prose"))

    assert first.budget_id == second.budget_id
    assert dataclasses.replace(
        first,
        explanation="localized explanation",
        max_wallclock_ms=999,
    ).budget_id == first.budget_id
    assert first.budget_id == _canonical_budget_id(first)


def test_evidence_spans_preserve_order_duplicates_and_identity() -> None:
    first_span = SourceSpan("same", 0, 4, 0)
    second_span = SourceSpan("other", 5, 10, 0)
    decision = decide_compute_budget_for_gate(
        _gate(evidence_spans=(first_span, second_span, first_span))
    )
    reversed_decision = decide_compute_budget_for_gate(
        _gate(evidence_spans=(second_span, first_span, first_span))
    )

    assert decision.evidence_spans == (first_span, second_span, first_span)
    assert len(decision.evidence_spans) == 3
    assert decision.budget_id != reversed_decision.budget_id


@pytest.mark.parametrize(
    "evidence_spans",
    (
        None,
        [],
        (object(),),
        (SimpleNamespace(text="x", start=0, end=1, sentence_index=0),),
    ),
)
def test_malformed_evidence_spans_fail_closed(evidence_spans: object) -> None:
    malformed_gate = SimpleNamespace(
        decision_id="gate-a",
        policy_version="search_gate.v1",
        input_digest="a" * 64,
        status=SearchGateStatus.ELIGIBLE,
        reason_code="eligible_missing_role",
        evidence_spans=evidence_spans,
    )

    decision = decide_compute_budget_for_gate(malformed_gate)  # type: ignore[arg-type]

    assert decision.status is ComputeBudgetStatus.BUDGET_UNASSESSABLE
    assert decision.reason_code == "budget_unassessable_malformed_evidence_spans"
    assert decision.evidence_spans == ()
    _assert_zero_limits(decision)


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_reason"),
    (
        (
            "decision_id",
            "",
            "budget_unassessable_missing_gate_decision_id",
        ),
        (
            "policy_version",
            " ",
            "budget_unassessable_missing_gate_policy_version",
        ),
        (
            "input_digest",
            None,
            "budget_unassessable_missing_gate_input_digest",
        ),
    ),
)
def test_missing_gate_identity_fields_fail_closed(
    field_name: str,
    field_value: object,
    expected_reason: str,
) -> None:
    values = {
        "decision_id": "gate-a",
        "policy_version": "search_gate.v1",
        "input_digest": "a" * 64,
        "status": SearchGateStatus.ELIGIBLE,
        "reason_code": "eligible_missing_role",
        "evidence_spans": (),
    }
    values[field_name] = field_value

    decision = decide_compute_budget_for_gate(  # type: ignore[arg-type]
        SimpleNamespace(**values)
    )

    assert decision.status is ComputeBudgetStatus.BUDGET_UNASSESSABLE
    assert decision.reason_code == expected_reason
    _assert_zero_limits(decision)


def test_compute_budget_decision_contains_no_authority_fields() -> None:
    forbidden_fields = {
        "candidate",
        "proposal",
        "proof",
        "answer",
        "verdict",
        "repair",
        "action",
        "search",
        "search_run",
        "runtime",
        "serving_allowed",
        "mutation",
        "promotion",
        "rank",
        "priority",
        "score",
        "confidence",
    }

    assert forbidden_fields.isdisjoint(
        {field.name for field in dataclasses.fields(ComputeBudgetDecision)}
    )


def test_module_coupling_and_side_effect_guards() -> None:
    path = Path("generate/compute_budget.py")
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    imported_names: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "hashlib",
        "json",
        "generate.kernel_facts",
        "generate.search_gate",
    }
    assert {
        "decide_search_gate",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
    }.isdisjoint(imported_names)
    assert {
        "decide_search_gate",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
        "repair",
        "serve",
        "store",
        "write",
        "open",
        "write_text",
        "write_bytes",
        "request",
        "urlopen",
        "sleep",
        "time",
        "uuid4",
    }.isdisjoint(calls)
    assert "generate.search_gate" in source
    assert "compute_budget" not in Path("generate/search_gate.py").read_text()
    assert "compute_budget" not in Path(
        "generate/contract_residuals.py"
    ).read_text()


def test_no_filesystem_network_clock_random_or_environment_identity() -> None:
    source = Path("generate/compute_budget.py").read_text("utf-8")
    forbidden_fragments = (
        "import os",
        "from os",
        "import pathlib",
        "from pathlib",
        "import random",
        "from random",
        "import time",
        "from time",
        "import datetime",
        "from datetime",
        "import uuid",
        "from uuid",
        "import socket",
        "from socket",
        "import subprocess",
        "from subprocess",
        "import requests",
        "from requests",
        "os.environ",
        "getenv(",
        "gethostname(",
        "Path(",
    )

    assert not any(fragment in source for fragment in forbidden_fragments)
