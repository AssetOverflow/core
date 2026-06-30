# Session 2026-05-29 — The Multi-Step Build Arc: from "another matcher" to a comprehension composer

**Status:** In progress (EX-2 landing) ✓ through GB-2
**Companion:** [SESSION-2026-05-28 — risk/reward learning architecture](./SESSION-2026-05-28-risk-reward-learning-architecture.md) (the design discussion that opened this arc)
**Headline:** Took the GSM8K work from "build another recognizer per shape" to a **safe, inspectable, comprehension-guided multi-step solver** — and, just as importantly, proved *with measurement* exactly where coverage is gated (extraction richness × cue precision × scale), so the remaining roadmap is honest rather than hopeful.

---

## TL;DR

Across one long session we:

1. **Shipped ADR-0175 Phases 1–3b** (the two-regime calibrated-learning substrate) and **Phase 5a** (retired the inert reader; net −1,038 LOC; serving byte-identical at `3/47/0`).
2. **Did a lookback review** of the 5-PR stack (no live hazards; recorded drift); landed it.
3. **Built the multi-step machine** end-to-end: MS-1 (question-targeting) → MS-2 (chain model + comparatives) → MS-3 (target-guided search) → GB-1 (clause segmentation) → GB-2 (list-sum-then-scale) → EX-2 (decimal grounding).
4. **Scoped the full remaining roadmap** as ADRs 0176–0179.
5. Kept **`wrong=0` on serving (`3/47/0`) byte-identical the entire time** — every attempt-and-eliminate ran in the sealed practice lane.

The arc's intellectual payoff: each phase's *measurement* told us the next lever, and they converged on a clean dependency chain rather than a guessing game.

---

## The converged architecture (what we now believe)

```
ADR-0175  Two-regime calibrated learning      serving wrong=0  |  sealed practice attempt+eliminate
ADR-0176  Multi-step grounded search          extract → chain → self-verify gate (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness)
ADR-0178  Comprehension-guided structure      read clause-by-clause; structure-from-reading, not enumeration
ADR-0177  Cue-precision learning              trust gate + search prune (closes "self-verification necessary-not-sufficient")
ADR-0179  Extraction richness                 feed the composer real quantities (the unblock prerequisite)
                                              × SCALE (ADR-0163 §F) to compound
```

**The honest dependency chain (the session's central finding):**
> extraction richness (0179) → unblocks the built structure (MS-3/GB-2) → produces gold-matching chains → feeds cue-precision (0177) → coverage; all gated by `wrong=0` and amplified by scale.

Coverage does not come from more search — it comes from *reading the structure* and *feeding it real quantities*, with the self-verification gate keeping every attempt honest.

---

## What shipped to `main`

| PR | What | Result |
|---|---|---|
| #430 | Phase 5a — retire inert reader | net −1,038 LOC; `3/47/0` byte-identical |
| #432 | Phase 1 — reliability ledger + gate (`core/reliability_gate/`) | inert substrate; invariants #3/#4 proven |
| #433 | Phase 2 — sealed practice lane (`evals/gsm8k_math/practice/v1/`) | diagnosis: 35 skill / 12 knowledge / 0 ambiguity |
| #434 | Phase 3a — self-verification gate (`generate/derivation/`) | invariant #2 proven (spurious refuses) |
| #435 | Phase 3b — multiplicative search | first attempts live; the "necessary-not-sufficient" finding |
| #436 | self-verification **completeness** clause | practice wrongs 9→2 |
| #438 | `en_core_comparatives_v1` pack | irreducible world-facts (twice→×2, half→×0.5) |
| #439 | MS-1 — question-targeting (`Target`) | search pruning + stopping signal |
| #440 | MS-2 — chain model (text + comparative operands) | 0024/0033 mixed chains self-verify |
| #441 | MS-3 — target-guided bounded search | flips 0021; honest 4/9/37 practice |
| #444 | GB-1 — clause segmentation + clause-local sub-derivation | per-clause structure |
| #445 | GB-2 — same-unit list-sum-then-scale | clean-case capability; extraction-gated on practice |
| #447 | EX-2 — bare-decimal grounding (shared primitive) | **0003 unblocked** (+1 practice flip); serving byte-identical |

**Proposed (doc) PRs:** #437 (ADR-0176), #442 (ADR-0177), #443 (ADR-0178), #446 (ADR-0179).

---

## The findings the microscope produced (in order)

1. **Per-shape matchers can't compound** — 79% need multiplication, 0% single-step; phrasings are unbounded. (Killed the "another matcher" path.)
2. **Self-verification is necessary but not sufficient** (3b) — 9/13 self-verified attempts were wrong; the gap is *which composition*, not *can we multiply*.
3. **Completeness** catches multi-step-incomplete attempts (correct first-steps mistaken for answers) — wrongs 9→2.
4. **Two gaps**: A = cue→op precision; B = compositional structure. Gap B dominates.
5. **Structure-from-reading** (Gap B) resolves the rich-search-vs-uniqueness tension: every gold case fits a sequential clause read.
6. **Cue-precision is bottlenecked** — it can only learn from gold-matching chains (~4/50 on blunt shapes); it's the trust substrate + prune, not the coverage unlock.
7. **Extraction is the wall** — non-uniform units, decimals, word-numbers, multi-word units block the built machinery. (EX-2 proved it: fixing decimal grounding flipped 0003.)

Each finding came with a deterministic trace — the microscope, exactly as the design predicted.

---

## wrong=0 discipline held throughout

- Serving `3/47/0` byte-identical across all 13 PRs — verified at each landing (and EX-2, the one shared-primitive touch, gated by the pinned lane-SHA check).
- Every attempt-and-eliminate ran in the **sealed practice lane**; practice "wrongs" are gold-checked eliminations (learning signal), never served.
- Invariants proven by failing-under-violation tests at each phase (#1 seal, #2 spurious-refusal, #3 determinism, #4 no-self-authorization, completeness, target-match).
- A 5-PR **lookback review** caught and recorded drift before it compounded.

---

## Next levers (honest, in order)

1. **Finish EX (extraction richness)** — EX-1 word-numbers, EX-3 multi-word units, **EX-4 list-unit inheritance** (unblocks 0024's same-unit list). EX-2 (decimals) just proved the pattern.
2. **Cue-precision (ADR-0177)** — once richer extraction produces more gold-matching chains, the ledger has signal to learn from.
3. **Scale (ADR-0163 §F)** — volume is what makes the learning *compound*; 50 cases is mechanism-demonstration.
4. **CI-hosted contemplation loops** (recorded) — run the sealed practice loop on CI minutes, mobile-triggered, once the learning config stabilizes.

The eval headline (`3/47/0`) moves once extraction + structure + cue-precision compose on enough volume — and the substrate to make that lift *trustworthy* is now built and proven.
