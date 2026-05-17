# ADR-0025 — Rotor / Frame Admissibility (Design Note)

| Field        | Value                                |
|--------------|--------------------------------------|
| Status       | **Draft — Design Note Only**         |
| Date         | 2026-05-17                           |
| Supersedes   | —                                    |
| Extends      | ADR-0022, ADR-0023, ADR-0024         |
| Decision lead| Shay (with CORE assistant)           |

---

## Status note

This is a **design note**, not an implementation decision.  No code
changes are proposed.  Its purpose is to fix the home, scope, and
boundary of the next admissibility step *before* anything is built —
so the implementation doesn't inherit the wrong architectural shape
by default.

It will be promoted from Draft to a real ADR (Proposed → Accepted)
only after the design questions below are decided.

---

## Context

ADR-0024 added per-rotor inner-loop admissibility for the
**destination-token / direction** side of an `AdmissibilityRegion`:
when a candidate's CGA inner product against `relation_blade` falls
below `admissibility_threshold`, the candidate is excluded and the
walk re-selects until admitted or exhausted.

ADR-0024 explicitly deferred:

> Frame-versor admissibility (does the rotor preserve / transform
> within the frame constraint?) remains out of scope.

This note scopes that deferred work, but with two additional
constraints surfaced by the Phase 2–4 follow-up evidence:

1. **Phase 2 corpus observation** (`evals/forward_semantic_control/
   inner_loop_runner.py`): on the existing v1+dev corpus, the
   inner-loop mechanism is *wired, deterministic, causally
   attributable* (null-control = boundary-only exactly,
   `code_path_residual = 0.0`), but the chain-token outer-product
   region produces `exhaustion_rate = 0.33` at `t = 0.0` — well
   above the 5% benign-corpus ceiling.

2. **Phase 4 threshold characterization** (`threshold_
   characterization.py`): **per-case the geometry separates cleanly**
   (every mechanism-isolated v2 case has `correct_min > incorrect_max`),
   but **no static global threshold** delivers
   `separation_quality ≥ 0.8`.  Blade norms vary ~10× across cases,
   so the same threshold value means different things case-to-case.
   Static thresholds — global, relation-typed, or frame-derived as a
   constant — are insufficient.

These findings change the framing.  The next step is not "extend the
same idea to the rotor side."  It is two distinct questions:

* What level of the stack should enforce rotor/frame admissibility?
* What threshold scheme is geometrically valid given Phase 4?

---

## Question 1 — Architectural home

Three candidate homes for rotor-side admissibility:

### Option A — Generation-time filter (`generate/`)

Inherit ADR-0024's shape.  Add a check inside the same per-step inner
loop in `generate/stream.py` that examines the *rotor* `V` (not just
the destination versor) before propagation.

**Pros:**

* Locality with ADR-0024.  All admissibility decisions live in one
  module.
* Trace evidence is uniform — one `AdmissibilityTraceStep` per
  rotor-application.

**Cons:**

* Pushes algebra-shaped invariants into a generation-shaped module.
  `generate/` already orchestrates candidates, salience, attention,
  vault recall, persona — adding rotor invariant enforcement here
  bloats the hot path and entangles concerns.
* Re-creates the "hot-path repair" anti-pattern CLAUDE.md explicitly
  warns against, because the check would re-validate something
  algebra already constructed.

### Option B — Versor construction invariant (`algebra/versor.py`)

Make rotor/frame admissibility part of sandwich closure.  When
`word_transition_rotor(A, B)` builds the rotor, it also checks the
rotor against the active frame constraint.  Violations raise — same
shape as the existing `versor_condition < 1e-6` invariant.

**Pros:**

* Aligned with the CLAUDE.md doctrine that algebra-owned closure
  belongs in `algebra/`.
* No hot-path repair.  The check is part of *construction*, not a
  post-construction filter.
* Single invariant site — easier to reason about and prove.

**Cons:**

* Couples algebra to admissibility concepts (frame, relation_blade)
  that today live in `generate/admissibility.py`.  Either
  `algebra/versor.py` grows a dependency on admissibility, or
  admissibility primitives must be lifted to a shared layer.
* Honest refusal would surface deeper in the stack — callers that
  today catch `ValueError` from `generate()` would also need to
  catch from `propagate_step` or earlier.

### Option C — Field propagation guard (`field/propagate.py`)

Enforce at the *application* site: after rotor construction, before
`propagate_step` commits the new field state, verify the resulting
field stays within the frame's admissible cone.

**Pros:**

* Closest to the *claim*: rotor admissibility is fundamentally about
  the field staying coherent under propagation, not about token
  selection.
* `field/propagate.py` already owns the propagation invariant, so
  this is a natural home for an additional propagation-time check.

**Cons:**

* `field/propagate.py` is explicitly listed in CLAUDE.md as a
  *forbidden site* for normalization / drift repair / monitoring
  ("Do not add drift repair, grade projection, watchdogs, timers,
  hot-path normalizers, or monitoring functions whose only purpose
  is to repair another function").  An admissibility *guard* (raise
  on violation, never repair) is closer to a precondition than a
  monitor, but the boundary needs to be made explicit before this
  option is chosen — otherwise it sets a precedent that erodes the
  current rule.

### Recommended preliminary stance

**Option B** is the most aligned with project doctrine and the
cleanest invariant.  Option C is the second-best, but only if the
"guard vs. monitor" distinction is made explicit and respected — and
even then, the construction-site discipline of Option B is preferable.

