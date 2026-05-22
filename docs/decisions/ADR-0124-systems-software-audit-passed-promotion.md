# ADR-0124 — `systems_software` Audit-Passed Promotion

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0101, ADR-0106, ADR-0109, ADR-0122, ADR-0123

---

## Context

ADR-0122 attempted the third promotion on `systems_software` but deferred it due to a lane-shape mismatch on the `symbolic_logic` lane (mapped to accuracy-shape but producing inference-shape metrics). ADR-0123 resolved this blocker by re-mapping `symbolic_logic` to `inference_shape` in the `LANE_SHAPE_REGISTRY`.

With the registry correct, the only remaining blocker is signing the claim. This ADR closes the arc: ADR-0101 (ratification) → ADR-0122 (deferral) → ADR-0123 (registry remap) → ADR-0124 (promotion).

It is the third successful promotion, following `mathematics_logic` (ADR-0110) and `physics` (ADR-0111).

---

## Evidence

The `systems_software` domain attaches three lanes via the `en_systems_software_v1` pack manifest:

| Lane | Shape | Public | Holdout |
|---|---|---|---|
| `symbolic_logic` | `inference_shape` | all_three_pass_rate=1.0, replay_determinism=1.0, overall_pass=True (18 cases) | same (12 cases) |
| `inference_closure` | `inference_shape` | all_pass_rate=1.0, replay_determinism=1.0, overall_pass=True (20 cases) | same (12 cases) |
| `fabrication_control` | `refusal_shape` | by-class refusals 3/3/3, fabricated=0 across all classes | same (9 holdout cases) |

All thresholds documented in ADR-0109 §2 (and as amended by ADR-0123 for `symbolic_logic`) are met on both public and holdout splits for every attached lane.

`inference_closure` and `fabrication_control` results are shared infrastructure across all domains that attach them; the digest distinguishes systems_software from math and physics via `domain_id` + `evidence_revision`, not via lane-result divergence (per ADR-0106 §1).

---

## Decision

`systems_software` is promoted to `audit-passed=true` (formerly `expert_demo=true`).

The signed claim entered into `docs/reviewers.yaml` is:

```yaml
audit_passed_claims:
  - domain_id: systems_software
    evidence_lanes:
      - symbolic_logic
      - inference_closure
      - fabrication_control
    evidence_revision: "adr-0124:reviewed:2026-05-22"
    signed_by: shay-j
    claim_digest: "17e24436b6875b89f6d1a5c2992557413c7ef456250f549d463159f54438c407"
```

The `evidence_revision` follows the labeled form established by ADR-0110 (`adr-<id>:reviewed:<date>`); the load-bearing invariant remains replay byte-equality per ADR-0106 §1.5.

---

## Invariants

### row_is_audit_passed

`ledger_report()` must report `systems_software` with `predicates.audit_passed == true` and `status == "audit-passed"` so long as the signed claim in `docs/reviewers.yaml` resolves and the lane results on disk continue to produce the claimed digest.

### replay_digest_byte_equality

Re-deriving the evidence-bundle digest from the lane result files at this commit must reproduce `17e24436b6875b89f6d1a5c2992557413c7ef456250f549d463159f54438c407`.

### other_domains_unaffected

ADR-0124 promotes exactly one domain. `mathematics_logic` and `physics` continue at `audit-passed`; `hebrew_greek_textual_reasoning` and `philosophy_theology` continue at `reasoning-capable` with `audit_passed=false`.

### distinct_digest_from_adr_0110_and_0111

The systems_software digest must differ from both mathematics_logic (ADR-0110) and physics (ADR-0111), proving that distinct domains sharing evidence lanes still produce distinct signed claims.

---

## Acceptance evidence

Accepted when:

- `docs/reviewers.yaml` carries the signed `audit_passed_claims` entry for `systems_software`
- `evals/symbolic_logic/holdouts/v1/cases_plaintext.jsonl` exists (dev-mode fallback per ADR-0105)
- `evals/symbolic_logic/results/v1_public_*.json` and `v1_holdout_*.json` exist with compliant metrics
- `tests/test_adr_0124_systems_software_audit_passed.py` pins the four invariants above
- `ledger_report()` confirms `systems_software` row at `audit_passed=true` / `status="audit-passed"`
- README "Accepted reasoning-capable domains" table updated to note `systems_software` at audit-passed

---

## Consequences

- Third audit-passed promotion lands. The domain contract has now succeeded against three distinct domains.
- The deferral in ADR-0122 is resolved, confirming that registry/contract updates are the correct path to resolve mismatched lane shapes.
- The remaining reasoning-capable domains are next in line.

---

## Out of scope

- This ADR does not amend ADR-0106, ADR-0109, or ADR-0123.
- This ADR does not promote any other domain.
- Sealing the systems_software holdout under a real age recipient (ADR-0105's eventual design) remains future work. The dev-mode plaintext fallback is acceptable per ADR-0105's own §"Dev-mode fallback preserved" clause.
- Tightening `evidence_revision` to a raw git sha remains a candidate future amendment.
