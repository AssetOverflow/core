# GSM8K Capability Paradigm Sprint 11 — Lookback (2026-06-17)

## 1. Starting baseline

| Metric | Value |
|--------|------:|
| correct | **23** |
| refused | **27** |
| wrong | **0** |

After #823 (Sprint 10 dual-organ lift). Prerequisite satisfied.

## 2. Experience Flywheel output summary

`scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience-sprint11.json`

| Field | Value |
|-------|------:|
| retained_record_count | 50 |
| lift_refused_to_correct | **0** |
| scout serving | 23 / 27 / 0 |

Top signals:

- `multiplicative_aggregate:multiplicative_aggregation` — 0013 sole member; `not_promotable`, 0 sealed-wrong on surface tag.
- `already_served` — 23 cases; no flywheel promotion path.
- Blocked: DCS/relation_hypothesis (0032, 0047 neighbors), sealed_elimination (0011, 0026), currency (0019, 0028).

0013 remains the cleanest calendar/piecewise candidate; no sealed-wrong neighbor on the MA surface tag.

## 3. Scout/frontier/microscope output summary

| Regime | correct | refused | wrong |
|--------|--------:|--------:|------:|
| Serving | 23 | 27 | 0 |
| Sealed (resolve_pooled) | 3 | 39 | 8 |

- `lift_refused_to_correct`: **0**
- Dominant bottleneck: joint refusal (21/50)
- Sealed-wrong unchanged: 0011, 0018, 0019, 0025, 0026, 0028, 0032, 0047

Microscope: 0013 tagged `multiplicative_aggregate` / `temporal_aggregation`; adjacent solved temporal cases 0001, 0015, 0017 use distinct tariff/duration surfaces.

## 4. Candidate families ranked

| Rank | Family | Cases | Lift | Wrong-risk | Verdict |
|------|--------|-------|------|------------|---------|
| 1 | `calendar_grounded_piecewise_daily_hours_total` | 0013 | +1 | low–medium | **Selected (A2q)** |
| 2 | `multiplicative_aggregate` wholesale | 0013 | +1? | high (0025, 0047) | **Rejected** |
| 3 | Scout singletons (0004/0007) | — | +1 each | high neighbors | **Deferred** |
| — | DCS / currency / sealed_elimination | — | — | blocked | **Deferred** |

## 5. ClusterContract

```yaml
ClusterContract:
  family_id: calendar_grounded_piecewise_daily_hours_total
  proposed_organs:
    - piecewise_daily_hours_total (Gate A2q)
    - calendar_grounding (civil_month_day_count_table substrate)
  included_cases:
    - gsm8k-train-sample-v1-0013
  explicitly_excluded_cases:
    - gsm8k-train-sample-v1-0001  # temporal tariff overtime
    - gsm8k-train-sample-v1-0014  # rate conversion
    - gsm8k-train-sample-v1-0015  # duration segment total
    - gsm8k-train-sample-v1-0017  # bundle overflow tariff
    - gsm8k-train-sample-v1-0025  # MA sealed-wrong
    - gsm8k-train-sample-v1-0047  # DCS/divisive sealed-wrong
    - February / odd-day-month halfway confusers
  positive_anchors:
    - "N one-hour {content} each day" → N hours/day
    - "halfway through {NamedMonth}"
    - "doubled the number of video hours" + "remaining days"
    - "total … hours … end of the month"
  negative_anchors:
    - money/tariff ($, overtime, rent)
    - vague month ("about a month", "several weeks")
    - February without leap policy
    - odd-day-month halfway (31-day months)
    - asks daily rate / first period only
    - MA/DCS packing surfaces
  actor_binding_rule: leading subject before comma must appear in upload opener
  target_binding_rule: question must ask total hours at end of month (what/how + total + hours + month)
  unit_binding_rule: answer unit is hours; daily rate derived from one-hour event count
  quantity_obligations:
    - text-grounded daily event count (10)
    - table-grounded month span (June→30, provenance calendar_table)
    - comparative cues doubled, halfway, remaining
  allowed_external_grounding:
    - civil_month_day_count_table (fixed non-leap civil year)
  grounding_provenance: calendar_table:{month_name}
  blocked_sibling_families:
    - temporal_tariff
    - duration_segment_total
    - multiplicative_aggregate wholesale
    - rate_conversion
  composition_validation_pins: none changed (cv-0013 remains permanent refuse)
  required_confusers:
    - February, January-halfway, vague month, no month, asks rate, first-period-only
    - 0001/0017 tariff, 0015 duration, 0014 rate, 0025 MA
  serving_admission_rule: resolve_promotable_piecewise_daily_hours_total() after self-verification
  implementation_allowed: true
  reason: Typed chain + explicit table provenance + confuser matrix clears wrong-risk neighbors; only 0013 in train_sample — sibling proven via synthetic September case.
```

## 6. Calendar grounding policy decision

**Ratified for serving** with narrow constraints:

- Fixed `CIVIL_MONTH_DAY_COUNT` table (12 months, non-leap).
- February **serving-blocked** (leap ambiguity).
- Halfway split only on **even** day-count months (30-day civil months).
- Month operand provenance `calendar_table:{month}`; month **name** must appear in text.
- Not reconstruction-over-storage: table is a deterministic construction boundary, not vault memory.
- Not hidden normalization: no hot-path repair; table consulted only at organ admission.
- Not answer memorization: arithmetic recomputed from text rate + table span + comparative cues.

