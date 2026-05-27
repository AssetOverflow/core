"""ADR-0172 W0.1 — Trace replay-equivalence tests.

This test module verifies the determinism, cross-process stability,
and float-free property of canonical ReasoningTrace serialization.
"""

from __future__ import annotations

import os
import re
import sys
import json
import tempfile
import subprocess
import pytest

from teaching.math_reasoning_trace import (
    ReasoningStep,
    ReasoningTrace,
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


def test_build_trace_replay_equivalence_minimal() -> None:
    """Verify that a 2-step trace built 100 times yields identical canonical bytes."""
    ref_bytes: bytes | None = None
    ref_id: str | None = None

    for _ in range(100):
        step0 = _step(index=0, kind="observation", payload={"a": 1})
        step1 = _step(index=1, kind="grouping", payload={"b": [2, 3]})
        trace = build_trace([step0, step1])
        c_bytes = canonical_bytes(trace)

        if ref_bytes is None:
            ref_bytes = c_bytes
            ref_id = trace.trace_id
        else:
            assert c_bytes == ref_bytes
            assert trace.trace_id == ref_id


def test_build_trace_payload_dict_key_order_invariance() -> None:
    """Verify that dict key insertion order variations do not affect trace_id or canonical bytes."""
    payload_a = {"a": 1, "b": 2}
    payload_b = {"b": 2, "a": 1}

    step_a = _step(index=0, payload=payload_a)
    step_b = _step(index=0, payload=payload_b)

    trace_a = build_trace([step_a])
    trace_b = build_trace([step_b])

    assert trace_a.trace_id == trace_b.trace_id
    assert canonical_bytes(trace_a) == canonical_bytes(trace_b)

    # Validate recursive key sorting in nested structures
    nested_a = {"x": {"a": 1, "b": 2}, "y": [3, {"c": 4, "d": 5}]}
    nested_b = {"y": [3, {"d": 5, "c": 4}], "x": {"b": 2, "a": 1}}

    trace_nested_a = build_trace([_step(index=0, payload=nested_a)])
    trace_nested_b = build_trace([_step(index=0, payload=nested_b)])

    assert trace_nested_a.trace_id == trace_nested_b.trace_id
    assert canonical_bytes(trace_nested_a) == canonical_bytes(trace_nested_b)


def test_build_trace_under_process_restart() -> None:
    """Verify determinism across separate Python processes using uv run python -c."""
    step0 = _step(
        index=0,
        kind="observation",
        claim="Initial claim",
        justification="Some explanation",
        payload={"x": 10},
    )
    step1 = _step(
        index=1,
        kind="hypothesis",
        claim="Next claim",
        justification="Another explanation",
        payload={"y": [20, 30]},
    )
    trace = build_trace([step0, step1])
    original_bytes = canonical_bytes(trace)
    original_id = trace.trace_id

    # Write the canonical bytes to a temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(original_bytes)
        temp_path = tmp.name

    try:
        # Re-derive trace in a separate process and compare
        script = f"""
from teaching.math_reasoning_trace import ReasoningStep, build_trace, canonical_bytes
import sys

step0 = ReasoningStep(
    step_index=0,
    step_kind="observation",
    input_pointers=(),
    claim="Initial claim",
    justification="Some explanation",
    output_payload={{"x": 10}}
)
step1 = ReasoningStep(
    step_index=1,
    step_kind="hypothesis",
    input_pointers=(),
    claim="Next claim",
    justification="Another explanation",
    output_payload={{"y": [20, 30]}}
)
trace = build_trace([step0, step1])
new_bytes = canonical_bytes(trace)

with open(r"{temp_path}", "rb") as f:
    old_bytes = f.read()

if new_bytes != old_bytes:
    print("Canonical bytes mismatch across process!", file=sys.stderr)
    sys.exit(1)

if trace.trace_id != "{original_id}":
    print("Trace ID mismatch across process!", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
"""
        cmd = ["uv", "run", "python", "-c", script]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        assert res.returncode == 0, (
            f"Process restart validation failed (code {res.returncode}):\n"
            f"stdout: {res.stdout}\n"
            f"stderr: {res.stderr}"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_trace_id_collision_resistance() -> None:
    """Verify that 1000 random-but-deterministic traces don't suffer trace_id collisions."""
    import random
    rng = random.Random(1337)
    observed_ids: set[str] = set()
    kinds = ["observation", "grouping", "hypothesis", "conclusion"]

    for i in range(1000):
        # Generate variations deterministically using seeded rng
        step0_claim = f"claim_0_{i}_{rng.randint(0, 100000)}"
        step1_claim = f"claim_1_{i}_{rng.randint(0, 100000)}"
        payload0 = {"val": rng.randint(0, 100000), "nested": {"str": f"val_{i}"}}
        payload1 = {"arr": [rng.randint(0, 1000) for _ in range(3)]}

        step0 = _step(index=0, kind=rng.choice(kinds), claim=step0_claim, payload=payload0)
        step1 = _step(index=1, kind=rng.choice(kinds), claim=step1_claim, payload=payload1)

        trace = build_trace([step0, step1])

        assert len(trace.trace_id) == 64
        assert trace.trace_id not in observed_ids, f"Collision at index {i} on id {trace.trace_id}"
        observed_ids.add(trace.trace_id)

    assert len(observed_ids) == 1000


def test_canonical_bytes_no_floating_point() -> None:
    """Verify that floats are rejected at validation and no float representations appear in bytes."""
    float_pattern = re.compile(rb"[0-9]+\.[0-9]+")

    # 1. Ensure float values are recursively rejected at build time
    with pytest.raises(ValueError, match="floating-point"):
        build_trace([_step(payload={"w": 1.5})])

    with pytest.raises(ValueError, match="floating-point"):
        build_trace([_step(payload={"nested": {"ratio": 0.0}})])

    with pytest.raises(ValueError, match="floating-point"):
        build_trace([_step(payload={"list": [1, 2, 3.14]})])

    # 2. Assert no float pattern appears in canonical bytes for a variety of valid types
    corpus = [
        build_trace([_step(index=0, payload={"int": 42, "bool": True, "str": "hello", "none": None})]),
        build_trace([
            _step(index=0, payload={"list": [1, 2, 3, {"nested": "value"}]}),
            _step(index=1, kind="conclusion", payload={"another": {"x": 99}})
        ]),
        build_trace([_step(index=0, payload={"str_float": "not_a_float"})]),
        build_trace([_step(index=0, payload={"large": 12345678901234567890})]),
    ]

    for trace in corpus:
        cb = canonical_bytes(trace)
        match = float_pattern.search(cb)
        assert match is None, f"Floating point pattern found in canonical bytes: {cb!r}"
