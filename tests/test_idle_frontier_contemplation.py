"""ADR-0080 idle frontier-contemplation — the always-on life autonomously mines its
frontier into reviewable SPECULATIVE findings, with NO user turn.

Gated (``contemplate_frontier_during_idle``, default off → no behavior change); idempotent
per frontier (an already-mined frontier converges → no churn); SPECULATIVE-only (ADR-0080:
never COHERENT, never ratified here — the HITL path is untouched).
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from chat.always_on import run_continuous, serialize_report
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


def test_idle_frontier_pass_degrades_on_mining_failure(tmp_path, monkeypatch) -> None:
    # The frontier mine is an OPTIONAL pass on an indefinite-uptime life: a failure in
    # run_contemplation (e.g. a malformed frontier report) must DEGRADE to 0 findings and
    # warn, NEVER crash idle_tick. A converged continuous life cannot be killed by an
    # optional background pass.
    import core.contemplation.runner as runner_mod

    def _boom():
        raise ValueError("malformed frontier report")

    monkeypatch.setattr(runner_mod, "run_contemplation", _boom)
    rt = _runtime(tmp_path, frontier=True)
    with pytest.warns(RuntimeWarning, match="idle frontier-contemplation pass skipped"):
        result = rt.idle_tick()  # must NOT raise
    assert result.frontier_findings == 0  # degraded, no findings this beat
    assert _run_files(tmp_path) == []  # nothing persisted on failure


def test_idle_frontier_pass_degrades_on_write_failure(tmp_path, monkeypatch) -> None:
    # A transient filesystem fault mid-persist must also degrade, not crash. The run-cache
    # is mined, but the write fails → 0 findings + warning, loop survives.
    import core.contemplation.runner as runner_mod

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(runner_mod, "write_contemplation_run", _boom)
    rt = _runtime(tmp_path, frontier=True)
    with pytest.warns(RuntimeWarning, match="idle frontier-contemplation pass skipped"):
        result = rt.idle_tick()  # must NOT raise
    assert result.frontier_findings == 0


def test_always_on_loop_survives_frontier_failure(tmp_path, monkeypatch) -> None:
    # End-to-end: the always-on heartbeat completes all beats and persists its final
    # checkpoint even when every frontier mine fails — the continuous life is not killed.
    import core.contemplation.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "run_contemplation",
        lambda: (_ for _ in ()).throw(ValueError("boom")),
    )
    rt = _runtime(tmp_path, frontier=True)
    with pytest.warns(RuntimeWarning):
        report = run_continuous(rt, heartbeats=3)
    assert report.heartbeats == 3  # ran to completion, no crash
    assert report.final_checkpoint_ok is True
    assert report.total_frontier_findings == 0
    assert all(r.frontier_findings == 0 for r in report.records)


def test_lived_life_persists_frontier_findings(tmp_path) -> None:
    # did_work must have a durable explanation: when the only work of a beat is a frontier
    # mine (facts/proposals both 0), the persisted lived-life record must still show the
    # cause — frontier_findings per-record AND a run total — not an unexplained did_work.
    rt = _runtime(tmp_path, frontier=True)
    report_path = tmp_path / "es" / "lived_life.json"
    report = run_continuous(rt, heartbeats=2, report_path=report_path)

    assert report.total_frontier_findings >= 1
    beat0 = report.records[0]
    assert beat0.did_work is True
    # The mine — not facts/proposals — is what made beat 0 work; the record proves it.
    assert beat0.facts_consolidated == 0
    assert beat0.proposals_created == 0
    assert beat0.frontier_findings >= 1

    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["total_frontier_findings"] >= 1
    assert persisted["records"][0]["frontier_findings"] >= 1
    # serialize_report (the workbench projection) carries the same durable explanation.
    assert serialize_report(report)["records"][0]["frontier_findings"] >= 1
