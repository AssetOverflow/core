"""generate/bridge_trace.py — per-turn articulation bridge trace.

Phase 1 of the full-sentence output mastery plan.  Every call to
``articulate_with_intent()`` in ``generate/intent_bridge.py`` emits
one ``BridgeTraceRecord`` through the module-level sink when a sink
has been attached.  When no sink is attached the emission is a pure
no-op with zero overhead beyond the ``is None`` check.

Follows the same trust-boundary conventions as ADR-0040
(``chat/telemetry.py``):

* **Redact-by-default.**  ``recalled_words_sample`` and
  ``bridge_surface`` are only included in the serialized record when
  the caller sets ``include_content=True``.
* **No implicit wall-clock.**  ``timestamp`` is caller-provided.
* **Append-only file paths.**  ``JsonlFileSink`` opens in append mode.
* **Idempotent flush.**  Each ``emit()`` flushes immediately.

The record covers every diagnostic dimension named in the mastery
plan's Phase 1.3 trace specification:

  intent_tag            — classifier output (string name of IntentTag)
  intent_subject        — classifier subject slot
  plan_subject          — ArticulationPlan.subject
  plan_predicate        — ArticulationPlan.predicate
  plan_object           — ArticulationPlan.object (None → empty string)
  recalled_words_len    — len(recalled_words) passed to the bridge
  recalled_words_sample — first 5 recalled words (content-gated)
  pre_ground_obj        — graph node obj before ground_graph() ran
  post_ground_obj       — graph node obj after ground_graph() ran
  bridge_surface        — the surface the bridge produced (content-gated)
  bridge_useful         — whether _is_useful_surface() passed
  fallback_surface      — ArticulationPlan.surface (content-gated)

See ``docs/decisions/full-sentence-output-plan.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Protocol


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BridgeTraceRecord:
    """One per-turn observation record from the intent bridge.

    All fields are plain Python types so serialization is trivial and
    the record is safe to construct inside the hot path without any
    I/O or numpy dependency.
    """

    intent_tag: str                          # IntentTag.name (e.g. "DEFINITION")
    intent_subject: str                      # classifier subject slot, "" if None
    plan_subject: str
    plan_predicate: str
    plan_object: str                         # "" when ArticulationPlan.object is None
    recalled_words_len: int
    recalled_words_sample: tuple[str, ...]   # first ≤5 words; () when redacted
    pre_ground_obj: str                      # graph p0.obj before ground_graph
    post_ground_obj: str                     # graph p0.obj after ground_graph
    bridge_surface: str                      # "" when redacted
    bridge_useful: bool
    fallback_surface: str                    # "" when redacted


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def serialize_bridge_trace(
    record: BridgeTraceRecord,
    *,
    include_content: bool = False,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Produce a JSON-safe audit dict from a ``BridgeTraceRecord``.

    Content fields (``recalled_words_sample``, ``bridge_surface``,
    ``fallback_surface``) are only emitted when ``include_content``
    is True.  The metadata fields are always emitted so aggregation
    pipelines can compute grounding-rate statistics without ever
    seeing raw surface text.
    """
    out: dict[str, object] = {
        "type": "bridge_trace",
        "intent_tag": record.intent_tag,
        "intent_subject_len": len(record.intent_subject),
        "plan_subject_len": len(record.plan_subject),
        "plan_predicate_len": len(record.plan_predicate),
        "plan_object_present": bool(record.plan_object),
        "recalled_words_len": record.recalled_words_len,
        "pre_ground_obj_pending": record.pre_ground_obj in ("<pending>", "<prior>"),
        "post_ground_obj_pending": record.post_ground_obj in ("<pending>", "<prior>"),
        "bridge_useful": record.bridge_useful,
        # Derived diagnostic flag: grounding changed something.
        "grounding_changed_obj": record.pre_ground_obj != record.post_ground_obj,
    }
    if include_content:
        out["intent_subject"] = record.intent_subject
        out["plan_subject"] = record.plan_subject
        out["plan_predicate"] = record.plan_predicate
        out["plan_object"] = record.plan_object
        out["recalled_words_sample"] = list(record.recalled_words_sample)
        out["pre_ground_obj"] = record.pre_ground_obj
        out["post_ground_obj"] = record.post_ground_obj
        out["bridge_surface"] = record.bridge_surface
        out["fallback_surface"] = record.fallback_surface
    if timestamp is not None:
        out["timestamp"] = str(timestamp)
    return out


