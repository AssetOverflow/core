# ADR-0129 — Spaced Reviewed-Correction Replay (Deferred Proposal)

**Status:** Proposed — Deferred (backlog item; no implementation
scheduled until the GSM8K-math substrate arc through ADR-0127 /
ADR-0128 resolves Path-A vs Path-B)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:** ADR-0040 (telemetry sink), ADR-0042 (audit tour),
ADR-0043 (pack measurements phase 2), ADR-0059 (correction-pass
telemetry), the entire `teaching/*` subsystem
**Supersedes:** none

---

## Context

A research review of *Beyond Traditional Pedagogy* (`/Users/kaizenpro/Downloads/...md`)
plus follow-up literature confirmation surfaced two pedagogy
findings with unusually strong empirical support and clean structural
mapping onto CORE's existing teaching loop:

1. **Retrieval practice for retention of practiced material** —
   among the most robust findings in cognitive psychology
   (Roediger & Karpicke 2006 and ~two decades of replications).
2. **Spaced > massed practice** — Cepeda et al. 2006 meta-analysis;
   not seriously contested in any subsequent literature.

The combined "spaced retrieval" effect is consistently the single
highest-effect-size pedagogy intervention in well-replicated
literature. Far-transfer claims for retrieval are weaker (Pan &
Rickard 2018, Glaser & Richter 2025) — but **transfer to other
material is NOT the claim here**. The claim is *retention of
already-corrected material across long time horizons*, which is
precisely what retrieval-with-spacing addresses.

The full research-and-review context lives at
`docs/sessions/SESSION-2026-05-23-pedagogy-research-and-teaching-loop-pivot.md`.

### What CORE already has

`teaching/store.py` retains reviewed corrections. `teaching/review.py`
and `teaching/correction.py` provide the reviewed-write path. When a
correction is consulted (e.g., during a turn that touches the
corrected case), CORE recalls it from the vault — exact, deterministic.

### What CORE does NOT have

No **deterministic schedule** that proactively re-runs CORE
against past corrections at expanding intervals to verify the
correction still produces the intended behavior under the
*current* runtime state (which has since absorbed other
corrections, pack updates, ratifications). Reviewed corrections
sit in the store until something queries them; nothing pulls
them back into circulation on a cadence.

This is the gap "spaced retrieval" maps onto. In human pedagogy:
re-quiz the learner on previously-learned material at 1-day,
1-week, 1-month intervals to verify retention. In CORE: re-run
the deterministic pipeline against the past correction's input
on a fixed cadence and verify the output still matches the
correction's expected outcome.

---

## Decision (proposed; deferred)

Add a deterministic spaced-replay scheduler to the teaching
subsystem that, on a fixed cadence, re-runs the pipeline against
every retained reviewed-correction's input case and asserts the
output still matches the correction's expected outcome. Failures
become first-class "regression-against-prior-correction" events
emitted to the telemetry sink and surfaced in the operator
verdicts bundle.

### Proposed shape (non-binding sketch — implementation defers)

- **Cadence**: bounded, deterministic intervals. Initial proposal:
  every reviewed correction is replayed at session counts `{5, 25,
  125, 625}` past the original correction (geometric, mirroring
  spaced-repetition literature). Cadence drift is forbidden —
  same input session count → same replay event.
- **Replay path**: pure read; the replay does NOT mutate any
  state. It calls the standard pipeline against the correction's
  recorded input, compares actual output to the correction's
  expected output, emits an event.
- **Event shape**:
  ```json
  {
    "type": "spaced_correction_replay",
    "correction_id": "...",
    "original_session_count": N,
    "replay_session_count": M,
    "interval": M - N,
    "passed": <bool>,
    "actual_output_digest": "<sha256>",
    "expected_output_digest": "<sha256>",
    "trace_hash_delta": "<sha256-of-diff or empty>"
  }
  ```
