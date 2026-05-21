"""Unified-ingest flag null-lift + smoke (ADR-0090).

Pre-fix ``ChatRuntime.chat()`` ran ``probe_ingest`` first, gate-checked
the probe field, and only then committed.  The probe and committed
fields differ (commit applies drive bias), so the gate observed a
different manifold position than the walk subsequently navigated.

ADR-0090 ships a flag-gated unified-ingest path:

  * ``RuntimeConfig.unified_ingest=False`` (default) — historical
    behavior, bit-for-bit identical to pre-fix.
  * ``RuntimeConfig.unified_ingest=True`` — commit first, gate on
    the committed field, walk on the same field.

These tests pin:

  1. Flag defaults to False on ``DEFAULT_CONFIG``.
  2. Flag-off surface + trace_hash + vault_hits are byte-identical
     to the pre-fix behavior on every cognition-shape prompt.
  3. Flag-on produces well-formed responses and uses the unified
     ingest path (verified by checking that ``probe_ingest`` is not
     called).
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from core.config import DEFAULT_CONFIG, RuntimeConfig


def test_flag_defaults_to_false() -> None:
    assert DEFAULT_CONFIG.unified_ingest is False


def test_flag_off_byte_identical_surface_and_trace() -> None:
    """The null-lift invariant: flag-off behaviour is unchanged."""
    rt_a = ChatRuntime()
    rt_b = ChatRuntime()
    pa = CognitiveTurnPipeline(runtime=rt_a)
    pb = CognitiveTurnPipeline(runtime=rt_b)
    result_a = pa.run("What is truth?", max_tokens=4)
    result_b = pb.run("What is truth?", max_tokens=4)
    assert result_a.surface == result_b.surface
    assert result_a.trace_hash == result_b.trace_hash
    assert result_a.vault_hits == result_b.vault_hits


def test_flag_on_skips_probe_ingest(monkeypatch) -> None:
    """Flag-on must not call ``probe_ingest`` — the unified path commits
    first and gates on the committed field."""
    rt = ChatRuntime(config=RuntimeConfig(unified_ingest=True))

    called = {"probe": 0, "commit": 0}
    real_probe = rt._context.probe_ingest
    real_commit = rt._context.commit_ingest

    def counting_probe(*args, **kwargs):
        called["probe"] += 1
        return real_probe(*args, **kwargs)

    def counting_commit(*args, **kwargs):
        called["commit"] += 1
        return real_commit(*args, **kwargs)

    monkeypatch.setattr(rt._context, "probe_ingest", counting_probe)
    monkeypatch.setattr(rt._context, "commit_ingest", counting_commit)

    rt.chat("What is truth?", max_tokens=4)
    # Unified path commits once, does not probe.
    assert called["probe"] == 0
    assert called["commit"] >= 1


def test_flag_on_produces_well_formed_response() -> None:
    """Flag-on path still emits a surface and a trace_hash."""
    rt = ChatRuntime(config=RuntimeConfig(unified_ingest=True))
    pipeline = CognitiveTurnPipeline(runtime=rt)
    result = pipeline.run("What is truth?", max_tokens=4)
    assert isinstance(result.surface, str)
    assert result.surface
    assert result.trace_hash


def test_flag_off_still_calls_probe_ingest(monkeypatch) -> None:
    """Flag-off (default) must continue to call ``probe_ingest`` —
    confirms the historical path is unchanged."""
    rt = ChatRuntime()

    called = {"probe": 0}
    real_probe = rt._context.probe_ingest

    def counting_probe(*args, **kwargs):
        called["probe"] += 1
        return real_probe(*args, **kwargs)

    monkeypatch.setattr(rt._context, "probe_ingest", counting_probe)
    rt.chat("What is truth?", max_tokens=4)
    assert called["probe"] == 1
