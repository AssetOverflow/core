# GSM8K Capability Paradigm Sprint 6 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **12** |
| refused | **38** |
| wrong | **0** |

After #816 (Experience Flywheel PR-1) and #815 (question_bound_product). Preserved solved: 0002, 0003, 0008, 0014, 0018, 0021, 0024, 0025, 0029, 0037, 0038, 0042.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint6.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| compacted_record_count | 50 |
| lift_refused_to_correct | **0** |
| promotion_candidates (all) | 4 families, **all** `blocked_by_wrong_risk` |

Top missing primitives: `relation_hypothesis` (15), `diagnostic_hold` (7), `multiplicative_aggregate` (3), `temporal_tariff` (2).

**Key signal:** No scout refused→correct delta remained (Sprint 5 already promoted 0003/0021). Flywheel ranked clusters by joint-refusal density + wrong-risk absence, not lift delta.

## 3. Scout/frontier output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 12 | 38 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- `lift_recommendations`: **[]**
- Dominant bottleneck: recognizer matched → no injection (27/50)
- Sealed-wrong elimination: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

## 4. Candidate families ranked

| Rank | Family | Cases | Lift signal | Wrong-risk | Sprint 6 verdict |
|------|--------|-------|-------------|------------|------------------|
| 1 | `multiplicative_aggregate:multiplicative_aggregation` | 0006, 0013, 0045 | joint only | none on surface | **Decomposed** — 0045 solvable as survey organ; 0006/0013 need other primitives |
| 2 | `temporal_tariff:temporal_aggregation` | 0001, 0017 | joint only | low | Deferred — tariff/overtime shapes |
| 3 | `relation_hypothesis:discrete_count_statement` | 13 joint + 2 wrong | none | **blocked** (0032, 0047) | Deferred — confuser-gated |
| — | `composition_validation` R5 pin | 0015 (`cv-0022`) | typed chain documented | low | **Selected (A2g)** |
| — | Survey earnings sub-shape of MA cluster | 0045 | typed chain | low | **Selected (A2h)** |

## 5. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `relation_hypothesis:DCS` | 0032, 0047 sealed-wrong share recognizer surface |
| `conservative_boundary` | 0018, 0025 sealed-wrong on served-correct cases |
| `sealed_elimination` | 0011, 0026 hard elimination |
| `diagnostic_hold:currency_amount` | 0019, 0028 sealed-wrong |

## 6. Selected paradigm

**Dual narrow organs** (experience-guided decomposition, not broad MA/DCS promotion):

1. **Gate A2g `duration_segment_total`** — R5 comparative middle-leg + fixed legs, total-time question (`cv-0022` / 0015).
2. **Gate A2h `survey_rate_earnings`** — `(surveys_a + surveys_b) × questions_per_survey × $/question` with money+earn question binding (0045 MA sub-shape).

Rejected wholesale `multiplicative_aggregate` promotion: subagent chain analysis showed 0006/0013 not end-to-end MA; 0045 only the survey slice is sound.

## 7. Typed chains for target cases

**0015 (gold 38):** `10 + (10×2) + 8` — subway leg, train leg = twice subway, bike leg; question binds `total` + `time`.

**0045 (gold 14):** `(3+4) × 10 × 0.2` — Mon/Tue survey counts, questions/survey, rate/question; question binds `money` + `earn`.

## 8. Implemented organs

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/duration_segment_total.py` | `resolve_promotable_duration_segment_total` |
| `generate/derivation/survey_rate_earnings.py` | `resolve_promotable_survey_rate_earnings` |

Wired in `generate/math_candidate_graph.py` after Gate A2f, before rate short-circuits.

## 9. Before / after score

| | Before | After |
|---|------:|------:|
| correct | 12 | **14** |
| refused | 38 | **36** |
| wrong | 0 | **0** |

## 10. Newly solved IDs

- `gsm8k-train-sample-v1-0015`
- `gsm8k-train-sample-v1-0045`

## 11. Preserved solved IDs

0002, 0003, 0008, 0014, 0018, 0021, 0024, 0025, 0029, 0037, 0038, 0042

## 12. Wrong=0 proof

Ephemeral train_sample: `14 / 36 / 0`. Holdout_dev scan: **0 admissions** for either new promotion bridge.

## 13. Confuser matrix

| Confuser | Result |
|----------|--------|
| Duration without total-time question | refuse |
| Survey without rate clause | refuse |
| Comparative survey count (twice Monday) | refuse |
| Fraction duration surface | refuse |
| 0047 partition/remaining weight | refuse |
| 0032 percent-less time | refuse |

## 14. Sibling generality proof

- Duration sibling: bus 5h + ferry 2×5h + walk 3h → 18
- Survey sibling: (2+5)×8×$0.50 → 28

## 15. Sealed-wrong negative evidence used

Flywheel `blocked_by_wrong_risk` on DCS/MA families informed refusal to promote broad injectors. Tests explicitly refuse 0047/0032 shapes on new gates.

## 16–21. Confirmations

- `report.json` untouched (historical pin)
- Sealed-lane artifacts untouched
- No case-id logic
- No hardcoded final answers
- No direct-answer extraction
- **Non-goals:** broad `product_bridge`, broad DCS/MA injectors, `resolve_pooled` re-wire, report rebaseline, sealed movement, 0030 round-trip/beach organ (deferred), DCS family until confusers pass

## Validation

```bash
git diff --check origin/main...HEAD
pytest tests/test_math_candidate_graph_sprint6_experience_guided_lift.py -q
pytest tests/test_gsm8k_experience_flywheel.py -q
pytest tests/test_gsm8k_sealed_attempt_scout.py -q
pytest tests/test_composition_validation_corpus.py -q
core test --suite smoke -q
```

Composition-validation snapshot: **10 solve / 12 refuse / 0 wrong** (`cv-0022` flipped).