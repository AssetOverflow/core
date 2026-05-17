# Phase 5 — Stratified Mechanism-Isolation Findings (ADR-0024 / ADR-0026 / ADR-0025)

**Date:** 2026-05-17
**Corpus:** `evals/forward_semantic_control/public/v2_phase5/cases.jsonl` (20 cases)
**Runner:** `evals/forward_semantic_control/phase5_runner.py`
**Report:** `evals/forward_semantic_control/results/phase5_report.json`
**Contract tests:** `tests/test_phase5_corpus.py` (20 passing)

## Why Phase 5

Phase 3 produced a single mechanism-isolation pass rate over 5 v2
cases.  That is a binary signal: it cannot tell us *which kind* of
failure-mode the mechanism handles cleanly versus where the gate
behaves accidentally.  Phase 5 stratifies the corpus across five
geometric failure families so each lane reports its own pass rate,
refusal rate, and rejection-traced rate.

The stratification also de-risks ADR-0026's δ = 0.4 choice: if a
family surfaces blade-gaps below 0.4 that *should* admit, the corpus
will show a margin-mode refusal in that family, and we report the
architectural finding rather than patching δ per family.

## Families

| Family | Geometric construction | Threshold-mode expectation | Margin-mode expectation |
|---|---|---|---|
| **A. near_forbidden_correct_endpoint** | expected blade-score > forbidden by a small margin (0.002 to 0.55) | admit expected | admit if gap ≥ δ=0.4, else refuse |
| **B. near_equal_admissible** | two admissible candidates within ≤ 0.01 blade-score | admit either (tie-break stable) | refuse (diff < δ) |
| **C. no_admissible_path** | both candidates score ≤ 0 against blade | honest refusal (INNER_LOOP_EXHAUSTION) | honest refusal (INNER_LOOP_EXHAUSTION) |
| **D. multi_step_admissibility** | chain of two Family-A configurations | each step admits expected | margin-mode handles each step on its own δ test |
| **E. heterogeneous_relation** | chain with *different blades* at each step | each step admits under its own blade | each step admits under its own blade |

## Headline numbers

| metric | threshold mode | margin mode (δ=0.4) |
|---|---|---|
| overall pass_rate (20 cases) | **1.00** | **1.00** |
| mechanism_isolated | true | true |

Per-family pass_rate is 1.00 for both modes across all five families.

## Mechanism-evidence detail (Family A)

Within Family A (6 cases) we additionally surface two diagnostic rates:

| diagnostic | rate |
|---|---|
| `rejection_traced_rate_threshold` | 0.50 |
| `boundary_overridden_rate_threshold` | 0.50 |

Reading: in three of six near-forbidden cases the boundary already
prefers the expected token (so the inner-loop never *had* to reject
the forbidden — selection just succeeded).  In the other three, the
boundary picks the forbidden, the inner-loop *does* reject it, and
the rejection is visible in the trace.  Both halves are honest:
ADR-0024 does not promise rejection in every Family-A case; it
promises that *when* boundary diverges from blade-aligned ranking,
the inner-loop overrides it with rejection visible in the trace.

This is the kind of granular evidence that Phase 3's single
mechanism-isolation flag cannot surface.

## Family C — refusal contract

All three Family C cases refuse in both modes with
`RefusalReason.INNER_LOOP_EXHAUSTION`.  This is the load-bearing
evidence for ADR-0024 Phase 2's typed-refusal pipeline: when the
admissibility region contains no positive-scoring candidate, the
honest path is exhaustion, not silent boundary fallback.

## Family B — margin gate is doing real work

All five Family B cases admit under threshold mode and refuse under
margin mode.  Without ADR-0026 (margin), the corpus would silently
accept a near-tie selection; with it, the runtime surfaces the
ambiguity via honest refusal instead of an arbitrary tie-break.

## δ=0.4 falsifiability check

