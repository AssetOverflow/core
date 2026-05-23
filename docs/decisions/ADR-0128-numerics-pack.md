# ADR-0128 — `en_numerics_v1` Pack

**Status:** Proposed (scope-only; sibling to ADR-0127)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:**
- ADR-0126 (candidate-graph parser + round-trip filter)
- ADR-0127 (`en_units_v1` — units pack, cross-referenced for
  shared symbol/affix table)
**Supersedes:** none
**Sibling:** ADR-0127. Both packs are jointly required for the
units-aware candidate-graph parser to produce a fair empirical
result on the GSM8K-math lane. Either pack failing ratification
independently blocks the joint exit gate.

---

## Context

ADR-0127 introduces `en_units_v1` (dimensions, units, conversions,
containers, rate connectors). That pack handles the *physical /
economic* substrate. It does NOT handle the *linguistic forms* a
quantity can take in English math word problems:

- Cardinal number words ("seventeen", "two hundred and fifty")
- Ordinal words ("third", "twentieth")
- Fractions as words ("two-thirds", "a quarter") and as symbols
  (`½`, `¾`)
- Multiplier words ("twice", "triple", "half")
- Quantifiers ("all", "some", "each", "every", "many", "few")
- Comparison anchors ("more", "fewer", "less", "additional")
- Numeric format strings ("1,000", "1.5", "1/2", "75%")

Today these are scattered:
- `WORD_NUMBERS` table hard-coded in `generate/math_roundtrip.py`
  (one through twelve only)
- `_COMPARE_VERB` / comparison anchors hard-coded in
  `generate/math_parser.py`
- Fraction handling absent
- Percentage handling absent
- Multi-digit number-word parsing ("two hundred") absent

The GSM8K train sample shows the cost: e.g., "Half of the kids
are going to soccer camp" (refused — `half` not handled),
"3/4 of its temperature" (refused — `3/4` not recognized as
fractional form). These are unrecognized *quantity forms*, not
unrecognized *units*; they sit on a different lexical axis from
ADR-0127's substrate.

A units pack without a numerics pack solves "5 feet + 8 inches"
but still refuses "half a foot." Both packs are needed for the
architecture to get a fair empirical reading on the train sample.

---

## Decision

Add a `language_packs/data/en_numerics_v1/` ratified semantic pack
that exhaustively encodes the English linguistic forms of
quantities. Parser changes are minimal — most pack content
replaces today's scattered hard-coded tables with ratified
lookups.

### Pack content (`en_numerics_v1`) — EXHAUSTIVE SCOPE

Structure mirrors `en_arithmetic_v1` / `en_units_v1`:
`lexicon.jsonl` + `manifest.json` + `glosses.jsonl` +
`.mastery_report.json`.

**Cardinal number words** (entry_id prefix `en-num-card-`):

EXHAUSTIVE for grade-school range:

- `zero` through `twenty` (21 entries)
- Tens: `thirty`, `forty`, `fifty`, `sixty`, `seventy`, `eighty`,
  `ninety` (7 entries)
- Compound rule: `<tens-word>-<unit-word>` (e.g., "twenty-one",
  "ninety-nine") — structural composition, not enumerated
- `hundred`, `thousand`, `million`, `billion` (4 entries)
- Compound rule: `<N> hundred [and <M>]`, `<N> thousand
  [<conjunction> <M>]` — structural composition

Each entry carries `surface`, `numeric_value` (int), `morphology`
(`cardinal`).

**Ordinal number words** (entry_id prefix `en-num-ord-`):

EXHAUSTIVE for grade-school range (1st–31st covers most
calendar / position references in word problems):

- `first` through `tenth` (10 entries — irregular morphology)
- Suffix rule: `<cardinal>th` for 11–31 (eleventh, twelfth,
  thirteenth, …, thirty-first) — structural composition with
  spelling-irregularity table (`fifth` not `fiveth`, `eighth` not
  `eightth`, `twelfth` not `twelveth`, etc.)
- `twentieth`, `thirtieth`, `hundredth`, `thousandth` (4 entries)

Each entry carries `surface`, `position` (int), `morphology`
(`ordinal`).

**Fraction words** (entry_id prefix `en-num-frac-`):

- Named fractions: `half` (½), `third` (⅓), `quarter` (¼),
  `fifth` (⅕), `sixth` (⅙), `seventh` (⅐), `eighth` (⅛),
  `ninth` (⅑), `tenth` (⅒), `sixteenth` (¹/₁₆) — ~10 entries
- Compound rule: `<cardinal>/<ordinal-as-denominator>` (e.g.,
  "two-thirds", "three-quarters") — structural composition
- Article-bound: `a half`, `a quarter`, `a third` resolve to
  the same numeric value as the bare form
- **Symbol cross-link** to `en_units_v1` symbol table for `½`,
  `¼`, `¾`, `⅓`, `⅔`, `⅛`, `⅜`, `⅝`, `⅞`

Each entry carries `surface`, `numerator` (int), `denominator`
(int), `decimal_value` (float — `1/3 = 0.333…` etc.),
`morphology` (`fraction`).

**Multiplier words** (entry_id prefix `en-num-mult-`) — closed
set:

