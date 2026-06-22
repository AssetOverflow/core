from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.geometric_search_run import (
    GEOMETRIC_SEARCH_RUN_POLICY_VERSION,
    GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION,
    BudgetCharge,
    BudgetConsumed,
    CandidateAttempt,
    CandidateReplayStatus,
    GeometricSearchRun,
    RunExhaustionCode,
    SearchRunDisposition,
    SearchRunRefusal,
    initialize_geometric_search_run,
)
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _gate(
    *,
    input_digest: str = "a" * 64,
    residual_ids: tuple[str, ...] = ("residual-a",),
    status: SearchGateStatus = SearchGateStatus.ELIGIBLE,
    reason_code: str = "eligible_missing_role",
    policy_version: str = "search_gate.v1",
    candidate_organ: str | None = "unary_delta_transition",
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "gate prose",
) -> SearchGateDecision:
    payload = {
        "policy_version": policy_version,
        "input_digest": input_digest,
        "residual_ids": list(residual_ids),
        "candidate_organ": candidate_organ,
        "status": status.value,
        "reason_code": reason_code,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    return SearchGateDecision(
        decision_id=_digest(payload),
        policy_version=policy_version,
        input_digest=input_digest,
        residual_ids=residual_ids,
        candidate_organ=candidate_organ,
        status=status,
        reason_code=reason_code,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def _budget(
    gate: SearchGateDecision,
    *,
    status: ComputeBudgetStatus = ComputeBudgetStatus.BUDGET_ALLOWED,
    reason_code: str = "budget_allowed_missing_role",
    policy_version: str = "compute_budget.v1",
    max_candidates: int = 5,
    max_depth: int = 2,
    max_steps: int = 10,
    max_parallelism: int = 1,
    evidence_spans: tuple[SourceSpan, ...] | None = None,
    explanation: str = "budget prose",
) -> ComputeBudgetDecision:
    spans = gate.evidence_spans if evidence_spans is None else evidence_spans
    payload = {
        "policy_version": policy_version,
        "gate_decision_id": gate.decision_id,
        "gate_policy_version": gate.policy_version,
        "gate_input_digest": gate.input_digest,
        "status": status.value,
        "reason_code": reason_code,
        "max_candidates": max_candidates,
        "max_depth": max_depth,
        "max_steps": max_steps,
        "max_parallelism": max_parallelism,
        "evidence_spans": [_span_payload(span) for span in spans],
    }
    return ComputeBudgetDecision(
        budget_id=_digest(payload),
        policy_version=policy_version,
        gate_decision_id=gate.decision_id,
        gate_policy_version=gate.policy_version,
        gate_input_digest=gate.input_digest,
        status=status,
        reason_code=reason_code,
        max_candidates=max_candidates,
        max_depth=max_depth,
        max_steps=max_steps,
        max_wallclock_ms=None,
        max_parallelism=max_parallelism,
        evidence_spans=spans,
        explanation=explanation,
    )


def _initialize(
    *,
    gate: SearchGateDecision | None = None,
    budget: ComputeBudgetDecision | None = None,
    **changes: object,
) -> GeometricSearchRun | SearchRunRefusal:
    selected_gate = gate or _gate()
    selected_budget = budget or _budget(selected_gate)
    values: dict[str, object] = {
        "problem_frame_digest": "f" * 64,
        "contract_assessment_id": "assessment-a",
        "residual_ids": selected_gate.residual_ids,
        "gate_decision": selected_gate,
        "compute_budget": selected_budget,
        "operator_set_id": "operator-set-empty",
        "operator_set_version": "operators.v1",
    }
    values.update(changes)
    return initialize_geometric_search_run(**values)  # type: ignore[arg-type]


def _assert_refusal(
    outcome: object, disposition: SearchRunDisposition
) -> SearchRunRefusal:
    assert isinstance(outcome, SearchRunRefusal)
    assert outcome.run_disposition is disposition
    assert not hasattr(outcome, "candidate_attempts")
    assert not hasattr(outcome, "budget_consumed")
    return outcome


def test_public_api_exports_are_exact_and_inert() -> None:
    import generate.geometric_search_run as search_run

    assert GEOMETRIC_SEARCH_RUN_POLICY_VERSION == "geometric_search_run.v1"
    assert GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION == "geometric_search_run.schema.v1"
    assert tuple(search_run.__all__) == (
        "GEOMETRIC_SEARCH_RUN_POLICY_VERSION",
        "GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION",
        "SearchRunDisposition",
        "RunDisposition",
        "RunExhaustionCode",
        "CandidateReplayStatus",
        "ReplayStatus",
        "BudgetCharge",
        "BudgetConsumed",
        "CandidateAttempt",
        "SearchRunRefusal",
        "GeometricSearchRun",
        "SearchRunOutcome",
        "initialize_geometric_search_run",
    )


def test_valid_allowed_budget_produces_inert_operator_exhaustion() -> None:
    outcome = _initialize()

    assert isinstance(outcome, GeometricSearchRun)
    assert outcome.candidate_attempts == ()
    assert outcome.run_disposition is SearchRunDisposition.EXHAUSTED_NO_CANDIDATE
    assert outcome.exhaustion_code is RunExhaustionCode.OPERATOR_SET_EMPTY
    assert outcome.budget_consumed == BudgetConsumed(
        candidates_considered=0,
        max_candidates=5,
        depth_reached=0,
        max_depth=2,
        steps_used=0,
        max_steps=10,
        parallelism_used=0,
        max_parallelism=1,
        exhausted=False,
    )


@pytest.mark.parametrize(
    "status",
    (
        ComputeBudgetStatus.BUDGET_BLOCKED,
        ComputeBudgetStatus.BUDGET_ZERO,
        ComputeBudgetStatus.BUDGET_UNASSESSABLE,
    ),
)
def test_blocked_budget_statuses_refuse_without_a_run(
    status: ComputeBudgetStatus,
) -> None:
    gate = _gate()
    budget = _budget(
        gate,
        status=status,
        reason_code=f"{status.value}_reason",
        max_candidates=0,
        max_depth=0,
        max_steps=0,
        max_parallelism=0,
    )

    outcome = _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.BLOCKED_BY_BUDGET,
    )
    assert outcome.reason_codes == ("budget_not_allowed",)


@pytest.mark.parametrize(
    "status",
    (
        SearchGateStatus.BLOCKED,
        SearchGateStatus.INELIGIBLE,
        SearchGateStatus.UNASSESSABLE,
    ),
)
def test_noneligible_gates_refuse_before_budget(
    status: SearchGateStatus,
) -> None:
    gate = _gate(status=status, reason_code=f"{status.value}_reason")
    budget = _budget(
        gate,
        status=ComputeBudgetStatus.BUDGET_BLOCKED,
        reason_code="budget_blocked_gate_not_eligible",
        max_candidates=0,
        max_depth=0,
        max_steps=0,
        max_parallelism=0,
    )

    _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.BLOCKED_BY_GATE,
    )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("gate_decision_id", "0" * 64),
        ("gate_policy_version", "search_gate.future"),
        ("gate_input_digest", "b" * 64),
    ),
)
def test_gate_budget_identity_mismatch_is_invalid(
    field_name: str, replacement: str
) -> None:
    gate = _gate()
    budget = dataclasses.replace(_budget(gate), **{field_name: replacement})

    _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.INVALID_INPUT,
    )


