# GSM8K Capability Paradigm Sprint 10 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **21** |
| refused | **29** |
| wrong | **0** |

After #822 (Sprint 9 post-merge hardening). Prerequisite satisfied.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint10.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| lift_refused_to_correct | **0** |
| promotion_candidates | all `blocked_by_wrong_risk` or diagnostic hold |

Top signals:

- `multiplicative_aggregate:multiplicative_aggregation` — 0006, 0013 joint refusal; **0 sealed-wrong** on surface tag but wholesale MA blocked by 0025/0047 neighbors.
- Singletons 0004/0007/0009 — `joint_sealed_no_resolution`; no `candidate_family` cluster.
- Blocked: DCS (0032, 0047), currency (0019, 0028), sealed_elimination (0011, 0026).

## 3. Scout/frontier/microscope output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 21 | 29 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- Dominant bottleneck: joint refusal (23/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

Microscope: 0006/0013 tagged `multiplicative_aggregate`; 0004 fraction surface; 0007 unbound_target; 0009 unbound_target.

## 4. Candidate families ranked

| Rank | Family | Cases | Lift | Wrong-risk | Verdict |
|------|--------|-------|------|------------|---------|
| 1 | `piecewise_daily_hours_total` | 0013 | +1 | medium | **Deferred** — June=30 not grounded in problem text |
| 2 | `sequential_comparative_scale` | 0006 | +1 | medium | **Selected (A2p)** |
| 3 | `affine_comparative_inversion_total` | 0009 | +1 | low–medium | **Selected (A2o)** |
| 4 | `multiplicative_aggregate` wholesale | 0006, 0013 | +2? | **high** (0025, 0047) | **Rejected** |
| 5 | `nested_fraction_partition` | 0004 | +1 | high (0026) | **Rejected** |
| 6 | `loose_inventory_boxing` | 0007 | +1 | high (0047) | **Rejected** |
| — | DCS / currency / sealed_elimination | — | — | blocked | **Deferred** |

## 5. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `multiplicative_aggregate` wholesale | 0025, 0047 sealed-wrong share MA surface; 0006/0013 not end-to-end MA |
| `piecewise_daily_hours_total` | 0013 lacks explicit month day-count token (30 never appears) |
| `nested_fraction_partition` | 0026 sealed-wrong shares fraction chain |
| `loose_inventory_boxing` | 0047 sealed-wrong shares divisive packing |
| DCS / currency / sealed_elimination | unchanged blocked set |

## 6. Research gate decision

**Proceed with dual narrow organs** — not wholesale `multiplicative_aggregate`.

Arena subagents converged:

- 0006 and 0013 do **not** share one safe organ (Sprint 6 decomposition reaffirmed).
- 0013 blocked on calendar grounding for wrong=0 self-verification.
- 0009 clears negative-evidence audit (no sealed-wrong neighbor bleed).
- 0006 admits typed sequential scale chain with body-scoped completeness.

## 7. Selected paradigm

**Dual-organ Sprint 10** (independently narrow, independently verified):

1. **Gate A2o `affine_comparative_inversion_total`** — `N more A than M×B` + conditional given + `total` aggregate question.
2. **Gate A2p `sequential_comparative_scale`** — initial `pages` + ordered `times longer` / `previous length` scale chain.

Rejected: broad MA parser, piecewise calendar without grounded days, 0004/0007 singletons, product_bridge, DCS injector.

## 8. Typed chains for target cases

**0009 (gold 185):** `chickens = (150−10)/4 = 35` → `total = 150+35 = 185`.

**0006 (gold 480):** `8×5×3×4 = 480` (running page-length scale chain; age/year scaffolding excluded from completeness).

**0013 (deferred):** needs `days_half = 30×½` but **30 is not in problem text**.

## 9. Implemented organs

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/affine_comparative_inversion_total.py` | `resolve_promotable_affine_comparative_inversion_total` |
| `generate/derivation/sequential_comparative_scale.py` | `resolve_promotable_sequential_comparative_scale` |

Wired in `generate/math_candidate_graph.py` after Gate A2n.

## 10. Before/after score

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| correct | 21 | **23** | +2 |
| refused | 29 | **27** | −2 |
| wrong | 0 | **0** | 0 |

**State A achieved:** 23/27/0 (target was 23+/27-/0).

## 11. Newly solved IDs

**0006**, **0009**

## 12. Preserved solved IDs

0001, 0002, 0003, 0005, 0008, 0010, 0014, 0015, 0017, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045, 0046

## 13. Wrong=0 proof

- Full train_sample replay: 23 / 27 / 0
- `tests/test_math_candidate_graph_sprint10_frontier_lift.py::TestTrainSampleScore`
- Holdout_dev: wrong=0 (no new admissions required)
- Smoke suite: 108 passed
- Regression lane: 272+ passed (excluding pre-existing `report.json` historical pin drift)

## 14. Confuser matrix

| Confuser | Organ | Result |
|----------|-------|--------|
| Actor mismatch in conditional | A2o | refuse |
| No conditional given | A2o | refuse |
| Yield / non-nested comparative | A2o | refuse |
| Asks age not pages | A2p | refuse |
| Doubled weight (holdout shape) | A2p | refuse |
| Single scale step only | A2p | refuse |
| MA 0025 basket shape | A2p | refuse |
| MA 0047 macaroon shape | A2p | refuse |
| 0013 calendar without day token | piecewise (deferred) | refuse |

## 15. Sibling generality proof

- A2o sibling: `6 more apples than 3× oranges` + conditional → `(42−6)/3+42`
- A2p sibling: `12 pages` + `3× longer` + `2× longer` + `5× previous` → `12×3×2×5`

## 16. Sealed-wrong negative evidence used

- Rejected wholesale MA: 0025 (group under-count), 0047 (remainder vs total)
- Rejected 0004: 0026 fraction/money chain
- Rejected 0007: 0047 divisive packing
- A2o/A2p confuser tests include 0025/0047 surface shapes

## 17. Composition-validation pin changes

**None.** No new cv rows; organs gated by self-verification only.

## 18. report.json untouched

Yes.

## 19. Sealed artifacts untouched

Yes.

## 20. No case-id logic

Yes.

## 21. No hardcoded answer

Yes.

## 22. No direct-answer shortcut

Yes.

## 23. Sprint 11 recommendation

**Primary:** Ratify `piecewise_daily_hours_total` only after calendar grounding policy — either require explicit month day-count in problem text or a pinned, tested month-length table with confusers (0014 single-rate, 0017 tariff, MA opener misparse).

**Secondary:** Revisit 0013 jointly with temporal exemplar `ta-v1-0001` injection design — not recognizer widening.

**Non-goals:** DCS (0032/0047), currency (0019/0028), sealed_elimination (0011/0026), 0004 nested fraction until 0026 confuser matrix, 0007 boxing until 0047 confuser matrix.

**Experience Flywheel:** Continue compaction; no serving promotion from flywheel alone until `lift_refused_to_correct > 0` with sealed-wrong clearance.