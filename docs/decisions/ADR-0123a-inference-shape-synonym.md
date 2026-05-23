# ADR-0123a — `all_three_pass_rate` Synonym in `inference_shape` (ADR-0109 Amendment)

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Amends:** ADR-0109
**Depends on:** ADR-0109, ADR-0123, ADR-0124

---

## Context

Under [ADR-0109](ADR-0109-lane-shape-aware-thresholds.md), threshold verification rules are lane-shape-aware. [ADR-0123](ADR-0123-symbolic-logic-shape-remap.md) re-mapped the `symbolic_logic` lane to `inference_shape` because it emits inference-style metrics.

However, the `inference_shape` checker (`_check_inference_shape`) was written expecting the exact metric key `all_pass_rate`. The `symbolic_logic` lane actually emits `all_three_pass_rate` instead of `all_pass_rate`. This metric mismatch caused evaluation to fail closed.

A widening bridge was implemented in ADR-0124 to accept `all_three_pass_rate` as a synonym for `all_pass_rate`. This amendment formally documents this contract widening and codifies the synonym precedence rules.

---

## Decision

Document and verify the synonym behavior within the `inference_shape` checker in `core/capability/expert_demo.py`. 

The `inference_shape` checker accepts either `all_pass_rate` or `all_three_pass_rate` as the load-bearing pass-rate metric. 

### Precedence Rules
If both metric keys are present in the results payload:
1. The primary key `all_pass_rate` takes precedence.
2. The check evaluates the value of `all_pass_rate`, ignoring the value of `all_three_pass_rate`.

The threshold (`ALL_PASS_RATE_MIN = 0.95`) applies to whichever key is active.

---

## Invariants

### no_unregistered_synonyms
Only `all_pass_rate` and `all_three_pass_rate` are recognized as pass-rate keys under `inference_shape`. Any third synonym key (e.g. `foo_bar_rate`) is refused, causing the gate to fail closed.

---

## Acceptance Evidence

Accepted when:
- A unit test class `TestInferenceShapeAcceptsSynonyms` in `tests/test_lane_shape_thresholds.py` asserts that:
  - `_check_inference_shape` successfully accepts `all_three_pass_rate` alone.
  - `_check_inference_shape` successfully accepts `all_pass_rate` alone.
  - Any third synonym is rejected.
  - When both are present, `all_pass_rate` has precedence (e.g., if `all_pass_rate` is below threshold and `all_three_pass_rate` is 1.0, the check fails).

---

## Consequences

- The `inference_shape` is now a 2-key synonym shape, making future lanes that produce either key eligible without further changes.
- The gate remains secure against unregistered synonyms.

---

## Out of scope

- Introducing any new shapes or new checkers.
- Changing threshold values.
- Modifying threshold rules of other shapes.
