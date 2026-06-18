# GSM8K Capability Paradigm Sprint 12 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **24** |
| refused | **26** |
| wrong | **0** |

After #824 (Sprint 11 calendar ClusterContract). Prerequisite satisfied.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint12.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| lift_refused_to_correct | **0** |
| scout serving | 24 / 26 / 0 |

Top singleton signals:

- **0004** — `joint_refusal`, `fraction_surface`, `not_promotable`; no sealed-wrong on surface.
- **0007** — `joint_refusal`, `unbound_target`, `not_promotable`; no sealed-wrong on surface.
- Blocked families unchanged: `sealed_elimination` (0011, 0026), `relation_hypothesis` (0032, 0047), currency.
- No second calendar sibling under Sprint 11 contract.

## 3. Scout/frontier/microscope output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 24 | 26 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- Dominant bottleneck: joint refusal (20/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

Microscope: 0004 tagged `fraction_operand`; 0007 tagged `conditional_question`. Adjacent sealed-wrong neighbors 0026 and 0047 on distinct surfaces.

## 4. Candidate families ranked

| Rank | Candidate | Lift | Wrong-risk neighbor | Verdict |
|------|-----------|------|---------------------|---------|
| 1 | `nested_fraction_remainder_total` (0004) | +1 | 0026 sealed_elimination | **Selected (A2r)** |
| 2 | `loose_crayon_box_capacity` (0007) | +1 | 0047 DCS/divisive | **Selected (A2s)** |
| 3 | calendar contract extension | +0 | — | **Rejected** (no second sibling) |
| — | DCS / currency / sealed_elimination wholesale | — | blocked | **Deferred** |

0004 and 0007 rank equally on flywheel; both admitted with hard neighbor confuser matrices.

## 5. ClusterContracts

### nested_fraction_remainder_contract (Gate A2r)

```yaml
ClusterContract:
  family_id: nested_fraction_remainder_total
  proposed_organs:
    - nested_fraction_remainder_total
  included_cases:
    - gsm8k-train-sample-v1-0004
  explicitly_excluded_cases:
    - gsm8k-train-sample-v1-0026  # sealed_elimination / currency / scoops
    - gsm8k-train-sample-v1-0011  # sealed_elimination
    - asks subgroup only (not root altogether)
    - multiple fraction relations
    - 3/4 bill-of-money surfaces
  positive_anchors:
    - "Half of the {population}"
    - "1/4 of the {population} going to {camp} camp"
    - "{camp} camp in the morning" + afternoon complement count
    - question asks root {population} altogether
  negative_anchors:
    - $ currency / each saved / scoops / bill / ice cream
    - 3/4 of total money
    - asks soccer-camp subgroup only
    - multiple fractions
  actor_binding_rule: shared population token across half/quarter/afternoon clauses
  target_binding_rule: question must ask root population altogether
  unit_binding_rule: afternoon count unit matches bound population
  quantity_obligations:
    - text-grounded afternoon complement count
    - exactly one 1/4 inner partition
  allowed_external_grounding: none
  blocked_sibling_families:
    - sealed_elimination
    - currency_amount
    - percent_partition
  sealed_wrong_neighbors:
    - 0026 (blocked by currency/each/scoops/3/4 bill hazards)
  serving_admission_rule: resolve_promotable_nested_fraction_remainder_total()
  implementation_allowed: true
  reason: Typed morning/afternoon complement chain + 0026 confuser matrix clears wrong-risk.
```

### loose_crayon_box_capacity_contract (Gate A2s)

```yaml
ClusterContract:
  family_id: loose_crayon_box_capacity
  proposed_organs:
    - loose_crayon_box_capacity
  included_cases:
    - gsm8k-train-sample-v1-0007
  explicitly_excluded_cases:
    - gsm8k-train-sample-v1-0047  # equal-distribution weight / eaten bag
    - asks per-box capacity (not more boxes)
    - equal number in bags
    - weight/ounce surfaces
  positive_anchors:
    - "{actor} has N full boxes of {item}"
    - "M loose {item}" before friend clause
    - "friend has K loose"
    - conditional "total of T" in question
    - "how many more boxes"
  negative_anchors:
    - ounces / macaroons / equal number / eats / Steve
    - asks per-box not more-boxes
    - DCS divisive packing
  actor_binding_rule: primary actor owns full boxes + loose; friend contributes loose only
  target_binding_rule: question asks additional boxes for all loose items
  unit_binding_rule: answer unit is boxes
  quantity_obligations:
    - total, loose_primary, loose_friend, num_full_boxes all text-grounded
  allowed_external_grounding: none
  blocked_sibling_families:
    - multiplicative_aggregate / DCS
    - currency_amount
  sealed_wrong_neighbors:
    - 0047 (blocked by weight/equal-number/eaten-bag hazards)
  serving_admission_rule: resolve_promotable_loose_crayon_box_capacity()
  implementation_allowed: true
  reason: Capacity derivation from boxed portion + loose aggregation; 0047 confuser matrix holds.
```

