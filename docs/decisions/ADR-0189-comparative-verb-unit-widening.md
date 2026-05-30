# ADR-0189 — Comparative reading: anchor-verb widening + multi-word units

**Status:** Proposed (implemented in this PR). Extends
[ADR-0131.G.2](./ADR-0131-G-gsm8k-grammar-coverage.md) (candidate-graph
comparative extractors). Serving-path capability; landed wrong=0-proven.

> **One line.** The candidate-graph comparative extractor read only `has`/`have`
> + single-word units, so real-GSM8K comparatives (`Brooke **does** three times
> as many **jumping jacks** as Sidney`) didn't parse. This widens the anchor-verb
> set (excluding polarity-inverting verbs) and admits 1–2-word units. It feeds the
> existing ADR-0123 `compare_multiplicative`/`compare_additive` solver; wrong=0 is
> preserved (G2_comparatives 29/29; train_sample 3/47/0 byte-identical).

---

## 1. The gap (microscope finding, 2026-05-29)

The candidate-graph parser emits **no comparative operation** for the most common
real-GSM8K comparative surfaces, even though the **solver already supports them**
(ADR-0123 `compare_additive`/`compare_multiplicative`, fully wired in
`math_solver`). Measured: comparatives are a **dark statement in 17 places,
blocking 15 of the 47 refused `train_sample` cases**.

Two extractor limits caused the misses (`_comparison_anchor_verb()` was
`(?:has|have)` and units were `\w+`):

- **Verb coverage.** `does`/`collected`/`gained`/`studied`/`makes`/… were not
  recognized. (ADR-0131.G.2 deferred this explicitly: "past-tense + lemma-widening
  are deferred … to keep the precedence story narrow" — a scope limit, not a
  wrong=0 constraint.)
- **Multi-word units.** `jumping jacks` (case 0024) could not match.

## 2. The change

- `generate/math_candidate_parser._comparison_anchor_verb()` — widen to the
  already-vetted legacy `math_parser._COMPARE_VERB` lemmas plus the
  production/activity verbs seen in real GSM8K comparatives. **Deliberately
  EXCLUDES** polarity-inverting verbs (`lose/lost`, `win/won`, `spend/spent`,
  `use/used`, `give/gave`, `sell/sold`) — admitting them could read a comparison
  backwards and breach wrong=0.
- The two multiplicative regexes admit an optional second unit word
  (`\w+(?:\s+\w+)?`), grounded via the existing multi-word branch of
  `_unit_grounds`.

## 3. wrong=0 evidence

- **G2_comparatives lane: 29/29, wrong=0** (the dedicated comparative lane).
- G3_numerics 20 correct / 0 wrong; G4_multi_clause 32/32; train_sample
  **3/47/0 byte-identical** (no flip, no wrong).
- Polarity-inverting verbs proven refused (`test_…_polarity_inverting_verb_not_admitted`,
  `test_spend_verb_not_admitted`) — failing-under-violation.
- The round-trip filter is unchanged: the comparator anchor (`twice`/`N times`/
  `more`/`fewer`) and the reference actor still must ground.

## 4. Honest scope — a necessary component, not a standalone solve

This widening flips **zero** `train_sample` cases by itself, because every
comparative-blocked case also needs a composing partner the reader still lacks
(e.g. case 0024 needs Sidney's `20+36+40+50=146` day-of-week aggregation **and**
multi-word counted-noun injection before `Brooke = 3 × 146 = 438` can solve). The
comparative + question chain is proven to compose correctly in isolation
(`Sidney has 146 apples. Brooke has three times as many apples as Sidney.` →
**438**). This ADR ships the comparative component; the first metric flip
(`3/47/0 → 4/46/0`) lands when its companion capability (aggregation /
multi-word-noun injection) lands for a shared target case.

## 5. Why this obeys the standing principles

- **Decode, don't guess.** The engine could already *reason* about comparison
  (ADR-0123 solver); this teaches it to *read* the comparison — closing a
  comprehension gap, not adding a stored answer.
- **General, not overfit.** A widened closed verb set + multi-word units is a
  fundamental construction across 15 cases, not a per-case surface regex.
- **wrong=0 > coverage.** Polarity-inverting verbs excluded; G2 lane 29/29;
  serving 3/47/0 byte-identical; round-trip filter untouched.
- **No contradiction** with in-use ADRs: extends ADR-0131.G.2's extractor and
  feeds the ADR-0123 solver unchanged.
