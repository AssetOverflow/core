# Workbench Capability Mastery — Implementation Plan

**Branch:** `feat/workbench-capability-mastery-reconcile`  
**Reconciles:** Draft PR #821 (`feat/workbench-capability-mastery`) onto current `origin/main` after #825  
**Status:** Reconciled UI surfaces — honest documented milestones, no fake live data

## 1. What #821 originally attempted

PR #821 (`feat/workbench-capability-mastery`) added first Workbench surfaces on the Evals route:

- `ExperienceFlywheelPanel` — practice-memory record inspection
- `CapabilityParadigmPanel` — derivation lift / Gate A* visibility
- Integration in `EvalsRoute.tsx`
- A draft `capability-mastery-implementation-plan.md`

The draft branch also **deleted large sections** of `workbench-ui/src/api/queries.ts` and `workbench-ui/src/types/api.ts`, introduced stale API assumptions (`runtime.capability_health`, `GET /flywheel`), and left `ExperienceFlywheelPanel` as an incomplete stub. Workbench-ui CI failed at build.

## 2. What changed since #821 was cut

Capability sprints 9–12 landed on main:

| PR | Sprint | Gates / organs | train_sample after |
|----|--------|----------------|-------------------:|
| #816 | Flywheel PR-1 | measurement-only adapter | (no serving change) |
| #817 | 6 | A2g duration_segment_total, A2h survey_rate_earnings | 14/36/0 |
| #818 | 7 | A2i round_trip_trip_duration, A2j giveaway_target_residual | 16/34/0 |
| #819 | 8 | A2k fraction_decrease, A2l percent_partition | 18/32/0 |
| #820 / #822 | 9 + hardening | A2m temporal_tariff, A2n affine_fraction_delta | 21/29/0 |
| #823 | 10 | A2o affine_comparative_inversion_total, A2p sequential_comparative_scale | 23/27/0 |
| #824 | 11 | A2q calendar_grounded_piecewise_daily_hours_total + ClusterContract | 24/26/0 |
| #825 | 12 | A2r nested_fraction_remainder_total, A2s loose_crayon_box_capacity | **26/24/0** |

Lookback analyses through Sprint 12 are committed under `docs/analysis/gsm8k-capability-paradigm-sprint*-lookback-2026-06-17.md`.

## 3. Current capability baseline

