# ADR-0024 — Inner-Loop Per-Rotor Admissibility

| Field        | Value          |
|--------------|----------------|
| Status       | **Accepted**   |
| Date         | 2026-05-17     |
| Supersedes   | —              |
| Extends      | ADR-0022, ADR-0023 |
| Decision lead| Shay (with CORE assistant) |

---

## Context

ADR-0022 introduced `AdmissibilityRegion` and routed it through
`generate()` as a **boundary prefilter**: the region's
`allowed_indices` array is intersected with the language / salience
candidate set before `_nearest_next` runs, and an empty intersection
raises `ValueError` (honest refusal).  ADR-0023 then added
per-transition trace evidence: each step records `candidates_before /
candidates_after / selected_index / verdict`, hashed into the
deterministic trace.

That is enough to make the *token-set* side of admissibility
load-bearing.  It does not yet make the *blade-direction* side
load-bearing: `check_transition` is evaluated after selection and
recorded into the verdict, but the verdict does not influence which
candidate is chosen.  Today, a candidate that survives the index
prefilter is *always* selected even if its versor's CGA inner product
against `relation_blade` is negative — the trace says "rejected" and
the walk emits it anyway.

ADR-0023 §Decision explicitly deferred this:

> ADR-0024 will separately scope inner-loop admissibility (per-rotor
> admissibility checks after candidate prefilter) because that *is* a
> semantic change and interacts with the `versor_condition`
> invariant.

This ADR scopes that change.

## Decision

We add **inner-loop per-rotor admissibility** to `generate()`,
flag-gated and off by default.

When `inner_loop_admissibility=True` and a non-unconstrained region
is supplied:

1. `_nearest_next` selects a destination from the index-filtered
   candidate set, exactly as today.
2. `check_transition(region, candidate_index, candidate_versor,
   threshold=admissibility_threshold)` evaluates the candidate.
3. If `verdict.admitted` is `False`, the candidate is appended to a
   step-local `rejected_attempts` list, its index is added to a
   per-step exclude set, and `_nearest_next` re-runs with that
   exclusion.  The retry budget is bounded by
   `len(candidate_indices)`.
4. If every admissible candidate is rejected (selector returns an
   already-excluded index, or the retry budget is exhausted), the
   walk raises `ValueError(f"AdmissibilityRegion[{label}] inner-loop
   rejected all candidates at step {step_index}.")` — the same
   honest-refusal shape ADR-0022 §2 already commits to for empty
   admissible sets.
5. The selected (admitted) candidate proceeds through the existing
   rotor application: `V = word_transition_rotor(A, B)` and
   `propagate_step(current, V)`.  No new normalization site is
   introduced; the runtime versor invariant
   `versor_condition(F) < 1e-6` is still asserted after propagation
   exactly as before.

The rejected candidates are recorded in the trace via a new
`AdmissibilityTraceStep.rejected_attempts: tuple[tuple[int, str,
float], ...]` field.  The canonical form folds this field into the
trace hash only when non-empty, so any ADR-0023 turn (boundary-only
walk, or inner-loop on but no rejections) hashes to the same bytes it
hashed to before this ADR shipped.

Default is `False`.  Legacy call sites (`chat/runtime.py`,
`generate/proposition.py`, the ADR-0023 ablation lane) keep their
boundary-only semantics until they opt in.

## Why flag-gated

This is a real semantics change to the walk: it can divert selection
from the geometric nearest to a non-nearest admitted candidate.  That
is exactly what ADR-0022 promised the admissibility region would do
for the *direction* side of admissibility, but it changes the
distribution of emitted tokens for every constrained turn that hits
a rejection.  Flag-gating means:

* every commit before this ADR's eval lanes light up
  `inner_loop_admissibility=True` continues to produce byte-identical
  trace hashes;
* the change can be ramped per-call-site rather than as a global
  semantics flip;
* failures attributable to the inner loop are isolated by toggling
  the flag, not by reverting code.

