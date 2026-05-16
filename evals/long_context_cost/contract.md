# long-context-cost eval lane

## What it measures

Per-turn recall latency as a function of vault size.  The roadmap
flags this as the test of whether `vault/store.py` is sufficient at
scale: if recall is super-linear in N (the number of stored
entries), an indexing strategy is required.  Per CLAUDE.md, the
strategy must be **exact** — B-tree / suffix array / signature-
based bucketing — not approximate recall (HNSW / ANN are forbidden
on the runtime path).

## Setup

For each vault size N in {10³, 10⁴, 10⁵, 10⁶}:

1. Populate a fresh `VaultStore` with N synthetic versors of shape
   (32,) float32.  Reprojection is disabled during fill so the
   benchmark measures recall cost, not fill cost.
2. Run K independent recall queries against the populated vault.
   Each query is a fresh random versor; the timing budget excludes
   query generation.
3. Record per-query latency.

Per N the lane reports:
- `latency_median_ms`
- `latency_p95_ms`
- `latency_max_ms`
- `latency_mean_ms`

Aggregate analysis:
- log-log linear fit over (N, median latency).  Slope ≈ 1 indicates
  linear cost (the expected baseline for exact O(N) scan); slope
  > 1 indicates super-linear behaviour that requires intervention.
- `asymptotic_class` — `"linear"` if slope ∈ [0.85, 1.15], else
  the inferred class label.

## Phase 4 discipline

This is a quantitative-curve lane.  No pass/fail threshold beyond
the structural gates:

- Every recall must return without exception.
- Recall must not silently degrade (no zero-result returns at scale
  when the same query at smaller N produced results).

Curve interpretation is left to the reader.  The lane's job is to
publish the curve and recommend an indexing strategy if super-
linear scaling is detected.

## Indexing strategy decision

Per CLAUDE.md ("Vault recall is exact and deterministic.  Do not
add cosine similarity, HNSW, ANN indexes, or approximate recall to
the runtime path"), any indexing introduced must be an exact
acceleration.  Options on the table if the curve calls for it:

- **Norm-bucketed pre-filter.**  Pre-compute the L2 norm of each
  stored versor; for a query of norm q, only scan buckets whose
  norm lies in [q - δ, q + δ] for a bound δ derived from the
  inner-product threshold.  Exact: no candidate is dropped that
  could possibly beat the cutoff.
- **Blade-signature index.**  Group versors by which grade-1
  blades dominate; query searches the K buckets whose signature
  overlaps the query's.  Exact: full scan within the candidate
  set.
- **Layered store with promotion.**  Recently-stored versors live
  in a fast in-memory tier; older versors in a slower exact-scan
  tier.  Promotion is deterministic by access pattern.

v1 reports the measurement and recommends one of these (or "linear
scan is acceptable") with evidence.

## Anti-overfitting

- Synthetic versors are generated from a fixed seed for
  reproducibility.
- The same query distribution is used across all N (queries are
  not tailored to vault contents).
- K queries are sampled IID; we report variability via p95 and
  max, not just mean.

## Replay determinism

Latency itself is hardware- and load-dependent and is not
reproducible bit-for-bit.  What is reproducible is the **shape**
of the curve and the **asymptotic class**.  The lane reports the
curve from a single run; multi-run statistical analysis is v2
work.

## What this lane does NOT measure

- Fill cost (storing N entries) — separate concern, separately
  bounded by reproject interval policy.
- Memory footprint at N=10⁶ — separate concern.
- Recall quality on realistic vault contents (covered indirectly
  by every other lane that exercises real cognition pack content).

The lane is narrow: recall latency as a function of vault size.
