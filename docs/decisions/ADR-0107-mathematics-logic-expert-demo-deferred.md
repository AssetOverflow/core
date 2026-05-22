# ADR-0107 — `mathematics_logic` Expert-Demo Promotion: Deferred

**Status:** Accepted (decision: defer promotion)
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0097, ADR-0106, ADR-0108

---

## Context

ADR-0108 reserved ADR-0107 as the first worked expert-demo promotion
against the ADR-0106 contract, with `mathematics_logic` named as the
smallest expert-demo proof surface across the four ratified domains.

On evaluation, the ADR-0106 gate correctly refused to promote
`mathematics_logic`. ADR-0107 records that refusal honestly and reserves
the follow-up ADRs needed before promotion can re-attempt.

This is the contract working as designed. ADR-0106 §Consequences
predicted that "reasoning-capable" should not equal "demonstrated"; the
first promotion attempt has now surfaced two specific evidence-side
gaps that prove the gap is real.

---

## Evidence

`mathematics_logic` attaches three eval lanes via
`language_packs/data/en_mathematics_logic_v1/manifest.json`:

| Lane | Public split | Holdout split | Notes |
|---|---|---|---|
| `elementary_mathematics_ood` | `accuracy=1.0`, all C01–C13 cases pass | `accuracy=1.0`, `passed=39/39` | Reports lane-shape metrics, not cognition-shape metrics |
| `inference_closure` | `all_pass_rate=0.4`, `overall_pass=False` | requires `CORE_HOLDOUT_KEY` (sealed under ADR-0105) | Lane is currently below any reasonable promotion threshold |
| `fabrication_control` | refusals clean (`fabricated=0` across phantom / cross-pack / sibling-collapse classes) | not formally re-run after ADR-0105 sealing | Required by ADR-0106 §1.3 |

Neither `elementary_mathematics_ood` nor `inference_closure` nor
`fabrication_control` reports the four metric keys ADR-0106 §1.2 prescribes
(`surface_groundedness`, `term_capture_rate`, `intent_accuracy`,
`versor_closure_rate`). Those keys are cognition-pack-shape; the math
lanes carry their own native shapes.

---

## Decision

`mathematics_logic` is **not** promoted to `expert_demo=true`. The
ledger row stays at `reasoning-capable`. The reviewer registry receives
**no** `expert_demo_claims` entry as part of this ADR.

This is a positive decision recording two concrete blocking gaps:

### Gap 1 — ADR-0106 metric-shape uniformity assumption

ADR-0106 §1.2 prescribes cognition-shape thresholds uniformly across
every attached lane. In practice, each lane reports its own native
metric shape (`accuracy`, `passed_rate`, `all_pass_rate`,
`derived_recall_rate`). Enforcing cognition-shape keys uniformly causes
every non-cognition lane to fail the gate by absence-of-key, not by
substance.

**Resolution path:** ADR-0109 (reserved) — amend ADR-0106 with a
lane-shape adaptation layer that maps each lane's native metric to a
contract-bearing threshold. Candidate shapes already observable in the
repo:

- `cognition_shape` — the original four keys, used by the cognition pack
- `accuracy_shape` — single `accuracy` key, used by
  `elementary_mathematics_ood`
- `refusal_shape` — `fabricated`/`refused` counts, used by
  `fabrication_control`
- `inference_shape` — `all_pass_rate` + `replay_determinism`, used by
  `inference_closure`

ADR-0109 must specify the contract-bearing threshold per shape and pin
the mapping so a future lane introduces its shape explicitly rather
than silently broadening the gate.

### Gap 2 — `inference_closure` lane substantively fails

`inference_closure` reports `all_pass_rate=0.4` on the public v1 split.
Whether the failure is a runner bug, a case-set issue, or a genuine
substrate gap is unresolved. Either way, the lane is not a positive
signal for promotion at present.

**Resolution path:** Triage `inference_closure` failures (5 of 5 cases
on dev, 12 of 20 on public). Until that lane crosses an explicit
threshold under the ADR-0109 shape rules, `mathematics_logic` cannot
promote regardless of how the metric-shape question is resolved.

---

## Follow-up ADRs reserved

| ADR | Purpose |
|---|---|
| **ADR-0109** | Lane-shape-aware threshold rules amending ADR-0106. |
| **ADR-0110** | Re-attempt `mathematics_logic` expert-demo promotion under the ADR-0109-amended contract, conditional on `inference_closure` substantively passing. |

ADR-0107 explicitly does **not** pre-decide ADR-0110's outcome. It only
records that the current evidence cannot support promotion.

---

## Invariants

### `adr_0107_no_silent_promotion`

No `expert_demo_claims` entry for `mathematics_logic` exists in
`docs/reviewers.yaml` as a result of this ADR. A pytest gate confirms
the math row in `ledger_report()` reports
`predicates.expert_demo == false`.

### `adr_0106_refusal_recorded`

The `expert_demo_reason` field for the math row must name at least one
of the documented blockers (missing metric keys or
`inference_closure` failure). This is informational; it gives operators
a one-line legible reason without forcing them to read this ADR.

---

## Acceptance evidence

Accepted when:

- this ADR lands at `Accepted (decision: defer promotion)`
- README "Current frontier" updated: ADR-0107 moves out of the
  Proposed-ADR sequencing list; ADR-0109 and ADR-0110 enter as reserved
- `tests/test_adr_0107_deferral.py` pins `adr_0107_no_silent_promotion`
  against the live ledger
- no change to `core/capability/expert_demo.py` or
  `core/capability/reporting.py` — the contract is honored, not amended

---

## Consequences

- The ADR-0106 contract has demonstrated its load-bearing behavior: it
  refused a promotion attempt that the previous code-path would have
  silently failed-true on cognition metrics the math domain never
  produced.
- "`reasoning-capable`" remains an honest ceiling for
  `mathematics_logic`. External readers can see in `ledger_report()`
  that the row sits at `reasoning-capable` with a named blocker.
- The frontier shifts: ADR-0109 (metric-shape amendment) becomes the
  prerequisite work for any future expert-demo promotion across all
  four ratified domains, not just math.

---

## Out of scope

- This ADR does not amend ADR-0106. The amendment is ADR-0109's scope.
- This ADR does not investigate or fix `inference_closure`. That work
  is a prerequisite to ADR-0110, scoped to wherever the substrate gap
  actually lives.
- This ADR does not change the ratification status of `physics`,
  `systems_software`, or `hebrew_greek_textual_reasoning`. Each will
  face the same metric-shape question and should be re-evaluated under
  ADR-0109 when that lands.
