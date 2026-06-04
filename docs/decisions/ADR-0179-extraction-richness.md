# ADR-0179 — Extraction Richness: feeding the comprehension composer real quantities

**Status:** Accepted (ratified by ADR-0207, 2026-06-03)
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Builds on / unblocks:**
- [ADR-0176](./ADR-0176-multistep-composition-question-targeting.md) (MS-3 product search), [ADR-0178](./ADR-0178-compositional-structure.md) (GB-1/GB-2 composer) — built but **starved** by thin extraction.
- [ADR-0177](./ADR-0177-cue-precision-learning.md) — richer extraction produces the gold-matching chains that give cue-precision its signal.
- Reuses `en_numerics_v1` (cardinal table) + `WORD_NUMBERS` + the existing currency/fraction/compound grounding in `generate/math_roundtrip._value_grounds` (ADR-0128 / 0131.G.3).

---

## Context — the wall every recent measurement hit

The structure machinery (MS-3 search, GB-1 clauses, GB-2 list-sum) is built,
deterministic, and wrong=0-safe — and flips almost nothing on *practice* for one
recurring reason: **extraction is too thin to feed it.** Concretely, with
`extract.py`'s current `(\d+(?:\.\d+)?)\s+([a-z]+)` (digit + single following word):

| Case | Gap | Effect |
|---|---|---|
| 0024 | `"36 on Tuesday"` → unit `"on"` | non-uniform units → GB-2 list-sum never fires |
| 0003 | `"$0.75"` → bare `0.75`; `_value_grounds("0.75")` fails (currency branch needs the `$`; digit-runs `0`/`75` not checked for a bare decimal) | correct product (864) refuses |
| 0024/0033 | `"three times"` → `three` not a digit | word-number quantity lost |
| 0016/0024 | `"jumping jacks"`, `"stop signs"` | multi-word unit truncated |
| 0033 | `"Rachel is 12."` → no following unit word | sentence-final quantity lost |

The capability is there; the inputs aren't. **Extraction richness is the
prerequisite the prior phases kept naming** — and the place coverage should finally
move (modulo cue precision for op-disambiguation, and scale).

## Two layers — and their very different risk

- **(A) The sealed derivation extractor** (`generate/derivation/extract.py`).
  Enriching it is **safe**: it feeds only the (sealed, practice-only) derivation
  search; over-extraction is caught downstream (the gate's completeness + grounding
  + uniqueness; refuse-preferring). The bulk of this ADR lives here.
- **(B) The shared grounding primitive** (`_value_grounds` / `_tokens` in
  `math_roundtrip`). **wrong=0-sensitive**: the *serving* round-trip filter uses it.
  Exactly **one** change belongs here — bare-decimal grounding — and it must be
  proven to leave serving `3/47/0` byte-identical.

## Decision

Enrich extraction, lexeme-level (ADR-0165 — orthographic shapes, never grammar),
refuse-preferring, reusing existing numerics machinery:

1. **Word-number quantities** (extract.py) — `three`, `a hundred`, hyphenated
   compounds → values, via `en_numerics_v1` / `WORD_NUMBERS` (already the grounding
   table; extraction just *uses* it). Unblocks comparative/word operands.
2. **Currency + decimal extraction** (extract.py) — `$0.75` → `(0.75, "dollars")`
   preserving the money form; **plus** the one shared-primitive fix: `_value_grounds`
   grounds a **bare decimal** `"N.M"` when both digit-runs `N` and `M` appear as
   tokens — symmetric with the existing `$N.NN` and `N/M` logic. wrong=0-gated.
3. **Multi-word units** (extract.py) — `jumping jacks`, `stop signs` (a bounded
   unit-phrase: number + 1–2 following content words), so same-unit comparison works.
4. **List-unit inheritance** (extract.py) — in a list (`20 jumping jacks on Monday,
   36 on Tuesday, …`), a quantity with no unit word of its own inherits the list's
   head unit. This is what makes 0024 a same-unit list → GB-2 list-sum fires.
