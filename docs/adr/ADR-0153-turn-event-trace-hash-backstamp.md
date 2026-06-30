# ADR-0153 — TurnEvent trace_hash back-stamp (W-020a)

Status: accepted
Date: 2026-05-25

## Context

`teaching/discovery.py` documents that `DiscoveryCandidate.source_turn_trace`
"is the upstream `TurnEvent.trace_hash`" (module docstring, line 41).
The extractor reads it via:

```python
def _trace_hash(turn_event: Any) -> str:
    value = getattr(turn_event, "trace_hash", "") or ""
    return str(value)
```

But `TurnEvent` (`core/physics/identity.py`) has no `trace_hash` field.
Every `DiscoveryCandidate` written to disk had `source_turn_trace=""`.
Same defect at `chat/runtime.py:874` for `OOVCandidate`.

The real `trace_hash` is computed by `core/cognition/trace.py:compute_trace_hash`
inside `CognitiveTurnPipeline.process` **after** `runtime.chat()` returns —
which is after `_emit_discovery_candidates` has already buffered and
`_checkpointed_response` has already persisted the candidates.

Symptom observed: a 103-turn session wrote a `discovery_candidates.jsonl`
whose one candidate had `"source_turn_trace": ""` — provenance lost.

## Decision

1. Add `trace_hash: str = ""` to `TurnEvent`.
2. Add `ChatRuntime.finalize_turn_trace_hash(trace_hash)`. Back-stamps:
   - `turn_log[-1]` (via `dataclasses.replace`)
   - the unstamped tail of `_pending_candidates`
   - re-persists `discovery_candidates.jsonl`
3. `CognitiveTurnPipeline.process` calls `finalize_turn_trace_hash` after
   `compute_trace_hash`, before constructing `CognitiveTurnResult`.

The back-walk halts at the first already-stamped candidate, so prior
turns' candidates are never overwritten.

## Invariants

- Empty `trace_hash` is a no-op (refusal/stub call sites do not lose
  byte-identity).
- Re-stamping is idempotent for the most recent turn and forbidden for
  earlier turns.
- No change to `compute_trace_hash` inputs — trace_hash bytes for any
  given turn remain identical to pre-ADR-0153.
- No change to `TurnEvent` telemetry sink emission order (sinks receive
  the pre-stamp event; the persisted record gets the stamped one). A
  follow-up may add a "turn finalized" sink event with the trace_hash.

## Out of scope

- OOV candidates (`OOVCandidate.source_turn_trace`) — same root cause,
  but the sink is line-streamed at emit time, not buffered. Fix
  requires either buffering OOV or computing trace_hash earlier.
  Tracked separately; no production OOV sink was configured during
  the observed regression.
- Telemetry sink trace_hash exposure — see invariants above.

## Validation

`tests/test_adr_0153_trace_hash_backstamp.py`:
- `TurnEvent.trace_hash` field exists with default `""`
- main-path `pipe.run` stamps `turn_log[-1].trace_hash == result.trace_hash`
- main-path `pipe.run` stamps `_pending_candidates[*].source_turn_trace`
- on-disk `discovery_candidates.jsonl` reflects the stamped values
- empty trace_hash is a no-op
- idempotent: prior stamps are not overwritten

CLI lanes: `core test --suite cognition` (120 + 1 skipped),
`core test --suite smoke` (67), `core test --suite runtime` (17),
`core test --suite teaching` (20) all green.

## Provenance gap closure

After this ADR, every `DiscoveryCandidate` persisted via the
load-time auto-proposal pipeline (ADR-0151) carries the canonical
trace_hash of the turn that produced it, restoring the audit-trail
invariant the discovery module's docstring already promised.