- **Failure handling**: a failed replay is NOT silently
  re-corrected. It becomes an operator-visible event requiring
  human review (preserves the "no unreviewed mutation" doctrine).
  The original correction remains in the store; the new
  divergence is logged as a separate event linked by
  `correction_id`.
- **Determinism**: same `(input_sequence, pack_versions,
  correction_store_state)` → byte-equal replay event sequence.
- **Cost ceiling**: per-session replay cost bounded — at session
  count K, replays only fire for corrections whose
  `(K - original) ∈ {5, 25, 125, 625}`. Most corrections fire
  zero times per session; total replay cost is amortized.

### Invariants

| Invariant | Status |
|-----------|--------|
| `wrong == 0` | Preserved — replay is observational, not mutating |
| Trace determinism | Preserved — replay path is the standard deterministic pipeline |
| No unreviewed mutation | Preserved — replay failures emit events, do not auto-correct |
| Reviewed teaching only | Preserved — the scheduler operates only on already-reviewed corrections |
| `versor_condition(F) < 1e-6` | Untouched |

### Why this is deferred, not accepted

1. **Path-B uncertainty.** The GSM8K-math architectural arc
   through ADR-0126 / 0127 / 0128 may resolve to a benchmark
   re-targeting. If the math expert lane pivots, the
   correction-store population characteristics change, and the
   right cadence shape may differ.
2. **No measured regression.** ADR-0042's audit-tour demo + ADR-0043's
   pack measurements already prove replay-equality at the snapshot
   level. There is no observed instance of a past correction
   silently regressing under subsequent pack updates. Spaced
   replay would *detect* such regressions if they occur — but
   we don't currently have evidence they do.
3. **Cost/benefit unmeasured.** The scheduler adds bounded but
   nonzero per-session cost. Without an observed regression
   incident, the lift is theoretical.
4. **Pedagogy analog is suggestive, not proof.** The mapping
   from human-learner spaced retrieval to deterministic-engine
   correction replay is structurally clean but is not itself
   empirically validated *for engines*. CORE's exact-recall
   property may obviate the human-learner-style decay this
   addresses.

## Exit criteria for un-deferral

This ADR becomes a candidate for acceptance if any of:

1. A reviewed correction is observed to silently regress against
   current state (the failure mode the scheduler would have
   caught). One real incident promotes from "theoretical
   defense" to "documented incident response."
2. The teaching corpus grows past a threshold (~500 reviewed
   corrections, current count is far below) where manual audit
   is no longer feasible and proactive verification becomes
   load-bearing for trust.
3. The GSM8K-math arc resolves and produces a stable correction
   population whose retention characteristics can be
   characterized, removing the Path-B uncertainty.

## Alternatives considered

### A. Build the scheduler now as defensive infrastructure.
Rejected per reason #2 above — no observed regression.

### B. Run a single one-shot replay-all-corrections diagnostic.
Considered as a smaller alternative. May be worth a short ADR
of its own (`ADR-XXXX-correction-store-snapshot-audit`) if any
of the un-deferral exit criteria fire. Not pursued now.

### C. Make this a runtime-mode flag the operator can enable.
Considered. The current operator surface (CLI lanes, telemetry
sink, verdicts bundle) is already busy; adding another opt-in
toggle increases surface area without a clear use case.

## PR checklist (if/when proposed for acceptance)

```
What capability did this add?
  → Deterministic spaced verification of past reviewed
    corrections; defense against silent regression.
What invariant proves the field remains valid?
  → wrong == 0 (replay is observational); trace determinism
    (standard pipeline); no unreviewed mutation (failures emit
    events, do not auto-correct).
Which CLI suite/eval proves the lane?
  → New `core test --suite teaching-replay` lane runs replays
    against a fixture correction store and asserts deterministic
    event sequence; verdicts-bundle integration tested.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Cadence is fixed-integer. Replay path is the standard
    pipeline. Failures require human review.
If it touches user input, what trust boundary was enforced?
  → No user-input surface. Replays consume correction-store
    records, which are already ratified.
```
