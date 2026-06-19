# Kernel Substrate Tranche 1 — Implementation Documentation

This document records the implementation of the Kernel Substrate Tranche 1 base-layer foundations in the `AssetOverflow/core` repository.

---

## 1. Purpose

The Kernel Substrate layer establishes a deterministic, reusable knowledge base of math facts, unit conversions, process triggers, and ambiguity hazard indicators. Previously, math derivation and candidate alignment organs (A2 organs) duplicated the parsing and validation logic of fundamental surfaces. By centralizing this base knowledge into a domain-agnostic substrate, future organs can consume unified intermediate representations (IR) and focus solely on structural planning and alignment.

## 2. Relationship to PR #828

PR #827 and PR #828 introduced the core semantic packs (`en_units_v1` and `en_numerics_v1`) along with the low-level loader modules (`loader.py` and `numerics_loader.py`). This tranche constructs thin, contract-backed facade layers on top of those low-level loaders. It refines the raw dictionary/list lookup structures into typed, immutable records and enforces strict verification gates without altering the underlying pack schemas.

## 3. Modules Added

Seven new Python modules have been introduced to establish the substrate layer:

1. `generate/kernel_facts.py` — Immutable, typed records for facts, hazard annotations, and provenance verification.
2. `language_packs/scalar_equivalence.py` — Facade over the numerics loader returning exact rational fractions for scalar surfaces.
3. `language_packs/unit_dimensions.py` — Facade over the units loader offering dimension compatibility checks and exact conversions.
4. `language_packs/ambiguity_hazards.py` — Registry of known ambiguous terms, their hazard categories, and required resolving contexts.
5. `generate/process_frames.py` — Declarative, non-arithmetic process frame schemas declaring semantic roles and triggers.
6. `generate/problem_frame.py` — Target IR skeleton (`ProblemFrame`) and builder class (`ProblemFrameBuilder`) for intermediate problem state representation.
7. `scripts/gsm8k_substrate_morphology.py` — Diagnostic script mapping refused problems to missing-substrate categories.

---

## 4. Scalar Equivalence Coverage

### Canonicalize vs grounded extraction

`language_packs/scalar_equivalence.py` exposes two complementary APIs:

- **`canonicalize_scalar(surface)`** — pack-level helper for detached surface strings.
  Returns a `ScalarCandidate` with canonical `Fraction`, source kind, entry id, and
  hazards.  Provenance and span fields remain `None` (no problem-text grounding).
- **`extract_scalar_candidates(text)`** — text-level extraction for ProblemFrame
  substrate facts.  Every emitted candidate carries:
  - `source_surface` — exact substring from the original text
  - `source_span` — `(start, end)` character offsets (Python slice semantics)
  - `provenance_kind = "problem_text"`
  - `canonical` — exact `Fraction`
  - `source` — scalar resolution kind (`fraction_word`, `decimal`, etc.)
  - `hazards` — ambiguity hazard IDs

Pack/world/derived values (`classify_dimension`, detached `canonicalize_scalar`)
do not masquerade as `problem_text`.  Multiple scalars are emitted in deterministic
left-to-right span order.  Unsupported forms (`.5`, `1 / 2`) are omitted from
extraction and flagged separately by the morphology atlas.

Exposed scalar surfaces via the facade:
- **Word forms:** `half`, `one half`, `one-half`, `third`, `one third`, `two thirds`, `quarter`, `one quarter`, `three quarters`.
- **Symbols:** Unicode symbols (`½`, `¼`, `¾`, `⅓`, `⅔`).
- **Mixed numbers / slash forms:** `1/2`, `3/4`, `1 1/2`.
- **Decimals:** `0.5` -> `Fraction(1, 2)`, `0.25` -> `Fraction(1, 4)`, `0.75` -> `Fraction(3, 4)` (canonical values are strictly exact rational fractions).
- **Percentages:** `50%` -> `Fraction(1, 2)`, `25%` -> `Fraction(1, 4)`, `75%` -> `Fraction(3, 4)`, `100%` -> `Fraction(1, 1)`.

