# Kernel Operationalization + Legacy Deprecation Brief (2026-06-18)

This brief is the next implementation handoff after PR #829 (`Kernel Substrate Tranche 1`) merged.

PR #829 created the substrate. The next work must make it operational and begin retiring legacy raw-text/local-parser habits.

## Current anchor

- PR #829 is merged.
- Merge commit: `58a94c8e4bcb5ac0bcb2f0c8de46012ef2d418be`.
- Tranche 1 added kernel facts, scalar/unit facades, ambiguity hazards, process frames, ProblemFrame IR, morphology labels, docs, and tests.
- Expected baseline remains `train_sample: 30 correct / 20 refused / 0 wrong`.
- Holdout safety target remains `holdout_dev wrong_ids: []`.

## Strategic intent

The substrate must become the preferred operational path:

```text
raw problem text
→ KernelFacts
→ ProblemFrame
→ contract-backed derivation organs
```

The old way should become legacy:

```text
raw problem text
→ local regex / local phrase parser inside one organ
→ one-off answer derivation
```

The goal is not to delete all legacy code immediately. The goal is to prevent new legacy and start migrating the load-bearing paths.

## Non-negotiable direction

Do not add another isolated benchmark organ.

Do not add another local raw-prose parser for one family.

Do not treat Kernel Substrate as optional helper utilities.

Every new capability path should first ask:

1. Can the fact be represented as a `KernelFact` / `SubstrateFact`?
2. Can the problem be represented as a `ProblemFrame`?
3. Can the organ consume the `ProblemFrame` instead of scraping prose?

## Workstream A — Legacy derivation audit

Create:

```text
docs/analysis/kernel-substrate-deprecation-audit-2026-06-18.md
```

Audit likely legacy sites:

```bash
git grep -n "re.compile" generate/derivation generate/math_candidate_graph.py generate/math_candidate_parser.py generate/math_completeness.py generate/math_roundtrip.py
git grep -n "half\|quarter\|third\|percent\|per\|each\|remaining\|altogether" generate/ tests/
git grep -n "case_id" generate/ evals/ tests/
```

Classify findings into:

- `current_runtime_dependency` — keep temporarily; must not be broken.
- `migrate_to_problemframe` — should be refactored to consume ProblemFrame facts.
- `wrap_with_substrate_adapter` — can be fed by substrate without full rewrite.
- `delete_after_migration` — one-off helper that should disappear after migration.
- `allowed_non_derivation_regex` — harmless test/doc/format regex.

The audit must distinguish old-but-still-serving code from new-path code. This is not a blame list; it is a migration map.

## Workstream B — No-new-legacy rule

Update agent/architecture guidance so future agents do not add more local raw-text organs.

Candidate files:

```text
CLAUDE.md
GROK.md
AGENTS.md
docs/architecture/kernel-knowledge-layer-v1.md
docs/runtime_contracts.md
```

Add a rule equivalent to:

```text
New derivation capabilities must consume KernelFacts / ProblemFrame facts where the substrate can represent the needed meaning. New raw-prose/local-regex parsing inside a derivation organ requires an explicit LEGACY_EXCEPTION note and a migration rationale.
```

Add a test if feasible:

```text
tests/test_kernel_no_new_legacy_derivation_surfaces.py
```

The test may use an allowlist of current legacy files. The purpose is to prevent accidental growth of legacy patterns while migrations proceed.

## Workstream C — ProblemFrame builder

Create:

```text
generate/problem_frame_builder.py
tests/test_problem_frame_builder.py
```

Goal:

```text
raw text
→ scalar candidates
→ unit candidates
→ ambiguity hazards
→ process frame candidates
→ candidate relations
→ ProblemFrame
```

The builder should use the #829 substrate modules:

- `language_packs.scalar_equivalence.extract_scalar_candidates`
- `language_packs.unit_dimensions`
- `language_packs.ambiguity_hazards`
- `generate.process_frames`
- `generate.kernel_facts`
- `generate.problem_frame`

Required builder behavior:

- deterministic output ordering
- exact source spans where available
- no answer derivation
- no case-id behavior
- hazards are preserved
- known process frames attach as candidates, not conclusions
- unsupported/ambiguous surfaces remain hazardous/refused, not guessed

Minimum test scenarios:

1. percent/part text produces scalar facts and hazards without solving.
2. transfer/give text produces transfer process-frame candidate without solving.
3. box/container text produces container process-frame candidate without solving.
4. travel/route text produces travel process-frame candidate without solving.
5. ambiguous `quarter` surfaces carry hazards.
6. unsupported scalar surfaces do not silently broaden ADR-0128.
7. exact spans slice the original text.
8. deterministic ordering across repeated runs.

