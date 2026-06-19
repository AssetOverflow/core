# Kernel Knowledge Inventory — Repo Evidence (2026-06-18)

This document maps the locations in the CORE codebase where fundamental knowledge, conversions, scalar equivalents, and domain boundaries are handled locally or duplicated.

---

## 1. Empirical Starting Point (PR-0 Baseline)

As of PR-0, the baseline scoring metrics after #827 are:
- **`train_sample`:** 30 correct, 20 refused, 0 wrong (30/20/0)
- **`holdout_dev`:** 5 correct, 495 refused, 0 wrong (5/495/0)

> [!IMPORTANT]
> This PR is documentation-only and does not change these baseline numbers.

---

## 2. Files Inspected

The following key parts of the repository were analyzed:
- `language_packs/numerics_loader.py`
- `language_packs/loader.py`
- `scripts/generate_en_numerics_v1.py`
- `language_packs/data/en_numerics_v1/manifest.json`, `lexicon.jsonl`
- `language_packs/data/en_units_v1/manifest.json`, `lexicon.jsonl`, `conversions.jsonl`
- `generate/derivation/calendar_grounding.py`
- `generate/derivation/piecewise_daily_hours_total.py`
- `generate/derivation/nested_fraction_remainder_total.py`
- `generate/derivation/percent_partition.py`
- `generate/derivation/temporal_tariff.py`
- `generate/derivation/comparatives.py`
- `generate/derivation/extract.py`
- `generate/math_parser.py`
- `generate/math_roundtrip.py`
- `tests/test_math_candidate_graph_xhigh_sprint13_lift.py`
- `docs/analysis/gsm8k-xhigh-capability-sprint13-lookback-2026-06-18.md`

---

## 3. Existing Numeric/Fraction/Percent Handling

- **ADR-0128 (`en_numerics_v1`):** Establishes the static lookup mappings for numbers (cardinals/ordinals), fractions, multipliers, and format regexes (e.g., matching decimals or slash-fractions).
- **`generate/derivation/extract.py`:** Locally implements regexes for extracting fractions like `_HALF_OF_RE` and `_FRACTION_OF_RE`. It interprets these values using custom functions to map "half" to `0.5` rather than reading from `en_numerics_v1`.
- **`generate/math_parser.py`:** Contains custom comparative parser slots such as "half as many apples" or "half as much", separating them from other numbers.

## 4. Existing Unit/Dimension Handling

- **ADR-0127 (`en_units_v1`):** Standardizes dimension classes and unit conversions.
- **`generate/binding_graph/units.py`:** Employs static unit structures for dimensional checks.
- **`generate/math_candidate_parser.py`:** Widens parsing parameters dynamically to support trailing prepositions in unit extraction, rather than using structured lookups.

## 5. Existing Provenance/Source-Token Handling

- **`generate/derivation/calendar_grounding.py`:** Implements `MonthGrounding`, producing a provenance identifier of `calendar_table:month_name`.
- **`generate/derivation/state/provenance.py`:** Contains `provenance` validity verifiers that validate whether operands are bound to character positions in problem text.

## 6. Existing Hazard/Refusal Handling

- **`generate/derivation/calendar_grounding.py`:** Explicitly blocks February lookups due to leap year ambiguities.
- **`generate/derivation/piecewise_daily_hours_total.py`:** Checks if month lengths are even to license a "halfway" split.
- **`generate/derivation/percent_partition.py`:** Blocks and refuses ungrounded percentages or indefinite quantifiers (like "some").

---

## 7. Repeated Local Logic in Derivation Organs

Multiple derivation organs independently handle scalar scalars (like "half" and "1/2"), months of the year, rates, or comparatives. They use ad hoc matching regexes and mapping dictionaries, leading to severe code duplication and validation gaps.

---

## 8. Places Where Scalar Equivalence is Duplicated

- `generate/derivation/closed_reference_affine_aggregate.py` maps `"half"` to `0.5` for basic scaling, but treats the composite comparative contexts separately.
- `generate/derivation/nested_fraction_remainder_total.py` uses local regexes matching `half of the...` and inverse scalar scaling.
- `generate/derivation/percent_partition.py` uses local regex checks for `"half"`.
- `generate/derivation/temporal_tariff.py` parses `"half"` and `"1/2"` locally for overtime rate multipliers.

## 9. Places Where Unit Logic is Duplicated

- `generate/derivation/survey_rate_earnings.py` and `bounded_rate_projection.py` parse unit scales and dimensions ad hoc.
- `generate/math_candidate_parser.py` repeats checking of plurals/singulars for nouns and measurements.

## 10. Places Where Actor/Target Binding is Duplicated

- `generate/derivation/nested_fraction_remainder_total.py` parses actor-camp target bindings locally.
- `generate/derivation/piecewise_daily_hours_total.py` binds hours to specific actors in schedule lines.

## 11. Places Where Process-Frame Logic is Duplicated

