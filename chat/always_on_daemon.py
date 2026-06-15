"""The always-on daemon shell — the thin process that RUNS the continuous-life heartbeat.

``chat/always_on.run_continuous`` is the reusable loop; this module is the daemon a
``core always-on`` invocation drives. It resolves the engine-state dir, takes a
single-instance lock (ONE life per engine-state dir — two daemons would corrupt the one
continuous life), installs SIGINT/SIGTERM handlers for a graceful stop, builds the
continuous-life ``ChatRuntime``, and runs the heartbeat unbounded until a signal — writing
the ``lived_life.json`` evidence the workbench reads and checkpointing so the next start
resumes the SAME life.

No new authority (CLAUDE.md): the heartbeat only ticks the proposal-only ``idle_tick`` and
READS ``versor_condition`` (no hot-path repair). It is FOREGROUND and explicit — there is
no hidden background execution; an operator backgrounds it with their shell / service
manager. The only writes are to the engine-state dir it was pointed at (the lock, the
manifest checkpoint, ``lived_life.json``).
"""

from __future__ import annotations

import dataclasses
import fcntl
import os
import signal
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from chat.always_on import (
    LIVED_LIFE_FILENAME,
    AlwaysOnReport,
    HeartbeatRecord,
    run_continuous,
)
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from engine_state import EngineStateStore

LOCK_FILENAME = "always_on.lock"

# The continuous-life config: persist the lived field/vault across reboot (Shape B+),
# learn from determined facts each beat (Step D), and REFUSE to resume a different-identity
# checkpoint (the load-time identity guard). So a daemon restart is the SAME life or it
# stops — never a silent fork.
CONTINUOUS_LIFE_CONFIG_FLAGS: dict[str, Any] = {
    "persist_session_state": True,
    "consolidate_determinations": True,
    "strict_identity_continuity": True,
}


class AlwaysOnLockedError(RuntimeError):
    """Another live always-on daemon already holds the lock for this engine-state dir."""


class _SingleInstanceLock:
    """Single-instance lock backed by an advisory OS lock (``fcntl.flock``).

    The kernel holds the lock for the lifetime of the open fd and releases it AUTOMATICALLY
    when the process dies — so there is no stale-lock window, no PID-reuse ambiguity, and no
    empty / half-written-file race (a pid-file scheme has all three: a loser of the create
    race can read a not-yet-written file and mistake a live holder for stale, then reclaim,
    and two daemons proceed over one life). The lock FILE is intentionally never unlinked —
    unlinking it would let a waiting peer flock a different inode — so the persistent marker
    also carries the holder's pid for a human-readable refusal message.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def _holder_pid(self) -> int | None:
        try:
            return int(self._path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            # The lock is held by another LIVE process (the kernel released it if the holder
            # died). Read the marker pid for the message; it is informational only.
            holder = self._holder_pid()
            os.close(fd)
            suffix = f" (pid {holder})" if holder is not None else ""
            raise AlwaysOnLockedError(
                f"another always-on daemon{suffix} holds {self._path}"
            ) from exc
        # We hold the kernel lock; stamp our pid as a human-readable marker (best-effort —
        # exclusion is the flock, not this content).
        try:
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
        except OSError:
            pass
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self._fd)
        self._fd = None


@dataclass(frozen=True, slots=True)
class DaemonResult:
    """The outcome of one daemon run — the heartbeat report + how it ended."""

    report: AlwaysOnReport
    engine_state_path: Path
    stopped_by_signal: bool


def continuous_life_config(base: RuntimeConfig | None = None) -> RuntimeConfig:
    """``base`` (or a default config) with the continuous-life flags forced on.

    Forced, not defaulted: the daemon's whole purpose is ONE continuous life, so persistence
    + consolidation + the strict identity guard are not optional knobs here."""
    cfg = base if base is not None else RuntimeConfig()
    return dataclasses.replace(cfg, **CONTINUOUS_LIFE_CONFIG_FLAGS)


def run_daemon(
    *,
    config: RuntimeConfig | None = None,
    engine_state_path: Path | None = None,
    interval: float = 1.0,
    max_beats: int | None = None,
    no_load_state: bool = False,
    on_record: Callable[[HeartbeatRecord], None] | None = None,
    install_signals: bool = True,
    stop_event: threading.Event | None = None,
) -> DaemonResult:
    """Run the always-on heartbeat as a daemon until a signal (or ``max_beats``).

    Resolves the engine-state dir, takes the single-instance lock (raising
    ``AlwaysOnLockedError`` if a live daemon already owns this life), installs
    SIGINT/SIGTERM handlers (unless ``install_signals=False`` — tests drive ``stop_event``
    directly), then runs ``run_continuous`` with the continuous-life config forced on and
    persists ``lived_life.json`` beside the checkpoint.

    ``install_signals=True`` must be called from the main thread (a Python signal-handler
    constraint); tests pass ``install_signals=False`` with their own ``stop_event``.
    """
    resolved = EngineStateStore(engine_state_path).path
    cfg = continuous_life_config(config)
    stop_event = stop_event if stop_event is not None else threading.Event()
    signalled = threading.Event()  # distinguishes a signal stop from a max_beats / test stop

    lock = _SingleInstanceLock(resolved / LOCK_FILENAME)
    lock.acquire()  # fail fast BEFORE any signal/runtime setup if another life is live

    previous_handlers: list[tuple[int, Any]] = []
    try:
        if install_signals:

            def _handle(_signum: int, _frame: Any) -> None:
                signalled.set()
                stop_event.set()

            for sig in (signal.SIGINT, signal.SIGTERM):
                old = signal.getsignal(sig)
                signal.signal(sig, _handle)  # record only AFTER it actually changed
                previous_handlers.append((sig, old))

        runtime = ChatRuntime(
            config=cfg, engine_state_path=resolved, no_load_state=no_load_state
        )
        # An ephemeral (no-load-state) life persists nothing — including no durable
        # lived_life.json, which would otherwise overwrite the persistent life's artifact.
        report_path = None if no_load_state else resolved / LIVED_LIFE_FILENAME
        report = run_continuous(
            runtime,
            heartbeats=max_beats,
            sleep_seconds=interval,
            stop=stop_event.is_set,
            on_heartbeat=on_record,
            report_path=report_path,
        )
    finally:
        for sig, handler in previous_handlers:
            # getsignal can return None for a non-Python handler; restore SIG_DFL then.
            signal.signal(sig, handler if handler is not None else signal.SIG_DFL)
        lock.release()

    return DaemonResult(
        report=report, engine_state_path=resolved, stopped_by_signal=signalled.is_set()
    )
