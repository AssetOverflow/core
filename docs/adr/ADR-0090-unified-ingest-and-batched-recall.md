# ADR-0090 — Unified Ingest + Batched Recall (audit Findings 6 + 7)

**Status:** Proposed
**Date:** 2026-05-21
**Author:** Shay
**Related:** ADR-0054 (vault matrix cache), audit 2026-05-20 Findings 6 & 7, `chat/runtime.py:1295-1502`

---

## Context

The 2026-05-20 second-opinion audit identified two related issues in `ChatRuntime.chat()`:

**Finding 6 — within-turn multi-query recall is not batched.** `recall()` is called once for the gate check (line 1302) and again inside `generate()`'s walk loop (one call per step). `VaultStore.recall_batch` (ADR-0054) exists and amortises the matrix scan, but the chat path never uses it for the gate+walk pattern that fires every turn.

**Finding 7 — probe-ingest and commit-ingest create two different field states.** Line 1301 calls `probe_ingest(filtered)` to materialize a probe field for the gate check; line 1311 (gate-fired path) or 1379 (main path) calls `commit_ingest(filtered)` to produce the committed field that the walk actually uses. The two fields differ because:

1. `commit_ingest` applies drive bias and updates session turn state.
2. The probe field captures the prompt alone; the committed field also reflects the runtime's accumulated dialogue context.

Net effect: the gate observes a slightly different manifold position than the walk subsequently navigates. Honest refusal decisions are made on one field; the user-facing surface is generated from another.

The two findings are entangled. Batching the gate and walk recalls is only meaningful when they happen on the same field — which requires unified ingest. Resolving the ingest coherence gap is the precondition for the batching optimization.

---

## Decision

ADR-0090 ships a **flag-gated unified-ingest path** following the codebase's standard substantive-change pattern (ADR-0046 `forward_graph_constraint`, ADR-0062 `composed_surface`, ADR-0085 `gloss_aware_cause`, ADR-0088 `realizer_grounded_authority`). Default-off preserves byte-identity; flipping the flag enables the unified path for operators to validate against their workloads before any default change.

### Phase 1 — Unified ingest (this ADR, shippable now)

Add `RuntimeConfig.unified_ingest: bool = False`.

When `unified_ingest=True`:

1. `chat()` calls `commit_ingest(filtered)` **first**, producing the committed field once.
2. Drive bias is applied to the committed field immediately (matching today's `_apply_drive_bias` site on the post-gate path).
3. The gate check reads `committed.F` (not `probe_state.F`). Same `default_gate.check(...)` API, same decomposer.
4. If the gate fires, the stub-response path runs as today **with one observable change**: the turn has already committed to session state at this point. This is the intentional semantic change — stub-path turns now influence `_context.last_dialogue_blade` and the session vault's history. Operators opt into this by flipping the flag.
5. If the gate does not fire, the walk proceeds on the same `committed.F` the gate decided against. The walk and the gate see the same field. **No probe_ingest call is made on this path.**

When `unified_ingest=False` (default), today's behavior is preserved bit-for-bit. Null-lift invariant CI-pinned by a test that asserts surface + trace_hash equality across the flag-off and flag-on paths on every cognition eval case where the gate does not fire.

### Phase 2 — Batched recall reuse (separate PR after Phase 1 validates)

Once unified ingest is the default-on path:

1. The gate's `direct_hits` (top-k=3 against `committed.F`) is passed into `generate()` as a new `prebuilt_first_recall: list | None = None` parameter.
2. The walk's first step uses the prebuilt hits instead of re-calling `vault.recall()` on the same field.
3. Steps 1+ run the standard per-step recall as today, since each step's query depends on the previous step's propagation.

Phase 2 is **not shipped in this PR.** The substrate it needs (unified ingest) is the load-bearing first step. Phase 2's win is a single vault-recall call eliminated per turn — small in absolute terms, but the cleaner invariant ("gate and walk see the same hits") is what actually matters for the audit's coherence concern.

### Out of scope

- `recall_batch` for the per-step walk recalls. Each step's query depends on the previous step's field state; they cannot be batched without changing the walk's geometric semantics.
- Behavioral change on stub-path turns under `unified_ingest=False`. The pre-fix probe-then-stub-without-commit behavior is preserved exactly when the flag is off.

---

## Consequences

- **Honest refusal decisions and walk outputs are coherent** (Axiom 3 — propagation-over-mutation, Axiom 4 — one forward pass).
- **The probe/commit distinction is collapsed** when the flag is on. `probe_ingest` becomes dead code on the unified path. It's retained for the flag-off path until the flag-on path is validated and made default; at that point `probe_ingest` itself can be removed via a follow-up cleanup PR.
- **Stub-path turns now commit** when the flag is on. Operators must accept this trade-off (cleaner coherence + session-state continuity on refused turns) when they flip the flag. The alternative (commit, then roll back) introduces field-state rollback complexity that this ADR explicitly rejects.
- **Phase 2 substrate is unblocked.** The natural follow-up — pass the gate's hits to `generate()` to eliminate the duplicate recall — becomes a one-line wiring change once unified ingest is the live path.

---

## Rejected alternatives

1. **Land Phase 1 + Phase 2 as one PR.** Phase 2's `generate()` API change touches the walk's hot loop and warrants its own validation lane. Bundled changes risk masking a regression in either half. Rejected.
2. **Roll back the commit on gate-fired turns.** Field-state rollback requires snapshotting before commit and restoring after — non-trivial invariants (versor closure, holonomy bookkeeping) need to survive the rollback. The cleaner contract is "stub-path turns commit just like main-path turns; the only difference is the surface." Rejected.
3. **Default `unified_ingest=True` immediately.** Stub-path commit-behavior change is observable in any operator workload that distinguishes between "this turn was refused" and "the field was updated." Default-off, flag-flip-after-validation is the codebase's standard pattern (ADR-0046 / ADR-0062 / ADR-0085 / ADR-0088 / ADR-0089). Rejected.

---

## Validation gate

Phase 1 merge must demonstrate:

- `unified_ingest=False` (default) byte-identical to pre-fix on every cognition eval case (CI-pinned by `test_unified_ingest_null_lift`).
- `unified_ingest=True` produces well-formed responses on a smoke prompt set; gate decisions are made on the committed field; the walk uses the same field the gate decided against.
- Stub-path turn-state behavior change documented in `docs/runtime_contracts.md` as a flag-conditional invariant.

Phase 2 merge (separate PR) must demonstrate:

- The walk's first-step recall is bypassed when `prebuilt_first_recall` is provided and the field state matches.
- Walk surfaces remain byte-identical to the no-prebuilt path on a held-out test set.
- A single recall call per turn is eliminated, measurable in the existing pipeline-profiler benchmark.
