# ADR-0022 — Forward Semantic Control

**Status:** Draft (skeleton — sections marked **TBD** require design work
before promotion to Proposed)
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

### 3. The intent classifier is itself field-coupled (TBD)

The current `generate/intent.py` is rule-based regex over raw text.
Forward semantic control on top of a non-geometric classifier
recreates the same gap one level up — the classifier becomes the
oracle the field defers to.

**TBD design question:** what is the smallest deterministic
field-grounded intent operator that can replace or supplement the
regex classifier without re-importing sampling? Candidates to
evaluate:

- Construct intent from the prompt versor's projection onto a
  frame-relation manifold (deterministic, exact).
- Treat the regex classifier as a *seed* that the field must
  ratify; reject the intent if the prompt versor lies outside the
  intent's admissible region.
- Defer to v2; ship v1 with regex classifier explicitly marked as
  the load-bearing oracle and a `bench intent_field_coupling` lane
  that measures the gap.

The decision must be made before this ADR is promoted from Draft to
Proposed.

## Code impact (planned, not yet implemented)

### Modified

- `generate/proposition.py`
  - `propose()` consumes an `AdmissibilityRegion` parameter (default
    `None` preserves current behavior during transition).
  - Subject/predicate/object selection restricted to region.

- `generate/stream.py`
  - `_recall_state` accepts an `AdmissibilityRegion`; rejects rotor
    transitions that exit it.
  - `_nearest_next` accepts admissible-node candidate set.

- `generate/graph_planner.py`
  - `plan_articulation` returns both the existing `ArticulationTarget`
    and a new `AdmissibilityRegion`.

- `field/propagate.py`
  - Adds a region-aware propagation variant. Existing
    `propagate_step` retained for paths that do not yet pass a
    region (deprecation roadmap TBD).

- `core/cognition/pipeline.py`
  - Drops the parallel-then-override pattern in favor of single
    region-constrained generation.
  - Failure surface routes through the existing unknown-domain
    path (ADR-0021 §Articulation alignment).

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

This ADR is promoted from Draft to Proposed only when ALL hold:

1. **Eval lane exists.** `evals/forward_semantic_control/` with at
   least one case that *only the constrained walk passes*. Lane
   contract written, runner skeletonised, dev cases drafted.
2. **Determinism invariant designed.** Test fixture that proves
   same `(graph, field, region) → same surface` byte-for-byte
   across runs and across the two backend implementations
   (Python + Rust, when parity lands per ADR-0020).
3. **Failure surface designed.** Specified what the user sees when
   no admissible transition exists. Must reuse the existing
   refusal surface from `refusal_calibration` for honesty
   consistency.
4. **Intent oracle question answered.** §Decision item 3 has a
   concrete v1 path written, not deferred.
5. **No anti-patterns reintroduced.** A code-reviewer pass
   verifies none of the forbidden shapes (template authoring,
   sampling, symbolic planner, learned ranking) appears in any
   proposed module.

This ADR is promoted from Proposed to Accepted only when ALL hold:

6. The eval lane in (1) passes against the implementation.
7. Existing lanes (`refusal_calibration`,
   `articulation_of_status`, `contradiction_detection`,
   `teaching_injection_resistance`, `cognition`) remain green
   under the change.
8. `bench cost` and `bench footprint` show no regression beyond
   a budget stated in this ADR before promotion (the constraint
   layer should narrow candidate space earlier; a *speedup* is
   expected, a slowdown is the surprise to investigate).

## Named gaps and open questions

- **TBD-1 — Intent oracle.** See §Decision item 3.
- **TBD-2 — Region intersection algebra.** When the frame, the
  active typed relation, and the identity manifold each impose
  constraints, how do they compose? Set intersection on candidate
  sets is the obvious answer for tokens; for *rotors* the
  composition needs a closed operator. Likely candidate:
  conjugation under the frame versor, but the closure proof is
  not yet written.
- **TBD-3 — Backward compatibility window.** The constrained and
  unconstrained paths must coexist while the eval lane is built
  and while existing lanes are migrated. Default `region=None`
  preserving current behavior is the obvious bridge but creates
  the temptation to leave it on permanently. A removal date or
  removal-blocker test is needed.
- **TBD-4 — Identity manifold as constraint source.** The
  external assessment correctly notes identity can feed
  admissibility (`same graph, different identity manifold →
  different admissible transitions → different articulation
  trajectory`). The mechanism is plausible but the operator is
  not specified. v1 may exclude this; v1 must say so explicitly.
- **TBD-5 — Pack semantic depth.** Forward control over a thin
  pack will look like over-constraint ("nothing is admissible →
  refuse everything"). The cognition pack
  (`en_core_cognition_v1`) may need targeted extensions before
  the lane can pass. Required pack work to be enumerated in the
  v1 implementation PR.

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

## Implementation sequencing (proposed)

This is a roadmap sketch, not a commitment. Each step blocks the next.

1. Draft → Proposed: close all TBD items above. Land
   `evals/forward_semantic_control/` skeleton + dev cases.
2. Proposed → in-progress: implement `generate/admissibility.py`
   pure-function module. No call sites changed yet.
3. Wire `propose()` first (smallest surface change). Run all
   existing lanes; no regressions allowed.
4. Wire `_recall_state` and `_nearest_next`. Run eval lane and
   `bench cost`. Cost regression is a stop-the-line signal.
5. Drop the pipeline parallel-then-override pattern. Single
   region-constrained generation path.
6. Migrate `field/propagate.py` callers off the unconstrained
   variant. Mark TBD-3 removal-blocker test.
7. Rust parity (ADR-0020 sequence): port the constrained
   propagation operator. Byte-identical or no ship.

Each step ships as its own ADR-bound PR with its own evidence.

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
