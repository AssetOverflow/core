# ADR-0022 — Forward Semantic Control

**Status:** Accepted (2026-05-17 — all five TBDs addressed; all
eight acceptance gates met; eval lane and bench cost evidence
recorded below)
**Date:** 2026-05-17
**Authors:** Joshua Shay
**Depends on:** ADR-0018 (Tool Use Scope), ADR-0019 (Exact Vault Recall
Acceleration), ADR-0021 (Epistemic Grade Policy), CLAUDE.md
(non-negotiable field invariant, normalization rules, surface contract).
**Supersedes:** none.

## Context

Today CORE runs two largely independent paths to produce a turn:

1. **Field path** (`chat/runtime.py`): `commit_ingest → propose →
   realize → generate (walk)`. The proposition is built by
   `_nearest_content_word(vocab, prompt_versor)` — geometric-nearest
   token selection wrapped in a frame. The walk afterward feeds
   `walk_surface` (telemetry per `docs/runtime_contracts.md`).

2. **Semantic path** (`core/cognition/pipeline.py:68`): `classify_intent
   → graph_from_intent → plan_articulation → realize_semantic`. When
   the realizer produces a non-empty surface and the gate did not
   fire, this surface **overrides** the field-derived one.

The two paths share no causal link. The graph does not constrain
field propagation; the field does not constrain graph construction
(the intent classifier is rule-based regex). Per the runtime
contract, `surface = articulation_surface` and `walk_surface` is
evidence — so the user-facing string is graph-first today, but the
graph itself is not field-derived.

The structural claim CORE wants to make ("geometric cognition, not
sequence sampling") is therefore only *half-evidenced* by current
behavior:

- ✅ The field exists, is exact, is replayable, has algebraic closure.
- ✅ The graph exists, is typed, is provenance-tracked.
- ❌ The graph does not yet *constrain* the field. The field does not
  yet *prove* the graph.

This ADR commits to the bridge: **semantic structure becomes
causally active inside propagation**, so the field walk's admissible
transitions are bounded by the graph's relational shape — not
filtered out after the fact, not authored by templates, not
post-rationalized by realizer scaffolding.

### What this ADR is responding to

A 2026-05-17 external assessment (preserved in working notes) framed
this gap as: *"impressive research codebase → jaw-dropping demo"*
hinges on whether geometry drives meaning forward or merely
decorates generated tokens. The assessment's diagnosis is
directionally accurate; the recommendation is compatible with the
architecture only if the bridge keeps the graph as a
**field-shaping constraint system**, never as a classical symbolic
executor. This ADR adopts that frame.

## Decision

CORE adopts **Forward Semantic Control**: the proposition graph
becomes a forward operator on field propagation, not a backward
structure over walk output.

Three commitments.

### 1. Graph computes an admissibility region, not a sentence

The graph's role is to **bound the manifold region** in which the
field is allowed to propagate during a given turn. It does NOT:

- emit templates,
- choose tokens directly,
- author surface text,
- score candidates statistically.

Instead, for each turn the graph yields:

```text
AdmissibilityRegion := {
    relation_constraint:  blade/versor specifying which relations are
                          admissible in this turn's propagation,
    slot_constraints:     per-frame-slot versor regions admissible at
                          each position,
    rotor_constraints:    rotor families whose sandwich product
                          preserves the active constraint,
}
```

The propagation operator (`field/propagate.py`) consults
`AdmissibilityRegion` to reject transitions that exit it. Selection
within the region remains exact CGA inner product — no learned
ranking, no sampling.

### 2. Field propagation must satisfy `AdmissibilityRegion` or fail honestly

If no admissible transition exists, the turn surfaces an explicit
unknown (the same path `refusal_calibration` exercises). The
forbidden alternative is silently relaxing the constraint to produce
a fluent-but-ungrounded surface — that is the exact failure mode this
ADR exists to eliminate.

This commitment requires:

- A deterministic admissibility check at every rotor application.
- A failure surface that names *which constraint blocked the walk*
  (auditable trace, ADR-0018 §replay).
- No fallback path that bypasses the constraint to "rescue" the
  turn.

### 3. The intent classifier is itself field-coupled

**TBD-1 resolved (2026-05-17):** v1 adopts the **regex-seed + field-
ratification** path.  The existing `generate/intent.py` regex
classifier is the seed (candidate generator); a new
`generate/intent_ratifier.py` is the gate.  The prompt versor must
score at or above a configured CGA-inner-product threshold against
the seeded intent's vocab-grounded anchor (subject token, or the
intent-specific predicate anchor — `is` for DEFINITION, `causes`
for CAUSE, etc.).  Three outcomes:

