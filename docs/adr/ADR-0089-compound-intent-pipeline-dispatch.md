# ADR-0089 — Compound-Intent Pipeline Dispatch (Finding 4)

**Status:** Proposed
**Date:** 2026-05-20
**Author:** Shay
**Related:** `generate.intent.classify_compound_intent`, ADR-0066 (thread context), PR #76 (surface authority resolver)

---

## Context

The 2026-05-20 audit identified that `classify_compound_intent()` is fully implemented in `generate/intent.py` but **never called by the cognitive pipeline**. The two existing call sites are:

- `chat/runtime.py:961` — inside `_maybe_apply_discourse_planner`, gated by `RuntimeConfig.discourse_planner=False` (default off).
- `evals/compound_intent_decomposition/runner.py` and `evals/cold_start_grounding/runner.py` — eval-only.

`CognitiveTurnPipeline.run()` calls only the single-intent `classify_intent()` at line 110 and routes the result straight into `graph_from_intent()`. For an input like *"What is X and how does it relate to Y?"* the pipeline picks one intent by regex precedence (probably `DEFINITION` on `X`) and silently drops the `CAUSE` / `TRANSITIVE_QUERY` clause on `Y`. The graph never sees both subjects, the resolver never sees the second clause, and the trace hash records only the dominant clause.

Wiring compound intent into the pipeline is **not a single small PR**. Every downstream stage today assumes one intent + one subject:

1. `PropositionGraph` carries one root node per turn.
2. `plan_articulation` topologically orders the nodes of a single-root graph.
3. `realize_semantic` builds one `ArticulationTarget` per call.
4. The surface resolver (PR #76) picks one surface per turn.
5. `compute_trace_hash` records one `intent_tag` and one `articulation_surface` per turn.
6. The teaching loop binds one correction-source proposal per turn.
7. The speculative-subject cache (PR #77) tracks subjects per proposal, but the marker decision assumes one subject set per surface.
8. The register / anchor-lens telemetry (ADR-0072 / ADR-0073d) emits one `(register_id, register_variant_id)` and one `(anchor_lens_id, anchor_lens_mode_label)` per turn.

Naive multi-node dispatch breaks every one of these assumptions.

---

## Decision

ADR-0089 proposes a **three-phase rollout** that lands compound intent without breaking any existing invariant. Each phase is independently shippable.

### Phase C1 — Substrate (no behavior change)

- Add `CompoundIntent` plumbing to `CognitiveTurnPipeline.run()`:
  - Call `classify_compound_intent(text)` at step 1b alongside the existing `classify_intent(text)`.
  - When the compound classifier returns a single-clause result, the pipeline takes the existing single-intent path byte-identically.
  - When it returns multiple clauses, the pipeline **still routes the dominant clause through the existing path** and records the other clauses on a new `CognitiveTurnResult.dropped_compound_clauses: tuple[DialogueIntent, ...] = ()` field for observability.
- Add a CI invariant `tests/test_compound_intent_substrate.py::test_compound_dropped_clauses_recorded` that asserts: for the four canonical compound shapes (`AND`, `BUT`, `BECAUSE`, comma-joined), the dropped clauses appear in the result and the dominant-clause surface is byte-identical to today.

Phase C1 is **byte-identical** at the surface and trace_hash level. It surfaces the second-clause loss as observable telemetry instead of silent drop.

### Phase C2 — Multi-node graph (opt-in)

- Add `RuntimeConfig.compound_intent_dispatch: bool = False`.
- When enabled and the compound classifier returns multiple clauses, `graph_from_intent` is widened to accept a `tuple[DialogueIntent, ...]` and emits one node per clause with explicit `CompoundEdge(source=p0, target=p1, relation=ConjunctionRelation.AND|BUT|BECAUSE)` edges.
- `plan_articulation` walks the multi-node graph in topological order; each node yields an `ArticulationStep` with `move=RhetoricalMove.CONTINUE` for non-root nodes.
- `realize_semantic` consumes the multi-step target and emits one surface per clause joined by the appropriate conjunction (`and`, `but`, `because`).
- The surface resolver (PR #76) is widened to accept a `multi_clause_surface` field that, when non-empty, wins over the single-clause runtime surface. Walk / compose folds append to the multi-clause surface as before.
- `compute_trace_hash` is widened with a `compound_clauses_hash: str = ""` field — a deterministic hash of the dropped (Phase C1) or routed (Phase C2) clauses' intent tags + subjects. Empty string preserves pre-ADR-0089 trace hashes byte-identically when the dispatch is off.

Phase C2 is **opt-in substantive**. Default off preserves every existing invariant.

### Phase C3 — Telemetry alignment

- Widen `TurnEvent` and `ChatResponse` with `compound_clause_count: int = 0` and `compound_relation_chain: tuple[str, ...] = ()` so operators can see compound dispatch outcomes without parsing surfaces.
- Document the new fields in `docs/runtime_contracts.md` under a new "compound intent" subsection.
- Add a `core demo compound-tour` walking four prompts (`AND`, `BUT`, `BECAUSE`, comma-joined) × two modes (flag off, flag on) and asserting:
  - flag-off: byte-identical surfaces and trace_hashes (null-lift invariant).
  - flag-on: distinct surfaces, distinct trace_hashes, all clauses represented in the surface, all clauses recorded in the new telemetry fields.

---

## Consequences

- **Pipeline becomes compositionally complete** — input shape (compound) maps to output shape (multi-clause) deterministically.
- **The teaching loop will need to learn which clause a correction binds to.** Today a CORRECTION turn binds to the prior turn's single proposal; with multi-clause prior turns, the correction-binding rule must specify which clause is being corrected. Out of scope for ADR-0089 itself; a follow-up ADR handles correction routing under multi-clause priors.
- **Speculative-subject cache (PR #77) gains multi-subject inserts.** No code change required — `_remember_speculative_subject` is per-subject and idempotent; multi-clause proposals call it once per clause.
- **Register / anchor-lens dispatch is unaffected** — both axes apply to the realizer output as a whole, not per clause. ADR-0072 + ADR-0073d invariants remain pinned.

---

## Rejected alternatives

1. **Land compound intent as a single unified PR.** The blast radius (graph_planner + plan_articulation + realize_semantic + surface resolver + trace_hash + telemetry + tests) is too large for a load-bearing PR per CLAUDE.md. Rejected.
2. **Route compound intent through `_maybe_apply_discourse_planner` only.** That path is already wired but defaults off and produces multi-clause output via a different code path (the discourse planner builds clauses from a `GroundingBundle`, not from a multi-node graph). Doubling up the paths is structural drift. Rejected — Phase C2 supersedes the discourse planner's compound dispatch.
3. **Auto-enable compound dispatch by default.** Compound prompts are a minority of input shapes; flag-off byte-identity is load-bearing for re-baseline confidence. Rejected.

---

## Validation gate

Phase C1 merge:

- Compound classifier output appears on `CognitiveTurnResult.dropped_compound_clauses` for every multi-clause input.
- All existing tests pass byte-identically.
- New invariant test on the four canonical compound shapes.

Phase C2 merge (separate PR):

- Flag-off byte-identity invariant (`test_compound_intent_null_lift`).
- Flag-on multi-clause surface invariant (`test_compound_clauses_in_surface`).
- Flag-on distinct-trace-hash invariant (analogous to register / anchor-lens patterns).
- `core eval cognition` byte-identical with the flag off; flag-on is exercised via a new lane `evals/compound_intent_pipeline/`.

Phase C3 merge (separate PR):

- `core demo compound-tour` ships; both flag-on and flag-off assertions in CI.
- `docs/runtime_contracts.md` updated.
