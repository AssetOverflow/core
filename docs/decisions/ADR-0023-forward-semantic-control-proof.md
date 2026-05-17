# ADR-0023 — Forward Semantic Control: Proof Evidence

| Field        | Value          |
|--------------|----------------|
| Status       | **Accepted**   |
| Date         | 2026-05-17     |
| Supersedes   | —              |
| Extends      | ADR-0022       |
| Decision lead| Shay (with CORE assistant) |

---

## Context

ADR-0022 shipped the *mechanism* of Forward Semantic Control:

* an `AdmissibilityRegion` typed-blade object that bounds the manifold
  subset a turn may propagate into;
* a region-aware `generate()` and `propose()`, with empty admissible
  sets routed to the unknown-domain surface (honest refusal);
* field-ratified intent (TBD-1) and outer-product region composition
  (TBD-2);
* a lane (`evals/forward_semantic_control`) that shows the constrained
  pipeline can surface a chained endpoint where the unconstrained
  runtime cannot.

That is enough to establish the mechanism exists.  It is *not* enough
to demonstrate, to an industry-grade standard, that the admissibility
region itself is the load-bearing causal factor — as opposed to
some interaction of pipeline assembly, realizer override, typed-operator
fold, or ratification regex-seed.

This ADR scopes the second proof surface: **inspection and
isolation of the region as cause**.  It introduces no new runtime
semantics; every change is telemetry, hash-folded evidence, or eval
discipline.

ADR-0024 will separately scope inner-loop admissibility (per-rotor
admissibility checks after candidate prefilter) because that *is* a
semantic change and interacts with the `versor_condition` invariant.

---

## Decision

We commit to five evidence-strengthening changes:

