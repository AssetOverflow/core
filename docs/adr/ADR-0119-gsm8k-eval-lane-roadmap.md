# ADR-0119 — GSM8K Eval Lane Roadmap (Phase 5)

**Status:** Proposed (roadmap-only)
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Type:** Umbrella ADR; decomposes Phase 5 of ADR-0114 into sub-phases
**Depends on:** ADR-0114, ADR-0114a, ADR-0115, ADR-0116, ADR-0117, ADR-0118

---

## Context

ADR-0114 §Phase 5 designated the GSM8K eval lane as Phase 5 of the
expert-capability arc, with a single line of scope:

> "Phase 5 — GSM8K Eval Lane (ADR-0119, future).
> Author evals/gsm8k/: dev / public / holdouts; runner.py;
> contract.md. Exit criterion: lane runner produces deterministic
> results. Honest first number reported."

In practice this is a multi-week chunk that integrates:

- the parser / solver / verifier / realizer pipeline that Phases 1–4
  shipped on main (ADR-0115/0116/0117/0118)
- the anti-overfitting obligations from ADR-0114a that are
  GSM8K-specific (#1 sealed-holdout enforcement, #6 depth-curve
  measurement, #7 frontier-baseline comparison, #8 adversarial
  generation)
- a CORE-original dev / public corpus (kept disjoint from actual
  GSM8K to preserve test-set integrity)
- the eventual sealed encryption of the real GSM8K test set as the
  holdout split

ADR-0119 is the **roadmap** that decomposes Phase 5 into sub-phases
the same way ADR-0114 decomposed Phases 1–7. This document does **not**
ship code. Each sub-phase ships under its own ADR and PR.

---

## Decision: Phase 5 decomposition

ADR-0119 is the umbrella. Seven sub-phases below; each carries its
own ADR id and discharge target. The sub-phases land in priority
order but most can run in parallel.

### Phase 5.1 — Sealed-holdout encryption for one lane (ADR-0119.1)

**Goal:** Convert one lane's holdout from the ADR-0105 dev-mode
plaintext fallback to a proper age-encrypted seal. Establishes the
key-management and runner-decryption pattern that the remaining lanes
will mirror.

**Lane choice:** `fabrication_control` (smallest plaintext file,
fewest dependencies).

**Discharges:** ADR-0114a Obligation #1 for this one lane.

**Acceptance:**
- `evals/fabrication_control/holdouts/v1/cases.jsonl.age` exists
- Plaintext fallback removed from the repo
- Age recipient public key documented in
  `docs/holdout_recipients.txt`
- Private identity path documented but NOT committed
- `holdout_runner._decrypt_holdout` reads the `.age` file when
  `CORE_HOLDOUT_KEY` is set; raises typed error otherwise
- Test `tests/test_adr_0119_1_sealed_holdout.py` pins:
  (a) `.age` file exists and is age-formatted
  (b) decryption with known identity reproduces plaintext byte-equal
  (c) missing `CORE_HOLDOUT_KEY` raises typed refusal

**Status:** Delegated (Gemini-style brief).

### Phase 5.2 — CORE-original GSM8K-style corpus (ADR-0119.2)

**Goal:** Author 200 grade-school math problems for the lane's
dev / public splits. **NOT drawn from actual GSM8K** — the real
GSM8K test set is reserved for the sealed holdout (Phase 5.7).
The dev / public splits are CORE-original work in the same style.

**Distribution:** 50 dev + 150 public, depths 1–8, every operation
kind exercised ≥ 30 times, 80+ multi-entity cases.

**Constraints:** Must stay within the parser grammar shipped by
ADR-0115. Every case must round-trip:
`parse_problem → solve → answer matches expected`. A `verify.py`
script enforces this gate; PR cannot land if any case fails.

**Discharges:** lane corpus prerequisite for 5.3 / 5.4 / 5.6.

**Acceptance:**
- `evals/gsm8k_math/dev/cases.jsonl` (50 cases)
- `evals/gsm8k_math/public/v1/cases.jsonl` (150 cases)
- `evals/gsm8k_math/holdouts/v1/cases.jsonl.age` (empty / placeholder
  pending Phase 5.7 GSM8K-test seal)
- `evals/gsm8k_math/README.md` + `contract.md`
- `evals/gsm8k_math/verify.py` → 200/200 OK

**Status:** Delegated (Codex-style brief).

### Phase 5.3 — Lane runner (ADR-0119.3)

**Goal:** Build `evals/gsm8k_math/runner.py` that drives every case
through:

```text
parse_problem(text) → graph
solve(graph)        → trace
verify(graph, trace) → verdict
realize(initial_state, trace) → prose
```

