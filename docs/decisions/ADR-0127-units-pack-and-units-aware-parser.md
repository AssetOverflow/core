# ADR-0127 — `en_units_v1` Pack + Units-Aware Candidate Extractors

**Status:** Proposed (scope-only; implementation follow-up to ADR-0126)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:**
- ADR-0115 / 0116 / 0117 / 0118 (parser / solver / verifier / realizer)
- ADR-0122 (Rate operand)
- ADR-0126 (candidate-graph parser + round-trip filter)
**Supersedes:** none
**Blocks:** the Path-B decision for the GSM8K-math lane (the real
empirical answer can't be obtained until the parser consumes a
units pack).

---

## Context

ADR-0126's first empirical run produced **0 / 50 correct, 0 wrong,
50 refused** on the GSM8K train-sample inner-loop gate. Inspection
of the refusal reasons revealed a pattern: every refusal happens at
the *first statement* of each problem, and every refused first
statement shares the same shape — **the parser fails on the
unit-of-measurement construction, not on the operation grammar**.

Representative train-sample first statements (all refused):

| Case | First statement | What's structurally not recognized |
|------|----------------|-----------------------------------|
| 1 | `Tina makes $18.00 an hour.` | Money + time = rate dimension |
| 2 | `Jan buys 1000 feet of cable.` | Length unit + substance qualifier |
| 3 | `... bookstore donated 48 boxes of erasers.` | Container + count-content |
| 5 | `In one hour, Addison mountain's temperature ...` | Temperature dimension + fractional ratio |

The shared failure mode is not "unknown verb" or "unknown sentence
shape." It is "the parser has no ontology of units." The current
parser asks "is `feet` a valid noun?" via `_canonical_unit` which
just pluralizes. The right question is "what *dimension* is `feet`,
and does `of cable` modify it as a substance qualifier?"

This is structurally different from the per-axis grammar treadmill
that produced four zero-lift ADRs (0122 / 0123 / 0123a / 0123b).
Vocabulary expansion is unbounded and adversarial; **units of
measurement form a finite, externally well-defined ontology**
(NIST SI tables for physical units; closed sets for currency, time,
English container nouns). A units pack is *semantic substrate the
parser consults*, not more grammar regex.

ADR-0126's candidate-graph topology is built to consume exactly
this kind of substrate — the round-trip filter already does
token-level grounding; adding a "matched_unit_token must resolve
to a known dimension in the pack" check is a natural extension.

Without ADR-0127 the ADR-0126 empirical result is uninformative:
0/50 reflects P2's deliberate minimum-viable scope, not the
architecture's capacity. The architecture's real verdict lives
behind the units pack.

---

## Decision

