# Phase 6 — Comparative Demo: CORE vs In-System Baseline

**Date:** 2026-05-17
**Corpus:** `evals/forward_semantic_control/public/v2_phase6_demo/cases.jsonl` (8 cases)
**Runner:** `evals/forward_semantic_control/phase6_demo.py`
**Report:** `evals/forward_semantic_control/results/phase6_demo_report.json`
**Contract tests:** `tests/test_phase6_demo.py` (17 passing)

## What this demo shows

Three head-to-head conditions where adding the Phase 2-5 mechanisms
(inner-loop admissibility, margin gate, typed refusals) produces
behavior that the in-system baseline (boundary-only, ADR-0023) cannot
produce.  The "baseline" is **the same CORE codebase** with
`inner_loop_admissibility=False` — a true ablation, not a comparison
to a transformer LLM or any external system.

## Why the baseline is in-system

A transformer-LLM comparison would be:

1. Non-deterministic — directly violating CLAUDE.md's anti-stochastic
   stance.
2. Unable to be CI-enforced — every run would produce different
   outputs.
3. An apples-to-oranges comparison — the LLM has access to its
   training corpus; CORE has access only to the curated pack.

The in-system ablation is the honest comparison because it isolates
*the contribution of the mechanism itself*, not the corpus, prompt,
or sampling differences.

## Headline

| metric | value |
|---|---|
| `all_three_conditions_pass` | **true** |
| C1 replay determinism (baseline) | **8/8** stable across 5 reruns |
| C1 replay determinism (CORE) | **8/8** stable across 5 reruns |
| C2 baseline emits forbidden | **3/3** |
| C2 baseline admits forbidden | **0/3** (inadmissibility is visible but ignored) |
| C2 CORE corrects-or-refuses | **3/3** |
| C2 CORE rejection in trace | **3/3** |
| C3 baseline typed refusals | **0/3** |
| C3 baseline emitted inadmissible | **3/3** |
| C3 CORE typed refusals | **3/3** with `RefusalReason.INNER_LOOP_EXHAUSTION` |

## Condition 1 — Replay determinism

Both baseline and CORE produce byte-identical
`hash_admissibility_trace(...)` outputs across 5 reruns on the same
case.  This is *preserved*, not added, by Phase 2-5.

**What CORE adds on top:** the trace now also folds
`refusal_reason` into its payload when present (ADR-0024 Phase 2),
so a refusal event itself is replayable evidence, not just an
exception type at runtime.

This is the load-bearing precondition for everything that follows:
without determinism, "the rejection appeared in the trace" is not a
verifiable claim, just a probabilistic one.

## Condition 2 — Traced rejection

On three adversarial cases the boundary geometrically picks the
forbidden token (`meaning` / `reason` / `question`).  Both legs see
the same field state, same vocabulary, same persona.

**Baseline behavior (ADR-0023):** boundary picks the forbidden
token.  The admissibility verdict for that selection is
`admitted = False` — *the inadmissibility is visible in the trace*
but the walk emits the forbidden anyway.  This is the "silent
emit" failure mode: the rejection is observable but not actionable.

**CORE behavior (ADR-0024 + ADR-0026):** inner-loop overrides
boundary, selects the blade-aligned expected token (or refuses on
sub-δ margin), and the forbidden token appears in
`rejected_attempts`.  The rejection is now *causally responsible*
for the selection difference between baseline and CORE — not just
observable.

This is the falsifiable mechanism-isolation claim of ADR-0024.

## Condition 3 — Coherent refusal

On three no-admissible-path cases (all candidates score negative
under the chosen blade), the two configurations produce qualitatively
different outputs:

**Baseline:** never raises a typed refusal.  Emits an inadmissible
candidate (`admitted = False`) or fails with an untyped `ValueError`.
The refusal — if it happens — carries no `RefusalReason` and no
`rejected_attempts` evidence.