Per-case outcome is exactly one of:
- `correct` — verifier passes AND `trace.answer_value` equals the
  case's `expected_answer`
- `wrong`   — verifier passes AND `trace.answer_value` differs
  from the case's `expected_answer`
- `refused` — `ParseError` or `SolveError` (typed refusal at any
  stage)

**Critical: ADR-0114a Obligation #4 requires `wrong == 0`.** The
lane's pass threshold is `correct + refused == total` AND
`wrong == 0`. A nonzero `wrong` invalidates the lane regardless of
correct rate.

**Discharges:** lane runtime; the substrate every other Phase 5.X
gate consumes.

**Acceptance:**
- `evals/gsm8k_math/runner.py` exposes `run_lane(cases, *, config) → LaneReport`
- Each case in `LaneReport.case_details` carries the trace, the
  realized prose, and the outcome category
- Determinism: same case file → same `LaneReport.canonical_bytes()`
- `tests/test_adr_0119_3_runner.py` parametrizes over dev/public

### Phase 5.4 — Frontier-baseline comparison (ADR-0119.4)

**Goal:** Discharge ADR-0114a Obligation #7. Pair CORE's lane
score with frozen-citation frontier-LLM numbers on the same
problem distribution. Citation only — no live API. Pattern
mirrors ADR-0045 (long-context comparison).

**Acceptance:**
- `evals/gsm8k_math/baselines/frontier.json` carries:
  - per-vendor (Claude / GPT / Gemini) headline GSM8K scores with
    publication dates and URLs
  - note that vendor scores are on the *full GSM8K test*, not on
    our CORE-original public split (acknowledge the apples-vs-
    oranges; publish anyway)
- A comparison report (`evals/gsm8k_math/baselines/comparison_v1.json`)
  ties CORE's CORE-public-split score to the cited vendor scores
  with the disclaimer in place
- Test pins citation freshness (no broken URL, dated within last
  18 months)

**Discharges:** Obligation #7.

### Phase 5.5 — Adversarial generation (ADR-0119.5)

**Goal:** Discharge ADR-0114a Obligation #8. Generate problems
designed to exploit weak grammar / solver coverage. Misparse rate
**must be zero**; refused rate may be arbitrarily high.

**Approach:** Programmatic generator targeting:
- edge-case phrasings within the documented parser grammar
- combined patterns the parser supports separately but never
  jointly