Add a `language_packs/data/en_units_v1/` ratified semantic pack and
extend the ADR-0126 candidate parser to consult it during candidate
emission. **No new operation kinds.** **No new ADR-0114a
obligations.** **No new exit gates beyond ADR-0126's** (`correct ≥
10/50, wrong == 0` on the train sample, this time with units pack
in scope).

### Pack content (`en_units_v1`) — EXHAUSTIVE SCOPE

Structure mirrors `en_arithmetic_v1`: `lexicon.jsonl` +
`manifest.json` + `glosses.jsonl` + `conversions.jsonl` + a
self-sealing `.mastery_report.json` ratification artifact.

**Dimension classes** (entry_id prefix `en-units-dim-`):

| Dimension | Canonical unit | Notes |
|-----------|---------------|-------|
| `count` | (dimensionless) | The no-unit dimension |
| `length` | foot | imperial + metric families |
| `time` | minute | seconds through millennia |
| `mass` | pound | imperial + metric |
| `money` | cent | with currency-symbol attachments |
| `temperature` | °F | affine scales (F/C/K/R) |
| `volume` | cup | cooking + liquid + dry |
| `area` | sq ft | **derived** = length × length |
| `speed` | mph | **derived** = length / time |
| `density` | lb/cu ft | **derived** = mass / volume |
| `frequency` | Hz | **derived** = 1 / time |
| `wage` | $/hour | **derived** = money / time |
| `unit_price` | $/item | **derived** = money / count |

Derived dimensions are encoded *compositionally* via a
`dimension_algebra.jsonl` table. The parser recognizes
"miles per hour" structurally as `length-unit + per +
time-unit`; it does NOT need a `mph` primitive. Reduces unit
combinatorics from O(unit²) to O(unit + connector).

**Unit lemmas** (entry_id prefix `en-units-unit-`) — exhaustive
for grade-school math word problems (~150 entries):

| Dimension | Lemmas |
|-----------|--------|
| length | inch/in, foot/ft, yard/yd, mile/mi, millimeter/mm, centimeter/cm, meter/m, kilometer/km |
| time | second/sec/s, minute/min, hour/hr/h, day, week, month, year/yr, decade, century, millennium |
| mass | ounce/oz, pound/lb, ton, gram/g, kilogram/kg, milligram/mg, metric_ton/tonne |
| volume | teaspoon/tsp, tablespoon/tbsp, cup, pint/pt, quart/qt, gallon/gal, milliliter/mL, liter/L |
| money | cent/¢, dollar/$, plus optional foreign: euro/€, pound_sterling/£, yen/¥, peso |
| temperature | degree/°, Fahrenheit/°F, Celsius/°C, Kelvin/K |
| area | sq_inch, sq_foot, sq_yard, sq_mile, sq_meter, sq_kilometer, acre, hectare |
| count | (open class — head-noun grammar; pack does not enumerate, but provides count-dimension stamp for any unmatched noun in countable position) |

Each unit carries `singular`, `plural`, `symbol`, `dimension`,
`is_canonical_for_dimension` (bool). Plural forms include the
irregulars: foot/feet, child/children (count), person/people
(count), mouse/mice (count), goose/geese (count),
fish/fish (count), sheep/sheep (count), deer/deer (count),
woman/women (count), man/men (count), leaf/leaves,
knife/knives, life/lives.

**Multi-word units** (entry_id prefix `en-units-multiword-`):

Structural composition rules (not lexicon enumeration):

- `square <length-unit>` → area (sq_ft, sq_meter, sq_mile, …)
- `cubic <length-unit>` → volume_derived
- `<length-unit> per <time-unit>` → speed
- `<money-unit> per <count-noun-or-unit>` → unit_price or wage
- `<mass-unit> per <volume-unit>` → density

The pack ships the *patterns*, not every concrete combination —
the parser composes them at recognition time.

**Container nouns** (entry_id prefix `en-units-container-`) —
closed set (~25):

`box`, `bag`, `pack`, `basket`, `batch`, `dozen`, `group`,
`set`, `case`, `pair`, `pile`, `stack`, `bunch`, `bundle`,
`carton`, `crate`, `jar`, `can`, `bottle`, `cup` (when
container, not volume-unit — context-disambiguated), `plate`,
`bowl`, `tray`, `sack`, `container`, `gross` (=144).

Each declares syntax `<count> <container> of <content>` and
optional `default_size` (only `dozen=12`, `pair=2`, `gross=144`,
others null).

**Rate connectors** (entry_id prefix `en-units-rate-`) — closed
set (~6):

`per`, `an`, `every`, `each`, `by`, `in` (as in "every 3 days").
Each declares the dimension-algebra template it participates in.

**Symbol/affix table** (entry_id prefix `en-units-symbol-`):

`$`, `¢`, `°`, `°F`, `°C`, `%`, `½`, `¼`, `¾`, `⅓`, `⅔`, `⅛`,
`⅜`, `⅝`, `⅞`. Each maps to its lexical lemma. Cross-linked to
`en_numerics_v1` (sibling pack, ADR-0128) for fraction symbols.

**Substance qualifiers** (entry_id prefix `en-units-substance-`):

Pattern `N <unit> of <substance>` (e.g., "1000 feet of cable").
The pack does NOT enumerate substances — that's open class. It
encodes the *structural rule* that any measure-dimension unit
admits an `of <NP>` substance tail, which the round-trip filter
treats as a discarded grounded modifier.

**Unit-conversion graph** (`conversions.jsonl`, separate file):

Each line declares a directed edge `(from_unit, to_unit, ratio)`
where `to_unit = ratio × from_unit`. The pack ratifies the
*connected* weighted graph per dimension. Examples:

```jsonl
{"edge_id":"en-units-conv-001","from":"inches","to":"feet","ratio":0.0833333333,"dimension":"length"}
{"edge_id":"en-units-conv-002","from":"feet","to":"inches","ratio":12,"dimension":"length"}
{"edge_id":"en-units-conv-003","from":"cents","to":"dollars","ratio":0.01,"dimension":"money"}
{"edge_id":"en-units-conv-004","from":"dollars","to":"cents","ratio":100,"dimension":"money"}
{"edge_id":"en-units-conv-005","from":"minutes","to":"hours","ratio":0.01666666667,"dimension":"time"}
{"edge_id":"en-units-conv-006","from":"hours","to":"days","ratio":0.04166666667,"dimension":"time"}
```

**Temperature edges carry an affine `offset` field** because
temperature conversion is not pure multiplication:
`°F = 1.8 × °C + 32`. Schema: `{"from","to","ratio","offset",
"dimension"}`. Multiplicative-only edges have `offset=0`.

The graph is **the conversion table as data**, not as code. The
solver consults it; the parser doesn't need to. Coverage target
is EXHAUSTIVE within each dimension's lemma set (~80 edges
total: every pair of in-pack units in the same dimension must be
reachable). Bounded by NIST SI tables (closed set); ratification
proves completeness — see invariants below.

### Why conversions matter

Without conversions, the pack solves only single-unit arithmetic
(`5 apples + 3 apples`). With conversions, it solves
within-dimension mixed-unit arithmetic — which is the majority
of real word problems:

| Without conversions | With conversions |
|--------------------|------------------|
| `5 feet + 8 inches = ?` (refused) | canonicalize to feet (or inches), add, emit |
| `$2 + 75¢ = ?` (refused) | canonicalize to cents (or dollars), add, emit |
| `2 hours 30 minutes` (refused) | canonicalize to minutes (or hours), normalize |

Solver-side responsibility (delegated to ADR-0127.5 below):
when an operation's operand has a unit in the same dimension as
the actor's last quantity but a different unit, the solver
canonicalizes via shortest path in the conversion graph before
performing arithmetic. The canonical_bytes of `SolutionTrace`
records which edges fired, preserving determinism and
replay-equality.

### Graph ratification invariants (`en_units_v1`-specific)

The pack ratification process validates *graph correctness*, not
just lexicon well-formedness:

1. **Round-trip identity** — for every edge `(A, B, r)`, there
   must exist an edge `(B, A, 1/r)` with `|round_trip_error| <
   1e-9`. Asymmetric tables are rejected at ratification.
2. **Per-dimension connectivity** — within each dimension, the
   subgraph induced by that dimension's units must be connected
   (every unit reachable from every other). Isolated unit
   lemmas are rejected.
3. **Path consistency** — for any two units A and C in the same
   dimension, all shortest paths from A to C must yield the
   same product of ratios within `1e-9`. Inconsistent paths
   (e.g., 12 in/ft × 3 ft/yd ≠ 1 yd/36 in) are rejected at
   ratification, not at runtime.
4. **Canonical unit per dimension** — each dimension declares
   one canonical unit (`feet` for length, `seconds` or
   `minutes` for time, `dollars` for money, etc.). All
   canonicalization routes through the canonical unit; this
   bounds the shortest-path computation to O(1) lookups.
5. **Exhaustive coverage gate** — every dimension's lemma set
   must produce a fully connected conversion subgraph. Adding
   a unit lemma without conversion edges (or with edges that
   don't connect to the canonical) is rejected at ratification.
   This prevents the inventory from silently fragmenting.
6. **NIST/ISO provenance** — every conversion ratio cites a
   source via `provenance_id` (NIST SP 811 for SI, ISO 4217 for
   currency, etc.). Unsourced ratios are rejected.
7. **Dimension algebra closure** — every derived-dimension entry
   (speed, density, wage, area) has both decomposed forms
   present (e.g., for `speed`: at least one length-unit and one
   time-unit are present in their respective dimensions).

These invariants live in `tests/test_adr_0127_pack_ratification.py`
and run at every pack-change PR — the conversion graph cannot
ship broken or incomplete.

### Parser integration

Three load-bearing changes to `generate/math_candidate_parser.py`
(no changes to legacy `math_parser.py`):

1. **`extract_initial_candidates` widens** to recognize three
   additional shapes when pack consultation confirms dimensional
   typing:
   - `<Entity> has N <pack-unit>` (with `of <substance>` tail
     discarded)
   - `<Entity> has N <pack-container> of <content>`
   - `There are N <pack-unit> [of <substance>]`

2. **New `extract_rate_declaration_candidates`** recognizes
   `<Entity> makes $N <rate-connector> <pack-time-unit>` as an
   `apply_rate` candidate (ADR-0122 shape; the pack supplies the
   dimensional check that today's narrow regex misses).

3. **Round-trip filter gains a dimensional check.** The existing
   `roundtrip_admissible` adds an optional `require_pack_typed_unit`
   parameter (default False to preserve P1 behavior). When True,
   `matched_unit_token` must resolve to a known unit lemma in
   `en_units_v1`. This is the wrong-answer firewall for unit
   hallucination: a parser that fires on `Sam buys 3 contemplations`
   would now fail because `contemplations` is not pack-typed.

4. **Solver gains a dimensional-canonicalization helper.** New
   module `generate/math_unit_conversion.py` exports
   `canonicalize_to_dimension_canonical(quantity, conversion_graph)
   -> (quantity_in_canonical_unit, [edges_fired])`. Operations whose
   operand unit differs from the actor's tracked unit (but shares
   dimension) get canonicalized before arithmetic. The fired-edges
   list joins `SolutionTrace.steps` so replay reproduces the
   conversion path byte-equal. Mixed-dimension operands
   (`apples + dollars`) remain a SolveError — units type the
   arithmetic.

### What ADR-0127 explicitly does NOT do

- Does NOT model fractional-of-prior-quantity phrasing
  (`3/4 of its temperature`). That's a separate compositional
  pattern, not a unit-ontology question.
- Does NOT model multi-step rate compositions
  (`overtime = base + 1/2 base`). That's solver-level.
- Does NOT add new operation kinds. ADR-0126 + 0122 cover the
  needed shapes (add, subtract, transfer, multiply, divide,
  apply_rate, compare_*). The pack just helps the parser
  *recognize* the operand inputs.
- Does NOT replace `_canonical_unit`. The pack lookup is
  *additive* — when the pack confirms a token, dimensional
  routing kicks in; when not, the legacy plural-canonicalization
  fallback remains.
- Does NOT touch the sealed holdout. Re-runs against the
  unsealed train sample only.

---

## Invariants preserved / added

| Invariant | Preserved or added | How |
|-----------|--------------------|-----|
| `wrong == 0` | Preserved | Pack-typed unit check is a *stricter* gate, never a looser one |
| `trace_hash` byte-equality | Preserved | Pack consultation is deterministic; same pack version → same lookup result |
| Pack-binding (ADR-0114a #10) | Reinforced | The parser now explicitly cites pack entry_ids in `SolutionTrace.provenance` for unit-typed candidates |
| Round-trip admissibility | Strengthened | When `require_pack_typed_unit=True`, hallucinated units fail to ground |
| `versor_condition(F) < 1e-6` | Untouched | No runtime field changes |
| Manifest checksum SHA-256 of bytes-on-disk | Required | Mastery report self-seals like `en_arithmetic_v1` |

## Exit criterion

**Same gate as ADR-0126 but with `en_units_v1` mounted:**

```
correct >= 10 / 50  on evals/gsm8k_math/train_sample/v1/cases.jsonl
wrong  == 0
```

**If passed:** run sealed holdout *once* and freeze the number in
ADR-0127-results. Architecture + units substrate jointly validated.

**If missed (Path-B trigger, now real):** the deterministic
parser-by-rule approach + units ontology + candidate-graph
topology is the *full* design we believed was right, and it still
doesn't move GSM8K. That is the empirical signal to demote GSM8K
and re-target the math expert promotion to a benchmark where
exact-recall and determinism are the discriminators.

---

## Alternatives considered

### A. Skip the units pack, just expand parser regex.
Rejected — this IS the per-axis grammar treadmill (4 zero-lift
ADRs). Adding patterns like `<Entity> has N \w+ of \w+` without
dimensional typing produces wrong candidates the round-trip
filter can't catch (any noun would ground; nothing rejects "5
contemplations of cable").

### B. Pull units from a third-party library (Pint, etc.).
Rejected — violates "no opaque dependencies in the runtime path."
A curated pack of ≤ 60 lemmas is auditable, version-pinnable,
ratifiable, and inspectable; an external library is none of those.

### C. Defer units, ship ADR-0126 with the honest 0/50 + open
question. Considered. Discarded because 0126's empirical result
is genuinely uninformative without the substrate it was designed
to consume. Shipping the architecture with a misleading "0 lift"
headline invites the wrong conclusion (Path B prematurely).

### D. Build the units pack but DON'T integrate it; ship as
inventory. Rejected — the pack must be load-bearing per CLAUDE.md
"prefer compact, curated packs" plus the project's general stance
against decoration without integration.

---

## Implementation plan (proposed sub-phases)

| Phase | Module | Description |
|-------|--------|-------------|
| 0127.1 | `language_packs/data/en_units_v1/` | Pack content: lexicon (dimensions + units + containers + rate connectors) + `conversions.jsonl` + manifest + glosses + mastery report |
| 0127.2 | `language_packs/loader.py` (or sibling) | Pack loader API: `lookup_unit(token) -> UnitEntry \| None`; `get_conversion_graph(dimension) -> ConversionGraph` |
| 0127.3 | `generate/math_roundtrip.py` | Optional `require_pack_typed_unit` parameter on `roundtrip_admissible` |
| 0127.4 | `generate/math_candidate_parser.py` | Three new initial-possession shapes + rate-declaration extractor, consulting the pack loader |
| 0127.5 | `generate/math_unit_conversion.py` (new) | `canonicalize_to_dimension_canonical(quantity, graph)`; shortest-path lookup + edges-fired provenance for `SolutionTrace.steps` |
| 0127.6 | `generate/math_solver.py` | Wire dimensional canonicalization into add/subtract/transfer/compare arithmetic; mixed-dimension operands → SolveError |
| 0127.7 | `evals/gsm8k_math/train_sample/v1/runner.py` | Re-run with units pack engaged; new `report.json` |
| 0127.8 | `tests/test_adr_0127_*.py` | Pack ratification (round-trip identity + connectivity + path consistency + canonical-unit-per-dimension) + parser integration + solver canonicalization + train-sample lift gate |

Regression gates (must remain green at every phase):
- `core test --suite smoke -q`
- `core test --suite math -q` (existing 714/714 + ADR-0126 74/74)
- `core test --suite packs -q` (new `en_units_v1` ratification entries)
- ADR-0126 P3+P4 tests (the candidate-graph machinery is unchanged)

## PR checklist (when proposing for merge)

```
What capability did this add?
  → Pack-typed unit recognition for the candidate-graph parser; the
    semantic substrate ADR-0126 was designed to consume.
What invariant proves the field remains valid?
  → Pack-typed unit check (new); wrong == 0 (preserved); manifest
    checksum SHA-256 of bytes-on-disk (required).
Which CLI suite/eval proves the lane?
  → smoke + math + packs + train_sample_runner (this is the
    re-measurement that decides Path B or not).
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Pack lookup is deterministic; unit ontology is bounded
    and curated; no learned scoring; ratified pack only.
If it touches user input, what trust boundary was enforced?
  → Pack file paths are validated via the existing safe_pack_id
    sanitiser (ADR-0051). Pack content is mastery-report-sealed.
```
