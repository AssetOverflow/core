# Wave-Next Revised — DCS Sub-Shapes + Schema-Gap Backlog

**Date:** 2026-05-27
**Supersedes:** `docs/handoff/WAVE-NEXT-INJECTORS.md` (kept for history)
**Why revised:** The A1–A4 dispatch surfaced findings that invalidate three
of the four briefs' lift assumptions. This doc replaces them with the
actually-tractable next steps.

---

## What A1–A4 actually found

| Brief | Outcome | Schema gap surfaced |
|---|---|---|
| **A1** `currency_amount` | Sandbox-blocked write; analysis only. **Real lift potential** — new verbs (`charges`, `earns`) outside `_INITIAL_HAS_RE` coverage. Implementation ready, design intact. | None |
| **A2** `rate_with_currency` | PR #369 opened (schema-refusal). Lift=0. | `Rate` not in `SentenceChoice = Union[CandidateInitial, CandidateOperation]` |
| **A3** `multiplicative_aggregation` | Sandbox-blocked write; analysis only. Lift=0. | Brief's `CandidateOperation(multiply)` spec is wrong: would compute `0 * inner = 0` with no prior `InitialPossession`. Correct emission is `CandidateInitial(outer × inner)` pre-computed product. |
| **A4** `temporal_aggregation` | Sandbox-blocked write; analysis only. Lift=0. | Needs `apply_rate` primitive that doesn't exist in the algebra. |

**Three of four categories have schema-level prerequisites before any
injector can ship.** The original Wave-Next brief misframed them as
injector work. The honest read: they're each their own ADR-sized
schema-extension followed by an injector wave.

---

## The actually-tractable next wave: DCS sub-shapes

