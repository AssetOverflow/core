# ADR-0131 — Re-Target Math Expert Promotion to Architecture-Aligned Benchmarks

**Status:** Proposed
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114a (10 anti-overfitting obligations), ADR-0119
(+ 8 sub-phases), ADR-0120 (expert promotion contract), ADR-0121
(math expert promotion deferred), ADR-0126 (candidate-graph parser),
ADR-0127 (units pack), ADR-0128 (numerics pack),
ADR-0127-0128-RESULTS (Path-B trigger evidence)
**Supersedes:** the GSM8K-coverage requirement in ADR-0120's
`expert` gate for the `mathematics_logic` domain. The other 12 of
ADR-0120's 13 checks remain unchanged.

---

## Context

ADR-0121 deferred the `mathematics_logic` → `expert` promotion with
named blocker `correct_rate = 0/1319 on sealed GSM8K`. The
project then ran a four-ADR arc to address that blocker:

| ADR | Hypothesis | Sealed-lift result |
|-----|-----------|-------------------|
| ADR-0122 | per-rate-shape grammar expansion | 0 / 1319 |
| ADR-0123 / 0123a / 0123b | comparison-phrasing + upstream shape gaps | 0 / 1319 |
| ADR-0126 (architectural pivot) | candidate-graph topology replaces fail-hard parser | 0 / 50 train sample |
| ADR-0127 + ADR-0128 (substrate) | exhaustive units + numerics packs feed the new architecture | 0 / 50 train sample |

`ADR-0127-0128-RESULTS` documents the architectural verdict: the
full deterministic design (candidate-graph + units + numerics +
pack-aware parser) is correct, complete, replay-deterministic,
and produces zero coverage on the GSM8K train sample. The
refusal-cause breakdown shows 27/50 refusals are OTHER_SHAPE
gaps (cross-statement pronouns, possessives, subordinate clauses,
multi-word entities, multi-step inference) that no pack
substrate can address.

The empirical finding is unambiguous: **GSM8K's distribution is
not parseable by any deterministic rule set at the per-statement
parse rate the substrate enables.** GSM8K rewards paraphrase
flexibility — which is the one thing CORE's algebraic substrate
is structurally weakest at — and undervalues exact recall,
provenance, and replay determinism — which are CORE's structural
strengths.

This ADR re-targets the math expert promotion to benchmarks
that *measure what CORE actually excels at*, rather than
penalizing it for the one axis it doesn't optimize for.

---

## Decision

Define the `mathematics_logic` expert promotion contract in terms
of **three complementary benchmarks**, each measuring a
discriminator the architecture should excel at. All three must
pass at their respective thresholds, AND the other 12 ADR-0120
checks must hold. **The GSM8K-coverage requirement is removed.**

### Benchmark 1 — Symbolic equivalence (primary discriminator)

**What:** Given two algebraic expressions A and B, the engine
must determine whether `A ≡ B` (algebraically equivalent) under
the CGA substrate's exact-recall semantics. Coverage scope:
polynomials in 1–4 variables, rational expressions, equations in
standard form, factored forms, expanded forms.

**Why:** This is *exactly* what CGA exact-recall is built for.
There is no paraphrase-variance ceiling. The discriminator is
algebraic correctness, which is the architecture's strongest
axis.

**Dataset:** Curated, ratified, version-pinned. Initial scope:
~500 (A, B, label) triples drawn from algebra-1 / algebra-2 /
precalc symbolic-equivalence canon. Mirror the
`evals/gsm8k_math/holdouts/v1/cases.jsonl.age` sealing pattern:
public-split + sealed-holdout, never-decrypted-by-CI.

**Pass criterion:** `correct_rate ≥ 0.95 on public split AND on
sealed holdout`. `wrong == 0` invariant preserved. (The high
threshold is appropriate because the architecture has no
structural disadvantage on this task.)

### Benchmark 2 — CORE-native teaching-corpus eval (lane gate)

**What:** Run the math expert against the math teaching corpus's
own evaluation lane. Problems are sourced from ratified
teaching chains in `language_packs/data/en_arithmetic_v1` +
en_units_v1 + en_numerics_v1; the parser's grammar matches the
corpus's surface forms *by construction* (no paraphrase-variance
gap because both sides of the eval consume the same ratified
substrate).

**Why:** This is the lane that proves the math expert is
internally consistent with the ratified knowledge it claims to
encode. If this lane fails, the engine cannot reliably evaluate
its own teaching corpus — a deeper problem than any
external-benchmark coverage gap.

**Pass criterion:** `correct_rate ≥ 0.95 on the corpus eval AND
trace_hash byte-equality across replay AND wrong == 0`. This
mirrors the existing cognition-lane gate pattern.

### Benchmark 3 — Bounded-grammar word-problem set (operator surface)

**What:** A small (~150 cases), ratified, hand-curated set of
single-statement-style word problems whose surface forms are
*pre-filtered* to match the ADR-0126/0127/0128 parser scope.
Lane purpose: demonstrate the end-to-end pipeline produces correct
answers on the *in-scope* word-problem distribution.