5. **Sentence-final / unit-less quantities** (extract.py) — `"Rachel is 12."` →
   `(12, <inherited/empty unit>)`, so the quantity isn't lost.

Each is independently bounded and refuse-preferring; (4) and (1) are the highest-
leverage (they unblock 0024 and the comparatives).

## wrong=0 obligations (must be *proven*, not asserted)

1. **Shared-primitive change keeps serving byte-identical.** After the bare-decimal
   grounding fix, serving stays `3/47/0` *byte-identical* (the `verify pinned lane
   SHAs` gate). If a decimal case now grounds and shifts a serving verdict, evaluate
   it explicitly; any `wrong > 0` shift reverts the change. (Grounding a true
   token-run is a false-negative fix; the round-trip + disagreement + solver still
   gate any new admission.)
2. **Over-extraction cannot break wrong=0.** Spurious/mis-attributed quantities flow
   into the derivation gate, where completeness + grounding + uniqueness refuse
   them. A test: an over-extracted quantity yields refusal, never a wrong commit.
3. **Determinism/replay**; extraction is deterministic and lexeme-level (no grammar
   templates — ADR-0165).
4. **List-unit inheritance must not invent units** — a quantity only inherits a unit
   present in its list head; otherwise it stays unit-less (refuse-preferring on
   same-unit comparison).

## Honest payoff

This is the prerequisite, not a coverage promise by itself — but it is the one that
**unblocks built capability**: uniform units → GB-2 list-sum fires on 0024-class;
decimal grounding → MS-3 product flips 0003-class; word-numbers → comparative
operands resolve; and every newly-extracted gold-matching chain **feeds cue-precision
its signal** (ADR-0177's bottleneck). Expect the practice flip-curve to finally move
on the extraction-blocked cases — measured, not assumed; op-ambiguity (cue precision)
and volume (scale) still gate the rest.

## Sub-phases

- **EX-1 — word-number quantities** (extract.py; reuse `en_numerics_v1`/`WORD_NUMBERS`).
- **EX-2 — currency/decimal extraction** (extract.py) **+ bare-decimal grounding**
  (shared primitive, wrong=0-gated: serving `3/47/0` byte-identical). The one
  shared-primitive touch; ship it alone with the lane-SHA proof.
- **EX-3 — multi-word units** (extract.py).
- **EX-4 — list-unit inheritance** (extract.py) — unblocks 0024 same-unit list.
- **EX-5 — sentence-final / unit-less quantities** (extract.py).
- **EX-6 — measurement.** Re-run MS-3 + GB-2 on the enriched extraction; report the
  flip-curve delta and the residual (cue-precision + scale) honestly.

## Acceptance criteria (Proposed → Accepted)

1. EX-2's shared-primitive change proven to keep serving `3/47/0` byte-identical
   (lane-SHA gate); capability lanes G1–G5/S1 stay 100% `wrong=0`.
2. Over-extraction is refuse-preferring (proven: a mis-attributed quantity refuses,
   never wrong-commits).
3. The measurement shows the previously extraction-blocked cases (0003, 0024-class)
   reach a gold-matching chain (flip or honest hold under cue ambiguity), under
   ADR-0114a perturbation; determinism/seal invariants hold.

## Cross-references

- **Unblocks:** [ADR-0176](./ADR-0176-multistep-composition-question-targeting.md),
  [ADR-0178](./ADR-0178-compositional-structure.md); **feeds**
  [ADR-0177](./ADR-0177-cue-precision-learning.md).
- **Reuses:** `en_numerics_v1`, `WORD_NUMBERS`, and the existing currency/fraction/
  compound grounding in `_value_grounds` (ADR-0128, ADR-0131.G.3) — extends, never
  reinvents.
- **Constraint:** [ADR-0165](./ADR-0165-regex-scope-rule.md) — lexeme/orthographic
  extraction only, never grammar templates.
- **Thesis:** [[thesis-decoding-not-generating]] — read the quantities the text
  actually states; don't pattern-match a shape.
