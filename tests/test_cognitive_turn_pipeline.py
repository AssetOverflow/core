"""
Tests for CognitiveTurnPipeline — the cognitive spine.

Five tests, no micro-test explosion:
  1. test_pipeline_known_token_turn         — happy-path turn with known tokens
  2. test_pipeline_unknown_token_grounding  — OOV token handled; field still valid
  3. test_pipeline_two_turn_memory_continuity — field evolves across turns
  4. test_pipeline_trace_hash_deterministic — identical inputs → identical hash
  5. test_pipeline_preserves_versor_closure — versor_condition < 1e-6 per turn
"""

from __future__ import annotations

import numpy as np
import pytest

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline, CognitiveTurnResult
from core.cognition.trace import trace_hash_from_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def runtime() -> ChatRuntime:
    return ChatRuntime()


@pytest.fixture()
def pipeline(runtime: ChatRuntime) -> CognitiveTurnPipeline:
    return CognitiveTurnPipeline(runtime)


# ---------------------------------------------------------------------------
# 1. Known token turn
# ---------------------------------------------------------------------------

def test_pipeline_known_token_turn(pipeline: CognitiveTurnPipeline) -> None:
    """A single turn with known tokens yields a fully populated result."""
    result = pipeline.run("light logos", max_tokens=8)

    assert isinstance(result, CognitiveTurnResult)

    # Input layer
    assert result.input_text == "light logos"
    assert len(result.input_tokens) >= 1
    assert len(result.filtered_tokens) >= 1

    # Field layer
    assert result.field_state_before is None   # first turn: no prior state
    assert result.field_state_after is not None
    assert result.field_state_after.F.shape == (32,)

    # Output surfaces
    assert result.surface.strip()
    assert isinstance(result.walk_surface, str)
    assert isinstance(result.articulation_surface, str)

    # Dialogue
    assert result.dialogue_role in {"assert", "elaborate", "question", "refute"}

    # Bookkeeping
    assert isinstance(result.versor_condition, float)
    assert isinstance(result.trace_hash, str) and len(result.trace_hash) == 64
    assert isinstance(result.vault_hits, int)


# ---------------------------------------------------------------------------
# 2. Unknown / OOV token grounding
# ---------------------------------------------------------------------------

def test_pipeline_unknown_token_grounding(pipeline: CognitiveTurnPipeline) -> None:
    """OOV token in an open pack should not prevent field from staying valid."""
    result = pipeline.run("what is דברית", max_tokens=4)

    # Runtime must still produce a valid result
    assert result.surface.strip()
    assert result.field_state_after is not None
    assert result.versor_condition < 1e-6


# ---------------------------------------------------------------------------
# 3. Two-turn memory continuity
# ---------------------------------------------------------------------------

def test_pipeline_two_turn_memory_continuity(pipeline: CognitiveTurnPipeline) -> None:
    """Field state evolves between turns, confirming the pipeline threads memory."""
    first = pipeline.run("light logos", max_tokens=8)
    second = pipeline.run("truth logos", max_tokens=8)

    # second turn knows about first
    assert second.field_state_before is not None
    assert second.field_state_before.F.shape == (32,)

    # field genuinely moved between turns
    assert not np.array_equal(
        first.field_state_after.F,
        second.field_state_after.F,
    ), "Field state must evolve across turns."

    # Both versor conditions are closed
    assert first.versor_condition < 1e-6
    assert second.versor_condition < 1e-6


# ---------------------------------------------------------------------------
# 4. Trace hash determinism
# ---------------------------------------------------------------------------

def test_pipeline_trace_hash_deterministic() -> None:
    """Identical inputs on a fresh runtime produce the same trace hash."""
    rt1 = ChatRuntime()
    rt2 = ChatRuntime()

    r1 = CognitiveTurnPipeline(rt1).run("light truth", max_tokens=6)
    r2 = CognitiveTurnPipeline(rt2).run("light truth", max_tokens=6)

    # Re-derive via the helper to confirm the hash formula is stable
    assert r1.trace_hash == trace_hash_from_result(r1)
    assert r2.trace_hash == trace_hash_from_result(r2)

    # Same hash across two independent runtimes with same prompt
    assert r1.trace_hash == r2.trace_hash, (
        f"Expected deterministic hash, got:\n  r1={r1.trace_hash}\n  r2={r2.trace_hash}"
    )


# ---------------------------------------------------------------------------
# 5. Versor closure preserved across all turns
# ---------------------------------------------------------------------------

def test_pipeline_preserves_versor_closure(pipeline: CognitiveTurnPipeline) -> None:
    """versor_condition must stay below 1e-6 for every turn in the session."""
    prompts = [
        "logos light",
        "truth word",
        "what is λόγος",
        "spirit breath",
    ]
    for prompt in prompts:
        result = pipeline.run(prompt, max_tokens=6)
        assert result.versor_condition < 1e-6, (
            f"Versor closure broken after prompt {prompt!r}: "
            f"versor_condition={result.versor_condition:.2e}"
        )
        # Field state invariant: shape must be intact
        assert result.field_state_after.F.shape == (32,)