**Why:** This is the honest version of the GSM8K claim. We are
explicitly *not* claiming to solve arbitrary natural-language
math word problems. We *are* claiming to solve word problems
that fall within a well-defined, externally-inspectable grammar
contract. The bounded-grammar set is the externally-reviewable
proof of that claim.

**Curation policy** (load-bearing):
- Every problem must be solvable by the current parser pipeline
  *without future grammar extensions* — the set proves coverage
  of a fixed grammar, not a moving target.
- Every problem ships with a "shape category" tag
  (`canonical_has_buys`, `there_are_count`, `substance_qualifier`,
  `compare_additive`, etc.) drawn from a closed set documented
  in the lane's README.
- No problem may be added that requires inference beyond a
  single statement's parse. Multi-step problems are excluded
  by design.
- Adversarial probes ensure the parser refuses (`wrong == 0`)
  on out-of-grammar shapes even when those shapes appear
  superficially similar to in-scope shapes.

**Pass criterion:** `correct_rate ≥ 0.95 on public split AND on
sealed holdout`. `wrong == 0` preserved including on adversarial
out-of-grammar shapes.

### Composite expert-promotion gate

For the `mathematics_logic` domain, the `expert` promotion
contract (ADR-0120) is revised:

| ADR-0120 check | Status under ADR-0131 |
|---|---|
| `audit_passed` holds | unchanged |
| ADR-0114a obligations #1–#10 | unchanged |
| Signed `expert_claims` entry with reproducible digest | unchanged |
| **`correct_rate ≥ 0.60` on public AND sealed holdout** | **REVISED:** replaced by composite requirement: Benchmark 1 ≥ 0.95 AND Benchmark 2 ≥ 0.95 AND Benchmark 3 ≥ 0.95, each with `wrong == 0` |
| `wrong == 0` enforcement | strengthened (now three lanes) |