---

## 5. Unit / Dimension Coverage

Exposed via `language_packs/unit_dimensions.py`:
- **Supported Families:** `count` (items), `money` (dollars, cents), `time` (seconds, minutes, hours, days, weeks), `length` (inches, feet, yards, miles).
- **Rate Dimensions:** wage (`money/time`), speed (`length/time`), unit price (`money/count`), frequency (`count/time`), density (`mass/volume`), items per container (`count/container`).
- **Compatibility:** Two dimensions are compatible if they match exactly, or if both are rate dimensions with compatible numerator and denominator components.
- **Conversion:** Exact conversions (e.g. feet to inches, dollars to cents) return exact rational ratios. Multi-hop conversions are not licensed in Tranche 1.

---

## 6. Kernel Fact / Provenance Model

Exposed via `generate/kernel_facts.py`:
- **Fact Records:** `GroundedScalar`, `GroundedUnit`, `CandidateRelation`, and the union wrapper `SubstrateFact`.
- **Provenance Verification:** Enforced in `__post_init__`:
  - `problem_text` provenance must carry exact character-offset `SourceSpan` records.
  - `derived` provenance must specify `input_fact_ids`.
  - Pack-backed facts (`kernel_unit`, `kernel_calendar`, `kernel_math`, `reviewed_pack`) must not carry source spans (masquerading as problem text is forbidden).
  - `speculative` facts can be registered in the IR but are explicitly blocked from serving consumption (`is_speculative` flag).

---

## 7. Ambiguity Hazard Model

Exposed via `language_packs/ambiguity_hazards.py`:
- **16 Required Surfaces:** `half`, `quarter`, `third`, `percent`, `percentage points`, `times`, `more than`, `less than`, `of`, `per`, `each`, `some`, `remaining`, `left`, `total`, `altogether`.
- **16 Required Categories:** `unbound_base_quantity`, `half_duration`, `quarter_coin`, `quarter_calendar_period`, `quarter_school_term`, `third_ordinal`, `ordinal_context`, `currency_context`, `temporal_context`, `percent_change_vs_percent_of`, `multiplicative_vs_occurrence_times`, `comparative_direction_ambiguity`, `indefinite_quantity`, `remainder_context_required`, `total_question_target_required`, `blocked_provenance_gap`.
- **Design:** Statically built at module load. Provides deterministic categories and hazard ID lists (`haz-0001` to `haz-0021`) indicating resolving signals (like `numeric_base_quantity` for `half`).

---

## 8. Process Frame Schemas

Exposed via `generate/process_frames.py`:
- Exposes 8 declarative frames: `transfer`, `consumption`, `transaction`, `labor_rate`, `travel`, `container_packing`, `partition`, and `comparison`.
- Each schema declares:
  - Trigger surfaces (e.g. `give` / `receive` for `transfer`).
  - Required and optional semantic roles (e.g. `buyer`, `seller`, `price` for `transaction`).
  - Target candidate relation type.
  - Known ambiguity hazards.
  - Explicit **not-licensed** constraints (e.g., executing arithmetic or solving is strictly forbidden).

---

## 9. ProblemFrame IR Skeleton

Exposed via `generate/problem_frame.py`:
- **IR Node:** `ProblemFrame` holds tuples of grounded scalars, facade candidates, units, actors, objects, relations, process frames, question targets, hazards, and provenance.
- **QuestionTarget:** Represents the question structure (`surface`, `target_type`, `unit`).
- **Builder:** `ProblemFrameBuilder` aggregates facts, automatically gathering nested hazards and provenance records to yield the immutable `ProblemFrame`.

---

## 10. Morphology / Flywheel Labels

