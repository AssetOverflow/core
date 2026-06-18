# GSM8K Capability Strike Batch 2 — Lookback (2026-06-17)

## Selected target

- **Primary case:** `gsm8k-train-sample-v1-0008` (Marnie bead bracelets)
- **Family:** `container_of_product` (stmt) + `yield_question` (question) composing into existing `unit_partition`

## Before / after (live ephemeral)

| Metric | Before (#810) | After (this branch) |
|--------|---------------|---------------------|
| correct | 7 | **8** |
| refused | 43 | **42** |
| wrong | 0 | **0** |

**Newly admitted:** `0008`  
**Preserved admissions:** `0002`, `0014`, `0018`, `0024`, `0029`, `0038`, `0042`

## Implementation slice

1. **`_bags_of_product_candidates`** — `N <container> of M <unit>` under closed acquisition verbs; conjoined sum when units match.
2. **`_pattern_yield_question_candidates`** — `how many <product> will <entity> be able to make` with rate inferred from `If N <unit> are used to make one <product>`.
3. **`CandidateUnknown` yield fields** — graph-build injects `unit_partition` (reuses Gate A2a solver path; no new op kind).
4. **`_bind_parser_pronoun_actor`** — extended to bind pronoun **entities** on `CandidateInitial` (She → Marnie via discourse prior).

## Anti-overfit evidence

- Sibling synthetics: Tom/marbles→displays (6), Alice/coins→charms (5).
- Confusers refuse: mismatched conjunct units, missing rate clause, product/rate mismatch, non-integer quotient.
- Regression: `0042` embedded-quantifier conditional-op path still admits 30.
- No case-id branches; no hardcoded answers.

## Hazards reviewed

| Hazard | Mitigation |
|--------|------------|
| Confuse bags-of with embedded-quantifier (in each) | Separate regex; `0042` regression test |
| Ingredient vs product count | `unit_partition` requires exact integer quotient; mismatched units refuse |
| Pronoun entity vs question entity | Discourse binding on initials + named entity in question |
| Completeness false-positive on "one" | Rate tokens `(n, "one")` on question candidate |

## Non-goals

- `report.json` untouched
- Sealed lanes untouched
- No `determine()` / FrameVerdict paths
- No broad DCS widening

## Files changed

- `generate/math_candidate_parser.py`
- `generate/math_candidate_graph.py`
- `tests/test_math_candidate_graph_container_of_product.py` (new)
- `tests/test_gsm8k_post_gate_a1_frontier_microscope.py` (live-count fixture update)
