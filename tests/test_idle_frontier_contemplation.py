"""ADR-0080 idle frontier-contemplation — the always-on life autonomously mines its
frontier into reviewable SPECULATIVE findings, with NO user turn.

Gated (``contemplate_frontier_during_idle``, default off → no behavior change); idempotent
per frontier (an already-mined frontier converges → no churn); SPECULATIVE-only (ADR-0080:
never COHERENT, never ratified here — the HITL path is untouched).
"""

from __future__ import annotations

import dataclasses
import json

from chat.always_on import run_continuous
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


def _runtime(tmp_path, *, frontier: bool) -> ChatRuntime:
    config = dataclasses.replace(
        RuntimeConfig(), contemplate_frontier_during_idle=frontier
    )
    return ChatRuntime(config=config, engine_state_path=tmp_path / "es")


def _run_files(tmp_path) -> list:
    d = tmp_path / "es" / "contemplation_runs"
    return sorted(d.glob("idle_*.json")) if d.exists() else []


def test_idle_frontier_off_by_default(tmp_path) -> None:
    # Default config (flag off): no mining, no run persisted — behavior unchanged.
    result = _runtime(tmp_path, frontier=False).idle_tick()
    assert result.frontier_findings == 0
    assert _run_files(tmp_path) == []


def test_idle_frontier_mines_when_enabled(tmp_path) -> None:
    result = _runtime(tmp_path, frontier=True).idle_tick()
    assert result.frontier_findings >= 1  # autonomously mined a finding, no user turn
    assert len(_run_files(tmp_path)) == 1  # persisted one reviewable run
    # Atomic write: a complete artifact, no orphan temp left at the canonical path.
    runs_dir = tmp_path / "es" / "contemplation_runs"
    assert not list(runs_dir.glob(".*.tmp"))
    json.loads(_run_files(tmp_path)[0].read_text(encoding="utf-8"))  # valid (not torn)


def test_idle_frontier_mines_once_per_session(tmp_path, monkeypatch) -> None:
    # A converged life must not re-read/parse/hash the frontier every beat (indefinite
    # uptime): the static frontier is mined ONCE per session and memoized.
    import core.contemplation.runner as runner_mod

    real = runner_mod.run_contemplation
    calls = {"n": 0}

    def _spy():
        calls["n"] += 1
        return real()

    monkeypatch.setattr(runner_mod, "run_contemplation", _spy)
    rt = _runtime(tmp_path, frontier=True)
    rt.idle_tick()
    rt.idle_tick()
    rt.idle_tick()
    assert calls["n"] == 1


def test_idle_frontier_findings_are_speculative(tmp_path) -> None:
    # wrong=0 / ADR-0080: an autonomously-mined finding is SPECULATIVE, never COHERENT.
    _runtime(tmp_path, frontier=True).idle_tick()
    run = json.loads(_run_files(tmp_path)[0].read_text(encoding="utf-8"))
    findings = run["findings"]
    assert findings
    assert all(f["epistemic_status"] == "speculative" for f in findings)


def test_idle_frontier_converges_idempotent(tmp_path) -> None:
    # A mined frontier is not re-mined — the life converges (no churn), the wrong=0 invariant
    # for a continuous life: an idle beat over an exhausted frontier does no work.
    rt = _runtime(tmp_path, frontier=True)
    first = rt.idle_tick()
    second = rt.idle_tick()
    assert first.frontier_findings >= 1
    assert second.frontier_findings == 0  # already mined this frontier
    assert len(_run_files(tmp_path)) == 1  # no duplicate run persisted


def test_heartbeat_mines_then_converges(tmp_path) -> None:
    # The always-on heartbeat over a frontier-contemplating life: beat 0 mines (did_work via
    # frontier_findings), then the saturated life settles to rest.
    rt = _runtime(tmp_path, frontier=True)
    report = run_continuous(rt, heartbeats=4)
    assert report.records[0].did_work is True  # beat 0 mined the frontier
    assert report.records[-1].did_work is False  # converged to rest
    assert len(_run_files(tmp_path)) == 1
