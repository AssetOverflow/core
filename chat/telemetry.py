"""ADR-0040 — structured-logging sink for turn-event audit.

Consumes ``TurnEvent`` records that ADR-0039 makes uniform across
main and stub paths.  Emits one JSON-line per turn with deterministic
field ordering, suitable for log aggregation, replay, and offline
audit pipelines.

Trust boundary (per CLAUDE.md):

* **Metadata-only by default.**  Surface text and input tokens are
  redacted unless the caller explicitly opts in via
  ``include_content=True``.  Audit needs counts, ids, and flags —
  not raw content — and the redact-by-default stance prevents
  accidental PII leakage when sinks point at shared log stores.
* **No implicit wall-clock.**  Timestamps are caller-provided so
  emission is reproducible under replay.  The runtime never reaches
  for ``datetime.now()`` here.
* **Append-only file paths.**  ``JsonlFileSink`` opens the target in
  append mode and never truncates.  Path is fixed at construction;
  the sink does not interpret user-controlled paths at emit time.
* **Idempotent flush.**  Each ``emit()`` flushes immediately so a
  crashed turn loop still has its prior turns durable on disk.

See ``docs/decisions/ADR-0040-telemetry-sink.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Protocol


_UNKNOWN_DOMAIN_SURFACE = "I don't know — insufficient grounding for that yet."


# ---------- pure serializer ----------


def serialize_turn_event(
    event,
    *,
    safety_pack_id: str = "",
    ethics_pack_id: str = "",
    identity_pack_id: str = "",
    include_content: bool = False,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Produce a JSON-safe audit dict from a ``TurnEvent``.

    Pack ids are passed as kwargs because ``TurnEvent`` does not
    carry them — the runtime knows them.  Fields are typed
    deliberately at the boundary so an upstream change to
    ``TurnEvent`` doesn't silently break the wire format; missing or
    differently-typed values fall back to safe defaults.
    """
    verdicts = getattr(event, "verdicts", None)
    out: dict[str, object] = {
        "turn": int(getattr(event, "turn", 0)),
        "safety_pack_id": str(safety_pack_id),
        "ethics_pack_id": str(ethics_pack_id),
        "identity_pack_id": str(identity_pack_id),
        "refusal_emitted": bool(getattr(verdicts, "refusal_emitted", False)),
        "hedge_injected": bool(getattr(verdicts, "hedge_injected", False)),
        "versor_condition": float(getattr(event, "versor_condition", 0.0)),
        "vault_hits": int(getattr(event, "vault_hits", 0)),
        "cycle_cost_total": float(getattr(event, "cycle_cost_total", 0.0)),
        "flagged": bool(getattr(event, "flagged", False)),
        "stub_path": getattr(event, "walk_surface", "") == _UNKNOWN_DOMAIN_SURFACE,
        "dialogue_role": str(getattr(event, "dialogue_role", "")),
        # ADR-0072 (R5) — operator-visible register identity per turn.
        # Empty strings on pre-R5 events / UNREGISTERED runtimes / empty
        # marker buckets, so the wire format degrades cleanly.
        "register_id": str(getattr(event, "register_id", "") or ""),
        "register_variant_id": str(getattr(event, "register_variant_id", "") or ""),
        # ADR-0073d (L1.4) — operator-visible anchor-lens identity per
        # turn.  Empty strings on pre-L1.4 events / UNANCHORED runtimes /
        # turns where the lens did not engage.
        "anchor_lens_id": str(getattr(event, "anchor_lens_id", "") or ""),
        "anchor_lens_mode_label": str(getattr(event, "anchor_lens_mode_label", "") or ""),
        # ADR-0075 (C1) — realizer slot-type guard verdict per turn.
        # Empty strings on pre-C1 events; closed enums otherwise.
        "realizer_guard_status": str(getattr(event, "realizer_guard_status", "") or ""),
        "realizer_guard_rule": str(getattr(event, "realizer_guard_rule", "") or ""),
    }
    safety = getattr(event, "safety_verdict", None)
    if safety is not None:
        out["safety_violated"] = sorted(
            getattr(safety, "violated_boundaries", ()) or ()
        )
        out["safety_runtime_checkable_count"] = int(
            getattr(safety, "runtime_checkable_count", 0)
        )
        out["safety_upheld"] = bool(getattr(safety, "upheld", True))
    ethics = getattr(event, "ethics_verdict", None)
    if ethics is not None:
        out["ethics_violated"] = sorted(
            getattr(ethics, "violated_commitments", ()) or ()
        )
        out["ethics_runtime_checkable_count"] = int(
            getattr(ethics, "runtime_checkable_count", 0)
        )
        out["ethics_upheld"] = bool(getattr(ethics, "upheld", True))
    identity_score = getattr(event, "identity_score", None)
    if identity_score is not None:
        out["identity_alignment"] = float(
            getattr(identity_score, "alignment", 0.0)
        )
        out["identity_flagged"] = bool(getattr(identity_score, "flagged", False))
        out["identity_deviation_axes"] = sorted(
            getattr(identity_score, "deviation_axes", ()) or ()
        )
    if include_content:
        out["input_tokens"] = list(getattr(event, "input_tokens", ()))
        out["surface"] = str(getattr(event, "surface", ""))
        out["walk_surface"] = str(getattr(event, "walk_surface", ""))
        out["articulation_surface"] = str(
            getattr(event, "articulation_surface", "")
        )
    if timestamp is not None:
        out["timestamp"] = str(timestamp)
    return out