- red-herring numbers (numbers in entity names like "Person 5";
  numbers in questions that don't ask about quantities)

Runs through the same `runner.py` from Phase 5.3 and reports the
correct / wrong / refused triple. **`wrong == 0` is the gate.**

**Acceptance:**
- `evals/gsm8k_math/adversarial/generator.py`
- `evals/gsm8k_math/adversarial/cases.jsonl` (≥ 100 cases)
- `tests/test_adr_0119_5_adversarial_misparse.py` asserts
  `wrong == 0` across all adversarial cases

**Discharges:** Obligation #8.

### Phase 5.6 — Depth-curve harness (ADR-0119.6)

**Goal:** Discharge ADR-0114a Obligation #6 measurement-side. Bucket
the lane's correct rate by reasoning depth (`len(graph.operations)`)
and emit the depth-vs-correct curve.

**Acceptance:**
- `evals/gsm8k_math/scoring/depth_curve.py` produces a JSON report:
  `{ "depth_1": 1.0, "depth_2": 1.0, ..., "depth_8": 0.97 }`
- A documented threshold `ε` (per-step error tolerance) below which
  accuracy at depth N must stay: `accuracy(N) ≥ (1 - ε)^N`. ADR-0120
  picks the production `ε` value when it sets the `expert`
  threshold; ADR-0119.6 ships the *harness*, not the threshold

**Discharges:** measurement-half of Obligation #6.

### Phase 5.7 — Sealed GSM8K test (ADR-0119.7)

**Goal:** Encrypt the real GSM8K test set as the holdout split.
Final piece before any `expert` promotion attempt under ADR-0120.

**Acceptance:**
- `evals/gsm8k_math/holdouts/v1/cases.jsonl.age` carries the real
  GSM8K test set, encrypted to the recipient established in 5.1
- A sanity check (developed against a tiny held-out subset of
  GSM8K *train*) confirms the runner reads the sealed file and
  produces a lane report
- Documentation explicitly states the seal is one-way: the
  development team operates blind to the test contents until a
  release event signed-by-reviewer opens the lane

**Discharges:** Obligation #1 for the lane that ultimately gates
ADR-0120.

### Phase 5.8 — Overall lane gate (ADR-0119.8)

**Goal:** Compose the per-sub-phase gates into a single lane
verdict. The lane "passes" when:

- 5.1 sealed holdout active for the lane
- 5.2 dev + public corpora populated AND `verify.py` 200/200
- 5.3 runner produces deterministic `LaneReport` across two runs
- 5.4 frontier comparison report exists and is dated
- 5.5 adversarial generator's `wrong == 0`
- 5.6 depth-curve report exists
- 5.7 sealed GSM8K test in place
- Public split: `correct + refused == total`, `wrong == 0`
- Holdout split: same shape, scored only at release events

A new lane shape `gsm8k_capability_shape` is registered in
`LANE_SHAPE_REGISTRY` with the above thresholds. ADR-0119.8 ships
the shape; ADR-0120 invokes it.

---

## ADR-0114a obligation roll-up after Phase 5

| # | Obligation | Discharge target | Status today |
|---|---|---|---|
| 1 | Sealed-holdout discipline | 5.1 (one lane) + 5.7 (GSM8K test) | substrate present; per-lane enforcement deferred |
| 2 | OOD surface variation | ADR-0118a | **discharged** |
| 3 | Replay-equal trace | ADR-0117 verifier | **discharged** |
| 4 | Typed refusal; `wrong == 0` | ADR-0116 + 5.3 + 5.5 | discharged at runtime layers; lane gate enforces |
| 5 | Reasoning-isolation perturbation suite | ADR-0125 | **discharged** |
| 6 | Compositional-depth curve | 5.6 (harness) + ADR-0120 (threshold) | **harness pending**; threshold lives in ADR-0120 |
| 7 | Frontier-baseline comparison | 5.4 | pending |
| 8 | Adversarial generation; `wrong == 0` | 5.5 | pending |
| 9 | Determinism | solver + verifier + realizer | **discharged** |
| 10 | Operation provenance via pack | ADR-0116 | **discharged** |

Six of ten obligations land before Phase 5 starts. The remaining
four cluster under ADR-0119.

---

## Invariants

### `adr_0119_decomposes_phase_5`

Phase 5 ships as eight sub-ADRs (5.1 through 5.8). Adding,
removing, or reordering sub-phases requires a numbered amendment
to this ADR.

### `adr_0119_no_actual_gsm8k_in_dev_public`

The dev and public splits of `evals/gsm8k_math/` are CORE-original
work. The actual GSM8K test set enters the lane ONLY via the
encrypted holdout under 5.7. A pre-PR check in 5.2's `verify.py`
flags any case whose `problem` text matches a known GSM8K entry
(via fingerprint comparison against a hashed manifest of GSM8K
prompts; the manifest itself does not contain the GSM8K texts
verbatim).

### `adr_0119_wrong_count_is_load_bearing`

For any sub-phase that runs cases through the runner (5.3, 5.5),
the lane's per-split `wrong` count must be reported with the same
prominence as `correct`. ADR-0114a Obligation #4 requires
`wrong == 0`; a sub-phase with `wrong > 0` invalidates that sub-
phase regardless of `correct` rate.

---

## Acceptance evidence (for this roadmap ADR)

ADR-0119 is accepted when:

- The ADR file exists in `docs/decisions/` and is linked from
  `docs/decisions/README.md` (index + frontier)
- No code lands with this ADR; it's pure roadmap
- README cross-references update to mention Phase 5 sub-phasing

Each sub-phase is accepted independently under its own ADR.

---

## Consequences

- The Phase 5 work now has explicit decomposition. Each sub-phase
  has clear scope, clear acceptance, clear obligation-discharge
  target.
- Parallel work is enabled: 5.1 (Gemini), 5.2 (Codex), 5.3 (me)
  can run concurrently without conflict.
- ADR-0120 (first `expert` promotion contract) cannot land until
  all sub-phases of 5.1 through 5.8 have landed. The roadmap makes
  that dependency explicit.
- ADR-0114a Obligation #6's threshold (`ε`) lives in ADR-0120, not
  here. ADR-0119.6 ships the measurement harness only.

---

## Out of scope

- Specific numeric thresholds for the `gsm8k_capability_shape`
  lane gate. Those belong to ADR-0120.
- A second capability domain after GSM8K. ADR-0114 §Phase 7
  proposes symbolic logic; that's ADR-0121+.
- Multi-vendor adversarial cross-runs (CORE adversarial cases ⊗
  frontier LLMs). Out of scope for Phase 5 first cut; potential
  Phase 5.X future amendment.
- Renaming `evals/gsm8k_math/` to something else if the corpus
  expands beyond grade-school math. Future amendment.
