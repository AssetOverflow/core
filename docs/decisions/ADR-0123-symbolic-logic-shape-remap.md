# ADR-0123 — `symbolic_logic` Lane-Shape Remap (ADR-0109 Amendment)

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Amends:** ADR-0109
**Depends on:** ADR-0109, ADR-0122

---

## Context

Under [ADR-0109](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/docs/decisions/ADR-0109-lane-shape-aware-thresholds.md), threshold verification rules are lane-shape-aware, mapping specific lane IDs to defined metric shapes. [ADR-0109](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/docs/decisions/ADR-0109-lane-shape-aware-thresholds.md) mapped the `symbolic_logic` lane to `symbolic_logic_shape`, which internally dispatched to the accuracy-shape threshold checker (`_check_accuracy_shape`).

However, as documented in the deferred promotion of `systems_software` ([ADR-0122](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/docs/decisions/ADR-0122-systems-software-audit-passed-deferred.md)), the `symbolic_logic` lane output payload actually contains inference-style metrics (`all_pass_rate`, `replay_determinism`, and `overall_pass`) rather than accuracy-shape metrics (`accuracy` or `passed/total`). This mismatch caused the gate to fail closed with the error message: `lane 'symbolic_logic' missing accuracy (and no passed/total fallback)`.

This amendment corrects the mapping to unblock the `systems_software` promotion.

---

## Decision

Re-map the `symbolic_logic` lane to `inference_shape` within the `LANE_SHAPE_REGISTRY` in [core/capability/expert_demo.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/core/capability/expert_demo.py):

```python
LANE_SHAPE_REGISTRY["symbolic_logic"] = "inference_shape"
```

### Rationale
The `symbolic_logic` lane validates propositional inference closure. Because it checks deterministic symbolic inferences rather than approximate/statistical accuracy scalars, it naturally produces the standard inference-style metrics:
- `all_pass_rate`
- `replay_determinism`
- `overall_pass`

Mapping it to `inference_shape` aligns the contract verification logic with the lane's actual runtime evidence schema.

Additionally, because no other lane in the registry maps to `symbolic_logic_shape`, this shape checker is retired and removed from `SHAPE_CHECKERS` to preserve code cleanliness and avoid dead-shape drift.

---

## Invariants

### `inference_shape_thresholds_applied`
The existing `inference_shape` thresholds defined in [ADR-0109](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/docs/decisions/ADR-0109-lane-shape-aware-thresholds.md) now govern `symbolic_logic` verification:
- `all_pass_rate >= 0.95`
- `replay_determinism == 1.0`
- `overall_pass == True`

---

## Acceptance Evidence

Accepted when:
- The registry mapping in [core/capability/expert_demo.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/core/capability/expert_demo.py) is amended to map `symbolic_logic` to `inference_shape`.
- Unused `symbolic_logic_shape` is removed from `SHAPE_CHECKERS`.
- A unit test `TestSymbolicLogicShapeGate` in [tests/test_lane_shape_thresholds.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/tests/test_lane_shape_thresholds.py) asserts that:
  - `resolve_lane_shape("symbolic_logic") == "inference_shape"`
  - `symbolic_logic` results carrying compliant inference-style metrics pass the gate successfully.

---

## Consequences

- The contract blocker for `systems_software` is resolved: the lane gate now evaluates `symbolic_logic` outputs under the correct metric schema.
- The deferral in [ADR-0122](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/fix-symbolic-logic-shape/docs/decisions/ADR-0122-systems-software-audit-passed-deferred.md) can be resolved in a subsequent promotion attempt (likely ADR-0124) when a signed promotion claim is recorded.

---

## Out of Scope

- Actually signing the `systems_software` claim or updating the `audit_passed_claims` in `reviewers.yaml` (reserved for a follow-up promotion ADR).
