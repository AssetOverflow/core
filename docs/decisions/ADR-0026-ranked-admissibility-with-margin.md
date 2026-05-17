# ADR-0026 — Ranked Admissibility with Margin

**Status:** Accepted (2026-05-17)
**Supersedes (in part):** ADR-0024's static `admissibility_threshold`
mechanism for production admissibility gating.  ADR-0024 remains
Accepted; threshold mode is preserved for backward-compatible
acceptance evidence and is the default unless margin mode is
explicitly enabled.

## Context

Phase 4 threshold characterization (`tests/test_inner_loop_phase4.py`)
established a load-bearing geometric finding: **no single global static
threshold delivers `separation_quality >= 0.8` across the v2 mechanism-
isolation cases.**  Blade norms vary roughly tenfold across cases
(`best_separation_quality < 0.5` is now an invariant test), so the
same `tau` value means semantically different things case-to-case.

Three options were on the table for Phase 3:

1. **Per-case normalised thresholds** (e.g. `alpha * blade_self_score`).
   Adds a tuning surface; the constant becomes a knob.
2. **Per-pack thresholds.**  Migrates the tuning problem from the
   blade level to the pack level; same failure mode.
3. **Ranked-with-margin admissibility.**  Replaces the absolute-
   score gate with a *relative-ordering* gate: rank the admissible
   candidates by `cga_inner(versor, relation_blade)` descending and
   admit the top iff its margin over the second-ranked exceeds a
   single per-runtime `delta`.

Option 3 is the only option that is **scale-invariant under blade-
norm variation** — the gap between the top and second-ranked scores
scales with the blade norm, so the *relative* ordering carries the
semantic separation the static threshold was reaching for.  This is
the architectural difference between "what direction is admissible"
(blade alignment, absolute) and "which candidate is confidently
selected over the next-best" (separation, relative).

The previous assessment (recorded in the planning conversation that
preceded this ADR) put it this way:

> A global threshold — even normalized — assumes admissibility is an
> absolute property of a candidate.  It isn't: in your geometry,
> what matters is the ordering of admissibility scores across the
> candidate set, plus enough separation to be confident the
> boundary's pick can be rejected and replaced deterministically.

## Decision

Add a new admissibility mode `margin` alongside ADR-0024's existing
`threshold` mode.  When margin mode is active, the inner loop's
selection-and-admission collapses into a single deterministic step:

```python
ranked = rank_candidates_by_blade(region, candidate_indices=…, …)
verdict = check_margin(region, ranked, delta=admissibility_margin)
```

`rank_candidates_by_blade` sorts the post-region-filter candidate set
by `cga_inner(versor, relation_blade)` descending, with a strict `>`
tie-break: when scores are equal, ascending vocab index wins.  This
matches the `vocab.nearest` strict-`>` convention documented as
load-bearing in ADR-0024.

`check_margin` admits the top-ranked candidate iff:

1. `len(ranked) >= 1` (non-empty admissible set), AND
2. `ranked[0].score > 0` (basic positivity in the blade half-space),
   AND
3. `len(ranked) == 1` (trivial, no competitor) **OR**
   `ranked[0].score - ranked[1].score >= delta`.

When refused, the inner loop raises `InnerLoopExhaustion`
(ADR-0024 Phase 2) carrying the full ranking as `rejected_attempts` —
not a single rejected score, but the entire blade-ordering at the
failed step.

### Selection semantics in margin mode

Margin mode is **blade-rank-driven** selection: the top-ranked
admissible candidate IS the admitted destination.  This differs from
threshold mode, where `_nearest_next` (field-driven) picks one
candidate and `check_transition` gates it; on rejection, the
selector advances to the next field-closest candidate and re-gates.

This is a meaningful semantic difference, not a re-shading.  Margin
mode says *"of the candidates the region admits as semantically
valid, the most blade-aligned one is the destination, provided its
lead is confident."*  Threshold mode says *"of the candidates the
field's geometry prefers, accept the first one above an absolute
score bar."*

Both have a place: threshold mode is the ADR-0024 acceptance
evidence and remains the default to preserve every existing turn's
trace_hash byte-for-byte.  Margin mode is the new production
admissibility for cases where blade-norm variation makes the static
bar incoherent.

## The single `delta` choice

Phase 3 picks `delta = 0.4` as the default.  This was derived from
the v2 mechanism-isolation case margins:

| Case          | Top score | Second score | Margin |
| ------------- | --------- | ------------ | ------ |
| FSC-PUB-V2-001 | 1.420     | 0.824        | 0.596  |
| FSC-PUB-V2-002 | 1.173     | 0.717        | 0.456  |
| FSC-PUB-V2-003 | 12.720    | -0.550       | 13.270 |
| FSC-PUB-V2-004 | 5.740     | 2.370        | 3.370  |
| FSC-PUB-V2-005 | 14.360    | 1.620        | 12.740 |

The minimum margin across the five cases is **0.456**.  `delta = 0.4`
admits all five with headroom; `delta = 0.5` would refuse V2-002.
The default is *falsifiable*: Phase 5's diversified failure-mode
families may surface a case below `0.4`, in which case the finding
is architectural — margin alone is insufficient for that family —
and should be reported honestly rather than patched with a per-case
override.

## Wiring

