# ADR-0111 — `physics` Expert-Demo Promotion

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0100, ADR-0106, ADR-0109, ADR-0110

---

## Context

ADR-0110 landed the first reviewer-signed expert-demo promotion
(`mathematics_logic`) and, in doing so, validated the
ADR-0106 + ADR-0109 contract end-to-end against a real domain.
ADR-0110 §Consequences explicitly noted that the bridges it
landed (dev-mode holdout fallback, `fabrication_control` holdout
authoring, `by_class` fold in reporting) make future
expert-demo promotions for the remaining ratified domains
"feasible without new contract work — they need only their own
lane results to materialise and their own signed claims."

ADR-0111 is the second worked promotion. It exercises the contract
a second time on a distinct domain to confirm the ADR-0110 framing —
no contract change, no infrastructure bridge — and to retire the
"this only works for math" objection.

---

## Evidence

The `physics` domain attaches three lanes via the `en_physics_v1`
pack manifest (`provenance: adr-0100:reviewed:2026-05-21`):

| Lane | Shape | Public | Holdout |
|---|---|---|---|
| `foundational_physics_ood` | `accuracy_shape` | accuracy=1.0 (117/117) | accuracy=1.0 (39/39) |
| `inference_closure` | `inference_shape` | all_pass_rate=1.0, replay_determinism=1.0, overall_pass=True (20 cases) | same (12 cases) |
| `fabrication_control` | `refusal_shape` | by-class refusals 3/3/3, fabricated=0 across all classes | same (9 holdout cases) |

All thresholds documented in ADR-0109 §2 are met on both public and
holdout splits for every attached lane.

`inference_closure` and `fabrication_control` results are shared
infrastructure across all domains that attach them; the digest
distinguishes physics from math via `domain_id` + `evidence_revision`,
not via lane-result divergence. (See ADR-0106 §1 — the bundle
incorporates `domain_id` precisely so a shared lane result can
support multiple signed claims without digest collision.)

### Infrastructure preconditions (already landed)

ADR-0110 landed:

1. Plaintext holdout dev-mode fallback files for `inference_closure`
   and `elementary_mathematics_ood`.
2. Nine `fabrication_control` holdout cases across the three refusal
   classes.
3. `by_class` top-level → metrics fold in
   `core/capability/reporting.py:_fetch_lane_split`.

ADR-0111 needed only one additional small bridge:

4. **Plaintext holdout dev-mode fallback for `foundational_physics_ood`.**
   Copied `evals/foundational_physics_ood/holdouts/v1/cases.jsonl` to
   `cases_plaintext.jsonl` so `holdout_runner._decrypt_holdout`
   resolves the file without `CORE_HOLDOUT_KEY` (matches the
   ADR-0105 dev-mode convention exactly).

This is not a contract change. ADR-0106 + ADR-0109 contract bodies
remain untouched.

---

## Decision

`physics` is promoted to `expert_demo=true`.

The signed claim entered into `docs/reviewers.yaml` is:

```yaml
expert_demo_claims:
  - domain_id: physics
    evidence_lanes:
      - foundational_physics_ood
      - inference_closure
      - fabrication_control
    evidence_revision: "adr-0111:reviewed:2026-05-22"
    signed_by: shay-j
    claim_digest: "a104cad136f3219df05dc7ce6a78437c02f7b5827cd3cdce568db3acda6a43ed"
```

The `evidence_revision` follows the labeled form established by
ADR-0110 (`adr-<id>:reviewed:<date>`); the load-bearing invariant
remains replay byte-equality per ADR-0106 §1.5.

---

## Invariants

### `adr_0111_physics_expert_demo_holds`

`ledger_report()` must report `physics` with
`predicates.expert_demo == true` and `status == "expert-demo"` so
long as the signed claim in `docs/reviewers.yaml` resolves and the
lane results on disk continue to produce the claimed digest.

### `adr_0111_replay_digest_byte_equality`

Re-deriving the evidence-bundle digest from the lane result files at
this commit must reproduce
`a104cad136f3219df05dc7ce6a78437c02f7b5827cd3cdce568db3acda6a43ed`.
Tested by `tests/test_adr_0111_physics_expert_demo.py`.

### `adr_0111_other_domains_unaffected`

ADR-0111 promotes exactly one domain. `mathematics_logic` continues
at `expert-demo` (per ADR-0110); `systems_software`,
`hebrew_greek_textual_reasoning`, and `philosophy_theology`
continue at `reasoning-capable` with `expert_demo=false`.

### `adr_0111_distinct_digest_from_adr_0110`

The physics digest and the math digest must differ, demonstrating
that two domains sharing two of three evidence lanes
(`inference_closure`, `fabrication_control`) still produce distinct
signed claims via the bundle's `domain_id` + `evidence_revision`
fields. Tested by the same test module.

---

## Acceptance evidence

Accepted when:

- `docs/reviewers.yaml` carries the signed `expert_demo_claims`
  entry for `physics`
- `evals/foundational_physics_ood/holdouts/v1/cases_plaintext.jsonl`
  exists (dev-mode fallback per ADR-0105)
- `evals/foundational_physics_ood/results/v1_public_*.json` and
  `v1_holdout_*.json` exist with `accuracy=1.0` on both splits
- `tests/test_adr_0111_physics_expert_demo.py` pins the four
  invariants above
- `ledger_report()` confirms `physics` row at `expert_demo=true` /
  `status="expert-demo"`
- README "Accepted reasoning-capable domains" table updated to
  note `physics` at expert-demo

---

## Consequences

- Second expert-demo promotion lands. The ADR-0106 + ADR-0109
  contract has now succeeded against two distinct domains using
  three distinct lane shapes (accuracy, inference, refusal) plus
  one math-specific lane shape (accuracy on
  `elementary_mathematics_ood` vs `foundational_physics_ood` —
  both `accuracy_shape` but distinct lane ids).
- The "first promotion was bespoke to math" objection is retired.
  The bridges ADR-0110 landed were correctly scoped — the second
  promotion needed only a one-file fallback copy.
- Two remaining ratified domains (`systems_software`,
  `hebrew_greek_textual_reasoning`) are now next in line; both
  attach `inference_closure` + `fabrication_control` plus a
  third domain-specific lane, and both can follow this same path.

---

## Out of scope

- This ADR does not amend ADR-0106 or ADR-0109.
- This ADR does not promote any other domain.
- Sealing the physics holdout under a real age recipient (ADR-0105's
  eventual design) remains future work. The dev-mode plaintext
  fallback is acceptable per ADR-0105's own §"Dev-mode fallback
  preserved" clause.
- Tightening `evidence_revision` to a raw git sha remains a candidate
  future amendment; the labeled form is still load-bearing for replay.
