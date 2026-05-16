# long-context-cost — v1 gaps

## v1 evidence (synthetic vault, float32 (32,) versors)

Two runs were taken: the **pre-vectorisation** measurement that
diagnosed the bottleneck, and the **post-vectorisation** measurement
after ADR-0019 Stage 1 shipped in the same session.  Authoritative
machine-readable curve: `evals/long_context_cost/results/v1_metrics.json`.

| N        | pre-vec median | post-vec median (ADR-0019 S1) | speedup |
| -------- | --------------:| -----------------------------:| -------:|
| 1,000    | 874.774 ms     | 0.217 ms                      | ~4,030x |
| 10,000   | 8,727.420 ms   | 1.701 ms                      | ~5,130x |
| 100,000  | (extrapolated ≈ 87 s) | 20.795 ms              | ~4,200x |

The N=100,000 pre-vectorisation point was not measured to
completion — the N=1k and N=10k slope was 1.00 and wall-clock
for the third case projected to ~29 minutes, so the run was
stopped in favour of shipping Stage 1.  Stage 1 then completed
all three Ns in 0.71 s total wall time.

## Asymptotic class

Post-vectorisation log-log slope is **0.99** (`asymptotic_class =
"linear"`).  The cost shape is the expected O(N) exact scan, with
the constant factor now bounded by NumPy vector throughput rather
than Python interpreter dispatch.  At N=100,000, per-turn recall
pays ~21 ms, which is well within a runtime turn budget.

The Stage 1 change is **bit-identical** to the prior scalar
scoring path — see `tests/test_vault_recall_vectorised.py`, which
pins per-versor score equality and top-k ordering (including
ascending-index tie-break) against the per-element `cga_inner`
loop on multiple seeds.

## Root cause (pre-vectorisation)

`vault_recall` in the Python fallback iterated per-versor and
invoked `cga_inner(q, np.asarray(v))` inside the loop.  Each call
went through `geometric_product` twice with nested Python `for`
loops over 32×32 basis pairs, then `scalar_part`, then a Python
list `append`.  Per-iteration NumPy and Python dispatch dominated
the arithmetic by 3–4 orders of magnitude for 32-element vectors.

The fix exploited a structural property of Cl(4,1): the CGA inner
product is exactly diagonal with metric values ±1 (verified
empirically — zero off-diagonal contribution).  That gives:

```text
cga_inner(X, Y) = sum_i metric[i] * X[i] * Y[i]
```

which vectorises across N versors as a single C-speed scan,
while preserving per-versor serial component reduction order so
that scores are bit-for-bit identical to the scalar path.

## Recommendation — three layers, all exact

CLAUDE.md forbids approximate recall on the runtime path.  All three
proposals below preserve exact CGA inner-product semantics; the only
change is *how the scan is organised*.

1. **Vectorised inner-product scan (no index)** — *near-term win.*
   Replace the Python loop with a single matrix-vector product on
   the stacked versor matrix `M ∈ ℝ^{N×32}` (CGA inner product is
   bilinear, so it factors into a metric matrix multiplied once
   and reused).  Expected: 100× to 1,000× speed-up at every N
   tested, with bit-identical results.  No data-structure change;
   no index; no semantics change.  This is the right first step
   because it dissolves the artefact without committing the codebase
   to an index design.

2. **Norm-bucketed pre-filter** — *first exact index.*  After (1),
   if N grows past ~10⁶, pre-compute the L2 norm of every stored
   versor and bucket by norm range.  For a query of norm `q`, an
   inner-product threshold `τ` admits only versors whose norm lies
   in `[τ / q, ∞)` (Cauchy–Schwarz).  Buckets outside that range
   are *provably* below threshold — exact, not approximate.
   Within candidate buckets, the vectorised scan from (1) runs.

3. **Layered store with deterministic promotion** — *operational
   tier, not a search structure.*  Recently-stored versors in a
   small fast tier; older versors in a larger exact-scan tier.
   Promotion rules are deterministic by access pattern, so replay
   is preserved.  Useful once vault size dwarfs working-set; not
   yet load-bearing.

A **blade-signature index** was on the table in the contract but
is deferred: blade dominance under Cl(4,1) sandwiches is
non-trivial, and norm-bucketing already provides an exact and
much simpler pre-filter.

## Sequencing

- **Done (this session):** Stage 1 shipped.  `algebra/backend.py`
  now holds the vectorised exact path; `tests/test_vault_recall_vectorised.py`
  pins bit-identity and tie-break ordering.  Lane re-run produced
  slope 0.99, all Ns under 25 ms.
- **Not yet triggered:** Stage 2 (norm-bucketed pre-filter) and
  Stage 3 (layered store with promotion).  Both gated on real-
  content vault sizes exceeding ~10⁶ entries with measurable
  super-linearity, or on a Stage 1 re-run that regresses.  See
  ADR-0019 for trigger conditions.
- **Next axis:** Rust backend parity port of `vault_recall` is
  the natural next acceleration, since the vectorised contract
  is now stable and tested.  Per CLAUDE.md sequencing rule 5,
  Rust parity comes after Python semantics are locked by tests
  — that lock is now in place for this surface.

## Non-options (CLAUDE.md violations)

- HNSW, ANN, cosine fallback, embedding projection, learned index.
  All forbidden on the runtime path.  This lane is **not** an
  invitation to relax that.
- Drift-repair, watchdog, or hot-path normalizer inside
  `vault.recall`.  The bottleneck is per-iteration NumPy overhead,
  not numerical drift.

## What v2 needs

- Multi-run sampling at each N (current curve is single-run; p95
  is intra-run only).
- A real-content variant: synthetic versors are uniform-random;
  produced-by-pack versors have norm and grade distributions that
  may matter for bucket selectivity.
- A fill-cost curve as a separate sub-lane (currently mingled).