**Documented serving state (train_sample after #825):** `26 correct / 24 refused / 0 wrong`

This is shown in the UI as **documented** evidence from lookbacks — not as a live workbench API read.

## 4. Gate ladder (A2e → A2s)

| Gate | Organ | Sprint |
|------|-------|--------|
| A2e | goal_residual_question | Strike #814 |
| A2f | question_bound_product_aggregate | PR #815 |
| A2g | duration_segment_total | 6 (#817) |
| A2h | survey_rate_earnings | 6 (#817) |
| A2i | round_trip_trip_duration | 7 (#818) |
| A2j | giveaway_target_residual | 7 (#818) |
| A2k | fraction_decrease | 8 (#819) |
| A2l | percent_partition | 8 (#819) |
| A2m | temporal_tariff | 9 (#820) |
| A2n | affine_fraction_delta | 9 (#820) |
| A2o | affine_comparative_inversion_total | 10 (#823) |
| A2p | sequential_comparative_scale | 10 (#823) |
| A2q | calendar_grounded_piecewise_daily_hours_total | 11 (#824) |
| A2r | nested_fraction_remainder_total | 12 (#825) |
| A2s | loose_crayon_box_capacity | 12 (#825) |

## 5. Experience Flywheel is measurement-only

PR-1 (#816) adds `scripts/gsm8k_experience_flywheel.py` and `evals/gsm8k_math/train_sample/v1/experience.py`:

- Read-only report / sealed-practice inputs
- Explicit `--out` path only
- No serving mutation, no `report.json` writes, no pack/corpus mutation
- No auto-promotion into teaching or serving

## 6. ClusterContracts / singleton contracts

Sprint 11 ratified `calendar_grounded_piecewise_daily_hours_total` with:

- `piecewise_daily_hours_total` (Gate A2q)
- `calendar_grounding.py` — `civil_month_day_count_table` with `calendar_table:{month}` provenance
- Included case: `gsm8k-train-sample-v1-0013`

Sprint 12 extended the contract-first discipline with two singleton contracts:

- `nested_fraction_remainder_total` (Gate A2r) for `0004`, blocked against `0026` sealed-elimination confusers
- `loose_crayon_box_capacity` (Gate A2s) for `0007`, blocked against `0047` DCS/divisive confusers

See:

- `docs/analysis/gsm8k-capability-paradigm-sprint11-lookback-2026-06-17.md`
- `docs/analysis/gsm8k-capability-paradigm-sprint12-lookback-2026-06-17.md`

## 7. What is UI-live now

| Surface | Live? | Source |
|---------|-------|--------|
| Eval lane list | Yes | `GET /evals` |
| Eval lane run (read-only lanes) | Yes | `POST /evals/run` |
| Wrong-zero ledger from session run | Yes | `EvalRunResult` in session |
| Experience Flywheel records | **No** | Honest empty + CLI guidance |
| Capability paradigm milestones | **Documented static** | Committed lookback markdown |
| train_sample 26/24/0 headline | **Documented** | Lookbacks through #825, not live poll |

## 8. Honest empty states

- **Experience Flywheel:** states no workbench endpoint; points to `scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience.json`
- **Capability Paradigm:** labeled "Documented" badge; sprint cards cite lookback doc paths
- **No lane selected:** lane-selection guidance appears first; capability section follows as documented context

## 9. Backend endpoints still pending

- `GET /experience-flywheel` (or equivalent) — read-only compacted record feed from explicit artifact path or repo-local cache
- `GET /capability-paradigm` — optional; could mirror lookback JSON if generated deterministically
- Any endpoint must be read-only, drift-gated, and typed in `workbench/schemas.py` before client wiring

## 10. Explicitly not implemented

- Mutation endpoints for practice memory, serving, or reports
- Fake / seeded flywheel records in the UI
- `runtime.capability_health` footer theater
- Wholesale copy of #821 `types/api.ts` / `queries.ts` deletions
- Changes to `evals/gsm8k_math/train_sample/v1/report.json`
- Changes to sealed practice artifacts
- Live Sprint 12 metrics; Sprint 12 is documented from committed lookback evidence only

## 11. Invariants preserved

- ADR-0160 / ADR-0162 evidence-first, read-only Workbench posture
- No cognitive theater or invented mastery scores
- Route conformance unchanged (`EvalsRoute` empty/loading strings preserved for palette tests)
- `StatusFooter` unchanged on main (no fake capability_health)

## 12. Files in this reconciliation

| File | Action |
|------|--------|
| `workbench-ui/src/app/evals/capabilityMasteryData.ts` | New — documented milestones through #825 |
| `workbench-ui/src/app/evals/ExperienceFlywheelPanel.tsx` | New — honest empty state |
| `workbench-ui/src/app/evals/CapabilityParadigmPanel.tsx` | New — documented gate ladder |
| `workbench-ui/src/app/evals/CapabilityMasterySection.tsx` | New — composition |
| `workbench-ui/src/app/evals/EvalsRoute.tsx` | Integrate section; lane guidance remains first on landing |
| `workbench-ui/src/app/evals/capabilityMastery.test.tsx` | New tests |
| `docs/workbench/capability-mastery-implementation-plan.md` | This plan |

**Not ported from #821:** `queries.ts` / `types/api.ts` mass deletions, `StatusFooter` capability_health stub.

## 13. Next Workbench steps

1. Add read-only `GET /experience-flywheel` backed by explicit artifact path config (no default repo writes)
2. Optional deterministic `capability-paradigm.json` generator from lookback tables for API parity
3. Wire `ExperienceFlywheelPanel` to real records when endpoint exists; keep empty state as primary until then
4. Close #821 in favor of this PR after review

## 14. Verification

```bash
cd workbench-ui
pnpm install --frozen-lockfile
pnpm exec tsc -b
pnpm build
pnpm test -- --run src/app/evals
pnpm test -- --run src/app
```

From repo root:

```bash
uv run python -m core.cli test --suite smoke -q
```