## 6. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| calendar extension | No second train_sample sibling under #824 policy |
| DCS 0032/0047 | sealed-wrong; relation_hypothesis blocked |
| currency 0019/0028 | sealed-wrong |
| sealed_elimination 0011/0026 | sealed-wrong |
| wholesale multiplicative_aggregate | 0025/0047 sealed-wrong |

## 7. Research gate decision

**Proceed** with two independent singleton ClusterContracts (A2r + A2s). Calendar extension rejected for lack of sibling evidence.

## 8. Selected paradigm

Dual singleton organs under explicit contracts:

1. `generate/derivation/nested_fraction_remainder_total.py` — Gate A2r
2. `generate/derivation/loose_crayon_box_capacity.py` — Gate A2s

Wired in `generate/math_candidate_graph.py` after Gate A2q.

## 9. Typed chains for target cases

**0004 (gold 2000):**

- afternoon = 750 kids (3/4 of soccer-camp subgroup)
- subgroup = 750 / 0.75 = 1000
- total = 1000 × 2 = 2000 (half go to soccer camp)

**0007 (gold 2):**

- boxed = 85 − 5 = 80
- per_box = 80 / 5 = 16
- loose_total = 5 + 27 = 32
- boxes_needed = 32 / 16 = 2

## 10. Implemented organ(s)

| Module | Gate | Promotion entry |
|--------|------|-----------------|
| `nested_fraction_remainder_total.py` | A2r | `resolve_promotable_nested_fraction_remainder_total()` |
| `loose_crayon_box_capacity.py` | A2s | `resolve_promotable_loose_crayon_box_capacity()` |

## 11. Before/after score

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| correct | 24 | **26** | +2 |
| refused | 26 | **24** | −2 |
| wrong | 0 | **0** | 0 |

**State A achieved:** 26/24/0.

## 12. Newly solved IDs

**0004**, **0007**

## 13. Preserved solved IDs

0001, 0002, 0003, 0005, 0006, 0008, 0009, 0010, 0013, 0014, 0015, 0017, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045, 0046

## 14. Wrong=0 proof

- Full train_sample replay: 26 / 24 / 0
- `tests/test_math_candidate_graph_sprint12_singleton_contract_lift.py`
- Holdout_dev: wrong=0
- Regression lane: sprint6–12 + flywheel + scout + microscope

## 15. Confuser matrix

| Confuser | Organ | Result |
|----------|-------|--------|
| 0026 sealed_elimination | A2r | refuse |
| asks subgroup only | A2r | refuse |
| multiple fractions | A2r | refuse |
| 0047 equal-distribution weight | A2s | refuse |
| asks per-box capacity | A2s | refuse |
| equal number in bags | A2s | refuse |

## 16. Sibling generality proof

| Sibling | Expected | Result |
|---------|----------|--------|
| music camp / 600 afternoon | 1600 | pass |
| four marker boxes / 67 total | 6 boxes | pass |

## 17. Sealed-wrong negative evidence used

- 0026: currency + each + scoops + 3/4 bill → A2r hazard refusal
- 0047: ounces + equal number + eaten bag → A2s hazard refusal

## 18. Composition-validation pin changes

None.

## 19. report.json untouched

Confirmed — no changes to committed `report.json`.

## 20. sealed artifacts untouched

Confirmed — no sealed lane artifact movement.

## 21. no case-id logic

Confirmed — admission via structural anchors and bindings only.

## 22. no hardcoded answer

Confirmed — arithmetic recomputed from grounded quantities.

## 23. no direct-answer shortcut

Confirmed — self-verified derivation chains required.

## 24. ClusterContract method enabled bigger lift

Yes — bundling two narrow singleton contracts under explicit neighbor exclusions delivered +2 with wrong=0, exceeding single-organ sprint cadence.

## 25. Sprint 13 recommendation

1. **Practice-lane mini-family clustering** — flywheel joint_refusal clusters (20 cases) may yield a 2-case mini-family safer than next singleton.
2. **Deferred blocked surfaces** — DCS 0032/0047 and currency 0019/0028 remain blocked until dedicated confuser ADRs land.
3. **Calendar contract** — revisit only if practice lane surfaces a genuine second piecewise sibling without policy expansion.
4. Target: 27+/23-/0 via one mini-family or two verified singletons with lowest sealed-wrong adjacency (candidates from flywheel: 0004/0007 neighbors exhausted; next scout frontier TBD).