def format_turn_event_jsonl(event, **kwargs) -> str:
    """Serialize a turn event as one deterministic JSONL line.

    Field order is alphabetical (``sort_keys=True``) so two emissions
    of the same logical event produce byte-identical lines.  No
    trailing newline — the sink owns line termination.
    """
    payload = serialize_turn_event(event, **kwargs)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# ---------- ADR-0059 — correction-event serializer ----------


def serialize_correction_event(
    correction_result,
    *,
    target_turn: int,
    identity_pack_id: str = "",
    safety_pack_id: str = "",
    ethics_pack_id: str = "",
    timestamp: str | None = None,
) -> dict[str, object]:
    """Produce a JSON-safe audit dict from a ``CorrectionResult``.

    Distinct from a turn event: this records the *backward* update to
    a session graph triggered by ``ChatRuntime.correct()``.  The
    forward regen turn that follows still emits its own turn event;
    this event documents the perturbation itself so audit consumers
    can answer "which past turns moved, by how much, and toward what".

    Trust boundary (per CLAUDE.md):

    * **Metadata-only.**  Versor coordinates are NOT emitted — only
      the L2-delta-norm-per-record and a SHA-256 digest of the
      correction versor's float32 bytes (deterministic identifier).
    * **No implicit wall-clock.**  ``timestamp`` is caller-provided.
    * **Deterministic.**  Same ``CorrectionResult`` → byte-identical
      serialized line.  ``records`` are traversed in their tuple
      order (deterministic, matches insertion order from
      ``CorrectionPass.apply``).
    """
    import hashlib
    import math

    records = getattr(correction_result, "records", ()) or ()
    correction_versor = getattr(correction_result, "correction_versor", None)

    # Per-record L2 deltas + the max across records.
    deltas: list[float] = []
    turn_idxs: list[int] = []
    for r in records:
        old_v = getattr(r, "old_versor", None)
        new_v = getattr(r, "new_versor", None)
        if old_v is None or new_v is None:
            continue
        # numpy.ndarray subtraction + norm; pure stdlib fallback would
        # be slower but the runtime already imports numpy on this path.
        import numpy as np
        delta = float(np.linalg.norm(np.asarray(new_v) - np.asarray(old_v)))
        if math.isfinite(delta):
            deltas.append(delta)
        turn_idxs.append(int(getattr(r, "turn_idx", 0)))

    # SHA-256 digest of the correction versor's float32 bytes — gives
    # a stable identifier for the perturbation without leaking
    # coordinates.  Falls back to empty string when missing.
    digest = ""
    if correction_versor is not None:
        import numpy as np
        digest = hashlib.sha256(
            np.asarray(correction_versor, dtype=np.float32).tobytes()
        ).hexdigest()

    out: dict[str, object] = {
        "type": "correction",
        "target_turn": int(target_turn),
        "identity_pack_id": str(identity_pack_id),
        "safety_pack_id": str(safety_pack_id),
        "ethics_pack_id": str(ethics_pack_id),
        "records_count": int(getattr(correction_result, "turns_affected", len(records))),
        "turns_skipped": int(getattr(correction_result, "turns_skipped", 0)),
        "turn_idxs_affected": sorted(turn_idxs),
        "max_delta_norm": max(deltas) if deltas else 0.0,
        "mean_delta_norm": (sum(deltas) / len(deltas)) if deltas else 0.0,
        "correction_versor_digest": digest,
    }
    if timestamp is not None:
        out["timestamp"] = str(timestamp)
    return out