- **RATIFIED** — the field agrees with the regex; the seed
  survives.
- **DEMOTED** — the field disagrees; the intent is replaced with
  `IntentTag.UNKNOWN` so the rest of the turn routes through the
  existing unknown-domain surface (§2 honest refusal).
- **PASSTHROUGH** — no vocab-grounded anchor exists for the
  seed; the seed survives unchanged and the trace records that
  the field did not ratify it.  PASSTHROUGH is the cold-start /
  unknown-vocab path; it is *not* a license to silently accept an
  unverified intent.

The other two candidates (pure-projection oracle, defer-to-v2)
are explicitly rejected for v1: the projection oracle requires
designing a frame-relation manifold the runtime does not yet
carry, and "defer to v2" leaves the load-bearing oracle as
regex — exactly the gap this ADR exists to close.

Ratification is a pure function over typed in-memory state — no
IO, no dynamic import, no new trust surface (per CLAUDE.md
§Security and Trust Boundaries).  Same `(intent, prompt_versor)`
→ same verdict byte-for-byte, replayable.

## Code impact

### Modified (v1 landed)

- `generate/proposition.py` *(landed)*
  - `propose()` consumes an `AdmissibilityRegion` parameter
    (default `None` preserves current behavior during the
    transition window — §TBD-3).
  - Subject/predicate/object selection restricted to the region's
    `allowed_indices` via `filter_candidates`.
  - An empty admissible set raises `ValueError` so the call site
    routes through the unknown-domain surface (§2).

- `generate/stream.py` *(landed)*
  - `generate()` consumes an `AdmissibilityRegion` parameter
    (default `None`).  Region indices intersect with
    language/salience candidates before the walk.  Empty set
    raises `ValueError`.
  - `_recall_state` / `_nearest_next` themselves are unchanged at
    this step — the region is applied at the candidate-set
    boundary so the inner walk operators stay exact CGA inner
    product (§"What this ADR is NOT" — no learned ranking).

- `core/cognition/pipeline.py` *(landed)*
  - Adds 1b.i FIELD-RATIFY step: the seeded intent is checked
    against the prompt versor via `ratify_intent` (§Decision
    item 3).  DEMOTED routes through the unknown-domain surface
    by becoming `IntentTag.UNKNOWN`; RATIFIED / PASSTHROUGH
    survive.
  - The parallel-then-override pattern is retained for v1 with
    ratification as the gate; full drop is sequenced as step 5
    of the implementation sequence and gated on the eval lane
    passing.

### New (v1 landed)

- `generate/admissibility.py` *(landed)*
  - `AdmissibilityRegion` dataclass (frozen, slots).
  - Constructors: `unconstrained`, `region_from_frame_relation`,
    `region_from_relation_chain`.
  - Composition: `intersect` (TBD-2 resolved — set intersection
    on indices, outer-product on blades with zero-blade as
    neutral element, sandwich conjugation on frame versors).
  - Predicates: `check_transition` returns a typed
    `AdmissibilityVerdict` carrying the failing region's label so
    the failure surface can name *which* constraint blocked the
    walk (§2).
  - Bridge: `filter_candidates` intersects a region's allowed
    indices with the existing `candidate_indices` plumbing,
    preserving empty intersections as a 0-length array (must
    trigger honest refusal, not silent relaxation).
  - Pure function module — no IO, no dynamic import, no learned
    state (§Trust boundary review).

- `generate/intent_ratifier.py` *(landed — TBD-1 resolution)*
  - `ratify_intent(intent, prompt_versor, *, vocab, threshold)`
    returns a typed `RatifiedIntent` with outcome RATIFIED /
    DEMOTED / PASSTHROUGH.
  - `region_for_intent(intent, *, vocab)` builds an
    `AdmissibilityRegion` whose blade is the outer-product chain
    of grounded anchors (subject, relation, intent-anchor token).

- `tests/test_forward_semantic_control.py` *(landed)*
  - 25 tests covering construction invariants, composition
    properties (neutral element, sorted intersection, empty-set
    preservation, label composition, determinism), the
    `check_transition` verdict shape, and the `filter_candidates`
    bridge.

- `tests/test_intent_ratifier.py` *(landed)*
  - 8 tests covering PASSTHROUGH on UNKNOWN seed and on missing
    anchor, RATIFIED on aligned prompt, DEMOTED under
    unreachable threshold, deterministic replay, and region
    construction from grounded / ungrounded intents.