def test_residual_sequence_mismatch_is_invalid() -> None:
    _assert_refusal(
        _initialize(residual_ids=("residual-other",)),
        SearchRunDisposition.INVALID_INPUT,
    )


@pytest.mark.parametrize(
    ("target", "version_field", "version"),
    (
        ("gate", "policy_version", "search_gate.future"),
        ("budget", "policy_version", "compute_budget.future"),
        ("run", "run_policy_version", "geometric_search_run.future"),
        ("run", "schema_version", "geometric_search_run.schema.future"),
    ),
)
def test_unsupported_versions_fail_closed(
    target: str, version_field: str, version: str
) -> None:
    gate = _gate()
    budget = _budget(gate)
    changes: dict[str, object] = {}
    if target == "gate":
        gate = dataclasses.replace(gate, **{version_field: version})
    elif target == "budget":
        budget = dataclasses.replace(budget, **{version_field: version})
    else:
        changes[version_field] = version

    _assert_refusal(
        _initialize(gate=gate, budget=budget, **changes),
        SearchRunDisposition.INVALID_INPUT,
    )


@pytest.mark.parametrize(
    "field_name",
    ("max_candidates", "max_depth", "max_steps", "max_parallelism"),
)
def test_negative_structural_limits_fail_closed(field_name: str) -> None:
    gate = _gate()
    values = {
        "max_candidates": 5,
        "max_depth": 2,
        "max_steps": 10,
        "max_parallelism": 1,
    }
    values[field_name] = -1
    budget = _budget(gate, **values)

    _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.INVALID_INPUT,
    )