Option A is rejected as inheriting the wrong architectural shape from
ADR-0024 by momentum.  ADR-0024 lived in `generate/` because it was
about *which destination to select*; rotor admissibility is about
*whether the rotor itself is valid*, which is a construction-site
question.

**Decision required**: B vs. C.

---

## Question 2 — Threshold scheme

Phase 4 surfaced that static thresholds are geometrically invalid on
this manifold.  The right scheme is *not yet decided*, but the
candidates are:

1. **Per-candidate normalized score**: threshold = α · ‖blade‖, so
   the same fraction of blade self-score is required regardless of
   blade norm.  Probable best first cut.

2. **Cosine-similarity-style normalization**: replace `cga_inner` in
   the threshold check with
   `cga_inner(v, blade) / (‖v‖ · ‖blade‖)`.  Rejected on doctrinal
   grounds — CLAUDE.md says "do not add cosine similarity ... to the
   runtime path."  Listed for completeness only.

3. **Per-relation-type static threshold**: a small table mapping
   relation type → threshold.  Phase 4 suggests this is insufficient
   because *blade norm dominates*, not relation type, but it could
   be a fallback if normalized scoring proves unstable.

4. **Frame-derived threshold**: threshold is a property of the frame
   versor, not the candidate or the relation.  Requires the frame
   versor to be the primary admissibility object — i.e. Option B
   above — and may collapse Question 1 and Question 2 into one
   decision.

**Decision required**: (1) is the recommended starting point.  Final
choice depends on Question 1 outcome and on a focused diagnostic
sweep over (1) and (3).

**Out of scope for the eventual ADR**: learned thresholds, adaptive
thresholds, online tuning.  Deterministic replay must be preserved;
no learned policy enters the runtime path.

---

## Question 3 — Teaching loop boundary

ADR-0024 lives in `generate/`.  The teaching loop in `teaching/*`
corrects model behavior through reviewed mutation.  An open question:
when inner-loop (or rotor) admissibility rejects a candidate, does
that rejection become a *teachable event*?

Two stances:

* **A. Rejections are runtime hygiene only.**  The teaching loop
  sees the final selected token, not the rejected ones.  Rejection
  is a property of the deterministic admissibility region, not of
  the reviewed teaching example.

* **B. Rejections are correction signals.**  A teaching review can
  examine `rejected_attempts` and decide whether the rejection was
  correct (reinforce) or over-aggressive (loosen).  This entangles
  the teaching loop with admissibility geometry.

### Recommended stance: **A — strictly hygiene-only.**

Rationale:

* The teaching loop's contract is *reviewed mutation of identity /
  pack / vault*.  Admissibility regions are deterministic geometric
  objects derived from intents and frames; they are not learned, and
  there is no review surface for them today.
* Entangling teaching with admissibility would create a parallel
  correction path — explicitly forbidden by CLAUDE.md ("Do not
  create a parallel correction/learning path").
* Phase 4 showed that what needs to change is the threshold *scheme*,
  not the per-event rejection decisions.  Scheme changes belong in
  the eventual ADR-0025 implementation, not in reviewed teaching
  examples.

The decision must be **stated in the final ADR**, not left as a
silent default, so the next person who touches both systems doesn't
have to re-derive the boundary.

---

## Decisions to lock before ADR-0025 is implementable

1. **Home**: Option B (algebra construction) vs. Option C (field
   propagation guard).  Reject A explicitly.
2. **Threshold scheme**: blade-normalized fraction (recommended) vs.
   relation-typed table (fallback).  Run a small diagnostic sweep
   on the v2 corpus + a small extension before committing.
3. **Teaching boundary**: Stance A (hygiene-only) confirmed.  State
   explicitly in the eventual ADR's "Out of scope" section.
4. **Trace evidence**: extend `AdmissibilityTraceStep` to include
   rotor-side verdict, or add a separate `RotorAdmissibilityTrace`?
   Lean toward extending the existing step to keep the trace shape
   simple.
5. **Honest refusal**: at which layer does `ValueError` get raised
   on rotor rejection?  Decided by (1) — same site as the check.

---

## Evidence and links

* ADR-0022 — Forward Semantic Control (region prefilter).
* ADR-0023 — Forward Semantic Control proof evidence.
* ADR-0024 — Inner-loop per-rotor admissibility (token-side).
* Phase 2 report — `evals/forward_semantic_control/results/
  phase2_inner_loop_report.json` — causal attribution proven, but
  exhaustion gate fails on existing corpus.
* Phase 3 report — `evals/forward_semantic_control/results/
  phase3_v2_report.json` — mechanism isolated on real pack,
  `mechanism_isolated = true` on 5/5 cases.
* Phase 4 reports — `evals/forward_semantic_control/results/
  phase4_characterization_{v1_plus_dev,v2,combined}.json` — static
  thresholds geometrically insufficient.
* Tests pinning the findings: `tests/test_inner_loop_phase2.py`,
  `tests/test_inner_loop_phase3.py`, `tests/test_inner_loop_phase4.py`.

---

## What this note does NOT decide

This note does not:

* Choose between Options B and C — that requires a short focused
  spike on the algebra-vs-propagation tradeoff.
* Specify the threshold scheme — that requires a small diagnostic
  sweep over normalized-fraction vs. relation-typed schemes on the
  v2 corpus.
* Authorize any code changes.  Promotion from Draft to Accepted
  requires the open questions to be closed.