## 7. Blocked families and why

| Family | Blocked because |
|--------|-----------------|
| `multiplicative_aggregate` wholesale | 0025/0047 sealed-wrong; 0013 is piecewise not MA |
| DCS / currency / sealed_elimination | unchanged blocked set |
| February calendar | leap-year policy not ratified |
| 31-day halfway split | odd half-days ambiguous under table policy |
| Scout singletons 0004/0007 | 0026/0047 sealed-wrong neighbors |

## 8. Research gate decision

**Proceed** with ClusterContract-backed Gate A2q. Calendar table grounding is doctrinally safe under explicit provenance and narrow admission. State A (25+) not reachable with single train_sample member; fallback 24/26/0 accepted.

## 9. Selected paradigm

**ClusterContract organ bundle:**

1. `generate/derivation/calendar_grounding.py` — civil month table + provenance
2. `generate/derivation/piecewise_daily_hours_total.py` — Gate A2q piecewise organ

Wired in `generate/math_candidate_graph.py` after Gate A2p.

## 10. Typed chains for target cases

**0013 (gold 450):**

- daily_hours = 10 (10 one-hour videos/day)
- month_days = 30 (calendar_table:june)
- half_days = 15 (halfway through June)
- period1 = 10 × 15 = 150
- period2 = (10 × 2) × 15 = 300 (doubled remaining days)
- total = 450

## 11. Implemented organ(s)

| Module | Promotion entry |
|--------|-----------------|
| `generate/derivation/calendar_grounding.py` | `resolve_month_grounding()` |
| `generate/derivation/piecewise_daily_hours_total.py` | `resolve_promotable_piecewise_daily_hours_total()` |

## 12. Before/after score

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| correct | 23 | **24** | +1 |
| refused | 27 | **26** | −1 |
| wrong | 0 | **0** | 0 |

**Fallback achieved:** 24/26/0 + ratified ClusterContract. State A (25+) not reached — no second train_sample member in contract.

## 13. Newly solved IDs

**0013**

## 14. Preserved solved IDs

0001, 0002, 0003, 0005, 0006, 0008, 0009, 0010, 0014, 0015, 0017, 0018, 0021, 0024, 0025, 0029, 0030, 0035, 0037, 0038, 0042, 0045, 0046

## 15. Wrong=0 proof

- Full train_sample replay: 24 / 26 / 0
- `tests/test_math_candidate_graph_sprint11_cluster_contract_lift.py`
- Holdout_dev: wrong=0
- Smoke suite: 108 passed
- Regression lane: 307+ passed

## 16. Confuser matrix

| Confuser | Result |
|----------|--------|
| February halfway | refuse |
| January odd-month halfway | refuse |
| No named month | refuse |
| "about a month" | refuse |
| Asks daily rate | refuse |
| First period only | refuse |
| 0001 overtime tariff | refuse |
| 0017 bundle tariff | refuse |
| 0015 duration segment | refuse |
| 0014 rate conversion | refuse |
| 0025 MA shape | refuse |

## 17. Sibling generality proof

Synthetic September sibling: 6 one-hour episodes/day, halfway through September, doubled remaining → 6×15 + 12×15 = **270** (tested).

## 18. Sealed-wrong negative evidence used

- Rejected wholesale MA: 0025, 0047 confuser shapes refuse A2q
- Temporal tariff 0001/0017: $/overtime/rent blockers
- Duration 0015: no piecewise month surface

## 19. Composition-validation pin changes

**None.**

## 20. report.json untouched

Yes.

## 21. sealed artifacts untouched

Yes.

## 22. no case-id logic

Yes.

## 23. no hardcoded answer

Yes.

## 24. no direct-answer shortcut

Yes.

## 25. whether this enables bigger bundled lifts

**Yes, substrate-first.** The ClusterContract + `calendar_grounding` module is reusable for future organs that share:

- named-month whole-span grounding
- explicit `calendar_table` provenance
- shared confuser matrix (February, odd-month halfway, vague spans)

Next bundled lift could add a second organ under the same contract (e.g. uniform daily rate without doubling) once practice lane shows sibling coverage.

## 26. Sprint 12 recommendation

1. **Primary:** Scout-decomposed singleton with lowest sealed-wrong adjacency — re-audit **0004** only if nested-fraction confuser matrix against 0026 is ratified; otherwise **0007** only after 0047 divisive confuser matrix.
2. **ClusterContract extension:** Add second piecewise organ (uniform month total without rate change) under same calendar contract if practice/holdout cases appear — do not broaden to generic calendar parser.
3. **Blocked:** DCS 0032/0047, currency 0019/0028, sealed_elimination 0011/0026, wholesale MA.
4. **Experience Flywheel:** Continue compaction; no serving promotion from flywheel until `lift_refused_to_correct > 0` with sealed-wrong clearance.
5. **Target:** 25+/25-/0 requires either a second train_sample case under an existing contract or a verified singleton mini-family with sibling tests.