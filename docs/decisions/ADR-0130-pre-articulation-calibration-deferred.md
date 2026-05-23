# ADR-0130 — Pre-Articulation Calibration Logging (Deferred Proposal)

**Status:** Proposed — Deferred (backlog item; no implementation
scheduled until the GSM8K-math substrate arc through ADR-0127 /
ADR-0128 resolves Path-A vs Path-B)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:** ADR-0035 (turn-loop verdicts), ADR-0036 (safety
refusal), ADR-0040 (telemetry sink), ADR-0043 (pack measurements
phase 2), ADR-0059 (correction-pass telemetry)
**Supersedes:** none

---

## Context

The same research review that motivated ADR-0129
(`docs/sessions/SESSION-2026-05-23-pedagogy-research-and-teaching-loop-pivot.md`)
surfaced a second pedagogy finding with strong empirical support
and a clean structural mapping: **metacognitive calibration via
prediction-outcome comparison**.

In human pedagogy: learners predict their performance before a
task, compare prediction to outcome, and use the gap to recalibrate
their judgments of learning. Repeated calibration cycles shrink the
gap (Bjork, Dunlosky, Koriat, and successors). The mechanism is
that *uncalibrated confidence* is the central failure mode of
self-regulated learning — over-confidence leads to under-study;
under-confidence to over-study; both waste capacity.

CORE has analogs at the runtime layer:
- `ADR-0035` end-of-turn safety + ethics verdicts
- `ADR-0036` typed safety refusal
- `ADR-0040` structured telemetry sink

But CORE has **no analog at the teaching layer**. Before a
reviewed correction lands, no event captures the answer CORE
*would have produced* on the case-pre-correction; after correction,
no event captures the gap.

This is a genuine information loss. Unlike a human learner, CORE
can do this without subjective bias: the pre-correction answer is
deterministic and exactly recordable. The gap is a real
measurement, not a self-report.

---

## Decision (proposed; deferred)

Add a deterministic "pre-correction prediction" capture step to
the teaching subsystem. When a correction is proposed (before
review), record CORE's current pipeline output on the case as a
prediction event. When the correction is accepted (review passes,
correction lands in store), emit a paired calibration event
recording the delta between prediction and the corrected outcome.

### Proposed shape (non-binding sketch — implementation defers)

- **Pre-correction prediction event** (emitted at correction
  *proposal*):
  ```json
  {
    "type": "pre_correction_prediction",
    "correction_proposal_id": "...",
    "input_digest": "<sha256-of-input>",
    "predicted_output_digest": "<sha256>",
    "predicted_trace_hash": "...",
    "predicted_verdict": "correct | wrong | refused",
    "current_runtime_state_digest": "<sha256-of-pack-versions+correction-store>"
  }
  ```
- **Post-correction calibration event** (emitted at correction
  *acceptance*):
  ```json
  {
    "type": "post_correction_calibration",
    "correction_id": "...",
    "linked_prediction_id": "...",
    "predicted_output_digest": "<sha256>",
    "corrected_output_digest": "<sha256>",
    "delta_class":
      "no_change | answer_value | answer_unit | trace_only | refused_to_correct | correct_to_refused",
    "pack_provenance_diff": [...]
  }
  ```
- **Aggregation** (offline, periodic): a `calibration_report.json`
  in the teaching subsystem's reports directory, summarizing:
  - rate at which predictions matched corrections (no-change),
  - distribution of delta classes,
  - per-pack-version cohort comparisons (does calibration improve
    after pack ratifications?).
- **No runtime gating.** The prediction is observational. It does
  NOT alter what the operator can or cannot do; it does NOT veto
  any correction. It's measurement, not control.

### Invariants

| Invariant | Status |
|-----------|--------|
| `wrong == 0` | Preserved — prediction is observational |
| Trace determinism | Preserved — prediction uses standard pipeline |
| No unreviewed mutation | Preserved — prediction does not write to correction store |
| Reviewed teaching only | Preserved — calibration emits only at proposal AND acceptance, both of which are operator-mediated |
| Telemetry redaction defaults | Preserved — input digests, not raw input |
| `versor_condition(F) < 1e-6` | Untouched |

### What this enables that's not currently possible