- `generate/derivation/survey_rate_earnings.py`, `temporal_tariff.py`, and `piecewise_daily_hours_total.py` each independently define the rate-multiplication process (rate $\times$ hours $\times$ days) and overtime rules.

---

## 12. Existing Pack Machinery That Should Be Reused

- **`language_packs/numerics_loader.py`:** The `lookup_cardinal`, `lookup_fraction`, and `match_number_format` methods are already fully functional and will be imported.
- **`language_packs/loader.py`:** The units registry (`_UNITS_MAP` and `_DIMENSIONS_MAP`) and dimensional conversions graph will be utilized.

---

## 13. Gaps

- **ProblemFrame Integration:** There is currently no standardized ProblemFrame representation; organs consume raw text or candidate graph outputs directly.
- **Transitive Hazards:** Relational transitivity (`greater_than`, `before_event`) is implemented on the solver side rather than being checked at the boundary.

## 14. Risks

- **Silent Overruns:** Without unified dimension matching, organs might combine incompatible measurements (e.g., adding dollars and items) when solving.
- **Adversarial Overfitting:** Local parsers in organs are tuned to train samples; small text variations cause them to fail or misalign.

---

## 15. Recommended PR Sequence

1. **PR-0:** Documentation & Architecture Inventory (This PR).
2. **PR-1:** Refactor `language_packs` to combine numerics and units loaders.
3. **PR-2:** ScalarEquivalence facade over `en_numerics_v1`.
4. **PR-3:** Refactor `percent_partition.py` and `nested_fraction_remainder_total.py` to use the facade.

---

## Tables

### Table A — Repeated Scalar Logic

| File | Surface Handled | Canonical Meaning | Local Hazards | Should Move to Facade? |
|---|---|---|---|---|
| `generate/derivation/closed_reference_affine_aggregate.py` | `"half"` | `0.5` | `unbound_base` | Yes |
| `generate/derivation/nested_fraction_remainder_total.py` | `"half"` | `0.5` | `unbound_whole` | Yes |
| `generate/derivation/percent_partition.py` | `"half"` | `0.5` | `percent_vs_fraction` | Yes |
| `generate/derivation/temporal_tariff.py` | `"half"`, `"1/2"` | `0.5` | `double_overtime` | Yes |

*Note: The surface "half" corresponds to a scalar value of $0.5$. Relational comparatives such as "one-and-a-half" or "half-again" are treated as distinct $1.5$-style scalar relations.*

### Table B — Repeated Unit/Dimension Logic

| File | Unit Family | Conversion/Check | Local Hazards | Should Move to Unit Pack? |
|---|---|---|---|---|
| `generate/derivation/calendar_grounding.py` | `time.month` | Month day-count mapping | `leap_year` | Yes |
| `generate/derivation/survey_rate_earnings.py` | `money` | Currency formatting | `unsupported_currency` | Yes |
| `generate/derivation/bounded_rate_projection.py` | `speed` | Distance per time conversions | `ratio_inversion` | Yes |

### Table C — Repeated Process/Relation Logic

| File | Process Frame | Verbs/Surfaces | Relation Emitted | Hazards | Candidate Pack |
|---|---|---|---|---|---|
| `generate/derivation/temporal_tariff.py` | `labor` | `"works"`, `"paid"` | `wage_earned` | `overtime_tariff` | `process_frames` |
| `generate/derivation/nested_fraction_remainder_total.py` | `partition` | `"going to"`, `"rest"` | `subset` | `unbound_complement` | `part_whole` |
| `generate/derivation/survey_rate_earnings.py` | `labor` | `"makes"`, `"earns"` | `earnings` | `compound_rates` | `process_frames` |

### Table D — Provenance Risks

| File | Pattern | Risk | Recommended Provenance |
|---|---|---|---|
| `generate/derivation/calendar_grounding.py` | `calendar_table:{month}` | Fabricating world facts without source | `kernel_calendar` (explicit calendar table entry) |
| `generate/derivation/nested_fraction_remainder_total.py` | `"half"` | Lost token-span link | `problem_text` (exact span in narrative) |
| `generate/derivation/temporal_tariff.py` | `"1/2"` | Fabricated multiplier | `problem_text` (exact span in narrative) |

### Table E — Ambiguity Hazards

| Surface | Possible Meanings | Safe Contexts | Refusal Contexts | Candidate Pack |
|---|---|---|---|---|
| `"quarter"` | `0.25` / coin / school term | Explicit numeric math | Currency mix-ups / temporal splits | `ambiguity_hazards` |
| `"third"` | `1/3` / position | Explicit fraction | Calendar positioning / rank orders | `ambiguity_hazards` |
| `"half"` | `0.5` / time split | Simple scaling | Half an hour temporal conversions | `ambiguity_hazards` |
| `"some"` | quantity > 0 | None (indefinite) | All math operations | `ambiguity_hazards` |