`double` (×2), `triple` (×3), `quadruple` (×4), `quintuple` (×5),
`twice` (×2), `thrice` (×3), `half` (×0.5 — also a fraction
word; both entries cross-reference). Plus structural rule
`N times` for arbitrary integer multipliers.

**Quantifiers** (entry_id prefix `en-num-quant-`) — closed set:

`all`, `none`, `some`, `both`, `each`, `every`, `many`, `few`,
`several`, `most`, `any`, `no`, `single`.

Each declares its `semantic_type`: `total`, `empty`, `partial`,
`paired`, `distributive`, `indefinite`. The parser uses this to
decide whether the quantifier yields a determinate value
(`both = 2`, `single = 1`) or is undeterminate and triggers
refusal (`some`, `many`, `few` — refuse rather than guess; this
preserves `wrong == 0`).

**Comparison anchors** (entry_id prefix `en-num-compare-`):

Migrated from `generate/math_roundtrip.py`'s hard-coded
`COMPARE_ADDITIVE_ANCHORS` / `COMPARE_MULTIPLICATIVE_ANCHORS`.

- Additive: `more`, `fewer`, `less`, `additional`, `extra`,
  `missing`, `remaining`
- Multiplicative: `twice`, `thrice`, `times`, `half`, `double`,
  `triple`, `quadruple`, `third`, `quarter`

Each cross-references its multiplier or fraction entry where
applicable (avoiding duplicate truth).

**Number formats** (entry_id prefix `en-num-format-`) —
structural rules, not enumeration:

- Digit groups: `1,000` (US thousand separator), `10,000`,
  `1,000,000` — `(\d{1,3})(?:,\d{3})+` → strip commas, parse as int
- Decimals: `1.5`, `3.14`, `0.25` — `\d+\.\d+` → parse as float
- Slash-fractions: `1/2`, `3/4`, `7/8` — `(\d+)/(\d+)` →
  parse as `Fraction`
- Mixed numbers: `1 1/2`, `2 3/4` — `(\d+) (\d+)/(\d+)` →
  `whole + numerator/denominator`
- Percentages: `75%`, `1.5%` — `\d+(?:\.\d+)?%` → divide by 100
- Negative numbers: `-3`, `-0.5` — leading minus (rarely in
  grade-school but cheap to include)

Each format rule declares its regex pattern, `parser_function`
(by name), and `output_type` (`int`, `float`, `Fraction`).

### Cross-references with `en_units_v1`

- Fraction symbols `½`, `¼`, `¾`, etc. appear in both packs.
  Single source of truth lives in `en_numerics_v1`;
  `en_units_v1` symbol-affix table contains a *reference* entry
  pointing to the numerics pack via `cross_pack_id`. Ratification
  cross-pack consistency check (see ADR-0127 ratification
  invariants and below) verifies the references resolve.
- Percentage (`%`) cross-references between packs because it's
  both a numeric format and a dimensionless modifier.
- Multipliers (`double`, `twice`) cross-reference because they
  also appear as comparison anchors in `en_units_v1`'s parser-
  consumed register.

### Ratification invariants (`en_numerics_v1`-specific)

1. **Cardinal exhaustiveness** — every English cardinal 0..20,
   every "tens" form, every magnitude word
   (hundred/thousand/million) present.
2. **Ordinal exhaustiveness** — every English ordinal 1st..31st
   present (covers month days + most grade-school position
   references).
3. **Fraction exhaustiveness** — every named fraction 1/2 through
   1/10 present + the irregular set (sixteenth, thirty-second).
4. **Cross-pack consistency** — every fraction-symbol entry in
   `en_units_v1` resolves to a fraction entry in
   `en_numerics_v1`. Verified by joint pack-mount ratification.
5. **Quantifier semantic-type completeness** — every quantifier
   lemma carries a `semantic_type` from the closed set
   `{total, empty, partial, paired, distributive, indefinite}`.
6. **Format regex test corpus** — each format rule has a
   minimum of 10 positive + 10 negative test strings in
   `tests/test_adr_0128_numeric_formats.py`. Format ambiguity
   (e.g., `1.000` could be `1` or `1000`) is *refused* per
   `wrong == 0`, not guessed.

### Parser integration

1. **`generate/math_roundtrip.py`** — replace hard-coded
   `WORD_NUMBERS` and `COMPARE_*_ANCHORS` tables with calls into
   `en_numerics_v1` loader. Behavior preserved (current entries
   are a subset); future extensions land in the pack, not the
   source.

2. **`generate/math_candidate_parser.py`** — new value-token
   normalization helper `normalize_value_token(token) -> Quantity
   | Fraction | None` that consults `en_numerics_v1` format
   rules. Handles "two-thirds" → `Fraction(2,3)`, `75%` → `0.75`,
   `1,500` → `1500`, etc.

3. **Round-trip filter (`roundtrip_admissible`)** — the existing
   `_value_grounds` helper is extended to ground word-forms via
   the numerics pack loader (current hard-coded `WORD_NUMBERS`
   capped at "twelve" widens to the full cardinal table).

