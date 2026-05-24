from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from chat.dispatch_trace import DispatchTrace, DispatchAttempt
from core.cognition.pipeline import CognitiveTurnPipeline


def test_pack_grounded_definition_trace() -> None:
    """A pack-grounded DEFINITION turn produces selected='pack' and a trace whose
    final attempt is outcome='admitted'.
    """
    rt = ChatRuntime()
    # "What is light?" targets a pack-resident lemma and routes to pack-grounding
    resp = rt.chat("What is light?")
    
    assert resp.grounding_source == "pack"
    assert resp.dispatch_trace is not None
    assert resp.dispatch_trace.selected == "pack"
    
    attempts = resp.dispatch_trace.attempts
    assert len(attempts) > 0
    final_attempt = attempts[-1]
    assert final_attempt.source == "pack"
    assert final_attempt.outcome == "admitted"
    assert "pack_grounded_surface_found" in final_attempt.reason


def test_fully_oov_universal_disclosure_trace() -> None:
    """A fully-OOV prompt (or unknown intent prompt) produces a trace where
    pack/teaching/partial all show outcome='fell_through' with distinct reasons
    and selected='universal_disclosure'.
    """
    rt = ChatRuntime()
    # "hello" has no subject matching packs or teaching, falling back to universal disclosure.
    resp = rt.chat("hello")
    
    assert resp.grounding_source == "none"
    assert resp.dispatch_trace is not None
    assert resp.dispatch_trace.selected == "universal_disclosure"
    
    attempts = resp.dispatch_trace.attempts
    
    # Check that pack, teaching, and partial all show outcome="fell_through"
    attempts_by_source = {a.source: a for a in attempts}
    for source in ("pack", "teaching", "partial", "oov", "universal_disclosure"):
        assert source in attempts_by_source
        attempt = attempts_by_source[source]
        if source == "universal_disclosure":
            assert attempt.outcome == "admitted"
        else:
            assert attempt.outcome == "fell_through"
            
    # Verify they have distinct reasons
    reasons = {attempts_by_source[s].reason for s in ("pack", "teaching", "partial")}
    assert len(reasons) == 3


def test_trace_determinism() -> None:
    """The trace's reason strings are stable across two runs of the same prompt."""
    rt1 = ChatRuntime()
    rt2 = ChatRuntime()
    
    prompt = "What is light?"
    resp1 = rt1.chat(prompt)
    resp2 = rt2.chat(prompt)
    
    assert resp1.dispatch_trace is not None
    assert resp2.dispatch_trace is not None
    assert resp1.dispatch_trace.selected == resp2.dispatch_trace.selected
    assert len(resp1.dispatch_trace.attempts) == len(resp2.dispatch_trace.attempts)
    
    for a1, a2 in zip(resp1.dispatch_trace.attempts, resp2.dispatch_trace.attempts):
        assert a1.source == a2.source
        assert a1.outcome == a2.outcome
        assert a1.reason == a2.reason


def test_pipeline_carries_dispatch_trace() -> None:
    """CognitiveTurnPipeline exposes the dispatch trace in CognitiveTurnResult."""
    pipeline = CognitiveTurnPipeline(ChatRuntime())
    result = pipeline.run("What is light?")
    
    assert result.dispatch_trace is not None
    assert result.dispatch_trace.selected == "pack"
    assert len(result.dispatch_trace.attempts) > 0
    assert result.dispatch_trace.attempts[-1].outcome == "admitted"