@pytest.mark.parametrize("parallelism", (0, 2))
def test_allowed_budget_requires_serial_v1_parallelism(parallelism: int) -> None:
    gate = _gate()
    budget = _budget(gate, max_parallelism=parallelism)

    _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.INVALID_INPUT,
    )


@pytest.mark.parametrize("field_name", ("max_candidates", "max_steps"))
def test_allowed_budget_requires_positive_work_ceilings(field_name: str) -> None:
    gate = _gate()
    values = {field_name: 0}
    budget = _budget(gate, **values)

    _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.INVALID_INPUT,
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("problem_frame_digest", ""),
        ("contract_assessment_id", ""),
        ("operator_set_id", ""),
        ("operator_set_version", ""),
    ),
)
def test_missing_run_identity_fails_closed(field_name: str, value: str) -> None:
    _assert_refusal(
        _initialize(**{field_name: value}),
        SearchRunDisposition.INVALID_INPUT,
    )


def test_missing_upstream_ids_fail_closed_without_throwing() -> None:
    gate = dataclasses.replace(_gate(), decision_id="")
    budget = dataclasses.replace(_budget(_gate()), budget_id="")

    _assert_refusal(
        _initialize(gate=gate), SearchRunDisposition.INVALID_INPUT
    )
    _assert_refusal(
        _initialize(budget=budget), SearchRunDisposition.INVALID_INPUT
    )


def test_ordinary_malformed_objects_fail_closed_without_throwing() -> None:
    outcome = initialize_geometric_search_run(  # type: ignore[arg-type]
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=("residual-a",),
        gate_decision=SimpleNamespace(),
        compute_budget=SimpleNamespace(),
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
    )

    _assert_refusal(outcome, SearchRunDisposition.INVALID_INPUT)


def test_input_and_run_ids_are_canonical_and_structurally_sensitive() -> None:
    first = _initialize()
    second = _initialize()
    changed_frame = _initialize(problem_frame_digest="e" * 64)
    changed_gate = _gate(input_digest="b" * 64)
    changed_budget = _budget(changed_gate)
    changed_upstream = _initialize(gate=changed_gate, budget=changed_budget)
    gate = _gate()
    changed_budget_identity = _initialize(
        gate=gate,
        budget=_budget(gate, max_depth=3),
    )
    changed_operator = _initialize(operator_set_version="operators.v2")

    assert isinstance(first, GeometricSearchRun)
    assert isinstance(second, GeometricSearchRun)
    assert isinstance(changed_frame, GeometricSearchRun)
    assert isinstance(changed_upstream, GeometricSearchRun)
    assert isinstance(changed_budget_identity, GeometricSearchRun)
    assert isinstance(changed_operator, GeometricSearchRun)
    assert first.run_id == second.run_id
    assert first.input_digest == second.input_digest
    assert changed_frame.run_id != first.run_id
    assert changed_frame.input_digest != first.input_digest
    assert changed_upstream.run_id != first.run_id
    assert changed_upstream.input_digest != first.input_digest
    assert changed_budget_identity.budget_id != first.budget_id
    assert changed_budget_identity.run_id != first.run_id
    assert changed_budget_identity.input_digest != first.input_digest
    assert changed_operator.run_id != first.run_id
    assert changed_operator.input_digest != first.input_digest

    expected_input = {
        "problem_frame_digest": first.problem_frame_digest,
        "contract_assessment_id": first.contract_assessment_id,
        "residual_ids": list(first.residual_ids),
        "gate_decision_id": first.gate_decision_id,
        "gate_policy_version": "search_gate.v1",
        "gate_input_digest": "a" * 64,
        "budget_id": first.budget_id,
        "budget_policy_version": "compute_budget.v1",
        "operator_set_id": first.operator_set_id,
        "operator_set_version": first.operator_set_version,
        "run_policy_version": first.run_policy_version,
        "schema_version": first.schema_version,
    }
    assert first.input_digest == _digest(expected_input)

    expected_run = {
        "run_id": "",
        "run_policy_version": first.run_policy_version,
        "schema_version": first.schema_version,
        "problem_frame_digest": first.problem_frame_digest,
        "contract_assessment_id": first.contract_assessment_id,
        "residual_ids": list(first.residual_ids),
        "gate_decision_id": first.gate_decision_id,
        "budget_id": first.budget_id,
        "operator_set_id": first.operator_set_id,
        "operator_set_version": first.operator_set_version,
        "input_digest": first.input_digest,
        "candidate_attempts": [],
        "budget_consumed": dataclasses.asdict(first.budget_consumed),
        "run_disposition": first.run_disposition.value,
        "exhaustion_code": first.exhaustion_code.value,
    }
    assert first.run_id == _digest(expected_run)
    assert _digest(
        {
            **expected_run,
            "run_disposition": SearchRunDisposition.CANDIDATE_REPLAY_PENDING.value,
        }
    ) != first.run_id
    assert dataclasses.replace(first, explanation="different prose").run_id == first.run_id


