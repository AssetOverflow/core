# ADR-0122 — `systems_software` Audit-Passed Promotion: Deferred

**Status:** Accepted (decision: defer promotion)
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0101, ADR-0106, ADR-0109, ADR-0110, ADR-0111, ADR-0113

---

## Context

ADR-0101 ratified `systems_software` as `reasoning-capable`.
ADR-0110 and ADR-0111 then demonstrated two successful `audit-passed`
promotions (`mathematics_logic`, `physics`) under the ADR-0106 + ADR-0109
contract shape (signed digest + replay determinism + typed refusal + exact recall).

ADR-0122 is the attempted third promotion on `systems_software`.

---

## Attempt

`systems_software` attaches three eval lanes via its pack manifest:

- `symbolic_logic`
- `inference_closure`
- `fabrication_control`

For ADR-0122 we re-ran all three lanes on both `public` and `holdout` splits.
`inference_closure` and `fabrication_control` both pass with their expected
contract shapes (`inference_shape`, `refusal_shape`).

---

## Blocker

`symbolic_logic` lane produces inference-shape metrics
(`all_three_pass_rate` / `overall_pass` / `replay_determinism`) but
`LANE_SHAPE_REGISTRY` dispatches it to `_check_accuracy_shape`
(`symbolic_logic` → `symbolic_logic_shape`, checker expects
`accuracy` ≥ 0.95 or `passed/total` fallback).

Current `symbolic_logic` result payloads do not include `accuracy`
or `passed/total`, so the gate fails closed with:

`lane 'symbolic_logic' missing accuracy (and no passed/total fallback)`.

This is a real contract-shape mismatch. Either:

1. The lane runner must change to emit accuracy-shape output.
2. `LANE_SHAPE_REGISTRY` must be amended (e.g. map `symbolic_logic` to
   `inference_shape`, or add a dedicated checker that consumes its
   inference-style metric schema).

Both are contract/lane-shape amendments and are out of scope for ADR-0122.

---

## Decision

Defer `systems_software` audit-passed promotion until the named blocker
is resolved by a future ADR amendment to ADR-0109 lane-shape mapping/checking.

No claim is signed; no `audit_passed_claims` entry is added for
`systems_software`.

---

## Invariants

### `adr_0122_no_silent_promotion`

`systems_software` remains at `status="reasoning-capable"` with
`predicates.audit_passed == false`.

### `adr_0122_blocker_is_explicit`

Evaluating the gate with `systems_software` lanes and current
`symbolic_logic` outputs fails specifically on the accuracy-shape mismatch,
not on an opaque or unrelated error.

### `adr_0122_other_promotions_unchanged`

`mathematics_logic` and `physics` remain `audit-passed`; ADR-0122 does not
modify or weaken their claims.

---

## Consequences

- This is the second honest contract refusal after ADR-0107.
- Gate credibility increases: promotions are recorded only when evidence and
  contract shape align.
- Next move is explicit: lane-shape amendment ADR, then re-attempt promotion.