δ=0.4 was chosen in ADR-0026 from the minimum Phase 3 v2 margin
(0.456).  Phase 5 adds 15 single-step cases plus 5 chain cases
covering blade-gaps from 0.002 to 0.55.  No case surfaces a blade-gap
below δ that *should* admit (i.e., the corpus does not falsify the
δ choice).  Cases A-001 to A-004 have gaps below δ and they all
refuse under margin mode — which is the *intended* behavior under
ADR-0026, not a counterexample.

If a future PR adds a case with blade-gap < 0.4 where margin-mode
refusal is the *wrong* behavior, that finding must be reported in
this document as a δ-falsification rather than patched per-case.

## Replay determinism

`tests/test_phase5_corpus.py::TestReplayDeterminism::test_margin_mode_three_run_byte_identity`
runs the lane three times and asserts per-case selection identity
across all three runs.  All 20 cases pass — Phase 5 preserves the
ADR-0024 deterministic-replay invariant under both threshold and
margin modes, single-step and chained.

## Benign inner-loop corpus (EXHAUSTION_CEILING lane)

`evals/forward_semantic_control/public/inner_loop_benign/cases.jsonl`
(10 cases) is the benign single-step corpus the
`EXHAUSTION_CEILING = 0.05` gate in `inner_loop_runner.py` was
designed against.  Result on this corpus
(`results/phase5_benign_inner_loop_report.json`):

| condition | exhaustion_rate | pass_rate | gate |
|---|---|---|---|
| boundary_only | 0.0000 | 1.00 | OK |
| null_control | 0.0000 | 1.00 | OK |
| inner_loop_t0 | 0.0000 | 1.00 | OK |
| inner_loop_tpos (t=0.25) | 0.0000 | 1.00 | OK |

### Geometric finding surfaced while authoring this corpus

Cl(4,1) is Lorentzian — 23 of 85 pack tokens have **negative** self
`cga_inner` (most negative: `mean = -2.01`, `verify = -1.33`,
`context = -1.15`, `corrects = -0.74`).  This means a single-token
admissibility region with `chain_tokens = [tok]` can geometrically
forbid its own answer: if `cga_inner(versor(tok), versor(tok)) < 0`,
threshold-mode inner-loop refuses even with `threshold = 0`.

The Phase 5 benign corpus draws its 10 expected endpoints from the
62-token subset with `self-cga_inner > 0.25`.  Tokens like
`correction`, `verify`, `context`, `mean`, etc. cannot serve as
single-token expected endpoints under static thresholding — they
need either a different region shape (multi-token chain whose outer
product realigns the blade) or the ADR-0026 ranked-with-margin
mode, where the ranking metric is robust to per-token sign quirks.

This finding is consistent with the Phase 4 characterization result
that no static threshold delivers `separation_quality ≥ 0.8` across
v1+v2 — the algebra's signature itself resists static thresholds in
the general case.  The δ=0.4 margin lane survives because margin
compares score *differences*, not absolute scores.

## What this does *not* prove

* Rotor-side admissibility (ADR-0025) is exercised in `tests/test_rotor_admissibility.py`
  but Phase 5's region construction does not set `frame_versor`, so
  this corpus does not exercise the rotor-admissibility gate.  A
  future Phase 5.1 may add a sixth family for frame-cone refusals.
* The benign corpus is intentionally narrow (single-token regions
  drawn from positive-self-score tokens).  Broader benign corpora
  with multi-token outer-product blades remain an open question —
  Phase 5 does not claim that static thresholds work *generically*,
  only that they work on this curated corpus and that the margin
  lane works *generically* on the stratified corpus above.

## Files touched

* `evals/forward_semantic_control/public/v2_phase5/cases.jsonl` — 20 stratified cases
* `evals/forward_semantic_control/phase5_runner.py` — new lane runner
* `evals/forward_semantic_control/phase5_mine.py` — corpus-mining helper (offline; not run by suites)
* `evals/forward_semantic_control/results/phase5_report.json` — full per-case report
* `tests/test_phase5_corpus.py` — 20 contract tests
* `docs/evals/phase5_stratified_findings.md` — this note
