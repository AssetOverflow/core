"""teaching/oov_sink.py — Phase 2.3 emission for OOV "teach me" turns.

Mirrors :mod:`teaching.discovery_sink`.  When the runtime emits a P2.1
OOV invitation surface (``grounding_source="oov"``), it forwards a
structured :class:`OOVCandidate` JSONL line to the attached sink so
the operator's aggregation tooling can rank vocabulary gaps the same
way discovery candidates surface chain gaps.

Trust boundary:

  - Append-only.  No truncation, no rewrite.  Each ``emit()`` flushes
    so a crashed runtime keeps its prior OOV signals durable on disk.
  - Sink errors are NOT swallowed — fail-fast contract matches
    discovery and telemetry sinks.
  - The sink receives a sanitised candidate (the token has already
    passed through ``core._safe_display.safe_display`` at the runtime
    boundary before any persistence).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Callable, Literal, Protocol


@dataclass(frozen=True, slots=True)
class OOVCandidate:
    """Structured evidence that a turn hit an OOV token.

    Fields parallel :class:`teaching.discovery.DiscoveryCandidate`
    but the schema is OOV-specific.  ``trigger="unresolved_subject"``
    is the only v1 trigger; future Phase 2 work can add others
    (e.g. ``"unresolved_secondary_subject"`` for partial-grounding
    sinks).
    """

    candidate_id: str
    token: str
    intent: Literal[
        "definition", "recall", "cause", "verification",
        "comparison", "procedure", "correction",
    ]
    trigger: Literal["unresolved_subject"]
    source_turn_trace: str
    boundary_clean: bool
    review_state: Literal["unreviewed"] = "unreviewed"

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "token": self.token,
            "intent": self.intent,
            "trigger": self.trigger,
            "source_turn_trace": self.source_turn_trace,
            "boundary_clean": self.boundary_clean,
            "review_state": self.review_state,
        }


def hash_oov_candidate_id(token: str, intent: str, trace_hash: str) -> str:
    """Deterministic 32-char hex id for an OOV candidate.

    Identical ``(token, intent, trace_hash)`` always produces the
    identical id — the load-bearing replay property analogous to
    :func:`teaching.discovery._hash_candidate_id`.
    """
    payload = json.dumps(
        {"token": token, "intent": intent, "source_turn_trace": trace_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def format_oov_candidate_jsonl(candidate: OOVCandidate) -> str:
    """Render a candidate as one canonical JSONL line."""
    return json.dumps(candidate.as_dict(), sort_keys=True, separators=(",", ":"))


class OOVCandidateSink(Protocol):
    """Minimal sink contract — one JSONL line per emission."""

    def emit(self, line: str) -> None: ...


@dataclass
class OOVBufferSink:
    """In-memory sink that captures every emitted candidate line."""

    lines: list[str] = field(default_factory=list)

    def emit(self, line: str) -> None:
        self.lines.append(line)


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OOVMonthlyFileSink:
    """Append-only JSONL sink with monthly rollover.

    Path is computed at each ``emit()`` from the injected clock as
    ``<root>/<YYYY>/<YYYY-MM>.jsonl``.  Same on-disk shape as
    :class:`teaching.discovery_sink.DiscoveryMonthlyFileSink` so the
    aggregator can reuse the file-walk machinery.
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

    def __enter__(self) -> "OOVMonthlyFileSink":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


__all__ = [
    "OOVCandidate",
    "OOVCandidateSink",
    "OOVBufferSink",
    "OOVMonthlyFileSink",
    "format_oov_candidate_jsonl",
    "hash_oov_candidate_id",
]