## Workstream D — First migrated organ plan

Do not immediately rewrite all organs.

Select one organ for the first migration after the builder exists. Recommended candidates:

- `percent_partition`
- `nested_fraction_remainder_total`
- `fraction_decrease`
- `temporal_tariff`

Criteria:

- it currently performs local scalar/phrase parsing
- it can be fed by ProblemFrame facts
- it has existing train coverage
- it can preserve `wrong == 0`

The migration PR should show:

```text
before: raw-prose local parsing inside organ
after: ProblemFrame facts + explicit contract → derivation
```

## Workstream E — Morphology planner v2

Upgrade the substrate morphology classifier from #829 so it can plan work, not just label missing substrate.

Desired output fields:

- `case_id`
- `current_verdict`
- `recognized_scalars`
- `recognized_units`
- `recognized_process_frames`
- `recognized_hazards`
- `missing_substrate_labels`
- `legacy_parser_dependency`
- `recommended_migration_target`

This should help answer:

```text
Which legacy parser or missing substrate category blocks the most refused cases?
```

No automatic pack mutation.
No sealed artifact analysis.
No answer mining.

## Workstream F — Workbench / Logos inspection path

Once ProblemFrame construction exists, Workbench should expose it as an inspection surface.

Target surface:

```text
Kernel / ProblemFrame Inspector
```

Likely route placement:

- Evals route detail panel, or
- CORE-Logos route, if the inspection is positioned as substrate/meaning introspection.

It should show:

- raw text
- scalar candidates
- unit candidates
- process frames
- ambiguity hazards
- source spans
- provenance
- ProblemFrame JSON
- missing substrate labels

Do not add fake live data. If backend wiring does not exist yet, make the UI honestly documented or CLI-driven.

## Suggested branch for next PR

```text
feat/kernel-operationalization-deprecation
```

Suggested PR title:

```text
feat(kernel): operationalize ProblemFrame and deprecate legacy parsing
```

If too large, split naturally:

1. `docs(kernel): audit legacy parsing and add no-new-legacy rule`
2. `feat(kernel): build ProblemFrame from substrate facts`
3. `feat(kernel): add morphology planner v2`
4. `feat(workbench): inspect Kernel and ProblemFrame facts`

But do not split into micro-example PRs.

## Validation

Baseline checks:

```bash
git diff --check origin/main...HEAD
pytest tests/test_kernel_facts.py -q
pytest tests/test_problem_frame_skeleton.py -q
pytest tests/test_problem_frame_builder.py -q
pytest tests/test_gsm8k_morphology_missing_kernel_labels.py -q
pytest tests/test_adr_0128_numeric_formats.py -q
pytest tests/test_math_candidate_graph_xhigh_sprint13_lift.py -q
pytest tests/test_math_candidate_graph_sprint12_singleton_contract_lift.py -q
pytest tests/test_math_candidate_graph_sprint11_cluster_contract_lift.py -q
```

Capability stability:

```bash
uv run python - <<'PY'
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases, build_report
r = build_report(_load_cases(_CASES_PATH))
c = r["counts"]
print("train_sample:", c["correct"], c["refused"], c["wrong"])
print("wrong_ids:", sorted(x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"))
PY
```

Expected:

```text
train_sample: 30 20 0
wrong_ids: []
```

Holdout safety:

```bash
uv run python - <<'PY'
from evals.gsm8k_math.holdout_dev.v1.runner import build_report
r = build_report()
c = r["counts"]
print("holdout_dev:", c, "n=", r["n"])
print("wrong_ids:", [x["case_id"] for x in r["per_case"] if x["verdict"] == "wrong"])
PY
```

Expected:

```text
wrong_ids: []
```

If practical:

```bash
uv run python -m core.cli test --suite smoke -q
```

## Acceptance criteria

- #829 substrate is used by the new builder path.
- No new legacy parsing pattern is introduced without an explicit exception.
- Legacy parsing audit exists and names migration targets.
- ProblemFrame can be constructed from raw text without solving.
- Serving scores do not regress.
- No `report.json` rebaseline.
- No sealed artifact mutation.

## Review stance

The system should now converge on the fresh design:

```text
KernelFacts → ProblemFrame → contract-backed derivation
```

Legacy local parsing may remain temporarily, but it should no longer be treated as the normal design path.
