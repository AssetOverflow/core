# Kernel Substrate Legacy Deprecation Audit (2026-06-18)

Migration map for retiring raw-prose / local-regex derivation habits after PR #829
(Kernel Substrate Tranche 1). This is not a blame list — it classifies what still
serves, what should migrate, and what can be deleted after migration.

## Audit method

Searches run on `origin/main` at merge `58a94c8e` plus operationalization branch
additions:

```bash
git grep -n "re.compile" generate/derivation generate/math_candidate_graph.py \
  generate/math_candidate_parser.py generate/math_completeness.py generate/math_roundtrip.py
git grep -n "half\|quarter\|third\|percent\|per\|each\|remaining\|altogether" generate/ tests/
git grep -n "case_id" generate/ evals/ tests/
```

## Classification legend

| Class | Meaning |
|---|---|
| `current_runtime_dependency` | Still on the serving path; do not break during migration |
| `migrate_to_problemframe` | Should consume `ProblemFrame` / `KernelFacts` instead of scraping prose |
| `wrap_with_substrate_adapter` | Can be fed by substrate facades without full organ rewrite yet |
| `delete_after_migration` | One-off helper that should disappear once ProblemFrame path owns the surface |
| `allowed_non_derivation_regex` | Harmless test/doc/format regex outside derivation admission |

---

## Shared legacy substrate (highest leverage)

| File | Class | Notes |
|---|---|---|
| `generate/derivation/extract.py` | `migrate_to_problemframe` | Central quantity/word-qty regex (`_HALF_OF_RE`, `_FRACTION_OF_RE`, `_WORD_QTY_RE`). Every organ importing `extract_quantities` inherits this debt. |
| `generate/derivation/clauses.py` | `wrap_with_substrate_adapter` | Sentence split regex only; keep until clause segmentation moves behind a substrate contract. |
| `generate/derivation/comparatives.py` | `migrate_to_problemframe` | Local comparative scalar extraction (`half`, `times`, `more than`). |
| `generate/math_candidate_parser.py` | `current_runtime_dependency` | 47 regex sites; recognizer/candidate-graph serving path. Migrate incrementally via ProblemFrame inspection, not big-bang delete. |
| `generate/math_candidate_graph.py` | `current_runtime_dependency` | Organ dispatch hub; must keep until each organ migrates. |
| `generate/math_roundtrip.py` | `current_runtime_dependency` | Tokenization helper used by organs and verifier. |
| `generate/math_completeness.py` | `wrap_with_substrate_adapter` | Completeness checks; not a prose parser but coupled to legacy graph shape. |

---

## First-wave organ migration candidates

| Organ | Class | Local parsing debt | ProblemFrame feed |
|---|---|---|---|
| `generate/derivation/percent_partition.py` | `migrate_to_problemframe` | `_PERCENT_OF_GROUP_RE`, `_FRACTION_RE`, half-split phrase scan | `extract_scalar_candidates`, partition/consumption process frames, percent hazards |
| `generate/derivation/nested_fraction_remainder_total.py` | `migrate_to_problemframe` | `_OUTER_HALF_RE`, `_INNER_QUARTER_RE`, morning/afternoon regex | partition frame + grounded scalars + remainder hazards |
| `generate/derivation/fraction_decrease.py` | `migrate_to_problemframe` | `_DECREASE_TO_FRACTION_RE`, extra-fraction scan | scalar candidates + consumption/partition frames |
| `generate/derivation/temporal_tariff.py` | `migrate_to_problemframe` | hourly rate / threshold shift regex | labor_rate frame + unit dimensions (time/money) |

All four have train-sample coverage, perform local scalar/phrase parsing today, can be
fed by `build_problem_frame`, and can preserve `wrong == 0` when migrated under
contract-backed admission.

### Recommended first migration: `percent_partition`

**Before**

```text
raw-prose local parsing inside organ
  → _PERCENT_OF_GROUP_RE / half-split phrase heuristics
  → extract_quantities + comparative_step
  → answer derivation
```

**After (next PR)**

```text
build_problem_frame(problem_text)
  → grounded scalars (50%, half)
  → partition + consumption process-frame candidates
  → percent / remainder hazards preserved
  → explicit percent_partition contract consumes ProblemFrame facts
  → answer derivation (unchanged verifier gate)
```

