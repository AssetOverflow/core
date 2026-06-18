# GSM8K Capability Strike Batch 4 — Lookback (2026-06-17)

## Scout-guided target selection

Scout run (`scripts/gsm8k_sealed_attempt_scout.py --limit 50`) on #813 baseline:

| Serving | Sealed (resolve_pooled) |
|---------|-------------------------|
| 9 / 41 / 0 | 3 / 39 / 8 |

**Top lift recommendations:**

1. `lift_skill_gap_recognized_no_injection_discrete_count_statement` — cases **0003**, **0021** (n=2)
2. Same family — case **0037** (n=1)

**Scout interpretation:** First refusal on 0037 is DCS no-injection on the goal clause, but sealed/aggressive `compose_goal_residual` already commits **3.0**. The coherent family is **goal_residual** (R4), not discrete_count_statement injection.

**Deferred (scout + bisection):**

- **0003/0021** — `resolve_promotable_product` works on train_sample but product_bridge is **0 correct / 5 wrong** on held-out 1,319; stays disabled.
- **0007/0047/0004** — no sealed-correct signal; higher wrong-risk.

## Baseline (ephemeral, pre-change)

| Metric | Value |
|--------|-------|
| correct | **9** |
| refused | **41** |
| wrong | **0** |

Committed `report.json` unchanged (6/44/0 historical pin).

## After (ephemeral live scoring)

| Metric | Value |
|--------|-------|
| correct | **10** |
| refused | **40** |
| wrong | **0** |

**Newly admitted:** `gsm8k-train-sample-v1-0037`  
**Preserved:** `0002`, `0008`, `0014`, `0018`, `0024`, `0025`, `0029`, `0038`, `0042`

## Family implemented

**Gate A2e `goal_residual_question`** — re-wired serving promotion for `resolve_promotable_goal_residual` only:

- Goal anchor: `wants/needs/...` + single goal quantity
- Progress clauses: licensed change cues, same referent, all **subtract**
- Question: residual-to-goal (`meet goal`, `how much more`, …)
- Self-verification gate: `compose_goal_residual` (grounding ∧ unit ∧ completeness ∧ uniqueness)

**product_bridge stays disabled** (held-out wrong=0 breach).

## Why not overfit

- No case-id branches; uses existing R4 production + gain-goal divergence firewall (`test_r4_goal_residual.py`).
- Sibling: Maria save/earn goal → 9 (not 31 possession trap).
- Confusers refuse: no goal language, no residual question, cross-referent progress.
- 0003/0021 still refuse (product bridge off).
- Held-out bisection documented goal_residual **0/0** (inert); product **5 wrong**.

## Validation

```bash
git diff --check origin/main...HEAD
pytest tests/test_math_candidate_graph_goal_residual_lift.py -q
pytest tests/test_gsm8k_sealed_attempt_scout.py -q
pytest tests/test_gsm8k_frontier_report.py -q
pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
pytest tests/test_math_candidate_graph_fraction_portion.py -q
pytest tests/test_math_candidate_graph_unit_partition_injection.py -q
pytest tests/test_math_candidate_graph_container_of_product.py -q
pytest tests/test_math_candidate_graph_peer_partition_question.py -q
```

## Non-goals

- No product_bridge re-wire (0003/0021).
- No report.json rebaseline.
- No sealed-lane movement.
- No DCS injector widening for `wants to lose` as InitialPossession.