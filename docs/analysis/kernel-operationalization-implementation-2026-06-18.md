# Kernel Operationalization Implementation (2026-06-18)

Records the operationalization pass after PR #829 (Kernel Substrate Tranche 1).

---

## 1. Purpose

Make the #829 kernel substrate the **preferred operational path**:

```text
raw problem text → KernelFacts → ProblemFrame → contract-backed derivation organs
```

Begin retiring legacy `raw text → local regex organ → one-off answer` habits without
breaking serving (`train_sample: 30 / 20 / 0`, `wrong_ids: []`).

---

## 2. Relationship to #829

PR #829 (`58a94c8e`) added:

- `generate/kernel_facts.py`
- `language_packs/scalar_equivalence.py`
- `language_packs/unit_dimensions.py`
- `language_packs/ambiguity_hazards.py`
- `generate/process_frames.py`
- `generate/problem_frame.py` (IR skeleton)
- `scripts/gsm8k_substrate_morphology.py` (v1 labels)

This PR **operationalizes** those modules via `build_problem_frame`, adds deprecation
audit + no-new-legacy guardrails, and upgrades morphology to planner v2. No serving
organ rewrite in this PR.

---

## 3. Legacy audit summary

See `docs/analysis/kernel-substrate-deprecation-audit-2026-06-18.md`.

Key findings:

- **Shared debt:** `generate/derivation/extract.py` fans out to most organs.
- **Serving path (keep):** `math_candidate_parser.py`, `math_candidate_graph.py`.
- **First migration targets:** `percent_partition`, `nested_fraction_remainder_total`, `fraction_decrease`, `temporal_tariff`.
- **Recommended first organ:** `percent_partition`.

---

## 4. No-new-legacy rule

Added to agent/architecture guidance:

> New derivation capabilities must consume KernelFacts / ProblemFrame facts where the
> substrate can represent the needed meaning. New raw-prose/local-regex parsing inside a
> derivation organ requires an explicit `LEGACY_EXCEPTION` note and a migration rationale.

**Locations:**

- `AGENTS.md`
- `GROK.md`
- `CLAUDE.md`
- `docs/architecture/kernel-knowledge-layer-v1.md`
- `docs/runtime_contracts.md`

**Guard test:** `tests/test_kernel_no_new_legacy_derivation_surfaces.py`

---

## 5. ProblemFrame builder behavior

**Module:** `generate/problem_frame_builder.py`

**Entry point:** `build_problem_frame(problem_text: str) -> ProblemFrame`

Pipeline:

1. `extract_scalar_candidates` → scalar facts with exact spans (ordinal contexts like `third place` refused as fractions)
2. Unit token scan + `classify_dimension` → `GroundedUnit` with `problem_text` spans
3. `ambiguity_hazards` registry scan (+ `%` → percent hazards)
4. `process_frames` trigger scan → candidate frames (not conclusions)
5. `CandidateRelation` per matched process frame
6. Optional `QuestionTarget` from `how many` / `how much` / `?`

**Non-goals enforced:** no answer derivation, no case-id behavior, no ADR-0128 broadening
for unsupported surfaces (`.5`, `1 / 2`).

**Tests:** `tests/test_problem_frame_builder.py` (8 scenarios from brief)

---

## 6. Morphology planner v2 behavior

**Module:** `scripts/gsm8k_substrate_morphology.py`

**New API:** `plan_substrate_case(...)`, `recommend_migration_target(...)`

**CLI:** `--planner` emits v2 records; optional `--verdicts` attaches serving verdicts.

Output fields:

| Field | Source |
|---|---|
| `case_id` | caller / cases JSONL |
| `current_verdict` | optional report JSON |
| `recognized_scalars` | `build_problem_frame` |
| `recognized_units` | `build_problem_frame` |
| `recognized_process_frames` | `build_problem_frame` |
| `recognized_hazards` | `build_problem_frame` |
| `missing_substrate_labels` | `classify_missing_substrate` (v1) |
| `legacy_parser_dependency` | heuristic organ/module map |
| `recommended_migration_target` | organ or `substrate:*` extension |

No pack mutation, no sealed artifact analysis, no answer mining, no report rebaseline.

---

## 7. First organ migration recommendation

**Target:** `generate/derivation/percent_partition.py`

See audit doc § "Recommended first migration: percent_partition".

---

## 8. Serving integration status

| Surface | Status |
|---|---|
| `build_problem_frame` | **Available** — inspection/diagnostics/tests only |
| Morphology planner v2 | **Available** — CLI diagnostics |
| Serving answer admission from ProblemFrame | **Not wired** — intentional |
| `report.json` | **Unchanged** |
| Sealed artifacts | **Unchanged** |
| Train/holdout scores | **Unchanged** (validated below) |

---

## 9. Validation

```bash
git diff --check origin/main...HEAD
pytest tests/test_kernel_facts.py -q
pytest tests/test_problem_frame_skeleton.py -q
pytest tests/test_problem_frame_builder.py -q
pytest tests/test_gsm8k_morphology_missing_kernel_labels.py -q
pytest tests/test_kernel_no_new_legacy_derivation_surfaces.py -q
pytest tests/test_adr_0128_numeric_formats.py -q
pytest tests/test_math_candidate_graph_xhigh_sprint13_lift.py -q
pytest tests/test_math_candidate_graph_sprint12_singleton_contract_lift.py -q
pytest tests/test_math_candidate_graph_sprint11_cluster_contract_lift.py -q
```

Capability stability (expected `train_sample: 30 20 0`, `wrong_ids: []`):

```bash
uv run python - <<'PY'
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases, build_report
r = build_report(_load_cases(_CASES_PATH))
c = r["counts"]
print("train_sample:", c["correct"], c["refused"], c["wrong"])
print("wrong_ids:", sorted(x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"))
PY
```

Holdout safety (expected `wrong_ids: []`):

```bash
uv run python - <<'PY'
from evals.gsm8k_math.holdout_dev.v1.runner import build_report
r = build_report()
print("wrong_ids:", [x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"])
PY
```

---

## 10. Next PR recommendation

**`feat(kernel): migrate percent_partition to ProblemFrame`**

- Consume `build_problem_frame` facts inside `percent_partition`
- Keep verifier gate and `wrong == 0`
- No `report.json` rebaseline unless ratified
- Remove redundant local percent regex only after parity tests pass