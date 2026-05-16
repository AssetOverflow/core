# ADR-0019 — Exact Vault Recall Acceleration

**Status:** Accepted
**Date:** 2026-05-16
**Authors:** Joshua Shay
**Depends on:** ADR-0016 (Capability Roadmap),
`evals/long_context_cost/v1` evidence.

## Context

CLAUDE.md establishes that vault recall is exact and deterministic:

> Do not add cosine similarity, HNSW, ANN indexes, or approximate
> recall to the runtime path.  Vault recall is exact and
> deterministic.

The Phase 4 `long_context_cost` lane (v1) measured per-recall
latency of the current Python `vault_recall` fallback against
synthetic float32 (32,) versors:

- N = 10³ → median recall ≈ 870 ms
- N = 10⁴ → see `evals/long_context_cost/results/v1_metrics.json`
- N = 10⁵ → see `evals/long_context_cost/results/v1_metrics.json`

Even at N=10³ — well below any realistic vault size — recall is
~1 second per query, which is unfit for a per-turn runtime call.
The cost shape is dominated by per-iteration NumPy dispatch, not
by the algebra.  Exact correctness is preserved; performance is
not.

The question is *how to accelerate vault recall while remaining
exact* — and in what order.

## Decision

CORE adopts a **three-stage, semantics-preserving acceleration
plan** for vault recall.  Each stage is gated on evidence from
the previous stage.  No stage permits approximate recall.

### Stage 1 — Vectorised exact scan (commit immediately)

Replace the per-element Python loop in
`algebra/backend.py::vault_recall` with a single batched
matrix-vector inner product over the stacked versor matrix
`M ∈ ℝ^{N×32}`.  CGA inner product is bilinear; the metric
factors once and is reused.

- **Exactness:** required to be **bit-identical** to the scalar
  path, verified by a correctness test that asserts
  per-element equality across a fixture vault.  Float32 CGA inner
  products are deterministic under fixed reduction order, so we
  pin reduction order (e.g. `np.einsum` with explicit `optimize`
  off, or a single `M @ Gq` where `Gq` is the metric-folded
  query).
- **Surface preserved:** `vault_recall` signature, return shape,
  ordering, and top-K semantics unchanged.
- **No new state:** no new index files, no new mutable cache, no
  background reproject.

### Stage 2 — Norm-bucketed exact pre-filter (gated on Stage 1
re-run)

Triggered only if Stage 1 leaves recall super-linear past
N ≈ 10⁵ on real-content vaults.  Pre-compute the L2 norm of every
stored versor; bucket by norm range.  For threshold `τ` and query
norm `q`, by Cauchy–Schwarz only versors with norm ≥ `τ / q` can
clear the cutoff — buckets below that line are *provably* below
threshold.  Within candidate buckets, the Stage 1 vectorised scan
runs.

- **Exactness:** no candidate that could beat the threshold is
  dropped.  The bound is tight; no tolerance window.
- **Determinism:** bucket assignment depends only on stored
  versor norm; replay is preserved.
- **State:** norm vector cached alongside the store, updated on
  every `vault.store()` call; checksum hashes the bytes written
  per CLAUDE.md.

### Stage 3 — Layered store with deterministic promotion (gated on
Stage 2 evidence)

Triggered only if working-set patterns produce a vault where most
recalls hit a small recent tail and most stored versors are
rarely-queried.  Two tiers: fast in-memory, slow exact scan.
Promotion is by deterministic rule (e.g. last-N stored, or
access-count derived from replay-visible counters), never
stochastic.

- **Exactness:** every query scans both tiers; the layer split
  changes *cost*, not *result*.
- **Replay:** promotion counters are part of replay state; same
  inputs ⇒ same layer assignment.

### Non-options

The following are explicitly excluded by this ADR and by
CLAUDE.md, and any future PR proposing them must first revisit
this ADR and CLAUDE.md:

- HNSW / NSW / annoy / FAISS-IVF / any nearest-neighbour
  approximation
- Cosine fallback or any non-CGA metric on the recall path
- Learned indexes, embeddings, or projections trained on vault
  contents
- Hot-path drift repair inside `vault.recall` (the bottleneck is
  per-iteration NumPy overhead, not numerical drift)

### Blade-signature index (deferred, not rejected)

The `long_context_cost` contract listed a blade-signature index
as an option.  It is deferred because (a) blade dominance under
Cl(4,1) sandwiches requires careful definition to stay exact, and
(b) norm-bucketing is simpler and likely sufficient.  If Stage 2
proves insufficient, a future ADR may revisit signature indexing.

## Consequences

- The Python fallback path becomes the vectorised path; the
  scalar Python loop remains only as a correctness reference in
  tests.
- `vault.store()` gains an O(1) per-call cost: append norm to a
  pre-allocated buffer.  No behavioural change in store API.
- The Rust backend port (next axis after Phase 4) inherits the
  vectorised contract.  Stage 2/3 indexes, if they land, port
  the same data structures.
- Replay determinism is preserved at every stage by construction.
  Tests in `tests/test_trace_hash.py` and the eval replay suite
  must continue to pass bit-for-bit after each stage.

## Evidence

- `evals/long_context_cost/contract.md` — what we measured.
- `evals/long_context_cost/results/v1_metrics.json` — the curve.
- `evals/long_context_cost/gaps.md` — diagnosis and
  recommendation tree.
- `algebra/backend.py::vault_recall` — the function being
  accelerated.

## Open questions

- Does `cga_inner` factor cleanly into a static metric matrix in
  the chosen embedding?  If yes, Stage 1 is `M @ Gq` with one
  precomputed Gq per query.  If not, Stage 1 is `np.einsum` over
  the multivector basis.  Either way: exact, deterministic,
  vectorised.
- What is the real-content vault size in the curriculum era?  If
  it caps at ~10⁵, Stages 2/3 may never trigger.