1. **Same-path ablation (#1).**  A new eval leg drives `generate()`
   directly through the same runtime/vocab/field with `region=None`
   vs `region=R`.  The only varying input is the region object.  The
   existing pipeline-vs-runtime leg is retained as a corroborating
   integration signal.

2. **Per-transition admissibility trace (#4).**  Each call to
   `generate()` returns an `admissibility_trace: tuple[AdmissibilityTraceStep, ...]`
   recording, per step: region label, the candidate-index arrays
   before and after admissibility filtering, the selected destination,
   and the typed `AdmissibilityVerdict`.  The trace is exposed through
   `CognitiveTurnResult.admissibility_trace_hash` and folded into
   `compute_trace_hash` so per-transition admissibility decisions are
   load-bearing in deterministic replay.

3. **Ratification accounting (#5).**  `CognitiveTurnResult` carries
   the `RatificationOutcome` from the field-ratifier.  The lane reports
   `ratified_rate / demoted_rate / passthrough_rate`, and scored
   causal cases require `ratified` (PASSTHROUGH is forbidden in those
   cases).  This makes the regex-seed's residual load-bearingness
   measurable instead of latent.

4. **`region=None` instrumentation (#6).**  `CognitiveTurnResult` adds
   `region_was_unconstrained: bool`.  The forward-semantic-control
   lane runner asserts the constrained leg is *not* unconstrained.
   This is observation only; we do not fail-closed in production
   yet — the runtime keeps `None` as a legal cold-start sentinel.

5. **Lane expansion with adversarial distractors (#3 / #9).**
   `evals/forward_semantic_control/dev/cases.jsonl` covers multiple
   relation axes (cause, means, precedes, part_of) and includes
   adversarial distractor cases that bind a `forbidden_token` to a
   *different* relation off the same head.  These cases test that the
   region's blade is binding, not just its index set.

Out of scope for this ADR (deferred to ADR-0024 / later work):
inner-loop per-rotor admissibility, no-realizer scoring mode,
cost-matrix bench, and quarantining `region=None` in production.

---

## Acceptance gates

| # | Gate | Evidence |
|---|------|----------|
| 1 | Same-path ablation present | ✅ runner exposes `_run_region_ablation`; lane metrics include `region_only_constrained_rate=1.00`, `region_only_unconstrained_rate=0.00`, `region_only_gap=1.00` over 5 chain-dependent cases |
| 2 | Trace round-trips through hash | ✅ `hash_admissibility_trace` deterministic; `tests/test_admissibility_trace.py` includes same-trace-same-hash, mutation-changes-hash, reason-change-changes-hash, and pre-ADR-0023 byte-preservation tests (all green) |
| 3 | Ratification rates reported | ✅ lane reports `ratified_rate=1.00`, `demoted_rate=0.00`, `passthrough_rate=0.00`, `passthrough_on_scored=false`. Note: the first lane run after ADR-0023 §3 instrumentation surfaced a wiring bug in `_ratify_intent` (looked up `runtime.vocab` instead of `runtime.session.vocab`); the gate's measurement *itself* caught the bug — fix applied |
| 4 | Region-None observable | ✅ `CognitiveTurnResult.region_was_unconstrained` exposed; `region_was_unconstrained=False` folded into `compute_trace_hash` only when non-default so pre-ADR-0023 turn hashes are byte-preserved |
| 5 | Lane expanded | ✅ dev lane carries 8 cases across 4 relation axes (cause / means / precedes / part_of) including 2 adversarial distractors (FSC-DEV-007 means-vs-cause off the same head; FSC-DEV-008 branching distractor across cause and means). `causality_gap=0.80`, `region_only_gap=1.00` |
| 6 | Bench within budget | ✅ `evals/reports/cost_latest.json`: `wall_seconds_total=9.41s` for 20 turns (~470ms/turn) vs ADR-0022 baseline 12.38s — well inside the +5% budget |

### Lane metrics (dev, 2026-05-17)

```json
{
  "constrained_pass_rate": 0.80,
  "unconstrained_pass_rate": 0.00,
  "coincidence_rate": 0.00,
  "causality_gap": 0.80,
  "region_only_constrained_rate": 1.00,
  "region_only_unconstrained_rate": 0.00,
  "region_only_gap": 1.00,
  "ratified_rate": 1.00,
  "demoted_rate": 0.00,
  "passthrough_rate": 0.00,
  "passthrough_on_scored": false,
  "chain_dependent_count": 5,
  "negative_control_count": 3,
  "overall_pass": true
}
```

`region_only_gap=1.00` is the load-bearing piece of evidence: same runtime,
same vocab, same field state after primes, same persona, same prompt — the
only varying input is `region=None` vs `region=AdmissibilityRegion`. The
region alone moves pass rate from 0/5 to 5/5. This is the cleanest
single-variable demonstration that forward semantic control is causally
load-bearing.

---

## Anti-patterns explicitly rejected

These remain forbidden, consistent with CLAUDE.md and ADR-0022:

* Per-step admissibility trace must not introduce mutation, hidden
  normalization, or repair operators on the field path.  It is
  observation only.
* Adding admissibility trace must not change `versor_condition`
  behavior or alter which candidates are selected.
* Demotion to PASSTHROUGH must not be silently introduced as a
  fallback path for failed ratification: a turn that should have
  ratified but didn't is information, not a workaround.
* The same-path ablation does not bypass the pipeline; it
  *complements* it.  The pipeline-vs-runtime leg remains.

---

## Consequences

Positive:

* The claim "the admissibility region caused this answer" becomes
  inspectable per-turn and replayable via trace hash.
* PASSTHROUGH escape-hatch usage becomes a reported metric instead
  of a latent risk.
* Eval breadth covers multiple relation axes, not just `cause`.

Negative / costs:

* Per-step trace inflates the result object; we mitigate by storing
  immutable tuples and only hashing the canonical serialization.
* Eval lane grows from 3+1 cases to ≥ 8+, with corresponding runtime
  cost on `core eval cognition`; we accept this as the price of
  generality evidence.
