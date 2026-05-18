"""ADR-0055 Phase B — sinks for DiscoveryCandidate emission.

Mirrors the telemetry-sink shape from ADR-0040 / ADR-0041:

  - Protocol ``DiscoveryCandidateSink.emit(line)``.
  - ``DiscoveryBufferSink`` — in-memory, useful for tests and small-
    volume audit where persistence is the caller's responsibility.
  - ``DiscoveryMonthlyFileSink`` — append-only JSONL with per-month
    rollover under ``<root>/<YYYY>/<YYYY-MM>.jsonl``.  Path computed
    deterministically from an injected ``Clock`` so tests can pin
    the rollover instant without monkey-patching ``datetime``.

Trust boundary:

  - Append-only.  No truncation, no rewrite.  Each ``emit()`` flushes
    so a crashed runtime keeps its prior candidates durable on disk.
  - Sink errors are NOT swallowed by the runtime — Phase B keeps
    telemetry's fail-fast contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Callable, Protocol


class DiscoveryCandidateSink(Protocol):
    """Minimal sink contract — one JSONL line per emission."""

    def emit(self, line: str) -> None: ...


@dataclass
class DiscoveryBufferSink:
    """In-memory sink that captures every emitted candidate line."""

    lines: list[str] = field(default_factory=list)

    def emit(self, line: str) -> None:
        self.lines.append(line)


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DiscoveryMonthlyFileSink:
    """Append-only JSONL sink with monthly rollover.

    Path is computed at each ``emit()`` from the injected clock as
    ``<root>/<YYYY>/<YYYY-MM>.jsonl``.  The file handle is reopened
    when the month rolls over; the previous month's file is closed
    cleanly.

    The clock is injected (default UTC) so tests can pin the
    rollover instant without monkey-patching ``datetime``.
    """

    def __init__(self, root: str | Path, *, clock: Clock = _utc_now) -> None:
        self._root = Path(root)
        self._clock = clock
        self._fh: IO[str] | None = None
        self._current_path: Path | None = None

    def _path_for_now(self) -> Path:
        now = self._clock()
        return self._root / f"{now.year:04d}" / f"{now.year:04d}-{now.month:02d}.jsonl"

    def emit(self, line: str) -> None:
        target = self._path_for_now()
        if target != self._current_path:
            if self._fh is not None:
                self._fh.close()
                self._fh = None
            target.parent.mkdir(parents=True, exist_ok=True)
            self._fh = target.open("a", encoding="utf-8")
            self._current_path = target
        assert self._fh is not None
        self._fh.write(line)
        self._fh.write("\n")
        self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
            self._current_path = None

    def __enter__(self) -> "DiscoveryMonthlyFileSink":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


__all__ = [
    "DiscoveryCandidateSink",
    "DiscoveryBufferSink",
    "DiscoveryMonthlyFileSink",
]