GSM8K is **retained as a stress-test lane** that the math expert
*runs* but is *not gated on*. GSM8K refusal counts are reported
in the expert-claims artifact as honest disclosure ("here's what
we can't do") without blocking promotion.

---

## Why three benchmarks instead of one

A single benchmark is brittle: if the gate is set against any
one of them, that benchmark becomes the optimization target and
the architecture risks the same overfitting pathology ADR-0114a
was written to prevent. Three orthogonal benchmarks force the
math expert to demonstrate three distinct architectural
properties:

| Property | Benchmark that tests it |
|----------|------------------------|
| Algebraic correctness under exact recall | Benchmark 1 |
| Internal consistency with ratified teaching substrate | Benchmark 2 |
| End-to-end pipeline determinism on in-scope NL inputs | Benchmark 3 |

A pass on all three is a meaningful claim. A pass on any one in
isolation is not.

---

## Alternatives considered

### A. Keep GSM8K as the gate; lower the threshold (e.g., 0.20).
**Rejected.** ADR-0114a Obligation #4 ("wrong rate strictly
zero") AND the 4-ADR-zero-lift evidence both point against
optimizing for a benchmark the architecture cannot meaningfully
move. Lowering the threshold to fit our actual result is exactly
the goalpost-shifting that ADR-0114a was written to forbid.

### B. Switch to a single new benchmark (MATH symbolic subset).
**Considered.** MATH (Hendrycks et al.) has many of the same
paraphrase-variance issues GSM8K has. Symbolic-equivalence
problems are a *subset* of MATH and are the right discriminator,
but the rest of MATH would reproduce the GSM8K trap.

### C. Switch to MMLU-Math.
**Rejected.** Multiple-choice format is the wrong shape for the
architecture — it rewards calibrated guessing, which violates
`wrong == 0`. Refusing-on-uncertainty would surface as
"selected the wrong option" rather than "abstained," collapsing
the architecture's primary defensive property.

### D. Use a theorem-proving subset (miniF2F-style).
**Rejected for now.** Theorem proving is further from the
current substrate's capabilities than algebraic equivalence.
Worth revisiting as a future expansion of the math expert's
scope after ADR-0131 lands.

### E. Define the expert promotion in terms of CORE-native eval only (Benchmark 2 alone).
**Rejected.** External reviewability matters. Benchmark 2 alone
would be self-graded and lack the discipline of an external
discriminator. Benchmarks 1 and 3 provide that discipline.

### F. Skip the expert promotion entirely; keep math at audit-passed indefinitely.
**Considered.** The math substrate is already useful at
audit-passed tier. But the expert tier exists for a reason
(stronger claims, broader operator trust, downstream
dependencies). Indefinite deferral is a worse outcome than
re-targeted promotion.

---

## Exit criterion for ADR-0131 itself

ADR-0131 becomes Accepted when:

1. The composite benchmark definitions (Benchmarks 1, 2, 3) are
   ratified — initial dataset curation + sealed-holdout
   encryption + lane runner code + ratification tests all land.
2. The `mathematics_logic` domain re-runs the revised promotion
   contract and either passes (promotion lands) or fails on a
   specific named benchmark (which becomes the next blocker).
3. ADR-0121's `gap:mathematics_logic_expert_first_attempt_deferred`
   entry in `docs/gaps.md` is updated to reflect the new gate
   structure.

Until that work lands, ADR-0131 remains **Proposed** — the
GSM8K-coverage requirement is *not yet removed from ADR-0120*.
This ADR documents the proposed direction; the actual contract
revision is a follow-up implementation PR.

---

## Implementation plan (proposed sub-phases)

| Phase | Module / Lane | Description |
|-------|---------------|-------------|
| 0131.1 | `evals/math_symbolic_equivalence/` | Benchmark 1 substrate: dataset, public/sealed split, lane runner, ratification tests |
| 0131.2 | `evals/math_teaching_corpus_lane/` | Benchmark 2 substrate: pull from ratified packs, lane runner, byte-equality replay gate |
| 0131.3 | `evals/math_bounded_grammar_v1/` | Benchmark 3 substrate: hand-curated cases with shape-category tags, public/sealed split, adversarial probes |
| 0131.4 | `formation/ratify.py` + `formation/promote.py` | Update expert-promotion gate to consult the composite benchmark result |
| 0131.5 | `docs/decisions/ADR-0120-amendment.md` | Companion amendment to ADR-0120 documenting the composite gate; cross-reference ADR-0131 |
| 0131.6 | Re-run promotion attempt | Run revised gate; emit expert-claims artifact; either land promotion or open new named-blocker ADR |

Regression gates (must remain green at every phase):
- `core test --suite smoke -q`
- `core test --suite math -q` (existing 700+)
- `core test --suite packs -q` (en_units_v1 + en_numerics_v1 ratification)
- ADR-0126 candidate-graph test suite

---

## What this does NOT do

- Does NOT discard the GSM8K work. The substrate (ADR-0126 / 0127 /
  0128) stays in main as load-bearing infrastructure. GSM8K stays
  as a stress-test lane with honest-disclosure refusal counts.
- Does NOT weaken ADR-0114a obligations. All 10 remain unchanged;
  `wrong == 0` is *strengthened* (now three lanes instead of one).
- Does NOT introduce stochastic, learned, or LLM-assisted
  components anywhere in the math expert pipeline.
- Does NOT promote math to expert by fiat. Promotion still
  requires the composite gate to pass on real datasets that have
  to be built (sub-phases 0131.1–0131.3).
- Does NOT pre-judge whether the math expert will pass the new
  gate. The architecture's actual coverage on symbolic
  equivalence + corpus eval + bounded grammar is an empirical
  question that 0131.6 answers. The bet is that the architecture
  excels on these benchmarks because they align with its
  structural strengths; the bet may or may not pay off.

---

## Composition with other in-flight work

- **ADR-0129 + ADR-0130 (deferred teaching-loop ADRs):** these
  become more interesting once a stable correction-store
  population exists. Benchmark 2 (teaching-corpus eval) is the
  natural surface where reviewed corrections accumulate; if
  ADR-0131 promotes math to expert, the corrections from
  Benchmark 2's failures become the population that triggers
  ADR-0129/0130's un-deferral exit criteria.
- **Future language packs (`es_units_v1`, etc.):** Benchmarks 1
  and 3 are inherently language-bound. Cross-language expansion
  would require parallel benchmark sets per language.
- **Future domain expansions** (physics, etc.): the three-
  benchmark composite pattern this ADR introduces is a template
  that other domain expert promotions can adopt with their own
  domain-specific Benchmark 1 / 2 / 3 definitions.

---

## PR checklist (when proposing for acceptance + sub-phase implementations)

```
What capability did this add/protect?
  → Re-targeted math expert promotion gate to architecture-
    aligned benchmarks; preserves wrong == 0 across three lanes
    instead of one; honest disclosure of GSM8K refusal counts
    without GSM8K-coverage gating.
What invariant proves the field remains valid?
  → wrong == 0 enforced across all three new benchmark lanes
    (strengthened from previous single-lane enforcement).
    Replay determinism, pack-binding, trace_hash byte-equality
    all preserved.
Which CLI suite/eval proves the lane?
  → New: `core test --suite math-symbolic-equivalence`,
    `core test --suite math-teaching-corpus`,
    `core test --suite math-bounded-grammar`. Plus existing
    smoke + math + packs.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. All three benchmarks are deterministic, ratified,
    version-pinned. No LLM-assisted scoring. No probabilistic
    thresholds for refusal.
If it touches user input, what trust boundary was enforced?
  → No new user-input surfaces. Sealed-holdout encryption
    pattern mirrors ADR-0119.7. Public split is unsealed by
    design. Adversarial probes in Benchmark 3 are bounded by
    the lane's curation policy.
```
