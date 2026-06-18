# GSM8K Capability Paradigm Sprint 9 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **18** |
| refused | **32** |
| wrong | **0** |

After #819 (Sprint 8: fraction_decrease + percent_partition). Preserved solved: 0002, 0003, 0005, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045, 0046.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint9.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| lift_refused_to_correct | **0** |
| promotion_candidates | 4 families, **all** `blocked_by_wrong_risk` |

Top missing primitives: `temporal_tariff` (0001, 0017), `relation_hypothesis` (DCS), `diagnostic_hold` (currency).

**Key signal:** `temporal_tariff:temporal_aggregation` cluster (0001, 0017) has **zero sealed-wrong** neighbors — joint refusal only. `affine_equation_fraction_delta` (0010) sits in `joint_sealed_no_resolution` with zero sealed-wrong. Both families outrank blocked DCS/currency clusters for Sprint 9.

## 3. Scout/frontier/microscope output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 18 | 32 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- Dominant bottleneck: joint refusal (26/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

Microscope slices: `no_injection_temporal_aggregation` (0001, 0017), `affine_equation_fraction_delta` (0010).

## 4. Candidate families ranked

| Rank | Family | Cases | Lift signal | Wrong-risk | Sprint 9 verdict |
|------|--------|-------|-------------|------------|------------------|
| 1 | `temporal_tariff` overtime | **0001** | typed threshold + ½ OT + days | low | **Selected (A2m-A)** |
| 2 | `temporal_tariff` bundle overflow | **0017** | typed per-day-or-bundle + rental days | low | **Selected (A2m-B)** |
| 3 | `affine_fraction_delta` | **0010** | typed N/M-more-than-reference + plus K | low | **Selected (A2n)** |
| 4 | `multiplicative_aggregate` | 0006, 0013 | joint only | medium | Deferred |
| 5 | `relation_hypothesis:DCS` | 14 joint + 2 wrong | none | **blocked** (0032, 0047) | Deferred |
| 6 | `diagnostic_hold:currency_amount` | 0019, 0028 | sealed-wrong | **blocked** | Deferred |

## 5. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `relation_hypothesis:DCS` | 0032, 0047 sealed-wrong share discrete-count / partition surface |
| `conservative_boundary` | 0018, 0025 sealed-wrong on served-correct cases |
| `sealed_elimination` | 0011, 0026 hard elimination |
| `diagnostic_hold:currency_amount` | 0019, 0028 sealed-wrong; vet-insurance / profit-recovery shapes |

## 6. Selected paradigm

**Dual-organ Sprint 9** (Sprint 8 handoff targets; no cleaner family outranked on wrong-risk):

1. **Gate A2m `temporal_tariff`** — two typed sub-patterns in one module:
   - **Overtime shift earnings:** hourly rate + `more than N hours` threshold + `1/2` OT premium + hours/day × days.
   - **Bundle overflow tariff:** `$A per day or $B for C days` + rental days `> C` → `B + (rental−C)×A`.
2. **Gate A2n `affine_fraction_delta`** — prior initial-loss mutation establishes reference; `N/M more than what <entity> currently has, plus K` → `reference × (N/M) + K` (GSM8K gold semantics for 0010).

Rejected: broad temporal parser, generic affine equation parser, broad product_bridge, DCS injector.

**Research note:** No alternative family offered higher lift with lower wrong-risk than the Sprint 8 handoff targets. `multiplicative_aggregate` remains joint-only without end-to-end typed chains.

## 7. Typed chains for target cases

**0001 (gold 990):** Regular `8×18×5=720` + OT `(10−8)×(18+9)×5=270` → **990**.

**0017 (gold 800):** Bundle `500` + overflow `(20−14)×50=300` → **800**.

**0010 (gold 9):** Yun current `20−12=8` → Marion `8×(1/4)+7=9`.