def test_refusal_identity_excludes_explanation_and_includes_disposition() -> None:
    gate = _gate()
    budget = _budget(
        gate,
        status=ComputeBudgetStatus.BUDGET_BLOCKED,
        reason_code="budget_blocked",
        max_candidates=0,
        max_depth=0,
        max_steps=0,
        max_parallelism=0,
    )
    blocked = _assert_refusal(
        _initialize(gate=gate, budget=budget),
        SearchRunDisposition.BLOCKED_BY_BUDGET,
    )
    changed_prose = dataclasses.replace(blocked, explanation="localized prose")
    changed_disposition = dataclasses.replace(
        blocked, run_disposition=SearchRunDisposition.INVALID_INPUT
    )

    assert changed_prose.outcome_id == blocked.outcome_id
    assert changed_disposition.outcome_id == blocked.outcome_id
    expected = {
        "outcome_id": "",
        "run_policy_version": blocked.run_policy_version,
        "input_digest": blocked.input_digest,
        "gate_decision_id": blocked.gate_decision_id,
        "budget_id": blocked.budget_id,
        "run_disposition": blocked.run_disposition.value,
        "reason_codes": list(blocked.reason_codes),
    }
    assert blocked.outcome_id == _digest(expected)


def test_candidate_attempt_is_diagnostic_only_and_manual() -> None:
    attempt = CandidateAttempt(
        attempt_id="attempt-a",
        attempt_index=0,
        parent_attempt_id=None,
        operator_id="operator-a",
        operator_version="operator.v1",
        input_digest="a" * 64,
        candidate_digest="b" * 64,
        budget_charge=BudgetCharge(candidates=1, steps=1),
        depth=1,
        step_index=0,
        replay_status=CandidateReplayStatus.REPLAY_PENDING,
        replay_blockers=("replay_not_authorized",),
        evidence_spans=(SourceSpan("x", 0, 1, 0),),
        explanation="diagnostic prose",
    )

    assert attempt.replay_status is CandidateReplayStatus.REPLAY_PENDING
    assert isinstance(_initialize(), GeometricSearchRun)
    assert _initialize().candidate_attempts == ()  # type: ignore[union-attr]


def test_public_dataclasses_expose_no_authority_or_ranking_fields() -> None:
    forbidden = {
        "answer",
        "proof",
        "verdict",
        "promotion",
        "mutation",
        "serving_allowed",
        "runnable",
        "truth",
        "score",
        "confidence",
        "rank",
        "priority",
        "repair",
        "action",
        "runtime",
        "serve",
        "tool_call",
    }

    for record_type in (
        BudgetCharge,
        BudgetConsumed,
        CandidateAttempt,
        SearchRunRefusal,
        GeometricSearchRun,
    ):
        assert forbidden.isdisjoint(
            {field.name for field in dataclasses.fields(record_type)}
        )


def test_module_coupling_and_side_effect_guards() -> None:
    path = Path("generate/geometric_search_run.py")
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
        "generate.compute_budget",
        "generate.kernel_facts",
        "generate.search_gate",
    }
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "decide_compute_budget_for_gate",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
    }.isdisjoint(imported_names)
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "decide_compute_budget_for_gate",
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
    assert "generate.compute_budget" in source
    assert "generate.search_gate" in source
    for upstream in (
        "generate/compute_budget.py",
        "generate/search_gate.py",
        "generate/contract_residuals.py",
    ):
        assert "geometric_search_run" not in Path(upstream).read_text("utf-8")


def test_no_filesystem_network_clock_random_or_environment_identity() -> None:
    source = Path("generate/geometric_search_run.py").read_text("utf-8")
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
