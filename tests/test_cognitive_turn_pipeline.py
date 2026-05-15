"""
Tests for CognitiveTurnPipeline — the cognitive spine.

Tests 1-5: original pipeline contract tests.
Tests 6-10: intent-proposition graph wiring tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline, CognitiveTurnResult
from core.cognition.trace import trace_hash_from_result
from generate.intent import IntentTag
from generate.graph_planner import RhetoricalMove


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


# ---------------------------------------------------------------------------
# 6. Definition intent recorded
# ---------------------------------------------------------------------------

def test_pipeline_records_definition_intent(pipeline: CognitiveTurnPipeline) -> None:
    """A 'what is' prompt should produce a DEFINITION intent in the result."""
    result = pipeline.run("what is light", max_tokens=6)

    assert result.intent is not None
    assert result.intent.tag is IntentTag.DEFINITION
    assert "light" in result.intent.subject.lower()

    assert result.proposition_graph is not None
    assert len(result.proposition_graph.nodes) == 1
    assert result.proposition_graph.nodes[0].predicate == "is_defined_as"

    assert result.articulation_target is not None
    assert len(result.articulation_target.steps) == 1
    assert result.articulation_target.source_intent is IntentTag.DEFINITION


# ---------------------------------------------------------------------------
# 7. Comparison graph recorded
# ---------------------------------------------------------------------------

def test_pipeline_records_comparison_graph(pipeline: CognitiveTurnPipeline) -> None:
    """A comparison prompt produces a 2-node graph with a CONTRAST edge."""
    result = pipeline.run("compare light and truth", max_tokens=6)

    assert result.intent is not None
    assert result.intent.tag is IntentTag.COMPARISON

    graph = result.proposition_graph
    assert graph is not None
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].relation.value == "contrast"

    target = result.articulation_target
    assert target is not None
    moves = [s.move for s in target.steps]
    assert RhetoricalMove.CONTRAST in moves


# ---------------------------------------------------------------------------
# 8. Articulation target recorded
# ---------------------------------------------------------------------------

def test_pipeline_records_articulation_target(pipeline: CognitiveTurnPipeline) -> None:
    """Every turn produces an ArticulationTarget with at least one step."""
    result = pipeline.run("logos truth", max_tokens=6)

    assert result.articulation_target is not None
    assert len(result.articulation_target.steps) >= 1
    step = result.articulation_target.steps[0]
    assert step.move is RhetoricalMove.ASSERT
    assert step.node_id == "p0"


# ---------------------------------------------------------------------------
# 9. Trace hash changes with intent
# ---------------------------------------------------------------------------

def test_pipeline_trace_hash_changes_with_intent() -> None:
    """Different intent classifications produce different trace hashes."""
    rt1 = ChatRuntime()
    rt2 = ChatRuntime()

    r1 = CognitiveTurnPipeline(rt1).run("what is light", max_tokens=6)
    r2 = CognitiveTurnPipeline(rt2).run("why light", max_tokens=6)

    assert r1.intent.tag is IntentTag.DEFINITION
    assert r2.intent.tag is IntentTag.CAUSE
    assert r1.trace_hash != r2.trace_hash


# ---------------------------------------------------------------------------
# 10. ChatResponse contract unchanged
# ---------------------------------------------------------------------------

def test_pipeline_chat_response_contract_unchanged(pipeline: CognitiveTurnPipeline) -> None:
    """Adding intent fields must not break the existing ChatResponse contract."""
    result = pipeline.run("light logos", max_tokens=8)

    assert isinstance(result.surface, str) and result.surface.strip()
    assert isinstance(result.walk_surface, str)
    assert isinstance(result.articulation_surface, str)
    assert result.dialogue_role in {"assert", "elaborate", "question", "refute"}
    assert isinstance(result.versor_condition, float)
    assert isinstance(result.trace_hash, str) and len(result.trace_hash) == 64
    assert isinstance(result.vault_hits, int)
    assert result.proposition is not None
    assert result.articulation is not None