| Surface                                    | Field                          |
| ------------------------------------------ | ------------------------------ |
| `core/config.py::RuntimeConfig`            | `admissibility_mode: str = "threshold"` |
|                                            | `admissibility_margin: float = 0.4` |
| `chat/runtime.py::ChatRuntime.chat`        | forwards both fields           |
| `generate/stream.py::generate`             | `admissibility_mode` / `admissibility_margin` kwargs |
| `generate/admissibility.py`                | `RankedCandidate`, `MarginVerdict`, `rank_candidates_by_blade`, `check_margin` |

Selection ordering inside `generate.generate()`:

```text
if margin_mode_active:
    rank → check_margin → admit-or-refuse
else:
    _nearest_next → check_transition (per-attempt loop)
```

The rotor `V` is only constructed for the *admitted* candidate, so
the `versor_condition(F) < 1e-6` invariant is preserved by
construction (CLAUDE.md §Non-Negotiable Field Invariant).

## Why flag-gated (default off)

Margin mode is a real semantic change in selection.  Defaulting it
off preserves:

* Every existing trace_hash byte-for-byte (no payload bytes change
  when margin mode is unset).
* ADR-0024's acceptance evidence intact.
* The ability to A/B threshold vs margin on the same corpus during
  the transition window.

A future ADR may flip the default; this ADR does not.

## Invariants preserved

* `versor_condition(F) < 1e-6` — the rotor is constructed only for
  the admitted candidate; margin mode does not add a normalization
  or repair site (CLAUDE.md §Normalization Rules).
* Deterministic replay — strict `>` tie-break is now load-bearing
  in two places: `vocab.nearest` (ADR-0024) and
  `rank_candidates_by_blade` (this ADR).
  `tests/test_margin_admissibility.py::TestRankCandidates::test_strict_tie_break_by_ascending_index`
  pins it.
* No approximate recall, no cosine similarity, no HNSW/ANN.
  Margin is a pure rank-and-difference operation on the exact
  `cga_inner` scores already in use.
* No new code in `field/propagate.py`, `algebra/versor.py`,
  `vault/store.py`, or `chat/runtime.respond()`.

## Trust boundary

Same as ADR-0024 — admissibility regions are constructed upstream
from pack-grounded data; margin mode adds no new surface that
consumes user-controlled text, filesystem paths, or dynamic
imports.

## Acceptance evidence

* **5/5 v2 mechanism-isolation cases pass in margin mode** with
  `delta = 0.4`.  Forbidden token traced in every case's
  `rejected_attempts`.  Mirrors ADR-0024 §Acceptance evidence for
  threshold mode.
* **Threshold mode unchanged.**
  `tests/test_margin_admissibility.py::TestGenerateMarginMode::test_threshold_mode_unchanged_by_margin_plumbing`
  asserts `mode="threshold"` and unset `mode` produce identical
  tokens.
* **Refusal on insufficient margin.**
  `test_v2_001_refuses_when_delta_too_high` runs FSC-PUB-V2-001 at
  `delta = 0.9` (above its 0.597 margin) and asserts
  `InnerLoopExhaustion` with `reason=INNER_LOOP_EXHAUSTION` and the
  full ranking in `rejected_attempts`.  No silent boundary fallback.
* **Replay determinism.**
  `TestMarginModeDeterminism::test_margin_mode_replay_stable_across_5_runs`
  asserts 5 reruns of the same input produce identical canonical
  trace steps.
* **Strict tie-break determinism.**
  `TestRankCandidates::test_strict_tie_break_by_ascending_index`
  asserts equal-score candidates resolve to the lower-index winner
  reproducibly across 5 runs.

## Out of scope

* **Promoting margin to default.**  Requires a separate ADR plus
  trace-hash migration evidence.
* **Rotor-frame margin.**  ADR-0025 will wire rotor admissibility;
  if its mechanism also benefits from a margin gate, that's an
  ADR-0025 decision.
* **Per-family delta calibration.**  Phase 5 will report metrics
  stratified by failure-mode family.  If a family fails on the
  single `delta`, the finding is architectural and surfaces in
  Phase 5; this ADR explicitly forbids per-family tuned constants
  as a fix.
* **CLI flags.**  RuntimeConfig + ChatRuntime is the wired surface.
  A `--admissibility-mode` flag is a UX follow-up, not load-bearing
  for the contract.

## Risks

* **A single `delta` may fail on a future failure-mode family.**
  Mitigation: the default is falsifiable (Phase 5 will diversify);
  refusal is honest (`InnerLoopExhaustion` carries the ranking, so
  the failure mode is visible in the trace).  Patching with
  per-family constants is explicitly out of scope.
* **Margin mode changes selection semantics.**  Threshold-mode
  acceptance evidence does not transfer.  Mitigation: default off;
  separate test suite (`tests/test_margin_admissibility.py`) pins
  margin contract independently.
* **Cost.**  Margin mode evaluates `cga_inner` for every candidate
  in the admissible set, not just the field-closest one as
  threshold mode does.  In practice the admissible set is small
  (chain length / v2 case size) so this is bounded.  No
  approximation added.

## Rollback

Set `admissibility_mode = "threshold"` (the default) at every call
site.  The threshold path is unchanged from ADR-0024.  No trace_hash
migration required for non-refused turns.