Exposed via `scripts/gsm8k_substrate_morphology.py`:
- A diagnostic utility for labeling refused problems using 10 missing-substrate categories:
  `missing_scalar_equivalence`, `missing_unit_dimension`, `missing_process_frame`, `missing_part_whole_frame`, `missing_container_frame`, `missing_temporal_frame`, `missing_route_frame`, `missing_question_target`, `blocked_ambiguity_hazard`, `blocked_provenance_gap`.
- Exposes a deterministic function `classify_missing_substrate` and a CLI interface to batch-process cases.

### Corrected label semantics (post-patch)

`missing_*` labels now mean **substrate lookup failure**, not mere trigger-surface
presence.  For frame-backed categories, the classifier checks
`generate/process_frames.lookup_frame` before emitting a label:

- Text containing **give** does **not** receive `missing_process_frame` when the
  `transfer` frame is registered.
- Text containing **box** does **not** receive `missing_container_frame` when
  `container_packing` is registered.
- Similarly for **split** / `partition`, **drive** / `travel`, and other
  registered frame triggers.

Labels that remain trigger-based (not frame lookup):

- `missing_scalar_equivalence` — unsupported numeric surfaces (`.5`, `1 / 2`, etc.)
- `missing_unit_dimension` — unknown unit-like nouns after digits
- `missing_temporal_frame` — time surfaces with no registered process frame
- `missing_question_target`, `blocked_ambiguity_hazard`, `blocked_provenance_gap`

All labels are deterministic and sorted.

---

## 11. Serving Integration Status

All modules implemented in Tranche 1 are **substrate-only**. None of the new classes are imported or consumed inside hot-path candidate generation (`math_candidate_graph.py`), solver layers, or scoring pipelines. Serving behavior is fully preserved.

---

## 12. Unsupported Surfaces

Documented and explicitly refused surfaces in the scalar facade:
- `.5` (refused by number format matching to prevent ambiguous tokenization).
- `1 / 2` (refused due to spaces around the division slash).
- `a half` in multiplier contexts (forces refusal or flags an unbound base hazard).

---

## 13. Validation

### Post-patch verification (2026-06-18)

After grounding scalar spans and tightening morphology label semantics:

1. **`git diff --check origin/main...HEAD`** — no whitespace errors.
2. **Kernel substrate unit tests** — all pass:
   - `tests/test_kernel_facts.py`
   - `tests/test_language_packs_scalar_equivalence.py` (includes span/provenance extraction)
   - `tests/test_language_packs_unit_dimensions.py`
   - `tests/test_ambiguity_hazards.py`
   - `tests/test_process_frames.py`
   - `tests/test_problem_frame_skeleton.py`
   - `tests/test_gsm8k_morphology_missing_kernel_labels.py`
3. **Capability safety** — ADR-0128 numeric format and math candidate graph sprint tests pass.
4. **Evaluation scores (unchanged):**
   - `train_sample`: 30 correct / 20 refused / 0 wrong — `wrong_ids: []`
   - `holdout_dev`: 5 correct / 495 refused / 0 wrong — `wrong_ids: []`
5. **Smoke suite:** `core test --suite smoke -q` green.

### Initial tranche verification

Verification from the initial implementation:
1. **Unit tests:** 7 new test files containing 33 unit test cases verify all primitives, facade mappings, hazard lookups, and schemas. All 33 pass.
2. **Capability safety:** 227 existing tests pass, confirming zero regression.
3. **Evaluation scores:**
   - `train_sample` observed: 30 correct / 20 refused / 0 wrong (exact match to target).
   - `holdout_dev` observed: 5 correct / 495 refused / 0 wrong (exact match to target).
   - `wrong_ids: []` in both sets.

---

## 14. Next PR: First ProblemFrame-Consuming Organ

With the foundations locked, the subsequent step (Tranche 2) will write the first derivation organ consuming the `ProblemFrame` IR. This organ will transition raw token spans to `GroundedScalar` nodes, resolve ambiguity hazards using local context signals, and plan relations deterministically via the declarative process frame schemas.
