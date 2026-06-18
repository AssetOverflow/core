# GSM8K Capability Strike Batch 3 — Lookback (2026-06-17)

## Scope

Gate A2d `peer_partition_question` lift on train_sample case **0025**.

## Baseline (honest, ephemeral, pre-change)

Measured via `build_report()` on `origin/main` at #811 merge (708f27a2):

| Metric | Value |
|--------|-------|
| correct | **8** |
| refused | **42** |
| wrong | **0** |

Committed `report.json` remains **6/44/0** (historical pin; not rebaselined).

## After (ephemeral live scoring)

| Metric | Value |
|--------|-------|
| correct | **9** |
| refused | **41** |
| wrong | **0** |

**Newly admitted:** `gsm8k-train-sample-v1-0025`  
**Preserved:** `0002`, `0008`, `0014`, `0018`, `0024`, `0029`, `0038`, `0042`

## Family implemented

**`peer_partition_question`** — closed conditional + total-across question:

- Conditional: `If N of <Entity>'s friends pick the same amount as her/him`
- Question: `How many <unit> do <Entity> and her/his friends pick in all?`
- Graph injects `multiply` by `(1 + N)` on the anchor entity's unit state after WAVE-A statement ingestion.

## Why not overfit

- No case-id branches or hardcoded answers.
- Regex family generalizes across entities, units, and numeric/word friend counts.
- Sibling tests vary names, counts, and units (Tom/apples, Alice/strawberries).
- Confusers refuse: missing conditional, entity mismatch, indefinite quantifier, comparative 0007 unchanged.
- Reuses existing `multiply` solver path and WAVE-A `multiplicative_aggregate` statement injection.

## Deferred candidates (Arena)

| Case | Blocker |
|------|---------|
| 0007 | Pattern B comparative detection-only + multi-entity inverse residual |
| 0047 | Equal-N bag split ≠ `unit_partition` v1 |
| 0004 | Nested fraction referent binding beyond Gate A2b |

## Non-goals

- No `report.json` rebaseline.
- No sealed-lane movement.
- No `determine()` / `answer=False`.
- No `unit_partition` extension for equal-bag distribution.

## Validation

```bash
git diff --check origin/main...HEAD
pytest tests/test_math_candidate_graph_peer_partition_question.py -q
pytest tests/test_math_candidate_graph_fraction_portion.py -q
pytest tests/test_math_candidate_graph_unit_partition_injection.py -q
pytest tests/test_recognizer_unit_partition_inject.py -q
pytest tests/test_math_candidate_graph_container_of_product.py -q
pytest tests/test_gsm8k_frontier_report.py -q
pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
```