## Invariants preserved

* **Versor condition.**  The rotor `V` is constructed from
  `vocab.get_versor_at(word_idx)` for the *admitted* candidate; the
  rejected candidates never reach `word_transition_rotor`.  The
  `versor_condition < 1e-6` assertion at `propagate_step` is
  unaffected.  CLAUDE.md §Non-Negotiable Field Invariant: not
  weakened.
* **No new normalization site.**  The inner loop is a selection-side
  retry; it never rebalances `F`, projects grades, or unitizes
  rotors.  CLAUDE.md §Normalization Rules: respected (no addition to
  the forbidden list).
* **Exact CGA recall.**  Vault recall and `cga_inner` are unchanged.
  CLAUDE.md §Core Primitives: not touched.
* **Honest refusal.**  Exhaustion raises `ValueError` with the region
  label in the message, the same surface ADR-0022 already commits to
  for empty admissible sets.

## Trust boundary

No new I/O.  No new dynamic imports.  No new filesystem reads.  The
`rejected_attempts` tuple is built from already-grounded vocabulary
indices and scores produced by `cga_inner`, both of which the existing
trust-boundary review (ADR-0022 §Trust Boundary) covers.  No
user-controlled text enters the trace path.

## Acceptance evidence

* **Backward-compat trace hash.**  `compute_trace_hash` over an
  ADR-0023 turn (no rejected attempts) produces the same bytes
  before and after this ADR.  Covered by
  `tests/test_admissibility_trace.py::TestComputeTraceHashBackwardCompat`
  and by a new `tests/test_inner_loop_admissibility.py` case asserting
  that an empty `rejected_attempts` list canonicalizes without the
  key.
* **Re-selection on rejection.**  A new test constructs a small
  vocabulary where the geometric-nearest candidate would be rejected
  by a region whose blade points away from it; with
  `inner_loop_admissibility=True` and a positive threshold, the walk
  emits a *different* admitted token and the step's
  `rejected_attempts` records the rejected one.
* **Exhaustion → honest refusal.**  A region whose blade rejects
  every admissible candidate raises `ValueError` with the region label
  embedded in the message.
* **Default off preserves behavior.**  With the flag off, every
  existing pipeline / runtime / eval lane test continues to pass byte-
  for-byte; no test in `tests/` had to be updated to absorb this
  change.

## Out of scope

* **Pipeline / runtime wiring.**  This ADR only adds the parameter on
  `generate()`.  Wiring the flag through `RuntimeConfig`,
  `CognitiveTurnPipeline`, and `chat/runtime.py` is left to a follow-
  up so the eval lane can demonstrate causal isolation against the
  inner loop without touching production defaults.
* **Frame-versor admissibility.**  ADR-0022's `frame_versor` /
  `rotor_constraint` side of the region remains observed but unused
  for selection.  That belongs in a future ADR after this one's trace
  evidence shows whether blade-direction admissibility alone closes
  the remaining causality gap.
* **Adaptive thresholds.**  The threshold is a static parameter.
  Adaptive thresholds (learned, frame-derived, or annealed) are a
  separate semantic change.

## Risks

* **Selection drift.**  A non-zero `admissibility_threshold` will
  divert tokens.  Mitigation: default `0.0` matches the ADR-0023
  verdict computation; lanes ramp the threshold independently per
  case.
* **Cost.**  Up to `len(candidate_indices)` extra `check_transition`
  calls per step in the worst case.  In practice the admissible set
  is small (chain length) and rejections terminate after the first
  admitted candidate.
* **Test brittleness.**  Tests that asserted exact tokens on
  constrained walks could shift if they enable the flag.  Mitigation:
  flag stays off everywhere by default; opt-in is explicit per call
  site.

## Rollback

Set `inner_loop_admissibility=False` (the default) at every call
site.  The trace hash remains byte-identical to ADR-0023, so
deterministic replay over the existing corpus is unaffected.
