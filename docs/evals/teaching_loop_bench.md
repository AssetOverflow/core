# Teaching-Loop Determinism Benchmark

**Date:** 2026-05-18
**Runner:** `benchmarks/teaching_loop.py`
**CLI:** `core bench --suite teaching-loop [--runs N] [--json]`
**Contract tests:** `tests/test_teaching_loop_bench.py` (5 passing)
**Reference ADRs:** [0055](../decisions/ADR-0055-inter-session-memory-discovery-promotion.md), [0057](../decisions/ADR-0057-teaching-chain-proposal-review.md), [0045](../decisions/ADR-0045-long-context-recall-vs-transformer-baselines.md)

![teaching-loop benchmark](assets/teaching_loop_bench.gif)

## Headline claim

> For an identical candidate, N runs of the full reviewed-corpus
> extension pipeline (`propose_from_candidate` → real
> `run_replay_equivalence` → `accept_proposal`) produce N
> **byte-identical** artifacts at every observable point.
>
> The active teaching corpus on disk is byte-identical pre/post,
> regardless of N.

This is the determinism guarantee for the *learning loop itself* —
the analog of [ADR-0045's 100% exact-NIAH recall](../decisions/ADR-0045-long-context-recall-vs-transformer-baselines.md)
result, applied to the learning path rather than only to retrieval.

## What's asserted byte-identical

| Artifact | How it's derived | Why this matters |
|---|---|---|
| `proposal_id` | SHA-256 prefix of canonical-JSON `(source_candidate_id, proposed_chain)` | If hashing of inputs ever drifts (locale, dict-ordering, float formatting), this changes. |
| `replay_baseline` | Cognition lane metrics on the active corpus | If any cognition-lane component became non-deterministic, this varies across runs. |
| `replay_candidate` | Cognition lane metrics on transient-with-append corpus | Same as above, run against a different corpus state. |
| `regressed_metrics` | Sorted tuple of strict-decrease metric names | A 1-element drift would expose comparison non-determinism. |
| `chain_id_written` | Canonical `<intent>_<subject>_<connective>_<object>` | Append-side identifier derivation. |

If determinism breaks anywhere in the pipeline — proposal hashing, the
replay-equivalence gate, accept-side corpus-append, or `ProposalLog`
replay — at least one of the `unique_*` counts exceeds 1 and the bench
fails.

## 100-run reference result (today's main)

```text
unique(proposal_id) = 1     unique(chain_id) = 1
unique(baseline)    = 1     unique(candidate) = 1
unique(regressed_metrics) = 1
active_corpus_byte_eq = True

Latency per iteration:
  mean = 1.849s    p50 = 1.838s    p95 = 1.851s    total = ~185s
```

The p95 sits within 1% of the p50 — the loop's per-iteration cost is
dominated by the two cognition-lane runs inside the replay gate, both
of which are themselves deterministic in time as well as output.

## Sample 10-run output

```text
================================================================================
  Teaching-Loop Determinism Benchmark (ADR-0055..0057)
================================================================================
...
  [PASS] teaching_loop_determinism        1.0000 byte_identity_ratio
         10 runs; unique(proposal_id)=1, unique(baseline)=1,
         unique(candidate)=1, unique(chain_id)=1;
         mean=1.948s p50=1.846s p95=2.406s; active_corpus_byte_eq=True

ALL PASSED
```

(p95 in any single 10-run sample is noisier than the 100-run number — a
single warm-cache vs cold-cache iteration can move it ~30%. The 100-run
distribution is the canonical reference.)

## Trust boundary

Every write is confined to a tempdir created inside the bench loop:

```python
for _ in range(runs):
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "proposals.jsonl"
        transient = Path(tmpdir) / "cognition_chains_v1.jsonl"
        shutil.copyfile(active_path, transient)
        ...
```

The active corpus is read at the start and at the end. Any byte
difference would fail the bench. Re-pinned by
`test_teaching_loop_is_deterministic_across_three_runs` in
`tests/test_teaching_loop_bench.py`.

## How to reproduce

```bash
core bench --suite teaching-loop --runs 100        # canonical reference run
core bench --suite teaching-loop --runs 10         # quick smoke (~20s)
core bench --suite teaching-loop --runs 100 --json # machine-readable

python -m pytest tests/test_teaching_loop_bench.py -q  # ~25s
```

## Falsifiable claims

If any of these stops holding, the headline claim no longer holds:

- `report.deterministic` is `True` (all five `unique_*` counts are 1).
- `report.active_corpus_byte_identical` is `True`.
- `report.sample_proposal_id` is 32 lowercase hex chars (SHA-256 prefix).
- `report.sample_chain_id == "cause_thought_reveals_meaning"`.
- `report.elapsed_p95_s >= report.elapsed_p50_s`.
- `report.elapsed_total_s >= mean × runs × 0.9` (sanity check on wall-time accounting).

The contract test file pins all of these at low N for fast CI; the
100-run reference number is informational, not gated.

## Why this pairs with ADR-0045

[ADR-0045](../decisions/ADR-0045-long-context-recall-vs-transformer-baselines.md) showed
CORE achieves **100% exact recall** at N ∈ {100, 1k, 10k, 100k} in a
needle-in-a-haystack scan — the *retrieval* path is bit-exact.

This benchmark shows the **learning path** is also bit-exact: the same
candidate, run N times, produces the same accepted chain. Together
they form the two halves of the deterministic-cognition claim:

- **Read path** (ADR-0045): exact, scale-invariant, no approximation.
- **Write path** (this bench): exact, replayable, no non-determinism.

No LLM-based system has published equivalent numbers on either path,
let alone both.

## Related

- Anti-regression demo: [`anti_regression_demo.md`](anti_regression_demo.md) — what the gate does when a regression *is* detected.
- Learning-loop demo: [`learning_loop_demo.md`](learning_loop_demo.md) — the same pipeline as a narrative walkthrough.
- Long-context comparison: [ADR-0045 / `long-context-comparison`](../decisions/ADR-0045-long-context-recall-vs-transformer-baselines.md) — the sibling determinism number for the *read* path.