**Why first:** smallest surface area among the four candidates, clear scalar/frame
coverage in substrate, existing train coverage, and morphology planner v2 already
routes half+percent split problems to this organ.

---

## Other derivation organs (deferred)

| File | Class | Notes |
|---|---|---|
| `generate/derivation/affine_fraction_delta.py` | `migrate_to_problemframe` | Fraction decrease/increase affine cues |
| `generate/derivation/piecewise_daily_hours_total.py` | `migrate_to_problemframe` | Calendar + halfway-month local tables |
| `generate/derivation/loose_crayon_box_capacity.py` | `migrate_to_problemframe` | Container/box regex family |
| `generate/derivation/r1_reconstruction.py` | `current_runtime_dependency` | Broad fact-reconstruction regex suite |
| `generate/derivation/sequential_comparative_scale.py` | `migrate_to_problemframe` | Reader/scale regex |
| `generate/derivation/round_trip_trip_duration.py` | `migrate_to_problemframe` | Travel fraction cues |
| `generate/derivation/bounded_rate_projection.py` | `migrate_to_problemframe` | Percent projection regex |
| `generate/derivation/calendar_grounding.py` | `wrap_with_substrate_adapter` | Month-name regex pending `kernel_calendar` pack |
| `generate/derivation/state/bind.py` | `delete_after_migration` | Word token regex subsumed by substrate spans |
| `generate/derivation/state/source.py` | `delete_after_migration` | Conjunction split regex |

---

## New substrate path (target design)

| File | Class | Notes |
|---|---|---|
| `generate/problem_frame_builder.py` | **target path** | `build_problem_frame` — substrate-backed, no solving |
| `language_packs/scalar_equivalence.py` | **target path** | ADR-0128 facade; `extract_scalar_candidates` |
| `language_packs/unit_dimensions.py` | **target path** | ADR-0127 facade |
| `language_packs/ambiguity_hazards.py` | **target path** | Hazard registry |
| `generate/process_frames.py` | **target path** | Declarative process-frame candidates |
| `generate/kernel_facts.py` | **target path** | Typed fact/provenance model |
| `generate/problem_frame.py` | **target path** | ProblemFrame IR skeleton |
| `scripts/gsm8k_substrate_morphology.py` | **target path** | Planner v2 diagnostics |

---

## Phrase-surface grep summary (`generate/`)

Surfaces like `half`, `quarter`, `percent`, `remaining` appear in:

- **Substrate (keep):** `scalar_equivalence.py`, `ambiguity_hazards.py`, `process_frames.py`, `problem_frame_builder.py`
- **Legacy organs (migrate):** `derivation/extract.py`, `percent_partition.py`, `nested_fraction_remainder_total.py`, `fraction_decrease.py`, `comparatives.py`, and sprint lift organs
- **Serving graph (keep temporarily):** `math_candidate_graph.py`, `math_candidate_parser.py`
- **Non-derivation (allowed):** `process_frames.py` trigger tables, tests, docs

---

## `case_id` usage

| Area | Class | Notes |
|---|---|---|
| `evals/gsm8k_math/**` | `allowed_non_derivation_regex` | Case identifiers for measurement harnesses only |
| `tests/test_math_candidate_graph_*` | `allowed_non_derivation_regex` | Fixture pinning by case_id |
| `generate/derivation/**` | **none found** | Organs do not hardcode case_id (good) |
| `generate/problem_frame_builder.py` | **none** | Builder explicitly case-agnostic |

---

## Guardrails added in this PR

- **No-new-legacy rule** in `AGENTS.md`, `GROK.md`, `CLAUDE.md`, `docs/architecture/kernel-knowledge-layer-v1.md`, `docs/runtime_contracts.md`
- **`tests/test_kernel_no_new_legacy_derivation_surfaces.py`** — allowlisted legacy regex files; new regex in derivation paths requires `LEGACY_EXCEPTION`

---

## Next PR recommendation

Migrate **`percent_partition`** to consume `ProblemFrame` facts while keeping the
existing verifier gate and `wrong == 0` invariant. Do not change `report.json` or
sealed artifacts in the migration PR unless a ratified score change is intended.