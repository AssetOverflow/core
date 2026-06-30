# ADR-0018 — Tool Use Scope: Typed Deterministic Operators

**Status:** Accepted
**Date:** 2026-05-16
**Authors:** Joshua Shay
**Supersedes:** Open Scope Decisions row "Tool use (typed deterministic
operators)" in `docs/PROGRESS.md`.
**Depends on:** ADR-0017 (Agency Scope).

## Context

ADR-0016 flagged *tool use* as an open scope decision required
before Phase 3.  The capability roadmap (Phase 3 work items) notes
that multi-step reasoning *may* benefit from operator delegation
(`docs/capability_roadmap.md`).  Phase 3 v1 evidence
(`evals/inference_closure/gaps.md` Gap 1 + Gap 2,
`evals/multi_step_reasoning/gaps.md`) confirms this: closing the
inference-depth gaps requires a `transitive_walk` operator over the
proposition graph and a `path_recall` operator over the vault.

The question is what shape such operators take in CORE.  Three
positions are available:

- **No tools.**  Reasoning depth is implemented inline in the
  articulator and field-propagate machinery.  No first-class
  operator surface.
- **External tools.**  CORE invokes external services (calculator,
  search, code execution, shell) through a generic tool-use
  protocol.
- **Typed deterministic operators.**  CORE exposes a small,
  curated set of pure-function operators over its own typed state
  (proposition graph, vault, field state).  No external IO.  Each
  operator is invoked synchronously inside a responsive turn (per
  ADR-0017).

## Decision

CORE adopts **typed deterministic operators**:

1. **Operators are pure functions over CORE's typed state.**  Each
   operator takes typed inputs (proposition-graph nodes, vault
   entries, field versors, relation predicates) and returns typed
   outputs.  No side effects beyond the per-turn deterministic
   record.

2. **No external IO at this stage.**  CORE will not invoke shells,
   network endpoints, file IO outside the existing pack/vault
   contracts, or other models.  External tool integration is
   deferred to a later phase and would require its own ADR.

3. **Operator registry is curated and small.**  Adding an operator
   is a deliberate design act with an ADR-level decision.  No
   plug-in surface; no dynamic operator loading; no caller-supplied
   operators.  The deterministic-replay contract requires the
   operator set to be a fixed, versioned part of the build.

4. **Operators participate in trace_hash.**  When an operator is
   invoked during a turn, its name, inputs, and outputs are folded
   into `trace_hash` so replay is bit-for-bit reproducible.  This
   is the mechanical guarantee that makes operators safe to add.

5. **Operators are invoked by the articulator inside one turn.**
   Per ADR-0017, no operator runs autonomously between turns.  The
   articulator decides whether to invoke an operator based on the
   intent classification and proposition-graph shape produced for
   the current turn.

## Initial operator set (Phase 3 v2)

Two operators land together as the bounded Phase 3 v2 engineering
work that closes inference-closure Gap 1 + Gap 2:

- **`transitive_walk(graph, head, relation, max_hops) ->
  list[Node]`**
  Deterministic traversal of the proposition graph from `head`
  following only edges labeled `relation`.  Returns the path of
  visited nodes.  Bounded by `max_hops` (initial cap: 5; see
  `evals/multi_step_reasoning/contract.md`).  No approximate
  search.  Empty path is a valid result.

- **`path_recall(vault, entity, relation_chain) ->
  list[VaultEntry]`**
  Returns vault entries that participate in the named relation
  chain starting from `entity`.  Uses the existing exact-CGA
  inner product for entity matching; no approximate / HNSW /
  ANN substitution permitted (per CLAUDE.md).

Both operators are pure functions with no global state.  Both
produce outputs that are themselves addressable in the proposition
graph and vault, so their results round-trip through the existing
pipeline.

## What this rules out

- **Generic plugin protocols (MCP-style).**  CORE does not become a
  host for external tools.  The strict typing and replay-determinism
  contracts forbid arbitrary capability surfaces.
- **LLM-as-judge / LLM-as-tool patterns.**  No operator may call out
  to a stochastic model.
- **Approximate retrieval / search operators.**  Per CLAUDE.md
  ("Vault recall is exact and deterministic.  Do not add cosine
  similarity, HNSW, ANN indexes, or approximate recall to the
  runtime path."), search-shaped operators must remain exact.

## Consequences

- **Phase 3 v2 has a well-defined shape.**  The two-operator bundle
  above is the unit of engineering work.  It is small, testable,
  and replay-safe by design.
- **Operator-aware trace hashing.**  `core/cognition/trace.py` will
  need a small extension to fold operator invocation records into
  the hash.  This is one of the bounded design tasks inside the
  Phase 3 v2 work.
- **Articulator gains an operator-call site.**  `generate/realizer.py`
  and/or `generate/graph_planner.py` learn to decide *whether* to
  invoke an operator based on intent + graph shape.  This decision
  itself is deterministic — no learned policy.
- **No operator-registry hot path.**  Operator lookup is at the
  import-time level, not the per-turn level.  The operator set is
  effectively part of the build.

## Future extensions (recorded so they're not forgotten)

When (and if) external IO becomes scoped:

- **Calculator** (pure-function over typed numerics) is the
  cleanest first external operator candidate.  Still typed,
  still deterministic, no network.  Probably Phase 4 or later.
- **Document retrieval** over curated packs (not the open web)
  could become typed if the corpus is content-addressed and the
  result is bit-stable.
- **Search / code execution / shell** are out of scope for the
  foreseeable future.  They break replay determinism and the
  trust-boundary discipline in CLAUDE.md.

Metaphor, narrative, and writing-style work (raised in 2026-05-16
session, recorded in `evals/compositionality/gaps.md` and
`evals/cross_domain_transfer/gaps.md`) live under this ADR's
operator umbrella if they ever land: a metaphor operator is a
typed deterministic function over the proposition graph plus a
selectivity filter, not an external capability.

## Verification

- The two Phase 3 v2 operators land with unit tests showing
  replay-bit-stability.
- `trace_hash` extension passes determinism tests in
  `tests/test_determinism_proofs.py`.
- All inference-closure / multi-step-reasoning / compositionality /
  cross-domain-transfer lanes are re-scored after the operator
  bundle lands.
