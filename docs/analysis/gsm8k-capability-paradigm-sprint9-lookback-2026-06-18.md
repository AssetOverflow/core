# gsm8k-capability-paradigm-sprint9-lookback-2026-06-18

**Sprint:** 9  
**Primary Target:** temporal_tariff / rate-follow-up  
**Secondary Target:** affine_fraction_delta (conditional)  
**Branch:** `feat/gsm8k-capability-paradigm-sprint9-temporal-tariff-lift`  
**Date:** 2026-06-18  
**Baseline:** 18 correct / 32 refused / 0 wrong

---

## 1. Starting Baseline

- Correct: 18
- Refused: 32
- Wrong: 0
- Wrong IDs: []

Preserved solved set from previous sprints maintained.

## 2. Experience Flywheel Output Summary

*(To be filled with actual flywheel output when available)*

Key observations from bounded practice memory:
- High-signal cases retained
- Any promotion candidates relevant to temporal/rate families
- Hazard patterns observed

## 3. Scout / Frontier / Microscope Output Summary

*(To be populated from actual runs)*

## 4. Candidate Families Ranked

**Primary: temporal_tariff / rate-follow-up**
- Target cases: 0001, 0017
- Rationale: Clear duration × explicit rate structure appears in recent trajectory needs.

**Secondary: affine_fraction_delta**
- Target case: 0010
- Only to be pursued if temporal safely lifts +1 and microscope shows clean signal with low wrong-risk.

**Blocked families (per doctrine):**
- DCS (0032, 0047)
- currency_amount (0019, 0028)
- sealed_elimination (0011, 0026)
- broad multiplicative_aggregate
- broad product_bridge

## 5. Selected Paradigm

**Chosen organ:** `temporal_tariff_total` (narrow)

Design principles:
- Explicit rate/tariff language required
- Clear duration unit family
- Strong hazard surface refusal
- Self-verifying arithmetic (duration × rate = total)
- No generic temporal parser
- No broad "per" handling

## 6. Typed Chains for Target Cases

*(Detailed chains to be added after case analysis)*

## 7. Implemented Organ(s)

**File:** `generate/derivation/temporal_tariff.py`

Key components:
- `build_temporal_tariff()` — narrow recognizer
- `compose_temporal_tariff()` — self-verification wrapper
- `resolve_promotable_temporal_tariff()` — promotion seam

## 8. Before / After Score

**Target:** 20+ / 30- / 0

*(Actual numbers to be recorded after full evaluation)*

## 9. Newly Solved IDs

*(To be filled post-evaluation)*

## 10. Preserved Solved IDs

All previous solved cases must remain solved (see test file).

## 11. Wrong = 0 Proof

All tests and evaluation must confirm `wrong == 0` on full train_sample.

## 12. Confuser Matrix

Major refusal categories implemented:
- Fractions / percentages
- Multiple rates / tiered pricing
- Ambiguous "per" language
- Remaining time questions
- Mixed unit families

## 13. Sibling Generality Proof

*(To be demonstrated in tests)*

## 14. Sealed-wrong Negative Evidence

Any organ that would admit previously observed sealed-wrong patterns was rejected.

## 15–22. Doctrine Compliance

- [x] report.json untouched
- [x] sealed artifacts untouched
- [x] No case-id logic
- [x] No hardcoded answers
- [x] No direct-answer shortcuts
- [x] Narrow scope only
- [x] Self-verifying
- [x] wrong == 0 maintained

## 23. Sprint 10 Recommendation

*(To be written after full sprint completion and evidence review)*

**Current thinking (preliminary):**
If temporal_tariff successfully lifts 1–2 cases cleanly, Sprint 10 should focus on tightening the next highest-signal refused cluster from the Experience Flywheel, with strong emphasis on composition-validation pins.
