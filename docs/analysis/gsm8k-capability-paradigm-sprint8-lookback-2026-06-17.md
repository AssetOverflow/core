# GSM8K Capability Paradigm Sprint 8 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **16** |
| refused | **34** |
| wrong | **0** |

After #818 (Sprint 7: round_trip_trip_duration + giveaway_target_residual). Preserved solved: 0002, 0003, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint8.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| lift_refused_to_correct | **0** |
| promotion_candidates | 4 families, **all** `blocked_by_wrong_risk` |

Top missing primitives: `relation_hypothesis` (DCS), `multiplicative_aggregate`, `temporal_tariff`, `diagnostic_hold`.

**Key signal:** No scout refused→correct delta (prior sprints already promoted clean lifts). Composition-validation pins **cv-0007** (0005 fraction-decrease) and **cv-0008** (0046 percent-partition) provided typed R6 chains with low wrong-risk — aligned with Sprint 7 handoff.

## 3. Scout/frontier output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 16 | 34 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- Dominant bottleneck: joint refusal (28/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

Microscope slices: `affine_equation_fraction_target` (0005), `affine_equation` / percent partition (0046).

## 4. Candidate families ranked

| Rank | Family | Cases | Lift signal | Wrong-risk | Sprint 8 verdict |
|------|--------|-------|-------------|------------|------------------|
| 1 | R6 fraction-decrease (`cv-0007`) | **0005** | typed `base × (1−N/M)` | low | **Selected (A2k)** |
| 2 | R6 percent-partition (`cv-0008`) | **0046** | typed half-split + dual % | low | **Selected (A2l)** |
| 3 | `temporal_tariff:temporal_aggregation` | 0001, 0017 | joint only | medium | Deferred — confuser design |
| 4 | `affine_equation_fraction_delta` | 0010 | joint only | medium | Deferred — 1/4 more than affine |
| 5 | `relation_hypothesis:DCS` | 14 joint + 2 wrong | none | **blocked** (0032, 0047) | Deferred |
| 6 | `diagnostic_hold:currency_amount` | 0019, 0028 | sealed-wrong | **blocked** | Deferred |

## 5. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `relation_hypothesis:DCS` | 0032, 0047 sealed-wrong share discrete-count / partition surface |
| `conservative_boundary` | 0018, 0025 sealed-wrong on served-correct cases |
| `sealed_elimination` | 0011, 0026 hard elimination |
| `diagnostic_hold:currency_amount` | 0019, 0028 sealed-wrong |

## 6. Selected paradigm

**Dual narrow R6 organs** (composition-validation decomposition, not generic affine parser):

1. **Gate A2k `fraction_decrease`** — forecast ``decrease to N/M of`` + explicit current base + question asks **decrease by** delta (`cv-0007` / 0005).
2. **Gate A2l `percent_partition`** — total population + equal ``half`` / ``other half`` split + two ``N% of the <group>`` clauses + aggregate ownership question (`cv-0008` / 0046).

Rejected: broad product_bridge, DCS injector, generic affine equation parser, temporal_tariff wholesale promotion.

## 7. Typed chains for target cases

**0005 (gold 21):** `84 × (1 − 3/4) = 84 × 1/4 = 21` degrees decrease.

**0046 (gold 15):** `100 × 0.5 = 50` per group → `50 × 0.20 = 10` girl dog owners → `+ 50 × 0.10 = 5` boy dog owners → `15` total.

## 8. Implemented organs

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/fraction_decrease.py` | `resolve_promotable_fraction_decrease` |
| `generate/derivation/percent_partition.py` | `resolve_promotable_percent_partition` |

Wired in `generate/math_candidate_graph.py` after Gate A2j, before rate short-circuits.

## 9. Before/after score

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| correct | 16 | **18** | +2 |
| refused | 34 | **32** | −2 |
| wrong | 0 | **0** | 0 |

**State A met:** 18+/32-/0.

## 10. Newly solved IDs

**0005**, **0046**

## 11. Preserved solved IDs

0002, 0003, 0008, 0014, 0015, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045

## 12. Wrong=0 proof

- Full train_sample replay: 18 correct / 32 refused / 0 wrong
- `tests/test_math_candidate_graph_sprint8_r6_affine_lift.py::TestTrainSampleScore`
- Composition-validation firewall: 14 solve / 8 refuse / 0 wrong
- Holdout_dev: 0 new organ admissions
- Smoke suite: 108 passed

## 13. Confuser matrix

| Confuser | Organ | Result |
|----------|-------|--------|
| 0010 affine `1/4 more than` | A2k | refused |
| Final-value question (not decrease-by) | A2k | refused |
| Unequal 60/40 split (not half/half) | A2l | refused |
| 0032 percent time-decrease | A2l | refused |
| 0047 DCS equal-pack | A2l | refused |
| Goal-residual (cv-0005) | A2k | refused (goal_residual serves) |

## 14. Sibling generality proof

| Sibling | Gold | Organ |
|---------|-----:|-------|
| Cedar peak 2/3 decrease, 60° base | 20 | A2k |
| Club 80 members, 25%/15% half-split | 16 | A2l |

## 15. Sealed-wrong negative evidence used

- 0032 percent-decrease shape → A2l hazard refusal (not sequential % chain)
- 0047 equal-pack DCS → A2l hazard refusal (no half-split / no % of group)
- DCS flywheel `blocked_by_wrong_risk` → no broad partition injector

## 16. Composition-validation pin changes

| Pin | Before | After |
|-----|--------|-------|
| cv-0007 (0005) | refuse | **solve** (21) |
| cv-0008 (0046) | refuse | **solve** (15) |

Aggregate snapshot: 12/10/0 → **14/8/0**

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

## 22. Sprint 9 recommendation

**Track A — Capability Sprint 9** (continue capability paradigm)

| Evidence | Detail |
|----------|--------|
| Flywheel | `lift_refused_to_correct == 0`; dense `joint_sealed_no_resolution` cluster remains |
| Next targets | `temporal_tariff` (0001, 0017) after confuser matrix; `affine_equation_fraction_delta` (0010) |
| Secondary | `multiplicative_aggregate` joint cluster (0006, 0013) — only with hard verifier |
| Blocked | DCS (0032/0047), currency_amount (0019/0028), sealed_elimination (0011/0026) |
| Expected lift | +1–2 correct if temporal_tariff organ passes adversarial review |
| Modules | `generate/derivation/temporal_tariff.py` (proposed) |
| Non-goals | Flywheel PR-2, broad product_bridge, DCS injector, report.json rebaseline |

Track B (Experience Flywheel PR-2) and Track C (Diagnostic Hardening) deferred — flywheel still shows promotable typed chains in joint-refusal cluster, not exclusively wrong-risk blockage.