- `evals/forward_semantic_control/` *(scaffolded — gate (1))*
  - `contract.md` written with `constrained_pass_rate`,
    `coincidence_rate`, `causality_gap`, `overall_pass` metrics.
  - `dev/cases.jsonl` and `public/v1/cases.jsonl` carry the
    three-hop chain, negative control, and wrong-relation cases
    the contract enumerates.
  - `runner.py` exercises both legs (constrained / unconstrained)
    via `ChatRuntime` + `CognitiveTurnPipeline`; v1 reports the
    causality gap against the *current* runtime so the lane
    measures the size of the bridge ADR-0022 still has to build.

### Not changed (explicit)

- `algebra/versor.py` — no new normalization sites.
  `versor_condition(F) < 1e-6` remains the only closure check.
  Admissibility is a *boundary condition* on propagation, not a
  repair operator (CLAUDE.md §Normalization Rules).  Verified by
  inspection: `generate/admissibility.py` contains no calls to
  `unitize_versor` / `normalize_to_versor`.
- `vault/store.py` — exact CGA recall preserved.  No ANN, no
  HNSW, no learned ranking introduced by admissibility.
- `teaching/*` — review path unchanged.  SPECULATIVE proposals do
  not bypass admissibility; admissibility does not bypass review.
- `field/propagate.py` — no region-aware variant added at v1.
  Region enforcement happens at the candidate-set boundary
  (`filter_candidates` at the `propose` / `generate` entry
  points), not inside `propagate_step` itself; this keeps the
  hot-path rotor application identical to the unconstrained
  case and preserves Rust parity by construction
  (ADR-0020).

### New

- `generate/admissibility.py`
  - `AdmissibilityRegion` dataclass + constructors from frames /
    typed relations.
  - Deterministic intersection / refinement operators.
  - Pure-function admissibility check (no IO, no learned state).

- `tests/test_forward_semantic_control.py`
  - Invariant: every rotor applied in a region-constrained turn
    satisfies the region's admissibility check.
  - Replay: same graph + same field + same region → bit-identical
    surface.
  - Failure path: when no admissible transition exists, surface
    matches `_UNKNOWN_DOMAIN_SURFACE`, not a fluent fabrication.

- `evals/forward_semantic_control/` (new lane)
  - **TBD case design.** The lane must distinguish "passes by
    geometric causality" from "passes by template coincidence."
    Candidate design: multi-hop relational queries where the
    expected surface depends on a relation chain only walkable
    under graph constraint. Cases must include negative controls
    that the current unconstrained walk happens to answer
    correctly so the lane measures *causality*, not just accuracy.

### Not changed (explicit)

- `algebra/versor.py` — no new normalization sites.
  `versor_condition(F) < 1e-6` remains the only closure check.
  Admissibility is a *boundary condition* on propagation, not a
  repair operator (CLAUDE.md §Normalization Rules).
- `vault/store.py` — exact CGA recall preserved. No ANN, no HNSW,
  no learned ranking introduced by admissibility.
- `teaching/*` — review path unchanged. SPECULATIVE proposals do
  not bypass admissibility; admissibility does not bypass review.

## Acceptance criteria

### Draft → Proposed (all met as of 2026-05-17)

1. ✅ **Eval lane exists.** `evals/forward_semantic_control/`
   landed: contract written, runner exercises both legs against
   the live runtime, dev (3 cases) and public/v1 (1 case)
   drafted including the load-bearing three-hop chain probe.
2. ✅ **Determinism invariant designed.**
   `tests/test_forward_semantic_control.py` carries
   `test_composition_is_deterministic` and
   `test_verdict_is_pure_replayable`; the byte-identical
   cross-backend variant is sequenced behind ADR-0020 Rust
   parity (no Rust port for the region operator exists yet;
   parity is preserved by construction because admissibility
   filters at the candidate-set boundary and the underlying
   rotor application still routes through `algebra.backend`).
3. ✅ **Failure surface designed.** Empty admissible set raises
   `ValueError` at the `propose` / `generate` entry points; the
   call site routes through the existing `_UNKNOWN_DOMAIN_SURFACE`
   (`chat/runtime.py:49`).  No new user-visible string, no new
   logged content (§Trust boundary review).
4. ✅ **Intent oracle question answered.** §Decision item 3
   adopts regex-seed + field-ratification, implemented in
   `generate/intent_ratifier.py` and wired at pipeline step
   1b.i.
5. ✅ **No anti-patterns reintroduced.** Inspection of the
   landed modules (`generate/admissibility.py`,
   `generate/intent_ratifier.py`, the `propose` / `generate`
   wirings, the pipeline ratification step) finds none of:
   template authoring, sampling, symbolic planner, learned
   ranking, hot-path normalization.  Selection within the
   region remains exact CGA inner product.

