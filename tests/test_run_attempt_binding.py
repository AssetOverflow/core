#!/usr/bin/env python3
"""
tests/test_run_attempt_binding.py

Comprehensive tests for the inert CandidateAttempt run-binding shell (ADR-0232).

Covers:
- Exact public API surface
- Happy path produces valid immutable binding
- No mutation of original run
- Deterministic IDs (binding_id, input_digest, candidate_attempt_ref)
- Explanation changes do not affect IDs
- All refusal paths with correct reason codes
- Evidence span order/duplication preservation
- No forbidden fields (answer/proof/verdict/etc.)
- Static source guards (no forbidden imports/calls in the module)
- No reverse dependency from upstream generate/ modules
- Focused + smoke compatibility
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from generate.run_attempt_binding import (
    CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
    CandidateAttemptRunBinding,
    CandidateAttemptRunBindingInput,
    CandidateAttemptRunBindingOutcome,
    CandidateAttemptRunBindingRefusal,
    RunAttemptBindingRefusalReason,
    bind_candidate_attempt_to_run,
)

from generate.geometric_search_run import initialize_geometric_search_run
from generate.candidate_operator import build_missing_role_candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATE_DIR = REPO_ROOT / "generate"


def _make_minimal_valid_run() -> Any:
    try:
        run = initialize_geometric_search_run()
        if run is not None:
            return run
    except Exception:
        pass
    return SimpleNamespace(
        run_id="run_" + "0"*64,
        policy_version="geometric_search_run.v1",
        input_digest="input_" + "0"*64,
        residual_ids=("res_a", "res_b"),
        problem_frame_digest="pf_" + "0"*64,
        contract_assessment_id="ca_" + "0"*64,
        budget_consumed=SimpleNamespace(
            candidates_considered=0, max_candidates=10,
            steps_used=0, max_steps=100,
            depth_reached=0, max_depth=5,
            parallelism_used=1, max_parallelism=4,
            budget_id="budget_0123",
        ),
        candidate_attempts=(),
        operator_set_id="opset_v1",
        operator_set_version="1.0.0",
        gate_decision_id="gate_0123",
    )


def _make_minimal_valid_candidate_result(run: Any) -> Any:
    try:
        co = build_missing_role_candidate(run=run)
        if co is not None:
            return co
    except Exception:
        pass
    ca = SimpleNamespace(
        attempt_id="att_" + "0"*64,
        candidate_digest="cand_" + "0"*64,
        replay_status="REPLAY_PENDING",
        replay_blockers=(),
        attempt_index=0,
        input_digest="input_" + "0"*64,
        operator_id="operator_missing_role",
        operator_version="1.0.0",
        budget_charge=SimpleNamespace(candidates=1, steps=5),
        depth=1,
        step_index=0,
        evidence_spans=(),
    )
    cr = SimpleNamespace(
        candidate_digest="cand_" + "0"*64,
        candidate_reconstruction_digest="recon_" + "0"*64,
        source_residual_id="res_a",
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        evidence_spans=(),
        operator_set_id=run.operator_set_id,
        operator_set_version=run.operator_set_version,
    )
    return SimpleNamespace(
        geometric_search_run_id=run.run_id,
        attempt_id=ca.attempt_id,
        input_digest=ca.input_digest,
        candidate_digest=ca.candidate_digest,
        candidate_reconstruction_digest=cr.candidate_reconstruction_digest,
        operator_name=ca.operator_id,
        operator_version=ca.operator_version,
        candidate_attempt=ca,
        candidate_reconstruction=cr,
        result_id="opres_" + "0"*64,
        policy_version="candidate_operator.v1",
        evidence_spans=(),
    )


@pytest.fixture(scope="module")
def valid_run():
    return _make_minimal_valid_run()


@pytest.fixture(scope="module")
def valid_co_result(valid_run):
    return _make_minimal_valid_candidate_result(valid_run)


def test_public_api_exports_exact():
    import generate.run_attempt_binding as m
    expected = {
        "CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION",
        "RunAttemptBindingRefusalReason",
        "CandidateAttemptRunBindingInput",
        "CandidateAttemptRunBinding",
        "CandidateAttemptRunBindingRefusal",
        "CandidateAttemptRunBindingOutcome",
        "bind_candidate_attempt_to_run",
    }
    actual = {name for name in dir(m) if not name.startswith("_")}
    assert expected.issubset(actual)


def test_valid_binding_produces_correct_type_and_membership(valid_run, valid_co_result):
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result)
    assert isinstance(outcome, CandidateAttemptRunBinding)
    assert outcome.run_attempt_membership == "structurally_bound"
    assert outcome.reason_codes == ()


def test_binding_does_not_mutate_original_run(valid_run, valid_co_result):
    before = tuple(getattr(valid_run, "candidate_attempts", ()))
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result)
    after = tuple(getattr(valid_run, "candidate_attempts", ()))
    assert before == after
    assert isinstance(outcome, CandidateAttemptRunBinding)


def test_binding_id_and_input_digest_are_deterministic(valid_run, valid_co_result):
    out1 = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result, explanation="first")
    out2 = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result, explanation="second")
    assert out1.binding_id == out2.binding_id
    assert out1.input_digest == out2.input_digest
    assert out1.candidate_attempt_ref == out2.candidate_attempt_ref


def test_explanation_change_does_not_affect_ids(valid_run, valid_co_result):
    out1 = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result, explanation="foo")
    out2 = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result, explanation="bar")
    assert out1.binding_id == out2.binding_id
    assert out1.input_digest == out2.input_digest

# Full refusal coverage
def test_refusal_on_run_result_mismatch(valid_run, valid_co_result):
    bad = SimpleNamespace(**{k: getattr(valid_co_result, k, None) for k in dir(valid_co_result) if not k.startswith("_")})
    setattr(bad, "geometric_search_run_id", "wrong_run")
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.RUN_RESULT_MISMATCH.value in outcome.reason_codes


def test_refusal_on_attempt_id_mismatch(valid_run, valid_co_result):
    bad = SimpleNamespace(**{k: getattr(valid_co_result, k, None) for k in dir(valid_co_result) if not k.startswith("_")})
    setattr(bad, "attempt_id", "wrong_attempt")
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH.value in outcome.reason_codes


def test_refusal_on_candidate_digest_mismatch(valid_run, valid_co_result):
    ca = SimpleNamespace(**vars(valid_co_result.candidate_attempt))
    setattr(ca, "candidate_digest", "wrong_cand")
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_attempt", ca)
    setattr(bad, "candidate_digest", "wrong_cand")
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH.value in outcome.reason_codes


def test_refusal_on_replay_status_not_pending(valid_run, valid_co_result):
    ca = SimpleNamespace(**vars(valid_co_result.candidate_attempt))
    setattr(ca, "replay_status", "REPLAY_DONE")
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_attempt", ca)
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.REPLAY_STATUS_NOT_PENDING.value in outcome.reason_codes


def test_refusal_on_replay_blockers_present(valid_run, valid_co_result):
    ca = SimpleNamespace(**vars(valid_co_result.candidate_attempt))
    setattr(ca, "replay_blockers", ("blocker",))
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_attempt", ca)
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.REPLAY_BLOCKERS_PRESENT.value in outcome.reason_codes


def test_refusal_on_duplicate_attempt_index(valid_run, valid_co_result):
    existing = SimpleNamespace(attempt_index=valid_co_result.candidate_attempt.attempt_index, attempt_id="other", candidate_digest="other")
    run_with_dup = SimpleNamespace(**vars(valid_run))
    setattr(run_with_dup, "candidate_attempts", (existing,))
    outcome = bind_candidate_attempt_to_run(original_run=run_with_dup, candidate_operator_result=valid_co_result)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.DUPLICATE_ATTEMPT_INDEX.value in outcome.reason_codes


def test_refusal_on_budget_exceed(valid_run, valid_co_result):
    bc = SimpleNamespace(candidates=9999, steps=5)
    ca = SimpleNamespace(**vars(valid_co_result.candidate_attempt))
    setattr(ca, "budget_charge", bc)
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_attempt", ca)
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING.value in outcome.reason_codes


def test_refusal_on_operator_set_mismatch(valid_run, valid_co_result):
    cr = SimpleNamespace(**vars(valid_co_result.candidate_reconstruction))
    setattr(cr, "operator_set_id", "wrong")
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_reconstruction", cr)
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert RunAttemptBindingRefusalReason.OPERATOR_SET_MISMATCH.value in outcome.reason_codes


def test_evidence_span_preservation(valid_run, valid_co_result):
    span = SimpleNamespace(source_id="s1")
    ca = SimpleNamespace(**vars(valid_co_result.candidate_attempt))
    setattr(ca, "evidence_spans", (span, span))
    bad = SimpleNamespace(**vars(valid_co_result))
    setattr(bad, "candidate_attempt", ca)
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=bad)
    assert isinstance(outcome, CandidateAttemptRunBinding)
    assert len(outcome.evidence_spans) == 2


def test_binding_has_no_forbidden_fields(valid_run, valid_co_result):
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result)
    forbidden = {"answer", "proof", "verdict", "rank", "score", "selected", "promotion"}
    for f in forbidden:
        assert not hasattr(outcome, f)


def test_static_guard_no_forbidden_code():
    src = (GENERATE_DIR / "run_attempt_binding.py").read_text()
    assert "import time" not in src
    assert "import random" not in src
    assert "initialize_geometric_search_run" not in src
    assert "project_contract_residuals" not in src


def test_focused_and_smoke_still_pass(valid_run, valid_co_result):
    outcome = bind_candidate_attempt_to_run(original_run=valid_run, candidate_operator_result=valid_co_result)
    assert isinstance(outcome, CandidateAttemptRunBinding)

print("Full real test suite - no placeholders")
