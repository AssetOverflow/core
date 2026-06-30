# ADR-0059 — Correction-Pass Telemetry Emission

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

`ChatRuntime.correct(text, target_turn=-1)` propagates a backward
perturbation through the session graph: each past turn whose output
versor has non-trivial CGA-alignment with the correction versor is
blended toward it (decayed by graph distance).  The mechanism is
documented in `session/correction.py`; `CorrectionPass.apply()`
returns a `CorrectionResult` carrying:

- `records: tuple[CorrectionRecord, ...]` — per-turn old/new versors,
  alignment, decay, blend weight, distance from the correction-origin.
- `turns_affected: int`
- `turns_skipped: int`

The forward regen turn that follows `correct()` emits its own
`TurnEvent` via the existing telemetry sink.  But the **backward
perturbation itself** — which past turns moved, by how much, and
toward what — was invisible to the telemetry sink.

That gap matters for the audit story:

- The session graph's state changed *between* turn events.  A future
  replay of the session would see two turn events whose deltas don't
  add up unless the audit consumer knows a correction happened.
- The ADR-0055..0057 reviewed-corpus story rests on **every state
  change** being inspectable.  A backward correction that no sink
  records is a structurally invisible mutation.

---

## Decision

Emit one JSONL line per `correct()` invocation, discriminated by
`"type": "correction"`, to the existing telemetry sink.  Same sink
contract as `TurnEvent`; new event type alongside.

### Payload

```json
{
  "type": "correction",
  "target_turn": -1,
  "identity_pack_id": "default_general_v1",
  "safety_pack_id": "core_safety_axes_v1",
  "ethics_pack_id": "default_general_ethics_v1",
  "records_count": 1,
  "turns_skipped": 0,
  "turn_idxs_affected": [1],
  "max_delta_norm": 1.3337411880493164,
  "mean_delta_norm": 1.3337411880493164,
  "correction_versor_digest": "e7e98af75ff6b4475807ed66f0672ec0cfab6f205896f8e626fc1490026ed597"
}
```

- `records_count` / `turns_skipped` — how many turns were perturbed
  vs filtered by the minimum-alignment threshold.
- `turn_idxs_affected` — sorted tuple of affected turn indices.
  Lets a downstream consumer correlate the correction with the
  specific past turn events it perturbed.
- `max_delta_norm` / `mean_delta_norm` — L2 distance between
  old and new versors per record, max and mean across records.
  Magnitude of the backward perturbation without leaking
  coordinates.
- `correction_versor_digest` — SHA-256 hex of the correction
  versor's float32 bytes.  Deterministic identifier for the
  perturbation source; pairs identical corrections across runs
  without exposing coordinates.

### Trust boundary (per CLAUDE.md)

- **Metadata-only.**  No raw versor coordinates ever appear in the
  payload — `old_versor`, `new_versor`, `correction_versor` are not
  serialised.  Only the L2 deltas and the SHA-256 digest.
- **No implicit wall-clock.**  Timestamp is caller-provided (kwarg);
  the runtime does not reach for `datetime.now()` on this path.
- **Deterministic.**  Same `CorrectionResult` → byte-identical line.
  `sort_keys=True` in the serialiser; record order matches
  `CorrectionPass.apply` insertion order (deterministic).
- **No-op without a sink.**  When no telemetry sink is attached,
  `_emit_correction_event` returns immediately — `correct()`
  behaviour is byte-identical to pre-ADR-0059.
- **Sink errors propagate.**  Mirrors `_emit_turn_event`'s contract:
  a misconfigured durable sink surfaces loudly rather than
  silently dropping audit evidence.

---

## Why a discriminated event, not an extended turn event

Two options were considered:

1. **Add a `correction_event` block to `TurnEvent`.**  Same line,
   optional field.  Lighter touch but pollutes the turn-event
   schema with a payload that's only present on `correct()` calls,
   and conflates two semantically distinct events (the backward
   perturbation and the forward regen turn).

2. **Emit a separate event with a `"type": "correction"` discriminator.**
   New line type alongside turn events.  Sink contract unchanged
   (still `emit(line: str)`); consumers discriminate by reading
   the `"type"` field (absent on turn events today, present on
   correction events).

Path (2) chosen because:
- It keeps the turn-event schema clean.
- It models the underlying event structure honestly: a `correct()`
  call produces two events (the perturbation, then the regen turn),
  not one composite turn event.
- It composes with the existing `FanOutSink` and `JsonlFileSink`
  unchanged.
- A future `_emit_supersession_event`, `_emit_proposal_event`, etc.
  can follow the same discriminator pattern.

---

## Consequences

### What changes

- `chat/telemetry.py` gains `serialize_correction_event` and
  `format_correction_event_jsonl`.  No changes to existing
  serialisers.
- `chat/runtime.py` adds `_emit_correction_event` (mirrors
  `_emit_turn_event`) and calls it from `correct()` after the
  graph state is updated but before the forward regen turn.

### What does not change

- Sink contract: still `emit(line: str)`.
- Existing telemetry consumers that key off the absence of a
  `"type"` field (treating every line as a turn event) keep
  working — they'll see correction lines and either ignore them
  or fail loudly, depending on their parser.  Recommended consumer
  pattern: dispatch on `payload.get("type", "turn")`.
- `CorrectionPass` itself is untouched; `CorrectionResult` already
  carried everything the event needs.
- `versor_condition < 1e-6` invariant: this ADR adds telemetry
  emission only; no field state is touched.

---

## Verification

```
tests/test_correction_telemetry.py                    7 passed

  - no_emission_without_sink
  - emission_when_sink_attached
  - correction_payload_shape (required keys, types, ranges)
  - correction_versor_digest_is_sha256_prefix_or_empty
  - no_versor_coordinates_in_payload  (trust boundary)
  - correction_event_is_deterministic_across_runs (byte-identical lines)
  - turn_event_and_correction_event_coexist

Lanes (regression check):
  core test --suite smoke         67 passed
  core test --suite runtime       19 passed
```

---

## Cross-References

- [ADR-0040](./ADR-0040-telemetry-sink.md) — the structured-logging
  sink this ADR adds an event type to.
- [ADR-0039](./ADR-0039-bundled-turn-verdicts.md) — the
  `TurnVerdicts` bundle that made every turn event uniform.
- [ADR-0055](./ADR-0055-inter-session-memory-discovery-promotion.md)
  — the broader inter-session-memory architecture where every state
  change must be inspectable, of which correction events are now part.