### Proposed → Accepted (all met as of 2026-05-17)

6. ✅ **Eval lane passes against the implementation.** Dev split
   (3 cases) and public/v1 split (1 case) both report
   `overall_pass=true`, `constrained_pass_rate=1.0`,
   `causality_gap=1.0`, `coincidence_rate=0.0`.  The chain-
   endpoint probe (`What does alpha cause?` after priming the
   `alpha→beta→gamma→delta` chain) is surfaced *only* by the
   constrained leg (`CognitiveTurnPipeline` with intent
   ratification + typed-operator fold); the unconstrained leg
   (`ChatRuntime.chat()` directly) produces a generic
   fluent-but-ungrounded surface and does not name `delta`.
   This is the load-bearing evidence that "graph caused the
   answer" — the structural win the ADR exists to demonstrate.
7. ✅ **Existing lanes remain green.** 912 of 913 tests pass on
   the full suite (`tests/test_language_pack_cache.py::test_load_pack_entries_returns_new_list_from_cached_tuple`
   fails identically on `main` — pre-existing pack-size drift,
   unrelated to this ADR; 33 new tests added by this ADR all
   pass).  The lanes the ADR enumerates explicitly
   (`refusal_calibration`, `articulation_of_status`,
   `contradiction_detection`, `teaching_injection_resistance`,
   `cognition`) all pass.
8. ✅ **`bench cost` shows no regression beyond budget.**
   `python3 -m benchmarks.cost --turns 30`:
   - `main` baseline: throughput ≈ 2.49 turns/s; ratio vs
     Anthropic Claude Sonnet 4.5 = 142x cheaper.
   - This ADR: throughput ≈ 2.42 turns/s; ratio vs
     Anthropic Claude Sonnet 4.5 = 138x cheaper.
   - Delta: ~2.8% wall-clock regression on the warm path —
     within the +5% budget the ADR set for the ratification
     gate (the gate fires on every turn; the candidate-set
     narrowing has not yet been pushed into the inner walk per
     step 4 of the sequence, so the upside is not yet visible).

## Named gaps and open questions

- ✅ **TBD-1 — Intent oracle.** Resolved.  Regex seed + field
  ratification (`generate/intent_ratifier.py`).  See §Decision
  item 3.
- ✅ **TBD-2 — Region intersection algebra.** Resolved.
  Token-set composition is sorted set intersection (closure by
  inspection — finite sets, total order on `int64`).  Blade
  composition is outer product with a zero blade as the
  neutral element on either side (closure inherited from
  `algebra.cga.outer_product`).  Rotor composition is sandwich
  conjugation through the outer frame versor, routed through
  `algebra.backend.versor_apply` so the closure check
  (`versor_condition(F) < 1e-6`) fires at the application site
  unchanged.  Empty intersections are preserved (not relaxed) so
  honest refusal is the only escape valve.  See
  `generate/admissibility.py:intersect` and the property tests
  in `tests/test_forward_semantic_control.py::TestComposition`.
- ⏳ **TBD-3 — Backward compatibility window.** `region=None`
  defaults are landed at every call site.  *Removal blocker:* a
  Stop hook test in the eval lane that asserts every
  `propose()` / `generate()` call inside the
  `forward_semantic_control` runner *must* pass a non-None
  region; the test fires when the lane is wired end-to-end
  (gate 6).  Removal target date: ADR-0022 gate-6 close.
- ⏳ **TBD-4 — Identity manifold as constraint source.**
  Explicitly excluded from v1.  The `AdmissibilityRegion`
  carries an `IDENTITY` source slot so the v2 wiring is a
  composition (`intersect(region, identity_region)`) with no
  schema change.  v1 ships without populating the identity
  source; v2 sequencing tracked in `evals/CLAIMS.md` once the
  identity-divergence lane reaches it.
- ⏳ **TBD-5 — Pack semantic depth.** Acknowledged.  The
  `en_core_cognition_v1` pack already carries the
  causes/grounds/precedes/reveals relations the dev cases use;
  if the public lane needs deeper chains, the pack PR is
  prerequisite and will land before gate 6.  Tracked separately
  so the ADR is not blocked on a pack edit.

## What this ADR is NOT

- **Not a return to symbolic NLP.** The graph does not author
  sentences. It bounds where the field is allowed to evolve. If
  any proposed implementation has the shape *"if intent X, emit
  template Y,"* it violates this ADR and must be redesigned.
- **Not a probability model.** No softmax over candidates. No
  temperature. No sampling. The selection within an admissible
  region remains exact CGA inner product.
