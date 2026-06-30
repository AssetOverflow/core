# ADR-0158 — reboot_event audit trail entry (W-024 / L10b.3)

Status: accepted
Date: 2026-05-26

## Context

L10 scope §Sub-question 3 asked:

> **What does reboot record?** A `reboot_event` analog of `TurnEvent`,
> written to the audit trail, that lets future audit reconstruct the fact
> that this engine instance lost and regained its lifetime here.

ADR-0156 §"Out of scope" deferred this to L10b.3 / W-024. After W-022
(atomic writes) and W-023 (revision-mismatch warning), the checkpoint path
is now correct and observable. The missing piece is the audit record itself:
without it, the telemetry JSONL cannot distinguish a fresh start from a
reboot recovery, making the engine's lifetime history uninterpretable.

## Decision

### Serializer (`chat/telemetry.py`)

Add `serialize_reboot_event(...)` and `format_reboot_event_jsonl(...)`,
following the same pattern as `serialize_correction_event` / ADR-0059:

```jsonc
{
  "type": "reboot",                  // discriminator
  "restored_turn_count": 5,          // manifest["turn_count"]
  "stored_revision": "abc123",       // manifest["written_at_revision"]
  "current_revision": "def456",      // _git_revision() at load time
  "revision_matched": false,         // true iff both known and equal
  "recognizers_count": 2,            // DerivedRecognizers restored
  "candidates_count": 1,             // DiscoveryCandidates restored
  "timestamp": "..."                 // optional, caller-provided
}
```

`revision_matched` is `False` when either side is `"unknown"` or `""` —
the same guard as W-023's warning suppression, keeping the two features
consistent.

### Runtime wiring (`chat/runtime.py`)

The telemetry sink is `None` at `__init__` time — attached later via
`attach_telemetry_sink()`. Two-step buffered emission:

1. **`_load_engine_state()`** — builds and stores the JSONL string in
   `self._pending_reboot_payload: str | None`. The string is the fully
   serialized line; no further computation required at flush time.

2. **`attach_telemetry_sink(sink)`** — if `_pending_reboot_payload` is
   set and `sink` is not None, emits the line and clears the field.
   Subsequent calls to `attach_telemetry_sink` (e.g. replacing the sink)
   do NOT re-emit; the payload is consumed exactly once.

This placement guarantees the reboot event appears **before any turn
events** in the audit stream for the session, matching the semantic intent
of "lifetime boundary record".

### Trust boundary

Metadata only — no surface text, no tokens, no versor coordinates.
`_git_revision()` returns a short SHA derived from the local git repo;
already used for the manifest and W-023 warning.

## Invariants pinned by tests

`tests/test_adr_0158_reboot_event.py` (11 tests):

**Serializer:**
- Structure, fields, and `revision_matched` logic (match / mismatch / unknown)
- Optional `timestamp` field
- Byte-identical output for identical inputs (determinism)

**Runtime integration:**
- Reboot event emitted to sink on `attach_telemetry_sink` after checkpoint load
- Emitted exactly once — second `attach_telemetry_sink` call does not re-emit
- No event when no checkpoint directory exists (fresh start)
- No event when `no_load_state=True`
- `revision_matched: true` when revisions agree
- Reboot event precedes synthetic turn events in the stream

## L10b closure

With W-024, the L10b sequence is complete:

| Chunk | Work item | ADR  | What it does |
|---|---|---|---|
| L10b.1 | W-022 | ADR-0156 | Atomic checkpoint writes (write-temp + fsync + rename) |
| L10b.2 | W-023 | ADR-0157 | Revision-mismatch `RuntimeWarning` on load |
| L10b.3 | W-024 | ADR-0158 | `reboot_event` audit trail entry |

The checkpoint path now satisfies all three of ADR-0146's runtime-model
commitments: **atomic**, **observable** (warning on staleness), and
**auditable** (reboot recorded in the telemetry stream).