def format_correction_event_jsonl(correction_result, **kwargs) -> str:
    """Serialize a correction event as one deterministic JSONL line.

    The ``"type": "correction"`` field discriminates this line from
    turn events at consume time without changing the sink contract.
    """
    payload = serialize_correction_event(correction_result, **kwargs)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# ---------- sink protocol ----------


class TurnEventSink(Protocol):
    """Minimal sink contract.

    Sinks receive one already-serialized JSONL line per turn.  The
    runtime calls ``emit()`` after each ``turn_log.append()`` — see
    ``ChatRuntime._emit_turn_event``.
    """

    def emit(self, line: str) -> None: ...


# ---------- concrete sinks ----------


@dataclass
class JsonlBufferSink:
    """In-memory sink that captures every emitted line.

    Useful for tests, replay diffing, and small-volume audit where
    persistence is the caller's responsibility.
    """

    lines: list[str] = field(default_factory=list)

    def emit(self, line: str) -> None:
        self.lines.append(line)


class JsonlFileSink:
    """Append-only JSONL file sink with eager flush.

    The path is fixed at construction.  Each ``emit()`` flushes
    immediately so a crashed runtime still has its prior turns
    durable on disk.  Supports context-manager usage.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
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


# ---------- fan-out ----------


@dataclass
class FanOutSink:
    """Forward every emitted line to N sinks in declaration order.

    ADR-0041.  Composes with any combination of sinks — typically
    ``JsonlFileSink`` (durable) + ``JsonlBufferSink`` (in-memory
    audit), or two file sinks (local + shadow).

    **Error semantics:** fail-fast.  If sink *i* raises, sinks *i+1..*
    are NOT called and the exception propagates to the caller.  This
    is consistent with the single-sink contract: telemetry failures
    surface, never silently drop audit signal.  Callers wanting
    partial-success semantics wrap individual sinks in their own
    error-tolerant shim.
    """

    sinks: tuple = ()  # tuple[TurnEventSink, ...]

    def emit(self, line: str) -> None:
        for sink in self.sinks:
            sink.emit(line)


# ---------- operator-facing summary formatter ----------


def format_verdict_summary(verdicts) -> str:
    """ADR-0041 — one-line human-readable summary of a TurnVerdicts bundle.

    Used by ``core chat --show-verdicts`` to print a per-turn audit
    line to the operator.  Distinct from ``format_turn_event_jsonl``
    (machine-facing): this is dense, terse, and skims the high-signal
    fields.  Empty string when ``verdicts`` is None.

    Format::

        [identity=0.83 safety=ok ethics=ok refusal=- hedge=-]
        [identity=0.42 safety=VIOLATED:preserve_versor_closure ethics=ok refusal=YES hedge=-]
    """
    if verdicts is None:
        return ""
    parts: list[str] = []
    identity = getattr(verdicts, "identity_score", None)
    if identity is not None:
        alignment = float(getattr(identity, "alignment", 0.0))
        parts.append(f"identity={alignment:.2f}")
    else:
        parts.append("identity=-")
    safety = getattr(verdicts, "safety_verdict", None)
    parts.append(_format_verdict_short(
        safety, "safety", id_attr="violated_boundaries",
    ))
    ethics = getattr(verdicts, "ethics_verdict", None)
    parts.append(_format_verdict_short(
        ethics, "ethics", id_attr="violated_commitments",
    ))
    parts.append(
        "refusal=YES" if getattr(verdicts, "refusal_emitted", False)
        else "refusal=-"
    )
    parts.append(
        "hedge=YES" if getattr(verdicts, "hedge_injected", False)
        else "hedge=-"
    )
    return "[" + " ".join(parts) + "]"


def _format_verdict_short(verdict, label: str, *, id_attr: str) -> str:
    if verdict is None:
        return f"{label}=-"
    violated = sorted(getattr(verdict, id_attr, ()) or ())
    if not violated:
        return f"{label}=ok"
    return f"{label}=VIOLATED:{','.join(violated)}"


__all__ = [
    "FanOutSink",
    "JsonlBufferSink",
    "JsonlFileSink",
    "TurnEventSink",
    "format_correction_event_jsonl",
    "format_turn_event_jsonl",
    "format_verdict_summary",
    "serialize_correction_event",
    "serialize_turn_event",
]
