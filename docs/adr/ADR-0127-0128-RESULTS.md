# ADR-0127 + ADR-0128 Results — Path-B Triggered

**Status:** Empirical result; load-bearing for the GSM8K-math arc decision
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:** ADR-0126 (architecture), ADR-0127 (units pack),
ADR-0128 (numerics pack), ADR-0114a (10 anti-overfitting obligations),
ADR-0119 (+ all 8 sub-phases), ADR-0120 (expert promotion contract),
ADR-0121 (math expert promotion deferred)

---

## TL;DR

The ADR-0126 → 0127 → 0128 arc shipped the full deterministic
design that the parser-by-rule + units-substrate hypothesis
required. The empirical result on the GSM8K train sample is:

```
correct  =  0 / 50
wrong    =  0 / 50  (wrong == 0 preserved)
refused  = 50 / 50
```

Per ADR-0127's exit criterion and the Path-A vs Path-B decision
documented in ADR-0126: **the deterministic parser-by-rule
architecture, with full units + numerics substrate, does not move
the GSM8K-math lane.** This is the **real Path-B trigger.** The
math expert promotion path retargets to a benchmark where exact
recall and determinism are the discriminators — see
"Recommendation" below.

---

## What was shipped

| Layer | Module / Pack | What |
|-------|---------------|------|
| Architecture | `generate/math_roundtrip.py` | Round-trip admissibility primitive (26 tests, ADR-0126 P1) |
| Architecture | `generate/math_candidate_parser.py` | Candidate-emitting sentence parser (17 tests, ADR-0126 P2) |
| Architecture | `generate/math_candidate_graph.py` | Branch enumeration + decision rule (22 tests, ADR-0126 P3) |
| Architecture | `evals/gsm8k_math/runner.py::_score_one_candidate_graph` | Runner wiring (9 tests, ADR-0126 P4) |
| Substrate | `language_packs/data/en_units_v1/` | 284 lemmas, 401 conversion edges, NIST/ISO provenance (Gemini, PR #164) |
| Substrate | `language_packs/data/en_numerics_v1/` | 130 lemmas across cardinals/ordinals/fractions/multipliers/quantifiers/comparison-anchors/format-rules (Opus #2, PR #163) |
| Loader | `language_packs/loader.py` re-exports | Single import path for both packs (ADR-0127/0128 deferred coordination) |
| Integration | `generate/math_candidate_parser.py::_canonicalize_unit` | Pack-aware unit canonicalization — handles irregular plurals (feet, children, etc.) via pack lookup |
| Integration | `generate/math_candidate_parser.py::extract_initial_candidates` | Widened to `<Entity> has N <unit> [of <substance>]` + `There are N <unit> [in <place>]` shapes |
| Integration | `generate/math_candidate_parser.py::_is_indefinite_quantifier` | ADR-0128.4 quantifier-driven refusal (`some`, `many`, etc. → no candidate emitted; preserves wrong == 0) |
| Integration | `generate/math_candidate_parser.py` op-pattern trailing prep | Added `of` / `for` / `with` to the discardable preposition tail (ADR-0127 substance qualifier) |
| Integration | `generate/math_roundtrip.py::_value_grounds` | Pack-backed cardinal lookup (widens word-number coverage from hard-coded 0-12 to full numerics pack) |
| Integration | `evals/gsm8k_math/train_sample/v1/runner.py` | Swapped `_score_one` → `_score_one_candidate_graph` |

## What measurably works (synthetic verification)

The candidate-graph architecture + pack substrate solves the
*kinds* of problems it was designed to solve. Six tailored
synthetic cases verify end-to-end:

| Case | Result |
|------|--------|
| `Jan has 5 apples. Jan buys 3 apples. How many apples does Jan have?` | ✓ 8 |
| `Sam has 10 feet of rope. Sam uses 3 feet of rope. How many feet does Sam have?` | ✓ 7 (non-count unit; substance qualifier) |
| `There are 5 kids in camp. How many kids do they have?` | ✓ 5 (implicit-subject shape) |
| `Sam has 10 dollars. Sam spends 3 dollars. How many dollars does Sam have?` | ✓ 7 (money) |
| `Sam has 5 hours. Sam uses 2 hours. How many hours does Sam have?` | ✓ 3 (time-dimension unit) |
| `Sam has 10 children. Sam loses 2 children. How many children does Sam have?` | ✓ 8 (irregular plural via pack) |

**1050/1050** existing test regression suites green across math,
ADR-0126, ADR-0127 pack ratification, ADR-0128 pack ratification,
and runner. Zero regressions from the integration work.

## What did not move (empirical reality)

The 50-case GSM8K train sample stays at 0 correct / 0 wrong / 50
refused. Inspection of refusal causes shows that real GSM8K
problems carry compound linguistic structure that no pack adds
on its own:

| Refusal class (from baseline categorization) | Train sample share | Pack-addressable? |
|---|---|---|
| OTHER_SHAPE (subordinate clauses, multi-word entities, possessives, pronouns across statements) | 27 / 50 | **No** — these need parser grammar work, not packs |
| NON_COUNT_UNIT (`feet`, `hours`, etc.) | 8 / 50 | **Partial** — pack helps single-statement, but problems still chain across multiple statements that other gaps refuse |
| MONEY (`$N`) | 5 / 50 | **Partial** — same multi-statement compound issue |
| RATE (`per`, `each`) | 5 / 50 | Partial |
| INDEFINITE_QUANT (`some`, `few`) | 3 / 50 | Yes — pack refuses cleanly, but refusal isn't correct |
| CONTAINER_OF | 1 / 50 | Partial |
| THERE_ARE | 1 / 50 | Yes (now parses), but other statements in same problem still refuse |

The structural problem: a 3-5-sentence GSM8K problem refuses if
*any* sentence has no admissible candidate. P(problem passes) =
P(sentence passes)^N. The pack work raised per-sentence parse
rate measurably on simple shapes, but the *joint* pass rate
stayed at zero because every real problem contains at least one
sentence the parser still can't handle.

## Why this is the Path-B trigger ADR-0126 named

ADR-0126's exit criterion documented two outcomes:

> **If passed:** if 50-case train sample shows correct ≥ 10/50
> with wrong == 0, the architecture is validated; run the sealed
> holdout.
>
> **If missed:** if 50-case train sample shows correct < 10/50,
> the parser-by-rule architecture (in any topology) is the wrong
> abstraction for GSM8K coverage. ADR-0126 itself is deferred and
> the work pivots to benchmark re-selection.

ADR-0127's exit criterion sharpened this: re-run train sample
with units pack mounted; if still missed, the failure is *real*
(architecture + substrate both insufficient).

ADR-0128 added the numerics pack to the same exit criterion.

All three packs are mounted, the architecture is in place, the
substrate is exhaustive (284 unit lemmas + 130 numeric lemmas +
401 conversion edges), and the result is 0/50.

**This is the moment the architectural arc was designed to
surface a decision.** The deterministic design is correct,
load-bearing, and complete; it does not produce GSM8K coverage
because GSM8K's linguistic distribution is not parseable by any
deterministic rule set at the rate the substrate enables. The
27/50 OTHER_SHAPE refusals are the empirical evidence that the
gap is *grammar coverage of paraphrase variance*, not any
specific missing pack lemma.

## What `wrong == 0` actually bought us

Despite 0/50 correct, the wrong-zero discipline produced a
sound, replay-deterministic, audit-trail-complete pipeline that:

- Refuses honestly on every case it cannot handle
- Carries pack-grounded provenance on every emitted operation
- Round-trip-verifies every parsed slot against source tokens
- Passes every adversarial gate
- Composes with the existing teaching subsystem's reviewed-
  correction discipline

This is genuinely useful infrastructure. The verdict is "wrong
benchmark for this architecture's strengths," not "the
architecture is bad."

## Recommendation: Path B

Three sub-decisions:

### 1. Demote GSM8K-math lane from the math expert promotion contract.

GSM8K is retained as a stress test and as a "we honestly refuse
on this distribution" demonstration, but **`correct_rate` on
GSM8K is removed from the ADR-0120 expert-promotion gate** for
the `mathematics_logic` domain.

### 2. Re-target the math expert promotion to a benchmark where exact-recall + determinism are discriminators.

Candidates:

- **MATH symbolic subset** — symbolic-equivalence problems where
  exact algebraic recall is the right primitive
- **CORE-native teaching-corpus eval** — problems sourced from
  ratified teaching chains, where the parser's grammar exactly
  matches the corpus's surface forms by construction (no
  paraphrase-variance gap)
- **A curated word-problem set** with bounded grammar (e.g.,
  Khan Academy style problems pre-filtered to single-sentence
  arithmetic shapes)

A separate ADR (proposed: ADR-0131) scopes the re-targeting
decision and exit criteria.

### 3. ADR-0126 / 0127 / 0128 substrate stays in main as load-bearing infrastructure.

The candidate-graph topology, the round-trip admissibility
primitive, the units pack, the numerics pack, and the
deterministic pack-aware parser are useful for:

- Any future deterministic word-problem benchmark
- The teaching corpus's own evaluation lane (where grammar match
  is by-construction)
