# Matcher Extensions Milestone — ME-1 through ME-5

**Date:** 2026-05-27
**Author:** Shay
**Stack:** PRs #398 → #400 → #401 → #402 → #403 → #404
**Status:** All five PRs open and stacked; matcher half of the math
composition compounding loop is operational end-to-end.

---

## What landed

The matcher-extension wave delivers a runtime consumer for every entry
in `SAFE_COMPOSITION_CATEGORIES`. When a recognizer match publishes a
`composition_shape` key in `parsed_anchors` AND the
composition_registry carries an `affirms` entry for that shape,
`inject_from_match` emits a pre-composed `CandidateInitial` whose
value is the arithmetically composed quantity.

| PR | Wave | Scope | New tests |
|---|---|---|---|
| #398 | CW-1 + CW-2 | Consumption infrastructure: compile_frames, compile_compositions, frame_registry, composition_registry, manifest checksum extensions, inject_from_match consult | 38 |
| #400 | ME-1 | Currency-per-unit composition (multiplicative; Maria canary; Option A subject binding) | 21 |
| #401 | ME-2 | Cross-sentence subject binding (case 0019 real; threads prior_subject through match() + math_candidate_graph) | 19 |
| #402 | ME-3 | Additive composition (two-quantity same-unit "and" connective) | 15 |
| #403 | ME-4 | Subtractive composition (initial-then-removal; non-negative remainder discipline) | 17 |
| #404 | ME-5 | Integration smoke across all three SAFE categories + milestone | 4 |

**Total new tests:** 114, all green.
**Packs suite:** 127 passed.
**`core eval gsm8k_math --split public`:** 150/150, `wrong=0`.

---

## Architecture

```
audit refusal
  → core eval math-contemplation (decomposer dispatch)
  → MathCompositionClaimProposal
  → HITL ratify via apply_composition_claim()
  → compositions/{category}.jsonl append
  → pack-compile (CW-2) → compositions.jsonl + manifest.composition_checksum
                                  │
                                  ▼
                       load_composition_registry()
                                  │
─── runtime path ─────────────────┼────────────────────────────────
                                  ▼
recognizer matches statement
  → matcher extension (ME-1..ME-4) publishes composition_shape +
    composed_initial in parsed_anchors
  → inject_from_match per-category injector returns ()
  → _consult_composition_registry sees composition_shape
  → registry: affirms entry for the shape
  → CandidateInitial admitted
  → candidate graph admits the statement
  → previously-refused audit case admits
```

---

## SAFE_COMPOSITION_CATEGORIES — matcher coverage matrix

| Category | Surface pattern | Matcher | Dispatch via spec | Subject binding |
|---|---|---|---|---|
| `multiplicative_composition` | `bound(count) × bound(unit_cost)` | `_match_rate_with_currency` | `anchor_kind=\"currency_per_unit_composition\"` | Option A (ME-1) + Option C (ME-2 via `prior_subject`) |
| `additive_composition` | `bound(qty_a) + bound(qty_b)` | `_match_multiplicative_aggregation` | `anchor_kind=\"additive_quantity_composition\"` | Option A only |
| `subtractive_composition` | `bound(initial) − bound(removed)` | `_match_multiplicative_aggregation` | `anchor_kind=\"subtractive_quantity_composition\"` | Option A only |

---

## Invariants preserved across the entire stack

- `wrong == 0` on `core eval gsm8k_math --split public` (150/150)
- Case 0050 hazard pin (parametrized over all three allowlist categories)
- ADR-0166 — no new eval lanes
- ADR-0167 partition — no cognition imports in any new module
- ADR-0169 mutation boundary — registry is a gate, never an
  arithmetic primitive; matcher owns the math
- All matcher detection paths byte-identical (regression pins per PR)
- `engine_state/*` never committed
- `SAFE_COMPOSITION_CATEGORIES` enforced at write AND load
- Polarity `falsifies` honored uniformly across all matchers
- Refusal-preferring: pronoun / determiner / cross-unit / unobserved
  / unknown verb / zero count / negative remainder all refuse

---

## Scope boundary — what does NOT fire yet

The wiring is end-to-end correct (verified by ME-5's integration
test that stages a synthetic pack and admits all three canaries).
**Live `train_sample` admission** requires operator-seeded
ratifications:

1. A `RatifiedRecognizer` proposal in the proposal log carrying:
   - `shape_category = RATE_WITH_CURRENCY` (or `MULTIPLICATIVE_AGGREGATION`)
   - `canonical_pattern.anchor_kind = "currency_per_unit_composition"`
     (or `additive_quantity_composition` / `subtractive_quantity_composition`)
   - the right `observed_*` sets
2. A composition_registry entry compiled into the canonical pack:
   - `surface_pattern = "bound(count) × bound(unit_cost)"`
     (or the additive / subtractive shapes)
   - `composition_category` in the allowlist
   - `polarity = "affirms"`

These are operator decisions, not automated. When seeded, the live
train_sample run admits the 20 audit cases (12 quantity_extraction +
8 multi_quantity_composition) covered by this wave.

---

## Recommended next dispatch

**RAT-1:** Operator-workflow PR / runbook that seeds the necessary
RecognizerSpec proposals + composition_registry entries to fire the
live eval-delta truth test. With RAT-1 merged, `train_sample` moves
from 3/47 → ≥4/46 (with case 0050 still refused, `wrong=0`
preserved). The flywheel produces its first `ratify → admit` event
on the canonical pack.

---

## Memory pointers

- [[milestone-me1-me5-matcher-extensions-complete]] — this milestone
- [[project-ratification-consumption-gap-2026-05-27]] — original finding
- [[feedback-ratify-vs-consume-loop-closure]] — general pattern
- [[milestone-adr-0172-tier1-2026-05-27]] — Tier 1 parent
- [[adr-0167-audit-as-evidence-wave]] — parent corridor
- [[feedback-wrong-zero-hazard-case-0050]] — preserved across the stack
