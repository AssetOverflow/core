"""ADR-0153 (W-020a) — back-stamp canonical trace_hash onto TurnEvent
and DiscoveryCandidate.

Before this ADR, ``TurnEvent`` had no ``trace_hash`` field, so
``teaching/discovery._trace_hash`` (which read it via ``getattr(...,
"trace_hash", "")``) always returned ``""``.  Every persisted
``DiscoveryCandidate.source_turn_trace`` was empty, breaking the
audit trail that promises (per the dataclass docstring) to name the
originating turn.

The fix:
  1. Add ``trace_hash: str = ""`` to ``TurnEvent``.
  2. ``CognitiveTurnPipeline.process`` calls
     ``runtime.finalize_turn_trace_hash(trace_hash)`` after
     ``compute_trace_hash`` and before constructing
     ``CognitiveTurnResult``.
  3. The runtime back-stamps the last ``TurnEvent`` and the unstamped
     tail of ``_pending_candidates``, then re-persists the
     ``discovery_candidates.jsonl`` checkpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


def _pick_cold_cause_subject() -> str:
    """Pick a pack lemma that is NOT in any (lemma, cause) teaching chain.

    Mirrors the fixture-rotation pattern from
    ``tests/test_discovery_candidates.py`` so this test does not break
    when a future curriculum unit ratifies ``(principle, cause)``.
    """
    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    corpus = _corpus_index()
    for candidate in ("principle", "narrative", "concept", "judgment"):
        if candidate in _pack_index() and (candidate, "cause") not in corpus:
            return candidate
    pytest.skip("no cold (*, cause) pack lemma available for fixture")


def test_turn_event_has_trace_hash_field() -> None:
    """ADR-0153: ``TurnEvent`` exposes a ``trace_hash`` field."""
    from core.physics.identity import TurnEvent

    assert "trace_hash" in TurnEvent.__dataclass_fields__
    assert TurnEvent.__dataclass_fields__["trace_hash"].default == ""


def test_pipeline_back_stamps_turn_event_trace_hash(tmp_path: Path) -> None:
    """After ``pipe.run``, the last ``TurnEvent.trace_hash`` matches the
    pipeline's computed ``CognitiveTurnResult.trace_hash``."""
    state_path = tmp_path / "engine_state"
    runtime = ChatRuntime(
        config=RuntimeConfig(),
        engine_state_path=state_path,
    )
    pipe = CognitiveTurnPipeline(runtime=runtime)
    result = pipe.run("What causes light?")

    assert result.trace_hash, "pipeline must produce a non-empty trace_hash"
    assert runtime.turn_log, "turn_log must contain at least one event"
    assert runtime.turn_log[-1].trace_hash == result.trace_hash


def test_pipeline_back_stamps_pending_discovery_candidates(
    tmp_path: Path,
) -> None:
    """Discovery candidates emitted during the turn carry the canonical
    trace_hash in their ``source_turn_trace`` field after the pipeline
    finalizes the turn."""
    subject = _pick_cold_cause_subject()
    state_path = tmp_path / "engine_state"
    runtime = ChatRuntime(
        config=RuntimeConfig(),
        engine_state_path=state_path,
    )
    pipe = CognitiveTurnPipeline(runtime=runtime)
    result = pipe.run(f"What causes {subject}?")

    cold_candidates = [
        c
        for c in runtime._pending_candidates
        if c.proposed_chain.get("subject") == subject
        and c.proposed_chain.get("intent") == "cause"
    ]
    if not cold_candidates:
        pytest.skip(
            "discovery did not fire for "
            f"({subject}, cause) under default config; fixture stale"
        )

    assert result.trace_hash
    for cand in cold_candidates:
        assert cand.source_turn_trace == result.trace_hash, (
            "DiscoveryCandidate.source_turn_trace must equal the canonical "
            f"trace_hash; got {cand.source_turn_trace!r} vs {result.trace_hash!r}"
        )


def test_persisted_candidates_jsonl_carries_trace_hash(
    tmp_path: Path,
) -> None:
    """The persisted discovery candidates carry the back-stamped trace_hash.

    Uses the store's public load interface (load_discovery_candidates) rather
    than reading file paths directly, so the test is layout-agnostic.
    """
    subject = _pick_cold_cause_subject()
    state_path = tmp_path / "engine_state"
    runtime = ChatRuntime(
        config=RuntimeConfig(),
        engine_state_path=state_path,
    )
    pipe = CognitiveTurnPipeline(runtime=runtime)
    result = pipe.run(f"What causes {subject}?")
    runtime.checkpoint_engine_state()

    from engine_state import EngineStateStore
    loaded = EngineStateStore(state_path).load_discovery_candidates()
    if not loaded:
        pytest.skip("checkpoint did not write candidates this turn")

    cold = [
        c
        for c in loaded
        if c.proposed_chain.get("subject") == subject
        and c.proposed_chain.get("intent") == "cause"
    ]
    if not cold:
        pytest.skip("discovery did not fire under default config; fixture stale")
    for c in cold:
        assert c.source_turn_trace == result.trace_hash, (
            f"persisted candidate source_turn_trace must equal the trace_hash; "
            f"got {c.source_turn_trace!r} vs {result.trace_hash!r}"
        )


def test_finalize_is_noop_for_empty_trace_hash(tmp_path: Path) -> None:
    """Empty trace_hash MUST be a no-op (stub/refusal call sites)."""
    runtime = ChatRuntime(
        config=RuntimeConfig(),
        engine_state_path=tmp_path / "engine_state",
    )
    # Construct a fake last-turn so we can assert no mutation occurs.
    pipe = CognitiveTurnPipeline(runtime=runtime)
    pipe.run("Hello.")
    before = runtime.turn_log[-1].trace_hash
    runtime.finalize_turn_trace_hash("")
    assert runtime.turn_log[-1].trace_hash == before


def test_finalize_is_idempotent_on_already_stamped_tail(
    tmp_path: Path,
) -> None:
    """A second back-stamp with a different hash MUST NOT overwrite
    candidates whose ``source_turn_trace`` is already non-empty.

    Protects against re-stamping prior turns when a new turn fires
    discovery; the back-walk halts at the first already-stamped entry.
    """
    subject = _pick_cold_cause_subject()
    runtime = ChatRuntime(
        config=RuntimeConfig(),
        engine_state_path=tmp_path / "engine_state",
    )
    pipe = CognitiveTurnPipeline(runtime=runtime)
    pipe.run(f"What causes {subject}?")

    stamped_before = [
        c.source_turn_trace for c in runtime._pending_candidates
    ]
    runtime.finalize_turn_trace_hash("deadbeef" * 8)
    stamped_after = [
        c.source_turn_trace for c in runtime._pending_candidates
    ]
    assert stamped_before == stamped_after