## 8. Implemented organs

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/temporal_tariff.py` | `resolve_promotable_temporal_tariff` |
| `generate/derivation/affine_fraction_delta.py` | `resolve_promotable_affine_fraction_delta` |

Wired in `generate/math_candidate_graph.py` after Gate A2l, before rate short-circuits.

**Review hardening:** `percent_partition` now refuses subgroup-quantity-as-total confusers (`"girls group has 50"`).

## 9. Before/after score

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| correct | 18 | **21** | +3 |
| refused | 32 | **29** | −3 |
| wrong | 0 | **0** | 0 |

**State A exceeded:** 21/29/0 (target was 20+/30-/0).

## 10. Newly solved IDs

**0001**, **0010**, **0017**

## 11. Preserved solved IDs

0002, 0003, 0005, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045, 0046

## 12. Wrong=0 proof

- Full train_sample replay: 21 correct / 29 refused / 0 wrong
- `tests/test_math_candidate_graph_sprint9_temporal_affine_lift.py::TestTrainSampleScore`
- Composition-validation firewall: 14 solve / 8 refuse / 0 wrong
- Holdout_dev: 0 new organ admissions
- Smoke suite: 108 passed
- Full regression lane: 313 passed

## 13. Confuser matrix

| Confuser | Organ | Result |
|----------|-------|--------|
| 0019 vet + insurance | A2m | refused |
| 0028 amusement profit recovery | A2m | refused |
| OT asks hours not money | A2m | refused |
| Bundle rental ≤ bundle period | A2m | refused |
| 0005 fraction-decrease | A2n | refused (A2k serves) |
| Twice-as-many comparative | A2n | refused |
| 0032 percent time-decrease | A2m | refused |
| Subgroup-as-total percent partition | A2l | refused (hardened) |

## 14. Sibling generality proof

| Sibling | Gold | Organ |
|---------|-----:|-------|
| Rosa $20/hr, 6hr threshold, 9hr×4 days | 840 | A2m overtime |
| $40/day or $300/10d, 15-day rental | 500 | A2m bundle |
| Sam 20−4 marbles, 1/4 more + 3 | 7 | A2n affine |

## 15. Sealed-wrong negative evidence used

- 0019/0028 currency_amount flywheel `blocked_by_wrong_risk` → A2m hazard blockers (insurance, profit, percent, amusement, vet)
- 0032 percent-decrease → A2m hazard refusal
- DCS 0032/0047 → no partition/tariff broadening

## 16. Composition-validation pin changes

No new cv pins flipped this sprint (0001/0010/0017 lack dedicated cv rows). Aggregate snapshot unchanged: **14/8/0**.

## 17. report.json untouched

`evals/gsm8k_math/train_sample/v1/report.json` not modified.

## 18. Sealed artifacts untouched

No changes to sealed practice lanes, holdout, or `resolve_pooled` wiring.

## 19. No case-id logic

Promotion is family-typed only; no `case_id` conditionals in serving path.

## 20. No hardcoded answer

Answers derived from grounded arithmetic chains; no answer literals.

## 21. No direct-answer shortcut

No `answer_numeric` extraction or final-answer parsing.

## 22. Sprint 10 recommendation

**Track A — Capability Sprint 10** (continue capability paradigm)

| Evidence | Detail |
|----------|--------|
| Flywheel | `lift_refused_to_correct == 0`; 29 refusals remain, mostly `joint_sealed_no_resolution` |
| Next targets | `multiplicative_aggregate` cluster (0006, 0013) — only with typed end-to-end chain + confuser matrix |
| Secondary | `joint_sealed_no_resolution` singletons with clean decomposition (0004 fraction, 0007 divisive, 0009 additive) — case-by-case after scout decomposition |
| Blocked | DCS (0032/0047), currency_amount (0019/0028), sealed_elimination (0011/0026) |
| Expected lift | +1–2 correct if MA organ passes adversarial review; else diagnostic hardening |
| Non-goals | Flywheel PR-2, broad product_bridge, DCS injector, report.json rebaseline |

Track B (Experience Flywheel PR-2) deferred until joint-refusal cluster lacks typed promotable chains.