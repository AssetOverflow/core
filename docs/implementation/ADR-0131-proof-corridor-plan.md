# ADR-0131 Proof Corridor Hardening Plan

**Status:** Coordination / implementation plan  
**Date:** 2026-05-23  
**Branch:** `docs/adr-0131-proof-corridor-hardening`  
**Scope:** Docs-only guardrail for the post-GSM8K pivot.

---

## Executive verdict

The ADR-0122 through ADR-0128 math arc produced a useful and honest result:

```text
GSM8K-style coverage: 0 correct / 0 wrong / all refused
```

That result should not be treated as a failure of the project doctrine. It is evidence that the current deterministic math substrate is preserving the most important invariant (`wrong == 0`) while refusing problems whose natural-language shape exceeds the parser grammar contract.

The pivot in ADR-0131 is therefore directionally correct: stop optimizing the `mathematics_logic` expert gate around raw GSM8K coverage and retarget it to a composite proof corridor that measures CORE's actual strengths:

1. deterministic symbolic exactness,
2. internal consistency with ratified teaching substrate,
3. bounded natural-language grammar competence,
4. refusal-first behavior on out-of-contract inputs,
5. sealed-eval discipline and byte-equal replay.

The danger now is over-reading the first symbolic-equivalence v1 lane. A narrow 30-case, single-variable, integer-polynomial normalizer result is useful as a substrate bootstrap. It is not, by itself, expert proof.

---

## Claim boundaries

### Proven enough to rely on

- The GSM8K parser-expansion path is a poor promotion gate for the current architecture.
- `wrong == 0` remains the correct hard invariant.
- Candidate-graph parsing plus verifier filtering is the right topology for bounded grammar work.
- ADR-0131's three-benchmark composite pattern is the right replacement shape.

### Not yet proven

- General mathematical reasoning.
- GSM8K competence.
- Broad natural-language word-problem competence.
- `mathematics_logic` expert promotion.
- That symbolic-equivalence v1 is powered by the full CORE runtime rather than a deterministic adjacent normalizer.
- That learning / teaching-corpus growth scales without corrupting invariants.

### Language to avoid until the composite gate passes

Do not describe ADR-0131.1 v1 as:

- "math expert proof",
- "CORE solves algebra",
- "expert promotion achieved",
- "GSM8K replacement completed",
- "general math reasoning",
- "model-level proof" unless the runtime integration and replay artifact demonstrate that boundary.

Preferred language:

> "ADR-0131.1 establishes the first symbolic-equivalence substrate and lane scaffold. It is one component of the larger composite expert-promotion corridor."

---

## The proof corridor

ADR-0131 should mature into a single executable corridor:

```text
symbolic exactness
  + CORE-native teaching consistency
  + bounded-grammar word problems
  + adversarial refusal probes
  + sealed holdouts
  + byte-equal replay
  + expert-claim artifact
```

A pass on any one lane is insufficient. A pass on all three lanes, with `wrong == 0` and sealed/replay evidence, is the meaningful claim.

---

## Phase plan

### Phase 0131.1.B — Harden symbolic equivalence

Purpose: turn the current v1 substrate into the real Benchmark 1 described by ADR-0131.

Required work:

- Expand dataset from 30 hand-curated cases to approximately 300-500 cases.
- Add a public split and sealed holdout using the ADR-0119.7 / ADR-0105 sealing pattern.
- Add multi-variable polynomial support (`x`, `y`, `z`, etc.).
- Add exact rational coefficients with `Fraction`; no floats.
- Add equation normalization by moving both sides to canonical zero form.
- Add randomized/property-generated cases with committed seeds.
- Add metamorphic checks:
  - term reordering,
  - adding zero,
  - multiplying by one,
  - distributing nested parentheses,
  - expand/factor equivalence where supported.
- Add adversarial refusal cases:
  - unsupported functions,
  - malformed syntax,
  - unsupported symbolic division until rational expressions are implemented,
  - variable/scope violations,
  - overflow/size caps.
- Pin byte-equal `report.json` replay.

Acceptance:

```text
correct_rate >= 0.95 on public split
correct_rate >= 0.95 on sealed holdout
wrong == 0 on both
report replay byte-equal
all refusal reasons typed and stable
```

Implementation caution:

The normalizer may remain deterministic and symbolic, but the report must distinguish:

| Layer | What it proves |
|---|---|
| normalizer | algebraic canonicalization works |
| lane runner | benchmark method works |
| CORE integration | runtime can invoke / expose the capability |
| promotion artifact | expert claim is auditable |

Do not collapse these into one claim.

---

### Phase 0131.2 — CORE-native teaching-corpus eval

Purpose: prove internal consistency with ratified teaching substrate, without self-deceptive self-grading.

Required work:

- Define `evals/math_teaching_corpus_lane/`.
- Source cases from ratified math, numerics, and units packs.
- Include pack provenance and entry IDs in every case.
- Verify replay against the same pack versions.
- Add mutation/refusal probes for unratified or contradictory pack changes.
- Include correction-store examples only after review/proposal state is explicit.
- Track trace hashes and report byte-equality across replay.

