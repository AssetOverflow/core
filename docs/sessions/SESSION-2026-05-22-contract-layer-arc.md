# Session 2026-05-22 — Contract Layer Arc (ADR-0103 → ADR-0110)

**Date:** 2026-05-22
**Owner:** Joshua Shay (`shay-j`)
**Pair:** Claude (Opus 4.7)
**Outcome:** Evidence-Governed Domain Layer demonstrated end-to-end; first `expert_demo` promotion landed.

---

## Arc summary

The session opened with three in-flight Codex-drafted PRs (ADR-0103 fluency-lane attachment, ADR-0104 curriculum-sourced proposals, ADR-0105 sealed-holdout encryption) needing reconciliation and merge. It closed with the entire ADR-0091 evidence-governed domain chain demonstrated end-to-end, the first reviewer-signed `expert_demo` promotion landed on `mathematics_logic`, and the docs backfilled to reflect the work.

Net merged: **15 PRs** (106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121).

### Chronological sequence

1. **Codex reconciliation (PRs #106 / #107 / #108).** Fixed stale `curriculum_loop_closure` SHA pin; corrected pyrage API misuse (`Identity.from_str`, not `from_file`); resolved README rebase conflicts. All three merged.
2. **ADR-0106 — Expert-Demo Promotion Contract (proposed → accepted).** Domain-aware, reviewer-signed, replay-deterministic gate. Closes the cognition-lane bleed at `core/capability/reporting.py:418`. PRs #109 (proposed) + #113 (implementation).
3. **ADR-0108 — Proposed-ADR sequencing (meta).** Made the post-ADR-0105 frontier ordering explicit and revisable. PRs #111 + #112.
4. **ADR-0107 — `mathematics_logic` expert-demo deferred.** First worked attempt at the new contract; honestly refused on two named blockers (metric-shape uniformity assumption + `inference_closure` substantively failing at 40%). PR #114.
5. **ADR-0109 — Lane-shape-aware threshold amendment.** Five shapes (`cognition_shape`, `accuracy_shape`, `inference_shape`, `refusal_shape`, `symbolic_logic_shape`), 8 lane ids in the registry, unknown lanes fail-closed; cognition-shape thresholds preserved bit-identical. PRs #115 + #116.
6. **PR #117 — `_CORRECTION_CUE_PREFIX_RE` guard.** Investigation revealed `inference_closure` had regressed from 100% to 40% between 2026-05-17 and 2026-05-22; root cause was the declarative-relation regex swallowing "Actually X precedes Y." into VERIFICATION instead of CORRECTION. Premise-emit path is gated on CORRECTION, so non-`is` relations stopped producing `PackMutationProposal` records.
7. **ADR-0110 — `mathematics_logic` expert-demo promotion.** Surfaced and bridged a third transition gap (sealed-holdout dev-mode fallback files missing; `fabrication_control` holdout cases absent; top-level `by_class` not folded into metrics). Signed `expert_demo_claims` entry added to `docs/reviewers.yaml` with digest `94d74781e103854230c1a71590e4df2287f5d2e87832f1c29b8ec4618853c04b`. **First domain at `expert_demo=true`.** PR #118.
8. **ADR-0080 — Contemplation Loop Phase 1.** Delegated to Codex during ADR-0107/0109 investigation; merged in parallel as PR #119. Read-only frontier-compare miner, `SPECULATIVE`-only findings.
9. **Documentation audit (#1 + #2).** PR #120 fixed the README broken `evals/CLAIMS.md` link and added an Evidence-Governed Domain Layer section. PR #121 backfilled `docs/PROGRESS.md` + `docs/capability_roadmap.md` with Phase 6 plus retroactive coverage of ADR-0027..0089.

---

## The contract demonstration narrative

ADR-0106's value is precisely that it can refuse. Two refusals happened in this session:

- **First refusal (ADR-0107).** The contract as written required cognition-pack-shape metrics uniformly across every attached lane. Math lanes produce `accuracy` / `all_pass_rate` / `by_class`, not `surface_groundedness`. The contract refused promotion by absence-of-key. This was the right answer; the wrong contract would have either silently failed-true or been mis-stretched to fit.
- **Amendment (ADR-0109).** Lane-shape registry dispatches thresholds by shape. Unknown lanes fail-closed (introducing a new shape requires an ADR amendment, not a silent broadening). The amendment was small and self-contained because ADR-0106's other invariants (§1.1/§1.3/§1.4/§1.5) didn't need to move.
- **First successful promotion (ADR-0110).** Math passes the now-amended contract honestly. Public + holdout meet thresholds across all three attached lanes; signed claim digest reproduces byte-for-byte; production ledger shows `mathematics_logic` at `status=expert-demo`.

The arc is intentionally visible. "ADR-0106 → refused → amended → succeeded" is the legibility upgrade.

---

## Infrastructure bridges landed under ADR-0110 (not contract changes)

ADR-0107 named two blockers; ADR-0110 surfaced a third — the sealed-holdout transition gap. Three small bridges:

1. `cases_plaintext.jsonl` dev-mode fallback copied into `evals/elementary_mathematics_ood/holdouts/v1/` and `evals/inference_closure/holdouts/v1/` (matches ADR-0105 dev-mode convention exactly).
2. Authored 9 `fabrication_control` holdout cases across all three refusal classes (`phantom_endpoint`, `cross_pack_non_bridge`, `sibling_collapse`) — the lane's holdout file had previously been empty.
3. `core/capability/reporting.py:_fetch_lane_split` folds top-level `by_class` into the metrics dict so `refusal_shape` sees a canonical layout regardless of lane-internal result-file shape.

These are not contract changes. ADR-0106 + ADR-0109 contract bodies are untouched.

---

## Tests / invariants pinned

- `tests/test_adr_0110_math_expert_demo.py` (4 cases): math at expert-demo, signed claim present, replay digest byte-equal, other domains unaffected.
- `tests/test_lane_shape_thresholds.py` (13 cases): lane-shape explicit, shape thresholds named, unknown lane fails closed, cognition shape unchanged under amendment, plus dead-shape and threshold-value gates.
- `tests/test_expert_demo_contract.py::TestProductionLedgerPromotionsAreSignedOnly`: rewritten from "no domain promoted" to "every promoted domain has a signed claim." Load-bearing invariant preserved.
- `tests/test_correction_cue_prefix_routing.py` (10 cases): pin the intent-classifier regression fix from PR #117 in both directions.
- `tests/test_adr_0107_deferral.py` retired (deferral resolved by ADR-0110).
- `tests/test_contemplation_loop.py` (41 cases, Codex): pin Phase 1 read-only emission invariants.

---

## Ledger state at session close

| Domain | Status |
|---|---|
| `mathematics_logic` | **`expert-demo`** ✓ (ADR-0110) |
| `physics` | `reasoning-capable` |
| `systems_software` | `reasoning-capable` |
| `hebrew_greek_textual_reasoning` | `reasoning-capable` |
| `philosophy_theology` | `reasoning-capable` |

---

## What this session does NOT do

- Promote any domain other than `mathematics_logic`. The other three ratified domains are eligible under the now-amended contract but each needs its own signed claim + promotion ADR.
- Implement ADR-0084 (definitional layer) or ADR-0087 (rhetorical style axis). Both remain Proposed per ADR-0108 sequencing.
- Migrate from labeled `evidence_revision` (`adr-0110:reviewed:2026-05-22`) to raw git-sha form. The labeled form is acceptable under ADR-0106; tightening to git-sha-only would be a future ADR amendment.
- Replace the plaintext holdout dev-mode fallback with sealed encryption. The dev-mode fallback is acceptable per ADR-0105's own §"Dev-mode fallback preserved" clause.

---

## References

- `docs/decisions/ADR-0103-fluency-lane-attachment-for-adr-0102.md`
- `docs/decisions/ADR-0104-curriculum-sourced-teaching-proposals.md`
- `docs/decisions/ADR-0105-sealed-holdout-encryption.md`
- `docs/decisions/ADR-0106-expert-demo-promotion-contract.md`
- `docs/decisions/ADR-0107-mathematics-logic-expert-demo-deferred.md`
- `docs/decisions/ADR-0108-proposed-adr-sequencing.md`
- `docs/decisions/ADR-0109-lane-shape-aware-thresholds.md`
- `docs/decisions/ADR-0110-mathematics-logic-expert-demo-promotion.md`
- `docs/decisions/ADR-0080-contemplation-loop.md`
- `docs/reviewers.yaml` (first signed `expert_demo_claims` entry)
- `core/capability/expert_demo.py`
- `core/capability/reviewers.py`
- `tests/test_adr_0110_math_expert_demo.py`