**CORE:** raises `InnerLoopExhaustion` with
`reason = RefusalReason.INNER_LOOP_EXHAUSTION`, carrying the full
`rejected_attempts` list.  The refusal is:

* **Typed** — callers can pattern-match on `RefusalReason`.
* **Replayable** — the reason is folded into the trace hash.
* **Evidenced** — `rejected_attempts` shows *which* candidates were
  considered and what scores they received.

This is the "honest refusal" architectural commitment of CLAUDE.md
made concrete and CI-enforced.

## Three-condition compositionality

C1 + C2 + C3 together are the load-bearing claim: CORE is

1. deterministic (C1)
2. self-aware of bad selections (C2)
3. capable of refusing rather than emitting bad selections (C3)

Without C1, the other two are anecdotes.  Without C2, C3 is
unfalsifiable (every refusal could be a hidden bug).  Without C3,
C2's "rejection in trace" can still be ignored by the walk.

This is what distinguishes CORE from a wrapped LLM at the
mechanism level.

## Threats to validity (what this does NOT claim)

* **Not LLM benchmarking.**  This demo does not compare CORE against
  a transformer model on any natural-language benchmark.  Doing so
  would require accepting non-determinism and is out of scope.
* **Not a generality claim.**  The corpus is 8 hand-curated cases
  from the cognition pack, geometrically constructed to exercise
  each condition.  A larger natural corpus is exercised in Phase 5;
  the Phase 6 corpus is intentionally focused for narrative clarity.
* **Not a performance claim.**  CORE's inner-loop adds latency over
  boundary-only (see Phase 2 corpus report).  Phase 6 demonstrates
  *capability* gain, not *throughput* parity.
* **Not a soundness proof.**  C1's "byte-identical across 5 reruns"
  is empirical determinism, not formal.  Formal replay determinism
  is the responsibility of the `trace_hash` contract in
  `core/cognition/trace.py` and is exercised elsewhere.

## What this enables next

* A future "honest refusal in chat" PR can plumb
  `InnerLoopExhaustion.reason` into `ChatResponse.refusal_reason` and
  Phase 6's C3 contract will already enforce that the typed reason
  is preserved end-to-end.
* A future replay-debug UI can render `rejected_attempts` per step,
  and Phase 6's C2 contract guarantees that the data is there to
  render.
* Phase 5's δ=0.4 falsifiability gate composes with C2 here: any
  new corpus case that surfaces a margin below δ where margin-mode
  refusal is *wrong* would simultaneously fail C2's
  `core_corrects_or_refuses` predicate, surfacing the architectural
  finding rather than silently being patched.

## Files

* `evals/forward_semantic_control/public/v2_phase6_demo/cases.jsonl` — 8 demo cases
* `evals/forward_semantic_control/phase6_demo.py` — comparative runner
* `evals/forward_semantic_control/results/phase6_demo_report.json` — full per-case report
* `tests/test_phase6_demo.py` — 17 contract tests (C1: 4, C2: 6, C3: 6, headline: 1)
* `docs/evals/phase6_comparative_demo.md` — this note

## Six-phase ADR-0024 chain — closing summary

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Pack-grounded fixture rewrite + architectural finding | ✅ `3940290` |
| 2 | Typed refusals + trace fold + `RefusalReason` enum | ✅ `310793a` |
| 3 | ADR-0026 ranked-with-margin (δ=0.4) | ✅ `639e107` |
| 4 | ADR-0025 rotor / frame admissibility (sibling module) | ✅ `542e13d` |
| 5 | Stratified 5-family mechanism-isolation corpus + benign EXHAUSTION_CEILING corpus | ✅ `b664984` |
| 6 | Three-condition head-to-head demo (replay / traced rejection / coherent refusal) | ✅ this commit |

Total: 8 commits, ~58 contract tests added, 3 ADRs (0024 / 0025 / 0026)
moved to Accepted with implementation + characterization evidence.