Acceptance:

```text
correct_rate >= 0.95
wrong == 0
trace_hash byte-equal across replay
case provenance complete
unratified / contradictory cases refuse
```

Design warning:

This lane must not become circular. It is allowed to test internal consistency; it must not be the only proof of external capability.

---

### Phase 0131.3 — Bounded-grammar word-problem lane

Purpose: replace the false "arbitrary GSM8K" target with an honest, inspectable natural-language grammar contract.

Required work:

- Define a closed grammar-shape registry, for example:
  - `canonical_has_buys`,
  - `canonical_has_uses`,
  - `there_are_count`,
  - `substance_qualifier`,
  - `compare_additive`,
  - `compare_multiplicative`,
  - `unit_canonicalization`,
  - `indefinite_quantifier_refusal`.
- Build approximately 150 cases.
- Each case must include:
  - `case_id`,
  - `shape_category`,
  - source text,
  - expected graph shape,
  - expected answer or expected refusal,
  - required pack entries,
  - expected trace/replay artifact.
- Include adversarial near-miss cases that superficially resemble valid grammar but must refuse.
- Freeze grammar before evaluation; do not add cases that require future grammar expansion.

Acceptance:

```text
correct_rate >= 0.95 on public split
correct_rate >= 0.95 on sealed holdout
wrong == 0 including adversarial probes
out-of-grammar cases refuse with typed reason
trace/report replay byte-equal
```

Design warning:

This lane should not be "small GSM8K." It should be a formal, externally inspectable grammar proof.

---

### Phase 0131.4 — Promotion gate wiring

Purpose: convert ADR-0131 from proposal/docs into executable promotion machinery.

Required work:

- Update `formation/ratify.py` as needed.
- Update `formation/promote.py` for `mathematics_logic` expert gate composition.
- Add a composite report builder.
- Include GSM8K stress-lane disclosure in the expert claim artifact.
- Require all three ADR-0131 benchmark lanes before promotion can pass.

Acceptance command target:

```bash
core promote mathematics_logic --tier expert --report reports/math_expert_v1.json
```

The promotion should fail closed unless every lane result is present, fresh, digest-verified, and replay-compatible.

---

### Phase 0131.5 — ADR-0120 amendment

Purpose: formally revise the original expert promotion contract.

Required work:

- Amend ADR-0120 or add companion ADR documenting the exact replacement of the GSM8K `correct_rate` requirement.
- Preserve the other ADR-0120 checks unless explicitly superseded.
- State that GSM8K remains a stress/disclosure lane, not a promotion gate.
- Record why this is not goalpost shifting:
  - repeated zero-lift evidence,
  - invariant preservation,
  - new composite gate is stricter on `wrong == 0`,
  - public/holdout replay discipline remains.

---

### Phase 0131.6 — Final promotion attempt

Purpose: make one auditable `mathematics_logic` expert attempt.

Acceptance:

- Benchmark 1 passes public + sealed.
- Benchmark 2 passes replay and provenance checks.
- Benchmark 3 passes public + sealed.
- GSM8K stress result is disclosed honestly.
- Expert claims artifact includes digest, report paths, lane SHAs, and reviewer decision.
- Failure opens a named blocker ADR; success produces an accepted promotion ADR.

---

## Immediate recommendation for the next engineer

Do not expand GSM8K parser work next.

Do not treat symbolic-equivalence v1 as proof of expert capability.

The highest-leverage next implementation branch is:

```text
feat/adr-0131-1b-symbolic-equivalence-hardening
```

Target that branch at Phase 0131.1.B only:

1. expand normalizer scope,
2. expand dataset,
3. add property/metamorphic tests,
4. add sealed holdout,
5. pin replay determinism,
6. keep claim language narrow.

That branch should not mix in Benchmark 2, Benchmark 3, or promotion wiring.

---

## Non-negotiable gates

Every phase must preserve:

```text
wrong == 0
fail closed on missing evidence
typed refusals for out-of-scope inputs
byte-equal replay where claimed
sealed holdouts for external-facing lanes
no expert claim until the full composite gate passes
```

These gates are more important than coverage.

---

## Reviewer checklist

Before merging any ADR-0131 follow-up, ask:

1. Does this PR increase proof strength, or merely increase apparent coverage?
2. Does it preserve `wrong == 0` under adversarial near-miss cases?
3. Does it distinguish normalizer/tool capability from CORE runtime/model capability?
4. Is the dataset sealed where external claims depend on it?
5. Is replay byte-equal?
6. Are refusal reasons typed and stable?
7. Is claim language narrower than the evidence?
8. Does the branch keep one coherent scope?

If any answer is no, the PR should not promote capability claims.

---

## Strategic public framing

The public-safe claim should be:

> CORE demonstrates bounded-domain verified reasoning with deterministic replay, auditable traces, refusal-first behavior, and sealed-eval discipline.

The claim should not be:

> CORE broadly beats LLMs at math.

The former is true to the architecture. The latter is not yet proven.
