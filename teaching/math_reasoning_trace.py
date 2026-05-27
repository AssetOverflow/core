"""ADR-0172 W0 — ``ReasoningTrace`` substrate.

Schema-only module. Defines the byte-identical, replay-equivalent
reasoning trace carried by ``MathReaderRefusalShapeProposal`` (W1)
and emitted by the audit-corpus decomposer (W2).

Determinism contract:
- Canonical bytes are stable across processes and dict insertion order.
- ``trace_id`` is ``sha256(canonical_bytes)`` of the full step sequence.
- Floating-point values are forbidden in payloads (would break replay).

No runtime hook. No import from ``chat``/``field``/``generate``/``algebra``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, get_args

__all__ = (
    "ReasoningStep",
    "ReasoningTrace",
    "StepKind",
    "build_trace",
    "canonical_bytes",
    "compute_trace_id",
)


StepKind = Literal[
    "observation",
    "grouping",
    "abstraction",
    "hypothesis",
    "test_design",
    "test_application",
    "test_result",
    "conclusion",
]

_STEP_KINDS: frozenset[str] = frozenset(get_args(StepKind))


@dataclass(frozen=True)
class ReasoningStep:
    step_index: int
    step_kind: StepKind
    input_pointers: tuple[str, ...]
    claim: str
    justification: str
    output_payload: object


@dataclass(frozen=True)
class ReasoningTrace:
    trace_id: str
    steps: tuple[ReasoningStep, ...]


def _reject_floats(value: object, *, path: str) -> None:
    """Recursively reject any ``float`` instance in a JSON-shaped value.

    Booleans are a ``bool`` subclass of ``int`` and remain permitted.
    """

    if isinstance(value, float):
        raise ValueError(
            f"floating-point values are forbidden in canonical payloads (at {path})"
        )
    if isinstance(value, dict):
        for key, sub in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"payload dict keys must be strings (at {path}, got {type(key).__name__})"
                )
            _reject_floats(sub, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for idx, sub in enumerate(value):
            _reject_floats(sub, path=f"{path}[{idx}]")


def _validate_payload(payload: object) -> None:
    """Ensure payload is JSON-serializable and float-free."""

    try:
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"output_payload is not JSON-serializable: {exc}") from exc
    _reject_floats(payload, path="output_payload")


def _step_to_canonical(step: ReasoningStep) -> dict[str, object]:
    return {
        "step_index": step.step_index,
        "step_kind": step.step_kind,
        "input_pointers": list(step.input_pointers),
        "claim": step.claim,
        "justification": step.justification,
        "output_payload": step.output_payload,
    }


def _steps_canonical_bytes(steps: tuple[ReasoningStep, ...]) -> bytes:
    payload = [_step_to_canonical(step) for step in steps]
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_bytes(trace: ReasoningTrace) -> bytes:
    """Return the canonical byte serialization of a trace.

    The ``trace_id`` field itself is excluded (it is derived from these
    very bytes). Stable across processes and dict insertion order.
    """

    return _steps_canonical_bytes(trace.steps)


def compute_trace_id(steps: tuple[ReasoningStep, ...]) -> str:
    """Return ``sha256(canonical_bytes(steps))`` as hex digest."""

    return hashlib.sha256(_steps_canonical_bytes(steps)).hexdigest()


def build_trace(steps: list[ReasoningStep] | tuple[ReasoningStep, ...]) -> ReasoningTrace:
    """Validate, freeze, and hash a reasoning trace.

    Raises ``ValueError`` on:
    - empty step list
    - ``step_kind`` outside the ``StepKind`` Literal
    - ``step_index`` not starting at 0 with monotonic +1 increments
    - non-JSON-serializable payload
    - any floating-point value inside a payload (replay hazard)
    """

    frozen = tuple(steps)
    if not frozen:
        raise ValueError("reasoning trace must contain at least one step")

    for expected_index, step in enumerate(frozen):
        if step.step_kind not in _STEP_KINDS:
            raise ValueError(
                f"step {expected_index}: unknown step_kind {step.step_kind!r}"
            )
        if step.step_index != expected_index:
            raise ValueError(
                "step_index must start at 0 and increase monotonically by 1 "
                f"(step {expected_index} has step_index={step.step_index})"
            )
        if not isinstance(step.input_pointers, tuple):
            raise ValueError(
                f"step {expected_index}: input_pointers must be a tuple"
            )
        for pointer in step.input_pointers:
            if not isinstance(pointer, str):
                raise ValueError(
                    f"step {expected_index}: input_pointers must contain strings only"
                )
        _validate_payload(step.output_payload)

    trace_id = compute_trace_id(frozen)
    return ReasoningTrace(trace_id=trace_id, steps=frozen)