4. **Quantifier-driven refusal** — when a candidate's value-token
   resolves to an `indefinite` quantifier (`some`, `many`, `few`),
   the parser emits NO candidate for that sentence. Empty list →
   refusal at decision rule. Preserves `wrong == 0`.

### What ADR-0128 explicitly does NOT do

- Does NOT replace `en_units_v1`. The packs are siblings.
- Does NOT introduce new operation kinds. ADR-0126 + 0122 cover
  the operation grammar; this pack supplies value-token forms.
- Does NOT model number-system alternates (Roman numerals,
  Chinese numerals, etc.) — out of scope for English math
  problems.
- Does NOT model implicit numbers ("a dozen" / "a few") as
  determinate values — `a dozen = 12` is encoded via the
  container's `default_size` (ADR-0127's container entry, not
  here); `a few` is `indefinite` and triggers refusal.
- Does NOT add new exit gates. Joint exit criterion with
  ADR-0127 (re-run train sample with both packs mounted).

---

## Invariants preserved / added

| Invariant | Preserved or added | How |
|-----------|--------------------|-----|
| `wrong == 0` | Preserved | Indefinite quantifiers trigger refusal; format ambiguity triggers refusal |
| `trace_hash` byte-equality | Preserved | Pack lookup is deterministic |
| Pack-binding (ADR-0114a #10) | Reinforced | Value-token resolution cites `en-num-*` entry_ids in `SolutionTrace.provenance` |
| Round-trip admissibility | Strengthened | Word-form numbers ground via pack lookup, not regex enumeration |
| Replay equivalence | Preserved | Same pack version → same lookup result |
| `versor_condition(F) < 1e-6` | Untouched | No runtime field changes |
| Manifest checksum SHA-256 of bytes-on-disk | Required | Mastery report self-seals |

## Exit criterion

**Joint with ADR-0127** — both packs ratified, both mounted,
re-run train sample:

```
correct >= 10 / 50  on evals/gsm8k_math/train_sample/v1/cases.jsonl
wrong  == 0
```

**If passed:** run sealed holdout once, freeze in ADR-0127/0128
joint results.

**If missed:** **Path-B trigger** — full deterministic design
(candidate-graph + units + numerics) failed to move GSM8K.
Demote benchmark, re-target math expert promotion.

---

## Alternatives considered

### A. Fold numerics into `en_units_v1` as one big pack.
Rejected per ADR-0127 discussion: domain-distinct lexicons,
risk-isolation, future i18n composability.

### B. Keep hard-coded tables in `math_roundtrip.py` / `math_parser.py`.
Rejected — violates pack-binding (ADR-0114a #10); future
language packs (Spanish, German) would have to duplicate the
hard-coded tables; ratification is impossible.

### C. Use a third-party number-parsing library (`word2number`,
`num2words`, etc.). Rejected — same opacity / non-auditability
critique as ADR-0127 alt B.

### D. Ship only cardinals + fractions; defer quantifiers /
ordinals / formats. Rejected — quantifiers (`half`, `some`) are
*specifically* what the GSM8K train sample refuses on. Partial
pack delivers partial empirical signal — same trap ADR-0127
addresses re: scope mismatch.

---

## Implementation plan (proposed sub-phases)

| Phase | Module | Description |
|-------|--------|-------------|
| 0128.1 | `language_packs/data/en_numerics_v1/` | Pack content (lexicon + manifest + glosses + mastery report) |
| 0128.2 | `language_packs/loader.py` | `lookup_cardinal`, `lookup_ordinal`, `lookup_fraction`, `lookup_quantifier`, `match_number_format` |
| 0128.3 | `generate/math_roundtrip.py` | Replace hard-coded `WORD_NUMBERS` + `COMPARE_*_ANCHORS` with pack-backed lookups |
| 0128.4 | `generate/math_candidate_parser.py` | `normalize_value_token` helper; quantifier-driven refusal |
| 0128.5 | `tests/test_adr_0128_*.py` | Pack ratification (exhaustiveness gates) + parser integration + format regex corpus |
| 0128.6 | Joint with ADR-0127.7 | Re-run train sample with both packs mounted |

Regression gates:
- `core test --suite smoke -q`
- `core test --suite math -q`
- `core test --suite packs -q`
- ADR-0126 P3+P4 tests
- ADR-0127 pack ratification

## PR checklist (when proposing for merge)

```
What capability did this add?
  → Exhaustive English linguistic-form ontology for quantities;
    sibling substrate to en_units_v1 (ADR-0127).
What invariant proves the field remains valid?
  → Wrong==0 preserved via indefinite-quantifier refusal +
    format-ambiguity refusal; cardinal/ordinal/fraction
    exhaustiveness ratification gates.
Which CLI suite/eval proves the lane?
  → smoke + math + packs + joint train_sample re-run with
    ADR-0127.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Pack lookup is deterministic; lexicon is bounded and
    ratified; no learned tokenization; no fuzzy matching.
If it touches user input, what trust boundary was enforced?
  → Pack file paths validated via safe_pack_id (ADR-0051).
    Format regexes carry test corpora documenting accepted vs
    rejected inputs; user input is matched against ratified
    patterns only.
```
