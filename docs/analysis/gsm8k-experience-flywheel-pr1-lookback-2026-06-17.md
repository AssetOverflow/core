# GSM8K Experience Flywheel PR-1 — Lookback (2026-06-17)

## 1. Problem statement

Capability Paradigm Sprint 5 proved that sealed practice/scout evidence can discover
reusable reasoning organs before serving promotion (10/40/0 → 12/38/0).  The next
layer must make that loop **systematic and programmatic** without saving garbage,
bloating memory, or letting SPECULATIVE practice artifacts masquerade as reviewed
knowledge.

PR-1 adds a bounded, deterministic experience artifact layer — not serving promotion,
not corpus mutation, not auto-accept.

## 2. Trust boundary summary

| Boundary | PR-1 behavior |
|----------|---------------|
| Serving path | Unchanged; wrong=0 preserved |
| report.json | Read-only; mtime tests prove no write |
| Sealed practice artifacts | Unchanged |
| Teaching corpus / packs | No mutation |
| DiscoveryCandidate / proposals | No auto-emission; bridge documented for PR-2 |
| Contemplation findings | Remain SPECULATIVE; experience records are parallel diagnostic memory |
| Output | Explicit `--out` only; never default-writes into repo |

Experience records are **structured evidence for operators**, not active memory.
Promotion into serving or teaching still requires reviewed gates.

## 3. Artifact schema

Module: `evals/gsm8k_math/train_sample/v1/experience.py`

**ExperienceRecord** (pre-compaction):
- `record_id` — SHA-256 of load-bearing fields
- `case_id`, `serving_status`, `sealed_status`, `gold_answer`, `sealed_answer`
- `serving_refusal_family`, `sealed_failure_family`, `candidate_family`
- `first_missing_primitive`, `arithmetic_chain_signature`
- `positive_evidence_refs`, `negative_evidence_refs`, `hazard_tags`
- `recommended_action`, `promotion_status`
- `source_run_id`, `source_report_hash`, `schema_version`

**CompactedExperienceRecord** (case-level output):
- Dedupe key over `(case_id, candidate_family, arithmetic_chain_signature, hazard_tags)`
- `count`, `first_seen_run_id`, `last_seen_run_id`, `status_transitions`

**Experience report** adds:
- `family_summaries` — per-family lift/block counts and recommended next action
- `hazard_summaries` — hazard tag → case_ids
- `promotion_candidates` — families marked candidate or blocked_by_wrong_risk
- `experience_report_hash` — self-sealing digest

CLI: `scripts/gsm8k_experience_flywheel.py`

## 4. Retention gates

**Keep:**
1. `lift_refused_to_correct` (refused→correct delta)
2. `elimination_refused_to_wrong` and sealed-wrong surfaces
3. Serving-wrong (if any)
4. `already_served` correct (regression preservation set)
5. `serving_conservative_win` (conservative boundary evidence)
6. High-frequency `joint_refusal` clusters (≥3 cases share failure_family)

**Drop:**
1. Low-signal isolated `joint_refusal` (no cluster, no new family info)
2. Duplicate signatures within a run (compacted)
3. Raw problem text / full traces (never stored)

## 5. Compaction logic

Within a run and across runs (`--prior`):
- Group by dedupe key
- Collapse to one `CompactedExperienceRecord` with `count`, seen run IDs, status transitions
- Latest serving/sealed status wins for the compacted row

## 6. Promotion candidate rules

A family is **`candidate`** only when:
- At least one refused_to_correct record exists in the family group
- `first_missing_primitive` and `candidate_family` are explicit
- No `blocked_by_wrong_risk` records in the same family group
- No unblocked `unbound_target` hazard on lift rows

## 7. Blocked-by-wrong-risk rules

Marked **`blocked_by_wrong_risk`** when:
- `elimination_refused_to_wrong` or sealed_status=wrong
- Serving-wrong delta kinds
- Hazard tags include `sealed_elimination`, `wrong_risk`, `serving_wrong_boundary`
- Family summary has both lift candidates and blocked records

## 8. Determinism proof

- `record_id`, `source_run_id`, `source_report_hash`, `experience_report_hash` are SHA-256 over canonical JSON (`formation.hashing`)
- No clock, no randomness, no floats in hashed payloads
- `test_live_experience_report_determinism` — identical reports on repeated live runs
- `test_canonical_json_roundtrip` — stable serialization

## 9. Mutation-boundary proof

- `test_report_json_mtime_unchanged_by_experience_import`
- No imports of `VaultStore.store`, teaching corpus writers, or pack mutators
- Scout adapter is read-only over existing `build_scout_summary` output

## 10. Tests run

```bash
git diff --check origin/main...HEAD
pytest tests/test_gsm8k_experience_flywheel.py -q          # 18 passed
pytest tests/test_gsm8k_sealed_attempt_scout.py -q
pytest tests/test_contemplation_loop.py -q
pytest tests/test_contemplation_pipeline_convergence.py -q
pytest tests/test_architectural_invariants.py -q           # 123 total passed
core test --suite smoke -q
```

## 11. Live artifact snapshot (train_sample, post-#815)

From `build_experience_report()` on current main:
- Serving: 12 correct / 38 refused / 0 wrong
- Retained records: high-signal lift, sealed-wrong, promoted regression set
- Low-signal joint refusals dropped unless clustered
- `question_bound_product_aggregate` family appears as `promoted_in_pr` for 0003/0021

## 12. Future PRs

| PR | Scope |
|----|-------|
| PR-2 | Wire high-confidence `promotion_candidates` → `DiscoveryCandidate` / proposal draft (no auto-accept) |
| PR-3 | Operator review workbench over experience + contemplation streams |
| PR-4 | Sprint-to-sprint automatic candidate ranking from compacted history |
| PR-5 | Use accepted experience records to prioritize next capability paradigm sprint |

**Proposal bridge (PR-2 sketch):**
- Map `family_summaries` with `promotion_status=candidate` to `DiscoveryCandidate` with `trigger=would_have_grounded` or a new typed trigger
- Attach `positive_evidence_refs` as `ContemplationEvidenceRef`-compatible pointers
- Route through existing `TeachingChainProposal` review gate only

## 13. Non-goals

- No serving lift required
- No auto corpus / pack mutation
- No auto-accept proposal
- No broad product_bridge re-enable
- No report.json rebaseline
- No sealed artifact movement
- No background daemon
- No unbounded logging / raw trace persistence