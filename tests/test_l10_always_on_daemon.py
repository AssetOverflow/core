"""L10 — the always-on DAEMON shell: the process that runs the continuous-life heartbeat.

``run_continuous`` (the loop) is proven in ``test_l10_always_on``; this covers what the
daemon adds: the single-instance OS lock (one life per engine-state dir), the unbounded
run + prompt interruptible stop, the forced continuous-life config applied AT the runtime,
real SIGTERM shutdown, and that the daemon leaves a readable ``lived_life.json``. Most
tests drive ``stop_event`` directly (``install_signals=False``) so they never touch the
test process's signal handlers; one subprocess test exercises the real signal path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from chat.always_on import LIVED_LIFE_FILENAME, _sleep_until_stop
from chat.always_on_daemon import (
    LOCK_FILENAME,
    AlwaysOnLockedError,
    _SingleInstanceLock,
    continuous_life_config,
    run_daemon,
)
from core.cli import (
    _always_on_identity_break_message,
    build_parser,
    cmd_always_on,
)
from core.config import RuntimeConfig
from workbench.lived_life import lived_life_from_payload


def _read_lived_life(state_dir):
    payload = json.loads((state_dir / LIVED_LIFE_FILENAME).read_text(encoding="utf-8"))
    return lived_life_from_payload(payload)


def _bounded(state_dir, **kw):
    return run_daemon(
        engine_state_path=state_dir,
        interval=kw.pop("interval", 0.0),
        max_beats=kw.pop("max_beats", 1),
        install_signals=False,
        stop_event=threading.Event(),
        **kw,
    )


def test_daemon_runs_bounded_and_leaves_a_valid_lived_life(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    result = _bounded(state_dir, max_beats=3)

    assert result.report.heartbeats == 3
    assert result.stopped_by_signal is False  # ended on max_beats, not a signal
    assert result.report.final_checkpoint_ok
    assert result.engine_state_path == state_dir
    # The daemon left the workbench a readable, validated surface where it reads it.
    surface = _read_lived_life(state_dir)
    assert surface.status == "recorded"
    assert surface.heartbeats == 3
    # The lock is RELEASED on exit — a second run over the same dir acquires it cleanly.
    assert _bounded(state_dir, max_beats=1).report.heartbeats == 1


def test_daemon_forces_the_continuous_life_config_helper() -> None:
    # Even handed a config with persistence/continuity OFF, the helper forces them ON.
    base = RuntimeConfig(
        persist_session_state=False,
        consolidate_determinations=False,
        strict_identity_continuity=False,
    )
    cfg = continuous_life_config(base)
    assert cfg.persist_session_state is True
    assert cfg.consolidate_determinations is True
    assert cfg.strict_identity_continuity is True


def test_run_daemon_applies_the_forced_config_to_the_runtime(tmp_path, monkeypatch) -> None:
    # The wiring obligation: run_daemon must apply continuous_life_config to the ChatRuntime
    # it builds, not just expose the helper. Capture the config the runtime is constructed
    # with and assert the flags are forced on even though the base config had them off.
    import chat.always_on_daemon as daemon_mod

    captured: dict = {}
    real_ctor = daemon_mod.ChatRuntime

    def _spy(*, config, engine_state_path, no_load_state):
        captured["config"] = config
        return real_ctor(
            config=config, engine_state_path=engine_state_path, no_load_state=no_load_state
        )

    monkeypatch.setattr(daemon_mod, "ChatRuntime", _spy)
    run_daemon(
        config=RuntimeConfig(
            persist_session_state=False,
            consolidate_determinations=False,
            strict_identity_continuity=False,
        ),
        engine_state_path=tmp_path / "engine_state",
        interval=0.0,
        max_beats=1,
        install_signals=False,
        stop_event=threading.Event(),
    )
    cfg = captured["config"]
    assert cfg.persist_session_state is True
    assert cfg.consolidate_determinations is True
    assert cfg.strict_identity_continuity is True


def test_unbounded_run_stops_promptly_on_stop_signal(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    stop_event = threading.Event()

    def _stop_after_two(record) -> None:
        if record.tick >= 2:
            stop_event.set()

    result = run_daemon(
        engine_state_path=state_dir,
        interval=0.01,
        max_beats=None,  # would run forever without the stop
        install_signals=False,
        stop_event=stop_event,
        on_record=_stop_after_two,
    )
    assert result.report.heartbeats == 3  # beats 0,1,2 then the top-of-loop stop breaks
    assert result.stopped_by_signal is False  # a stop_event, not a SIGINT/SIGTERM


def test_live_flock_holder_refuses_a_second_daemon(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    state_dir.mkdir(parents=True)
    # A process actually HOLDING the flock (not merely a pid written in the file) -> refuse.
    holder = _SingleInstanceLock(state_dir / LOCK_FILENAME)
    holder.acquire()
    try:
        with pytest.raises(AlwaysOnLockedError):
            _bounded(state_dir)
    finally:
        holder.release()
    # After release, a daemon acquires cleanly — the lock was contended, not permanent.
    assert _bounded(state_dir).report.heartbeats == 1


def test_leftover_lock_file_from_a_dead_holder_does_not_block(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    state_dir.mkdir(parents=True)
    # A crash leaves a lock FILE with a dead pid, but the kernel released the flock on death
    # -> a new daemon acquires (no manual stale reclaim, no deadlock, no PID-reuse ambiguity).
    (state_dir / LOCK_FILENAME).write_text("999999\n", encoding="utf-8")
    assert _bounded(state_dir).report.heartbeats == 1


def test_no_load_state_writes_no_durable_lived_life(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    state_dir.mkdir(parents=True)
    # An ephemeral life must not drop a lived_life.json that would shadow a persistent life.
    run_daemon(
        engine_state_path=state_dir,
        interval=0.0,
        max_beats=2,
        no_load_state=True,
        install_signals=False,
        stop_event=threading.Event(),
    )
    assert not (state_dir / LIVED_LIFE_FILENAME).exists()


def test_real_sigterm_stops_the_daemon_cleanly(tmp_path) -> None:
    # The real signal path the other tests skip (install_signals=True on the main thread):
    # launch the actual CLI, send SIGTERM, assert a clean signal stop + a persisted artifact.
    import os

    state_dir = tmp_path / "engine_state"
    env = {
        **os.environ,
        "CORE_ENGINE_STATE_DIR": str(state_dir),
        "CORE_BACKEND": "numpy",
        "CORE_STRICT_MLX_ON_APPLE": "0",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "core.cli", "always-on", "--interval", "0.05"],
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(3)
    proc.terminate()  # SIGTERM on POSIX
    try:
        _, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        pytest.fail("daemon did not stop on SIGTERM (interruptible shutdown broken)")

    assert proc.returncode == 0
    assert "stopped (signal)" in err
    assert (state_dir / LIVED_LIFE_FILENAME).exists()


def test_interruptible_sleep_returns_immediately_when_stopped() -> None:
    start = time.monotonic()
    _sleep_until_stop(30.0, lambda: True)
    assert time.monotonic() - start < 1.0  # 30s vs <1s: a generous, non-flaky margin


def test_interruptible_sleep_without_stop_is_a_plain_sleep() -> None:
    start = time.monotonic()
    _sleep_until_stop(0.05, None)
    assert time.monotonic() - start >= 0.04  # actually waited (no stop predicate)


# --- PR B (ADR-0220): operator ergonomics — per-life state dir + safe recovery ---


def test_always_on_engine_state_flag_defaults_to_none() -> None:
    # Default: fall back to $CORE_ENGINE_STATE_DIR / the in-repo dir (engine_state_path=None).
    args = build_parser().parse_args(["always-on"])
    assert args.engine_state is None


def test_always_on_engine_state_flag_parses_to_path() -> None:
    args = build_parser().parse_args(["always-on", "--engine-state", "/tmp/es_x"])
    assert args.engine_state == Path("/tmp/es_x")


def test_always_on_threads_engine_state_to_run_daemon(tmp_path, monkeypatch) -> None:
    # The wiring obligation: --engine-state must reach run_daemon(engine_state_path=...),
    # not be silently dropped. Capture the kwargs and short-circuit before the heartbeat.
    import chat.always_on_daemon as daemon_mod

    class _Stop(Exception):
        pass

    captured: dict = {}

    def _fake_run_daemon(**kwargs):
        captured.update(kwargs)
        raise _Stop()  # stop before cmd_always_on's (un-mockable) summary epilogue

    monkeypatch.setattr(daemon_mod, "run_daemon", _fake_run_daemon)
    target = tmp_path / "branch_life"
    args = build_parser().parse_args(
        ["always-on", "--engine-state", str(target), "--max-beats", "0"]
    )
    with pytest.raises(_Stop):
        cmd_always_on(args)
    assert captured["engine_state_path"] == target


def test_identity_break_message_is_safe_and_revision_aware(tmp_path) -> None:
    # The humane recovery message: revision-aware option 1, the --engine-state escape
    # hatch, the underlying refusal preserved — and NEVER the mv/rm footgun (which would
    # destroy the engine_state Python package under the default dir; ADR-0220).
    state = tmp_path / "engine_state"
    state.mkdir()
    (state / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "turn_count": 7,
                "written_at_revision": "deadbeefcafe",
                "engine_identity": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    msg = _always_on_identity_break_message(state, RuntimeError("boom"))
    assert "git checkout deadbeefcafe" in msg  # copy-pasteable originating revision
    assert "--engine-state" in msg  # the safe per-life escape hatch
    assert "boom" in msg  # the original refusal is preserved
    assert "mv engine_state" not in msg  # the footgun is never suggested
    assert "rm -rf engine_state" not in msg


def test_identity_break_message_without_manifest_uses_placeholder(tmp_path) -> None:
    # No readable manifest -> placeholder revision, still structured, still safe,
    # and never degrades the path line to a bare "None".
    msg = _always_on_identity_break_message(tmp_path / "empty", RuntimeError("x"))
    assert "<checkpoint_revision>" in msg
    assert "mv engine_state" not in msg
    assert "rm -rf engine_state" not in msg
    assert "None" not in msg


def test_identity_break_message_handles_unresolvable_state_dir(monkeypatch) -> None:
    # Edge: no --engine-state given AND store resolution fails -> the path line must
    # fall back to a placeholder, never print a bare "None" (Gemini review nit).
    import engine_state as es_mod

    def _boom(*_a, **_k):
        raise RuntimeError("no store")

    # The helper does `from engine_state import EngineStateStore` at call time, so
    # patching the module attribute reaches it.
    monkeypatch.setattr(es_mod, "EngineStateStore", _boom)
    msg = _always_on_identity_break_message(None, RuntimeError("x"))
    assert "<engine_state_dir>" in msg  # path fell back, not None
    assert "<checkpoint_revision>" in msg  # rev fell back too
    assert "None" not in msg
