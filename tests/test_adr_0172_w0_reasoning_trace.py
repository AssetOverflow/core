"""ADR-0172 W0 — ``ReasoningTrace`` substrate tests."""

from __future__ import annotations

import pytest

from teaching.math_reasoning_trace import (
    ReasoningStep,
    build_trace,
    canonical_bytes,
    compute_trace_id,
)


def _step(
    *,
    index: int = 0,
    kind: str = "observation",
    pointers: tuple[str, ...] = (),
    claim: str = "claim",
    justification: str = "because",
    payload: object | None = None,
) -> ReasoningStep:
    return ReasoningStep(
        step_index=index,
        step_kind=kind,  # type: ignore[arg-type]
        input_pointers=pointers,
        claim=claim,
        justification=justification,
        output_payload={} if payload is None else payload,
    )


def test_step_index_must_start_at_zero() -> None:
    with pytest.raises(ValueError, match="step_index"):
        build_trace([_step(index=1)])


def test_step_index_must_be_monotonic() -> None:
    with pytest.raises(ValueError, match="step_index"):
        build_trace([_step(index=0), _step(index=2, kind="grouping")])


def test_canonical_bytes_stable_across_runs() -> None:
    steps_a = [
        _step(index=0, kind="observation", payload={"n": 3}),
        _step(index=1, kind="grouping", payload={"key": ["a", "b"]}),
    ]
    steps_b = [
        _step(index=0, kind="observation", payload={"n": 3}),
        _step(index=1, kind="grouping", payload={"key": ["a", "b"]}),
    ]
    trace_a = build_trace(steps_a)
    trace_b = build_trace(steps_b)
    assert canonical_bytes(trace_a) == canonical_bytes(trace_b)
    assert trace_a.trace_id == trace_b.trace_id


def test_trace_id_changes_when_claim_changes() -> None:
    base = build_trace([_step(claim="alpha")])
    other = build_trace([_step(claim="beta")])
    assert base.trace_id != other.trace_id


def test_trace_id_invariant_to_dict_insertion_order() -> None:
    payload_in_order = {"alpha": 1, "beta": 2, "gamma": 3}
    payload_out_of_order = {"gamma": 3, "alpha": 1, "beta": 2}
    trace_a = build_trace([_step(payload=payload_in_order)])
    trace_b = build_trace([_step(payload=payload_out_of_order)])
    assert trace_a.trace_id == trace_b.trace_id


def test_non_json_serializable_payload_rejected() -> None:
    with pytest.raises(ValueError, match="JSON-serializable"):
        build_trace([_step(payload={"bad": {1, 2, 3}})])


def test_all_eight_step_kinds_accepted() -> None:
    kinds = (
        "observation",
        "grouping",
        "abstraction",
        "hypothesis",
        "test_design",
        "test_application",
        "test_result",
        "conclusion",
    )
    steps = [_step(index=i, kind=kind) for i, kind in enumerate(kinds)]
    trace = build_trace(steps)
    assert tuple(s.step_kind for s in trace.steps) == kinds


def test_empty_trace_rejected() -> None:
    with pytest.raises(ValueError, match="at least one step"):
        build_trace([])


def test_unknown_step_kind_rejected() -> None:
    bad = ReasoningStep(
        step_index=0,
        step_kind="speculation",  # type: ignore[arg-type]
        input_pointers=(),
        claim="c",
        justification="j",
        output_payload={},
    )
    with pytest.raises(ValueError, match="unknown step_kind"):
        build_trace([bad])


def test_float_payload_rejected() -> None:
    with pytest.raises(ValueError, match="floating-point"):
        build_trace([_step(payload={"weight": 0.5})])


def test_compute_trace_id_matches_build_trace() -> None:
    steps = (_step(index=0, claim="x"),)
    assert compute_trace_id(steps) == build_trace(list(steps)).trace_id


def test_trace_is_frozen() -> None:
    trace = build_trace([_step()])
    with pytest.raises(Exception):  # FrozenInstanceError subclass of AttributeError
        trace.trace_id = "mutated"  # type: ignore[misc]
