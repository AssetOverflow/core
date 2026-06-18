# GSM8K Capability Paradigm Sprint 7 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **14** |
| refused | **36** |
| wrong | **0** |

After #817 (Sprint 6: duration_segment_total + survey_rate_earnings). Preserved solved: 0002, 0003, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0037, 0038, 0042, 0045.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint7.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| compacted_record_count | 50 |
| lift_refused_to_correct | **0** |
| promotion_candidates | 4 families, **all** `blocked_by_wrong_risk` |

Top missing primitives: `relation_hypothesis` (DCS cluster), `diagnostic_hold`, `multiplicative_aggregate`, `temporal_tariff`.

**Key signal:** No scout refused→correct delta (Sprint 6 already promoted easy lifts). Flywheel ranked `joint_sealed_no_resolution` cluster (0004, 0005, 0007, 0009, 0010, **0030**, 0035, 0048, 0050) plus composition-validation pins for decomposition.

## 3. Scout/frontier output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 14 | 36 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- `lift_recommendations`: **[]**
- Dominant bottleneck: joint refusal (30/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

## 4. Candidate families ranked

| Rank | Family | Cases | Lift signal | Wrong-risk | Sprint 7 verdict |
|------|--------|-------|-------------|------------|------------------|
| 1 | `joint_sealed_no_resolution` + cv-0006 | **0030** | typed R5 round-trip chain | low | **Selected (A2i)** |
| 2 | `joint_sealed_no_resolution` + cv-0021 | **0035** | typed R4 giveaway-residual | low | **Selected (A2j)** |
| 3 | `temporal_tariff:temporal_aggregation` | 0001, 0017 | joint only | medium | Deferred — tariff/overtime |
| 4 | `multiplicative_aggregate` | 0006, 0013 | joint only | low surface | Deferred — chained age/video shapes |
| 5 | `relation_hypothesis:DCS` | 14 joint + 2 wrong | none | **blocked** (0032, 0047) | Deferred |
| 6 | `diagnostic_hold:currency_amount` | 0019, 0028 | sealed-wrong | **blocked** | Deferred |

## 5. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `relation_hypothesis:DCS` | 0032, 0047 sealed-wrong share recognizer surface |
| `conservative_boundary` | 0018, 0025 sealed-wrong on served-correct cases |
| `sealed_elimination` | 0011, 0026 hard elimination |
| `diagnostic_hold:currency_amount` | 0019, 0028 sealed-wrong |

## 6. Selected paradigm

**Dual narrow organs** (composition-validation decomposition, not broad family promotion):

1. **Gate A2i `round_trip_trip_duration`** — one-way drive ×2 (each way) + comparative activity duration vs total driving; trip-time question (`cv-0006` / 0030).
2. **Gate A2j `giveaway_target_residual`** — possession − stated remainder − Σ giveaways (including `N more than` prior recipient); distinct from goal-residual (`cv-0021` / 0035).

Rejected wholesale DCS/MA/temporal_tariff promotion: flywheel blocked or joint-only without typed end-to-end chains.

## 7. Typed chains for target cases

**0030 (gold 14):** `2 + 2 = 4` driving → `4 × 2.5 = 10` beach → `4 + 10 = 14` trip total.

**0035 (gold 4):** `20 − 4 = 16` to give → `−5` Jane → `−5 − 2` James (2 more than Jane) → `4` more needed.

## 8. Implemented organs

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/round_trip_trip_duration.py` | `resolve_promotable_round_trip_trip_duration` |
| `generate/derivation/giveaway_target_residual.py` | `resolve_promotable_giveaway_target_residual` |

Wired in `generate/math_candidate_graph.py` after Gate A2h, before rate short-circuits.

## 9. Before / after score

| | Before | After |
|---|------:|------:|
| correct | 14 | **16** |
| refused | 36 | **34** |
| wrong | 0 | **0** |

## 10. Newly solved IDs

- `gsm8k-train-sample-v1-0030`
- `gsm8k-train-sample-v1-0035`

## 11. Preserved solved IDs

0002, 0003, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0037, 0038, 0042, 0045

## 12. Wrong=0 proof

Ephemeral train_sample: `16 / 34 / 0`. Holdout_dev scan: **0 admissions** for either new gate.

## 13. Confuser matrix

| Confuser | Result |
|----------|--------|
| Round trip without `each way` | refuse |
| Fraction/percent duration surface | refuse |
| Goal-language giveaway (cv-0005) | refuse giveaway organ; goal_residual still serves |
| Comparative giveaway question (`more than Jane`) | refuse |
| Duration segment total (0015) | refuse round-trip organ |
| 0032 percent-time shape | refuse |
| 0047 partition weight shape | refuse |

## 14. Sibling generality proof

- Round-trip sibling: 3h each way, 2× driving at lake → 18h trip
- Giveaway sibling: 30 oranges, 8 + (8+3) given, leave 6 → 5 more

## 15. Sealed-wrong negative evidence used

Flywheel `blocked_by_wrong_risk` on DCS/currency families informed refusal to promote broad injectors. Tests refuse 0032/0047 shapes on new gates.

## 16–21. Confirmations

- `report.json` untouched (historical pin)
- Sealed-lane artifacts untouched
- No case-id logic
- No hardcoded final answers
- No direct-answer extraction
- **Non-goals:** broad `product_bridge`, broad DCS/MA injectors, temporal_tariff organ, `resolve_pooled` re-wire, report rebaseline, sealed movement

## Sprint 8 handoff recommendation

**Recommended track: Track A — Capability Sprint 8**

| Field | Value |
|-------|-------|
| Evidence | Flywheel still shows dense `joint_sealed_no_resolution` cluster; composition-validation pins **cv-0007** (0005 fraction temp), **cv-0008** (0046 percent partition), and **cv-0021**-sibling **cv-0005** already served — next clean typed chains are affine/fraction (0005, 0046) and temporal_tariff (0001, 0017) after confuser design |
| Target families | `affine_equation` / R6 fraction-decrease (0005), percent-partition (0046); secondary: `temporal_tariff` (0001, 0017) |
| Blocked families | DCS (0032/0047), currency_amount (0019/0028), sealed_elimination (0011/0026) |
| Expected movement | +1–2 correct if R6 fraction or percent-partition organ passes wrong=0 adversary |
| Required modules | `generate/derivation/<family>.py`, `tests/test_math_candidate_graph_<family>_sprint8_lift.py` |
| Non-goals | Experience Flywheel PR-2 until lift_refused_to_correct > 0 or promotion_candidates unblock; no broad DCS until confusers pass |

Track B (Flywheel PR-2) deferred: no `promotion_candidates` with safe lift signal yet. Track C (Diagnostic Hardening) not warranted — two clean organs lifted this sprint.

## Validation

```bash
git diff --check origin/main...HEAD
pytest tests/test_math_candidate_graph_sprint7_experience_guided_lift.py -q
pytest tests/test_gsm8k_experience_flywheel.py -q
pytest tests/test_gsm8k_sealed_attempt_scout.py -q
pytest tests/test_composition_validation_corpus.py -q
core test --suite smoke -q
```

Composition-validation snapshot: **12 solve / 10 refuse / 0 wrong** (`cv-0006`, `cv-0021` flipped).