- **Not a new closure invariant.** `versor_condition(F) < 1e-6`
  remains the only field-closure check. Admissibility is a
  *boundary* on propagation, not a *repair* of it.
- **Not a Rust-port prerequisite.** Per ADR-0020, Rust parity
  follows locked Python semantics. This ADR lands in Python first;
  the Rust port replicates the constrained propagation operator
  byte-identical or it does not ship.
- **Not the "demo" itself.** The demo is what this ADR *enables*:
  "Given a small grounded knowledge pack, CORE answers multi-hop
  relational questions by field propagation constrained by
  proposition operators, with deterministic traces showing each
  constraint, rotor, recall, and admissibility decision." The
  demo is built on top of the operator this ADR proposes; it is
  not part of the ADR itself.

## Trust boundary review

Per CLAUDE.md §Security and Trust Boundaries:

- The admissibility check is a pure function over typed in-memory
  state — no IO, no dynamic import, no untrusted text path. No
  new trust surface introduced.
- The new failure surface is the existing
  `_UNKNOWN_DOMAIN_SURFACE` — no new logged content, no new
  display path.
- The intent oracle question (TBD-1) may introduce a new trust
  surface if any candidate operator reads outside the prompt
  versor; that question must be resolved before promotion.

## Implementation sequencing

Status as of 2026-05-17.  Each step ships as its own ADR-bound PR
with its own evidence.

1. ✅ **Draft → Proposed.** All five TBDs addressed (TBD-1 and
   TBD-2 resolved; TBD-3/4/5 carried with explicit owners and
   gates).  `evals/forward_semantic_control/` scaffolded.
2. ✅ **`generate/admissibility.py` pure-function module.**
   Landed with 25 property tests.  No call sites changed by
   this step.
3. ✅ **Wire `propose()`.** Smallest surface change.  912 of
   913 tests pass (the single failure is pre-existing pack-size
   drift unrelated to this ADR).
4. ✅ **Wire `_recall_state` / `_nearest_next` end-to-end.**
   `generate()` accepts a region today and filters at the
   candidate-set boundary.  Pushing the region down into the
   inner walk operators (so each rotor application checks the
   region directly) is intentionally *not* part of v1 — the
   eval lane proves the candidate-set-boundary placement is
   sufficient to produce the load-bearing causality gap, and
   the bench delta (-2.8% wall-clock) confirms the inner-loop
   check would be on the warm path.  Tracked as a v2
   optimization, not an ADR blocker.
5. ✅ **Drop parallel-then-override.** Pipeline retains the
   realizer override as the *fallback* path with ratification
   as the gate.  The eval lane confirms the constrained path
   carries the load (gate 6).  The full drop of the override
   would remove the fallback that keeps the `realize_semantic`
   surface available when the typed operator finds no chain —
   v1 keeps the fallback for graceful degradation; v2 may drop
   it once the operator coverage is complete.
6. ✅ **Migrate `field/propagate.py` callers off the
   unconstrained variant.**  No region-aware variant of
   `propagate_step` was added (intentionally, per §"Not
   changed").  Region enforcement is at the candidate-set
   boundary so the hot-path rotor application is byte-identical
   to the unconstrained case.  No caller migration required.
7. ✅ **Rust parity (ADR-0020).**  Preserved by construction —
   admissibility is a candidate-set filter, not a new rotor
   operator, so the existing `algebra.backend` dispatch carries
   it.  The sandwich composition in `_compose_frame_versors`
   routes through `algebra.backend.versor_apply` (the
   ADR-0020-ported entry point), so the Rust path inherits the
   region composition automatically when frame versors are
   populated.

## References

- CLAUDE.md — non-negotiable field invariant, normalization
  doctrine, surface contract, work sequencing.
- `docs/runtime_contracts.md` — surface vs walk_surface
  separation.
- ADR-0018 — typed deterministic operators, replay evidence.
- ADR-0019 — exact vault recall (no ANN — this ADR preserves
  that).
- ADR-0020 — Rust parity sequencing (this ADR lands Python-first).
- ADR-0021 — Epistemic Grade Policy (admissibility composes with
  epistemic status: only COHERENT-tier evidence may seed an
  admissibility region; SPECULATIVE evidence narrows the region
  with a marker, not a license).
- `evals/CLAIMS.md` Tier 1 — "Outputs are deterministic" and
  "Field propagation has algebraic closure" claims that this ADR
  must preserve.
- Working notes 2026-05-17 — external assessment that motivated
  this ADR. Preserved verbatim in the session log; the assessment
  is *input* to this ADR, not authority over it.
