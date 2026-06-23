# Generalization Benchmark Policy

> **Rule:** These datasets are audit/test-only instruments.
> They must never be used as training material, capability patches,
> or fine-tuning targets for any CORE organ.

## Core constraints

| Constraint | Rule |
|---|---|
| Vendoring | Do **not** commit full dataset files to the repo |
| Sealed splits | Do **not** inspect sealed holdout examples during implementation |
| Patch prohibition | Do **not** create capability patches from benchmark item failures |
| Mutation prohibition | Do **not** apply `pack_policy_operator` mutations derived from benchmark errors |
| License gate | Verify license before caching; record in manifest `license` field |
| Checksum gate | Record `sha256` in manifest after download; re-verify before each eval run |

## Directory layout

```
.data/benchmarks/<dataset>/          # gitignored local cache (never committed)
evals/generalization/manifests/      # manifest YAMLs (committed)
evals/generalization/smoke/          # tiny public smoke fixtures (committed, PR-2)
evals/generalization/reports/        # aggregate score reports (committed, no raw items)
```

## Two-PR plan

- **PR-1 (this PR):** Policy + manifests for datasets 1–8
- **PR-2:** Fetch/verify scripts + smoke fixtures where licenses allow;
  manifests for datasets 9–12 (MathQA, MATH L1-2, ARC-DA, CommonsenseQA)

## Inspection policy

Aggregate score reports only. No raw items from sealed slices may appear
in commit diffs, eval logs, or any CORE source file.

## Mutation policy

`no_direct_pack_policy_operator_mutation` — benchmark failures are
diagnosis signals, not direct targets for operator rewrite.
