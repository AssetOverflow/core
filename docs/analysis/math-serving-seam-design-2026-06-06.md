# Math-serving reach seam (ADR-0206 §5)

**Date:** 2026-06-06 · **Branch:** `feat/math-serving-reach-seam`

## What this is

Parameterize `select_self_verified` (the GSM8K wrong=0 serving gate) with a
`ReachPolicy`, completing the ADR-0206 §5 math-serving deferral in its own careful PR.
**It changes no serving behavior today** — it is the safe, byte-identical, sanctioned
*first edit* to the most wrong=0-critical line, with a live-wiring test, so the future
`VERIFIED` widening has a precise, proven integration point.

## The tension it resolves (why scope-first mattered)

- GSM8K `wrong == 0` is **absolute** (zero wrong, ever).
- A reliability license (Step E's mechanism) is **statistical** (a 0.99 Wilson floor).
- Math answers are **not disclosed** (`[approximate]`) like the cognition path.

⇒ Widening the math serve on a statistical license would eventually serve a **silent
wrong** — breaching the absolute invariant + the sealed lane SHAs. ADR-0206 §4 foresaw
this: **`VERIFIED` is "the only state that will license widening past gold,"** and it is
reserved because it needs a **canonical-comparison pass** (the soundness ≠ correctness
gap) that is unbuilt.

## Design (safe by construction)

`select_self_verified(..., policy=STRICT_POLICY)`:
- **STRICT** (the default every one of the 5 callers passes): the prior logic verbatim —
  unique self-verifying answer → `Resolution`; zero-verify or disagreement → refuse.
  Byte-identical; the pinned serving-lane SHAs (`demo_composition 3a3d09f3…`,
  `fabrication 01e1b6b7…`, `math_teaching_corpus eaf160d1…`) are unchanged.
- **Wider reach + disagreement**: resolve **only** via `_canonically_verified` — the
  `VERIFIED` gate. Its body returns `None` (the capability is unbuilt), so the widening
  is **structurally inert**: a disagreement refuses regardless of `policy`. wrong=0 holds
  by *construction*, not by caller discipline — even a future caller that wrongly passes a
  wider policy still refuses until a real `VERIFIED` producer exists.
- A statistical reliability license is **not** consulted here (the cognition/math
  asymmetry is deliberate: cognition discloses, math is absolute).

`test_seam_is_live_wiring` injects `_canonically_verified` to return a winner and proves
a wider reach then resolves the disagreement — **and STRICT still refuses even then**. So
the seam is live wiring, not dead code; the consumer is proven for the day `VERIFIED` lands.

## Invariants
- **Byte-identity** — STRICT path unchanged; `Resolution` unchanged; no caller passes a
  policy; the import adds no cycle and no serialized-output change (verified: the three
  fast serving-lane report hashes are identical before/after).
- **wrong=0** — structurally inert widening; absolute invariant preserved.
- **No overclaim** — serving is unchanged today; the docstrings say so.

## Out of scope (the real unlock)
The `VERIFIED` canonical-comparison producer — scoped separately in
`VERIFIED-canonical-comparison-scoping-2026-06-06.md`. Also still deferred: SITUATE
(stakes), the live FEED-BACK loop, and `reach_level` JSONL emission (a frozen-gate re-pin).