The `discrete_count_statement` category is 21 of 47 GSM8K refusals
(largest single bucket) and has a **working v1 injector** from #315
plus a **specification document on main** at
`docs/handoff/discrete_count_statement-injector-spec.md` (from #366).

The spec recommends *narrow incremental expansion* — one sub-shape
per PR, each carrying its own `wrong=0` hazard pins. That maps cleanly
to small focused PRs.

### Proposed sub-shape sequence

Order by lift-per-risk:

1. **DCS-S1** — proper-noun possession with single static count, no
   clause split (the canonical narrow form already partially handled
   by the v1 injector). Expand to cases the v1 injector currently
   misses for surface-shape reasons.
2. **DCS-S2** — proper-noun possession with `and`-coordinated counted
   nouns (e.g. "Francine has 5 boxes and 27 loose crayons"). Requires
   the multi-quantity composition decision but is structurally simpler
   than the full multi-quantity recognizer.
3. **DCS-S3** — pronoun-subject possession (e.g. "She had 6 baskets").
   Requires anaphora resolution to a prior proper noun. Higher risk
   surface than S1/S2.
4. **DCS-S4** — subject-anonymous possession ("There were 12 apples").
   Requires anonymous-subject handling decision.

Each sub-shape PR carries:
- A focused match-tightening + injector extension in
  `generate/recognizer_match.py` and `generate/recognizer_anchor_inject.py`
- A test file pinning the new admission cases AND the
  wrong=0 hazard (case 0050 + any newly-revealed hazard pattern)
- Eval delta section in `audit_brief_11.md`

The full DCS bucket lift potential is ~5–15 cases depending on
sub-shape coverage. Each sub-shape PR is a small, focused increment.

### Why not dispatch this as a Wave

The A1–A4 dispatch demonstrated that orchestrator-launched subagents
**burn 50k+ tokens per cold-start** with mixed PR-opening success
rates. The user dispatches operators in their own UIs/CLIs where
context costs amortize across the operator's session.

This document is the **reference brief** that operators read; the
**dispatch is the user's action**, not the orchestrator's. See
`memory/feedback-no-self-dispatch-of-subagents.md` for the binding
principle.

---

## Schema-gap backlog (file for separate ADRs, not Wave-Next)

The three findings from A2/A3/A4 deserve named ADRs when (and only when)
the prerequisite ADRs are in place. Until then they sit as queued items.

### Schema-Gap 1 — `Rate` in `SentenceChoice` union (from A2)

**From:** PR #369 (A2 rate_with_currency injector — refusal-only)
**Requires:** ADR-0168.x or new ADR-0170.

A2's concrete 4-step follow-up (preserved verbatim from the PR):

1. Add `CandidateRate` dataclass in `generate/math_candidate_parser.py`
   (sibling of `CandidateInitial`/`CandidateOperation`) — carries a
   `Rate` operand keyed by actor + source-span provenance.
2. Widen `SentenceChoice` to include `CandidateRate`; update
   `_slot_count`, `_collapse_per_sentence_ties`, admissibility
   predicates, and the per-sentence admission gate.
3. Teach `parse_and_solve` to compose `CandidateRate` with downstream
   `apply_rate`/`multiply` questions — unify with the existing
   `extract_earnings_candidates` short-circuit.
4. Then `inject_rate_with_currency` can emit `CandidateRate`. The
   matcher already extracts `(currency_symbol, amount, per_unit)`;
   needs entity extraction added.

**Lift potential after schema extension:** 3+ cases (the original
`rate_with_currency` bucket). Likely 4-5 more from `rate_*` adjacent
categories once the substrate exists.

### Schema-Gap 2 — `apply_rate` primitive in the algebra (from A4)

**From:** A4 temporal_aggregation analysis (no PR)
**Requires:** an algebra extension ADR.

The current solver has no `apply_rate` operation in its operator
inventory. Temporal aggregation ("5 hours per day, 7 days per week")
fundamentally needs this: a rate composed with a time-duration
quantity yields a total. Without it, temporal aggregation has nowhere
to ground.

**Lift potential after primitive lands:** 2 cases (the
`temporal_aggregation` bucket).

### Schema-Gap 3 — Multi-quantity composition emission shape (from A3)

**From:** A3 multiplicative_aggregation analysis (no PR)
**Requires:** correction to the original Wave-Next brief, plus a
multi-quantity-composition ADR coordinated with FOLLOWUPS §1
(CompositionClaim).

The brief's `CandidateOperation(multiply)` spec is mechanically wrong:
the solver's multiply operation does `state[(actor, unit)] *= value`,
requiring a prior `InitialPossession`. A standalone multiplicative
statement doesn't have that, so multiply would compute `0 * inner = 0`.

**Correct emission:** `CandidateInitial(outer_count × inner_count,
inner_unit)` — the pre-computed product as a possession.

**Lift potential after correction lands:** 0 cases (zero GSM8K
`multiplicative_aggregation` cases match the canonical narrow form
even with correct emission — they all need either coordination or
clause-split support). Effectively this category's bucket is empty
relative to current GSM8K; the schema correction is for future
problems, not for visible lift today.

### Schema-Gap 4 — A1's `currency_amount` injector (preserved, not dropped)

**From:** A1 currency_amount analysis (no PR, sandbox-blocked)
**Requires:** Only the sandbox fix + reimplementation. No schema work.

**Lift potential:** 2–4 cases (new verbs `charges`, `earns` not
covered by the existing `_INITIAL_HAS_RE`). The implementation design
is in A1's analysis — see agent transcript for details. This is the
smallest, lowest-risk follow-up if anyone picks it up; the brief is
sound, only execution failed.

---

## Standing pivot

The next operator pickup should be:

1. **DCS-S1** — narrow proper-noun possession sub-shape expansion (highest lift-per-risk, smallest scope)
2. **DCS-S2** — coordinated counted-nouns (medium lift)
3. **A1 reimplementation** (if sandbox config is fixed) — currency_amount with new verbs
4. **Schema-Gap 1 ADR** (Rate-in-union) — unblocks 3–8 follow-up cases
5. **Schema-Gap 2 ADR** (apply_rate) — unblocks 2 cases
6. **Schema-Gap 3** — folds into CompositionClaim ADR (FOLLOWUPS §1)

No timelines. Order is by leverage, not calendar.

---

## What this document does NOT do

- It does not dispatch any agents (per `feedback-no-self-dispatch-of-subagents`)
- It does not retire `WAVE-NEXT-INJECTORS.md` (kept for history; future
  readers should consult this document for current state)
- It does not modify any runtime code
- It does not add new eval lanes (ADR-0166)
- It does not propose any non-deterministic mechanism

## Cross-references

- `docs/handoff/WAVE-NEXT-INJECTORS.md` — original (now-superseded) brief
- `docs/handoff/discrete_count_statement-injector-spec.md` — the DCS sub-shape spec
- `docs/handoff/ADR-0167-FOLLOWUPS.md` — parent follow-up queue
- `docs/decisions/ADR-0168-frameclaim-ratification.md` — FrameClaim scoping
- `docs/decisions/ADR-0168.1-math-frameclaim-proposal-adapter.md` — adapter bridge
- PR #369 — A2's schema-refusal artifact
- `memory/feedback-no-self-dispatch-of-subagents.md` — binding dispatch principle