1. **Empirical answer to "is CORE actually getting better?"** Per-pack-
   version calibration trends would show whether ratifications
   improve pre-correction accuracy or just shift the surface.
2. **Audit story strengthens.** Today operators see that
   corrections happen; they don't see how often CORE was *already*
   right before the correction. The calibration gap is exactly
   that signal.
3. **Misconfigured-pack detection.** A pack version that suddenly
   spikes pre-correction error rate (vs the prior pack's rate)
   is a flag worth surfacing automatically.
4. **Honest framing of operator workload.** If the calibration
   shows pre-correction prediction matches the eventual correction
   95% of the time, the operator review can be lighter-touch on
   that pack; if 5%, heavier-touch is warranted.

### Why this is deferred, not accepted

1. **Path-B uncertainty** (same as ADR-0129): the GSM8K-math arc
   may produce a different correction-store population structure
   that changes the right calibration cohorts.
2. **No measured calibration problem.** We don't currently have
   evidence that pre-correction accuracy is misaligned with
   post-correction. The proposal is "measure to find out" — but
   the cost of building the measurement infrastructure should
   match the prior of finding something. We don't have a strong
   prior.
3. **Telemetry already substantial.** ADR-0040 / ADR-0042 /
   ADR-0043 ship significant telemetry. Adding two new event
   classes raises operator-noise floor; should only do so if the
   signal proves worth it.
4. **Operator workload concern.** Even though prediction is
   observational, a calibration report is a thing the operator
   has to read. More artifacts means more attention budget; only
   worth it if the artifacts surface decisions.

## Exit criteria for un-deferral

This ADR becomes a candidate for acceptance if any of:

1. An incident occurs where a correction was applied unnecessarily
   (CORE was already producing the right answer on that input)
   AND the wasted review effort would have been visible to a
   calibration-event sequence.
2. A pack ratification produces unexpected behavior whose
   detection would have been faster via per-pack calibration
   cohort comparison.
3. The teaching corpus grows to where operator review bandwidth
   becomes a bottleneck and routing reviews by calibration
   confidence would help triage.
4. The GSM8K-math arc resolves and ADR-0129 (spaced replay) is
   un-deferred — at which point these two capabilities should
   compose, since spaced replay events naturally produce
   calibration evidence and they should share infrastructure.

## Alternatives considered

### A. Build calibration logging now, defer reporting.
Considered. Logging without reporting still costs telemetry
volume; without a report nobody reads the events; without reading
the events the log is decoration. Rejected per CLAUDE.md "no
decoration without integration."

### B. Sample-based calibration (log a random 10% of proposals).
Considered. Determinism doctrine pushes against sampling — same
correction proposal should always produce same calibration event,
or none at all. Could be acceptable if sampling is content-keyed
(hash of input → bucket) so it's deterministic, but adds
complexity. Defer for now.

### C. Manual calibration audit on demand.
The CLI could provide `core teaching calibration --window N` that
re-runs the last N corrections through the prediction path
*offline* and produces a one-shot calibration report. Lower
implementation cost than continuous logging; could be a useful
half-step. Worth its own short ADR if any of the exit criteria
above fire.

## Composition with ADR-0129

If both ADRs are eventually un-deferred, they should share
infrastructure:

- Spaced-replay events (ADR-0129) naturally yield calibration
  evidence: each replay produces a prediction against the original
  correction's expected outcome. The two event streams should
  merge into a single calibration report.
- A correction whose spaced-replay events show repeated divergence
  is a stronger signal than either system alone would catch.

This composition is itself an argument for un-deferring both
together if either is un-deferred.

## PR checklist (if/when proposed for acceptance)

```
What capability did this add?
  → Deterministic measurement of pre-correction prediction
    accuracy; empirical signal for "is CORE getting better."
What invariant proves the field remains valid?
  → wrong == 0 (prediction is observational); trace determinism
    (standard pipeline); no unreviewed mutation (calibration
    writes events, not corrections).
Which CLI suite/eval proves the lane?
  → New `core test --suite teaching-calibration` lane; fixture
    correction-proposal sequence asserts deterministic event
    pairs and report aggregation.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Pure observational, deterministic pipeline call.
If it touches user input, what trust boundary was enforced?
  → Telemetry emits input digests (SHA-256), not raw input,
    consistent with ADR-0040's redact-by-default policy.
```