def format_bridge_trace_jsonl(
    record: BridgeTraceRecord,
    *,
    include_content: bool = False,
    timestamp: str | None = None,
) -> str:
    """Serialize one trace record as a deterministic JSONL line.

    Field order is alphabetical (``sort_keys=True``) for byte-stable
    replay diffing.  No trailing newline — the sink owns termination.
    """
    payload = serialize_bridge_trace(
        record, include_content=include_content, timestamp=timestamp
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Sink protocol
# ---------------------------------------------------------------------------


class BridgeTraceSink(Protocol):
    """Minimal sink contract (mirrors TurnEventSink in chat/telemetry.py).

    Sinks receive one already-serialized JSONL line per
    ``articulate_with_intent()`` call.  The sink is attached at the
    module level via ``attach_bridge_trace_sink``; callers that never
    attach a sink pay only the ``is None`` guard cost.
    """

    def emit(self, line: str) -> None: ...


# ---------------------------------------------------------------------------
# Concrete sinks
# ---------------------------------------------------------------------------


@dataclass
class JsonlBufferSink:
    """In-memory sink that captures every emitted line.

    Useful for tests and interactive session analysis where
    persistence is the caller's responsibility.
    """

    lines: list[str] = field(default_factory=list)
    include_content: bool = False

    def emit(self, line: str) -> None:
        self.lines.append(line)

    def records(self) -> list[dict]:
        """Parse all emitted lines and return them as dicts."""
        return [json.loads(line) for line in self.lines]

    def grounding_rate(self) -> float:
        """Fraction of turns where the bridge produced a useful surface.

        Returns 0.0 when no lines have been emitted yet.
        """
        parsed = self.records()
        if not parsed:
            return 0.0
        return sum(1 for r in parsed if r.get("bridge_useful")) / len(parsed)

    def pending_rate(self) -> float:
        """Fraction of turns where the post-ground obj was still <pending>.

        Returns 0.0 when no lines have been emitted yet.
        """
        parsed = self.records()
        if not parsed:
            return 0.0
        return sum(1 for r in parsed if r.get("post_ground_obj_pending")) / len(parsed)

    def recalled_words_empty_rate(self) -> float:
        """Fraction of turns where recalled_words_len == 0."""
        parsed = self.records()
        if not parsed:
            return 0.0
        return sum(1 for r in parsed if r.get("recalled_words_len", 0) == 0) / len(parsed)

    def summary(self) -> dict:
        """One-shot diagnostic summary dict for operator inspection."""
        parsed = self.records()
        n = len(parsed)
        if n == 0:
            return {"turns": 0}
        by_intent: dict[str, dict] = {}
        for r in parsed:
            tag = r.get("intent_tag", "UNKNOWN")
            bucket = by_intent.setdefault(tag, {"total": 0, "useful": 0, "pending": 0, "no_recalled": 0})
            bucket["total"] += 1
            if r.get("bridge_useful"):
                bucket["useful"] += 1
            if r.get("post_ground_obj_pending"):
                bucket["pending"] += 1
            if r.get("recalled_words_len", 0) == 0:
                bucket["no_recalled"] += 1
        return {
            "turns": n,
            "grounding_rate": round(self.grounding_rate(), 4),
            "pending_rate": round(self.pending_rate(), 4),
            "recalled_words_empty_rate": round(self.recalled_words_empty_rate(), 4),
            "by_intent": by_intent,
        }


class JsonlFileSink:
    """Append-only JSONL file sink with eager flush.

    Path fixed at construction.  Each ``emit()`` flushes immediately
    so a crashed turn loop still has prior turns durable on disk.
    Supports context-manager usage.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        include_content: bool = False,
    ) -> None:
        self._path = Path(path)
        self._include_content = include_content
        self._fh: IO[str] | None = None

    def emit(self, line: str) -> None:
        if self._fh is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self._path.open("a", encoding="utf-8")
        self._fh.write(line)
        self._fh.write("\n")
        self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "JsonlFileSink":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


@dataclass
class FanOutSink:
    """Forward every emitted line to N sinks in declaration order.

    Fail-fast: if sink *i* raises, sinks *i+1..* are NOT called.
    """

    sinks: tuple = ()  # tuple[BridgeTraceSink, ...]

    def emit(self, line: str) -> None:
        for sink in self.sinks:
            sink.emit(line)


__all__ = [
    "BridgeTraceRecord",
    "BridgeTraceSink",
    "FanOutSink",
    "JsonlBufferSink",
    "JsonlFileSink",
    "format_bridge_trace_jsonl",
    "serialize_bridge_trace",
]
