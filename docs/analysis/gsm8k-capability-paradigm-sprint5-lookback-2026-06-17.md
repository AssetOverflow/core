# GSM8K Capability Paradigm Sprint 5 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **10** |
| refused | **40** |
| wrong | **0** |

After #814 (Gate A2e goal_residual). Preserved solved: 0002, 0008, 0014, 0018, 0024, 0025, 0029, 0037, 0038, 0042.

## 2. Scout / practice evidence

Scout (`scripts/gsm8k_sealed_attempt_scout.py --limit 50`):

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 10 | 40 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

**Top lift cluster:** `lift_skill_gap_recognized_no_injection_discrete_count_statement` — cases **0003**, **0021** (n=2). Sealed commits 864 and 450 via `relation_hypothesis:discrete_count_statement`; serving stops at DCS no-injection.

**Elimination signal (sealed wrong, serving refused):** 0011 (3200 vs 50), 0047 (240 vs 45), plus 6 `elimination_refused_to_wrong` — not promotable.

## 3. Candidate family clusters

| family_bucket | case_ids | serving failure | sealed behavior | missing primitive | expected lift | wrong-risk |
|---------------|----------|-----------------|-----------------|-------------------|---------------|------------|
| discrete_count_statement → product | 0003, 0021 | DCS no-injection | sealed correct | typed product chain | +2 | medium via product_bridge |
| goal_residual (served) | 0037 | — | already served | — | 0 | low |
| joint_sealed_no_resolution | 32 | parse/injection | refused | various | 0 | low |
| sealed_elimination | 0011, 0047, … | refused | sealed wrong | not product | 0 | high |

## 4. Why selected paradigm

**`question_bound_product_aggregate` (Gate A2f)** — practice proved the reasoning chain is valid for 0003/0021, but broad `product_bridge` over `resolve_pooled` admitted held-out wrong (e.g. holdout-dev 0345: fraction surface + `total weight` → 6720 vs 595).

Built a **first-principles organ** (not a pooled filter):

1. **Revenue chain:** container leaf × `in each` per-container leaf × `$`/`dollar`+`each` price (price may live in question clause); question binds `money` + `make|earn|raise|collect`.
2. **Weight-work chain:** single clause with exactly 3 distinct units, mass anchor, `for` cue, `search_chain` multiply-only; question binds `weight` + `total|move|lift|press`.

## 5. Rejected candidates

| Candidate | Why unsafe / lower leverage |
|-----------|----------------------------|
| Re-wire `product_bridge` | Held-out 5 wrong; admits fraction/comparative `total weight` surfaces |
| Broad DCS injection | Would multiply arbitrary co-occurring numbers |
| 0007 / 0047 / 0004 chunk | No sealed-correct signal; sealed wrong on 0047 |
| `resolve_pooled` wholesale | 17% wrong on holdout_dev per 2026-06-04 measurement |

## 6. Typed paradigm implemented

Module: `generate/derivation/question_bound_product.py`

- `build_question_bound_product()` — typed chain construction
- `compose_question_bound_product()` — self-verification gate
- `resolve_promotable_question_bound_product()` — serving promotion (Gate A2f)
- Wired in `generate/math_candidate_graph.py` after goal_residual, before rate short-circuits

## 7. Before / after score

| | Before | After |
|---|------:|------:|
| correct | 10 | **12** |
| refused | 40 | **38** |
| wrong | 0 | **0** |

## 8. Newly solved IDs

- `gsm8k-train-sample-v1-0003`
- `gsm8k-train-sample-v1-0021`

## 9. Preserved solved IDs

0002, 0008, 0014, 0018, 0024, 0025, 0029, 0037, 0038, 0042

## 10. Wrong=0 proof

Full ephemeral train_sample: `12 / 38 / 0`. Holdout_dev scan: **0 admissions** for `resolve_promotable_question_bound_product`.

## 11. Confuser matrix

| Confuser | Result |
|----------|--------|
| Fraction surface (holdout 0345 shape) | refuse |
| Tom donates / Sam sells | refuse (seller≠supplier) |
| Additive distractor (loose pens) | refuse |
| Rate without money/weight target | refuse |
| `more than` comparative | refuse |
| Revenue without `in each` | refuse |
| Weight without `for` cue | refuse |
| Known product_bridge held-out hazard | refuse |

## 12. Sibling generality proof

- Revenue sibling: 12 cartons × 30 in each × $1.25 → 450
- Weight sibling: 20 kg × 8 reps × 4 sets → 640
- No case-id logic; no hardcoded answers

## 13. product_bridge status

**Broad `product_bridge` stays disabled** in `math_candidate_graph.py`. Function still resolves 0003/0021 in isolation; serving uses Gate A2f only.

## 14–19. Confirmations

- `report.json` untouched (historical 6/44/0 pin)
- Sealed-lane artifacts untouched
- No case-id logic
- No hardcoded final answers
- No direct-answer extraction
- **Non-goals:** broad product_bridge, report rebaseline, sealed movement, determine()/CLOSE, generic multiplication of co-occurring numbers

## Validation

```bash
git diff --check origin/main
pytest tests/test_math_candidate_graph_question_bound_product_lift.py -q
pytest tests/test_gsm8k_sealed_attempt_scout.py -q
pytest tests/test_gsm8k_frontier_report.py -q
pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
pytest tests/test_math_candidate_graph_fraction_portion.py -q
pytest tests/test_math_candidate_graph_unit_partition_injection.py -q
pytest tests/test_math_candidate_graph_container_of_product.py -q
pytest tests/test_math_candidate_graph_peer_partition_question.py -q
pytest tests/test_math_candidate_graph_goal_residual_lift.py -q
pytest tests/test_adr_0195_product_bridge.py -q
pytest tests/test_composition_validation_corpus.py -q
# 151 passed
```