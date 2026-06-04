# ADR-0208: Environmental Sensorium Loop

**Status:** Accepted — implementation landed (afferent scope)
**Date:** 2026-06-04
**Implementation:** `sensorium/environment/frame.py` (PR #540) + `sensorium/environment/harness.py` (PR #541). Proof obligations are covered by falsifiable tests in `tests/test_observation_frame_contract.py` (order-invariant frame trace hash, `merge_key` dedup, `TypeError` on raw-payload units, `ValueError` on efferent units) and `tests/test_observation_frame_harness.py`. Disjoint from the GSM8K serving path (no import of `generate.derivation` / `core.reliability_gate`).
**Domains:** `sensorium/environment/`, `sensorium/compiler/`, `sensorium/*`, future sensorimotor compilers
**Depends on:** ADR-0013, ADR-0180, ADR-0181, ADR-0197, ADR-0198

## Decision

CORE will represent a moment of environmental evidence as an `ObservationFrame`:
a deterministic bundle of already-compiled afferent `CompilationUnitLike`
deltas. The frame is not a fusion layer, not a shared embedding space, and not a
mutable world model.

```text
environment
  -> modality compilers
  -> compiled afferent units
  -> ObservationFrame
  -> Delta-CRDT merge
  -> field / recall / cognition
  -> governed efferent decode
  -> action result / proprioception re-enters as afferent evidence
```

## Contract

`ObservationFrame` contains:

```text
frame_id
monotonic_tick
source_clock
units: tuple[CompilationUnitLike, ...]
causal_parent_ids
environment_sha256
trace_hash
```

Rules:

- Units are canonicalized by `merge_key` and exact duplicates deduplicate.
- Trace records contain hashes and provenance only, never raw pixels, PCM, or
  actuator payloads.
- Audio chunks, vision tiles, text turns, and future proprioceptive feedback
  remain native compilation units.
- Motor commands and action traces are efferent; they are not observation units.
- Action outcomes re-enter through afferent sensorimotor/proprioceptive
  compilers.

## Consequences

This closes the architectural gap between independent modality compilers and an
embodied environment loop without inventing late fusion. Cross-modal coherence
is recovered after merge through exact manifold recall and field resonance. The
hot path stays local and deterministic; fleet/offline aggregation remains a
proposal/review path, not runtime truth.

## Proof Obligations

- Same afferent units in any arrival order produce the same frame trace hash.
- Unsafe raw payloads fail before entering frame traces.
- Efferent action records fail if passed as observation units.
- Sensorimotor feedback can enter as afferent evidence without enabling motor
  emission.
