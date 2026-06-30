# ADR-0040: Structured-Logging Sink for Turn-Event Audit

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0035-turn-loop-verdict-surfacing.md`](ADR-0035-turn-loop-verdict-surfacing.md), [`ADR-0039-audit-completeness.md`](ADR-0039-audit-completeness.md)

## Context

ADR-0039 closed the in-memory audit gap: every turn (including stub
paths) appends a `TurnEvent` to `turn_log`, and every event carries a
`TurnVerdicts` bundle with `refusal_emitted` / `hedge_injected`
flags.  But `turn_log` is in-process state.  Any consumer outside
the runtime (offline replay, log aggregation, dashboards, an oncall
console) had to either:

* receive the runtime instance by reference and walk `turn_log`, or
* convert events to a wire format ad hoc each time.

Neither is appropriate for audit infrastructure.  This ADR adds the
canonical sink surface — a small, opinionated, **deterministic**
serialisation contract that produces one JSONL line per turn, plus
runtime auto-emission when a sink is attached.

CLAUDE.md's trust-boundary discipline applies directly:

> Centralize safe display/log handling before increasing logging.
> Avoid leaking raw sensitive tokens unless the command is
> explicitly local/debug.

That guidance pins the design choices below.

## Decision

`chat/telemetry.py` introduces:

* `serialize_turn_event(event, **kwargs) -> dict[str, object]` —
  pure function producing a JSON-safe audit dict.
* `format_turn_event_jsonl(event, **kwargs) -> str` — deterministic
  JSONL line (`sort_keys=True`, compact separators, no trailing
  newline).
* `TurnEventSink` — minimal Protocol (one method: `emit(line)`).
* `JsonlBufferSink` — in-memory implementation for tests and
  small-volume audit.
* `JsonlFileSink` — append-only file sink with eager flush and
  context-manager support.

`ChatRuntime` gains:

* `attach_telemetry_sink(sink, *, include_content=False)` — opt-in
  attachment; pass `None` to detach.
* `_emit_turn_event(event)` — internal helper called after every
  `turn_log.append` (main and stub paths).
* New private state `_telemetry_sink`, `_telemetry_include_content`.

### Trust-boundary defaults

* **Redact-by-default.**  `include_content=False` (the default) emits
  metadata only — turn id, pack ids, verdict ids and counts,
  remediation flags, versor condition, vault hits, cycle cost,
  dialogue role, stub-path flag.  No surface text, no input tokens.
  Audit infrastructure typically wants counts and ids, not raw user
  content; the redact-by-default stance prevents accidental PII or
  intent leakage when sinks point at shared log stores.
* **`include_content=True` is explicit, per-attachment.**  When the
  caller knows the sink is local-only (a debug session, a local
  replay file), they opt in at attachment time:
  ```python
  rt.attach_telemetry_sink(sink, include_content=True)
  ```
  Surfaces (`surface`, `walk_surface`, `articulation_surface`) and
  `input_tokens` then ride the wire.
* **Path fixed at construction.**  `JsonlFileSink(path)` resolves
  the path once.  No user-controlled paths are interpreted at emit
  time.  Parent directories are created if missing — convenient and
  consistent with append-only semantics.
* **Errors are not swallowed.**  A failing sink raises out of
  `chat()`.  The principle: a broken telemetry path should surface
  visibly, not silently drop the audit signal an operator was
  relying on.  Callers who want resilience can wrap the sink in
  their own error-tolerant shim.

### Determinism

* JSON keys are alphabetised (`sort_keys=True`); compact separators
  (`",", ":"`).  Same event → byte-identical line.
* No implicit wall-clock.  Timestamps are caller-provided via the
  `timestamp` kwarg (passed to the runtime-level emitter is a
  future extension if needed; current scope omits per-line
  timestamps because replay determinism is the primary audit goal).
* Field set is fixed.  Missing or differently-typed `TurnEvent`
  attributes fall back to safe defaults (`getattr(..., default)`)
  so an upstream `TurnEvent` schema change doesn't crash the
  serialiser — it produces a slightly older-shaped line until the
  emitter is updated.

### Wire format

Stable field set in every line (alphabetised):

| Field | Type | Notes |
|---|---|---|
| `cycle_cost_total` | float | Total per-turn cost. |
| `dialogue_role` | string | `"assert"`, `"question"`, `"refute"`, `"elaborate"`. |
| `ethics_pack_id` | string | Empty when not provided. |
| `ethics_runtime_checkable_count` | int | Predicates with evidence. |
| `ethics_upheld` | bool | False when any commitment violated. |
| `ethics_violated` | list[string] | Lex-sorted violated commitment ids. |
| `flagged` | bool | Identity-flagged. |
| `hedge_injected` | bool | ADR-0038. |
| `identity_alignment` | float | Present iff identity score present. |
| `identity_deviation_axes` | list[string] | Present iff identity score present. |
| `identity_flagged` | bool | Present iff identity score present. |
| `identity_pack_id` | string | |
| `refusal_emitted` | bool | ADR-0036/0037. |
| `safety_pack_id` | string | |
| `safety_runtime_checkable_count` | int | |
| `safety_upheld` | bool | |
| `safety_violated` | list[string] | Lex-sorted violated boundary ids. |
| `stub_path` | bool | `walk_surface == _UNKNOWN_DOMAIN_SURFACE`. |
| `turn` | int | |
| `vault_hits` | int | |
| `versor_condition` | float | |

When `include_content=True`, additionally:

| Field | Type | Notes |
|---|---|---|
| `articulation_surface` | string | |
| `input_tokens` | list[string] | |
| `surface` | string | User-facing surface (refusal/hedge applied). |
| `walk_surface` | string | Token-walk evidence. |

When the caller passes `timestamp=...`:

| Field | Type | Notes |
|---|---|---|
| `timestamp` | string | Caller's clock; runtime never adds its own. |

## Consequences

### Positive

* **Audit infrastructure unblocked.**  Log aggregators, replay
  systems, and dashboards now have a stable JSONL contract to
  consume.  No more reaching into private runtime state.
* **Default safe.**  PII-bearing content is opt-in.  A misconfigured
  shared log store doesn't leak user input by accident.
* **Deterministic replay.**  Same event → same line.  Replay-based
  testing of audit pipelines is straightforward.
* **Stub turns participate.**  ADR-0039's stub-path TurnEvent
  emission means audit consumers see *every* turn, not just main-path
  turns.  Stub paths flag themselves via `stub_path=true`.
* **Cheap.**  ~7 µs/turn for the metadata-only path on warm cache;
  one fsync per emit on the file sink.  Full smoke / runtime /
  cognition CLI suites unchanged in runtime.

### Negative / risks

* **No per-line timestamp by default.**  Replay determinism wins
  over operational convenience here.  Operators who want timestamps
  inject them at attachment time (future ADR could add a clock-dep
  hook on the runtime).
* **Sink errors propagate.**  A flaky sink can break `chat()`.
  This is deliberate (telemetry failures should be visible) but
  means callers shipping to production should wrap sinks in their
  own resilience layer.
* **Surface text is opt-in.**  A consumer who needs full surfaces
  (for example, a content-moderation replay) must explicitly enable
  `include_content=True` and accept the privacy/PII implications.
* **Two emission call sites.**  Main path and stub path each call
  `_emit_turn_event`.  Adding new turn paths later will need a
  matching call.  Mitigated by the small surface; a future ADR
  could unify into a single end-of-turn hook.

## Verification

* `tests/test_telemetry_sink.py` — 29 tests covering: pure
  serializer (metadata-only default, content opt-in, pack ids,
  refusal flag, stub-path flag, timestamp opt-in); deterministic
  JSONL (byte-identical for the same event, keys alphabetised, no
  trailing newline); sinks (`JsonlBufferSink` capture, `JsonlFileSink`
  append + newline + parent-dir creation + context manager + eager
  flush); runtime auto-emit (no-op without sink; one line per turn;
  parseable JSONL; default redaction; content opt-in; detach;
  pack-ids propagate; stub path emits; refusal visible through
  sink; sink errors propagate); file-sink full session round-trip;
  standalone event serialisation (no runtime required, sparse
  TurnEvent serialises, hedge flag from bundle).
* Combined pack-layer + telemetry suite: **199 tests, all green**
  (was 170 after ADR-0039; +29).
* CLI suites unchanged: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent 100%, versor_closure 100% — baseline
  preserved.

## Open questions deferred to a future ADR

1. **Runtime clock hook for timestamps.**  Inject a
   `Callable[[], str]` at attach time so emission picks up the
   caller's clock without giving the runtime an implicit
   wall-clock dependency.
2. **`core chat --show-verdicts` CLI flag.**  Read the verdicts off
   `ChatResponse` and print a human-readable summary per turn.
   Lives alongside this sink (the sink is for machines; the CLI
   flag is for operators).
3. **Sink fan-out.**  Today one sink at a time.  A multiplexer sink
   that forwards to N sinks (e.g., local file + remote aggregator)
   is a thin wrapper but should land with explicit error semantics.
4. **Schema versioning on emitted lines.**  Add a `schema_version`
   field to the JSONL records so downstream consumers can detect
   format changes deterministically.
5. **Rotation / size caps on `JsonlFileSink`.**  Current sink is
   append-only forever.  Rotation belongs in an operational layer
   (logrotate / systemd) but a sibling sink with built-in rotation
   could land if callers need it.
6. **Backpressure for high-volume sinks.**  Today emission is
   synchronous.  Async / queued sinks would let high-volume
   deployments tolerate slow downstream consumers without slowing
   `chat()`.