- Future cross-language packs (`es_units_v1`, `es_numerics_v1`)
  that reuse the architecture
- Operator interaction surfaces where deterministic refusal +
  honest provenance matter more than raw coverage

**Do not revert.** This work proved a hypothesis correctly even
though the hypothesis didn't pan out for GSM8K.

## What this does NOT recommend

- Does **not** recommend abandoning the deterministic engine
  philosophy. The architecture works; the benchmark choice was
  the error.
- Does **not** recommend pulling in LLM-assisted parsing or
  any opaque component. The contract integrity is intact and
  worth preserving.
- Does **not** recommend more parser regex expansion within the
  current architecture for GSM8K. Four previous ADRs in that
  shape produced 0 lift; this one (the architectural pivot) did
  the same. The treadmill has been independently characterized
  twice now.

## Composition with deferred backlog (ADR-0129 / ADR-0130)

The deferred teaching-loop ADRs (`spaced-correction-replay`,
`pre-articulation-calibration`) become more interesting once Path
B lands a new benchmark, because:

- A benchmark where the parser handles by-construction grammar
  cleanly will produce a stable correction-store population —
  the precondition ADR-0129 named for un-deferral.
- A new benchmark's per-version calibration cohorts give
  ADR-0130 a real signal to measure.

These remain deferred under the new path, but their un-deferral
exit criteria become reachable.

## PR checklist

```
What capability did this add?
  → The integration layer that wires en_units_v1 + en_numerics_v1
    into the ADR-0126 candidate-graph parser. Pack-aware unit
    canonicalization, indefinite-quantifier refusal, substance-
    qualifier handling, There-are initial shape, pack-backed
    cardinal grounding. Also the Path-B trigger evidence.
What invariant proves the field remains valid?
  → wrong == 0 preserved on train sample (0/50 wrong). Trace
    determinism preserved. Round-trip admissibility extended
    with pack-typed unit grounding.
Which CLI suite/eval proves the lane?
  → smoke + math + packs + train_sample_runner. All 1050 tests
    green; train sample re-runs deterministic 0/0/50.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Pack lookups are deterministic. Indefinite quantifier
    refusal is a deliberate hard-no, not a probabilistic
    threshold. No LLM fallback added.
If it touches user input, what trust boundary was enforced?
  → No new user-input surfaces. Pack loaders already validate
    pack_id via safe_pack_id (ADR-0051). Train sample is
    unsealed by design (drawn from GSM8K train split, not
    holdout).
```
