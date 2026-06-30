# ADR-0170 — Recognizer Injector Contract Widening

**Status:** Accepted — W1 (type widening) + W2 (DCS-S1 acquisition →
`CandidateOperation(add)`) shipped to serving (`_INJECTORS`, PR #377; wrong=0,
train_sample 4/0/46). W3–W5 deferred (need `CandidateRate` / `apply_rate`,
ADR-0171). Status reconciled 2026-06-15 (mastery-v2 Step 2; was the stale
"Proposed / no runtime change in this PR", which never tracked W1/W2 landing).
**Date:** 2026-05-27
**Author:** Shay
**Parent:** ADR-0163.D.2 (parsed_anchors → MathProblemGraph)
**Related:** ADR-0131.G.1, ADR-0167, ADR-0167-FOLLOWUPS §7,
PR #369 (A2 rate_with_currency), DCS-S1 finding
**Gating rule:** [ADR-0166](./ADR-0166-measurement-capability-sequencing.md)

---

## Context

The `inject_from_match` dispatch in `generate/recognizer_anchor_inject.py`
has a return type of `tuple[CandidateInitial, ...]`. Every per-category
injector can only emit `CandidateInitial` records.

Wave-Next (the GSM8K next-capability push) attempted four parallel
sub-shape injectors. Three of the four hit the same substrate
constraint: the category they targeted cannot be expressed as
`CandidateInitial` alone.

| Brief | Required emission type | `CandidateInitial`-only sufficient? |
|---|---|---|
| A2 `rate_with_currency` | `CandidateRate(Rate(amount, num_unit, den_unit))` | No |
| A3 `multiplicative_aggregation` | `CandidateInitial(product)` OR `CandidateOperation(multiply)` | Partially (product semantics OK; composition not) |
| A4 `temporal_aggregation` | `CandidateOperation(apply_rate, ...)` | No |
| DCS-S1 (acquisition verbs) | `CandidateOperation(add)` (per ADR-0131.G.1) | No |

This is no longer four independent sub-shape gaps. It is **one
substrate constraint** that blocks the entire recognizer-injector
capability extension surface.

## Decision

Widen the `inject_from_match` contract so per-category injectors can
emit the full `SentenceChoice` union (and any extensions thereto),
not just `CandidateInitial`.

The widening is type-level only. The dispatch table, the four-narrowness
gating, the wrong=0 invariants, the per-sentence admission gate — all
preserved. The change is: per-category injectors gain the ability to
return `CandidateOperation` (and, after the corresponding schema work,
`CandidateRate`).

## Why this is not "just change a return type"

The widening interacts with three load-bearing existing rules:

### 1. ADR-0131.G.1 — branch-disagreement discipline

Acquisition verbs (`collected`, `bought`, `saved`, `buys`, `makes`) are
deliberately routed to `ADD_VERBS` / `SUBTRACT_VERBS` rather than to
initial-anchor extraction. The reason: `"Sam collected 5 apples"`
could otherwise emit both `CandidateInitial(Sam=5)` AND
`CandidateOperation(Sam, add, 5)`, triggering branch disagreement
and refusing the case.

ADR-0170 must preserve this discipline. The DCS injector's
acquisition-verb path emits `CandidateOperation(add)` — matching the
existing parser's behaviour for those verbs — NOT
`CandidateInitial`. The solver's defaults-from-zero rule then
produces `0 + N` for the single-statement case, identical to the
parser's current behaviour.

The wrong=0 hazard is: if the injector emits `CandidateOperation(add)`
and the parser ALSO emits `CandidateOperation(add)` from the same
sentence, that's a per-sentence collapsed-tie, not a branch
disagreement. Acceptable. But if the injector emits and the parser
silently drops the sentence (multi-word unit, etc.), the operation is
admitted from only one source — fine, but the test net must verify
no admission widens when the parser is updated to also extract.

### 2. ADR-0167 `SentenceChoice` union

PR #369 (A2 rate_with_currency) documented that `Rate` is not in
`SentenceChoice = Union[CandidateInitial, CandidateOperation]`. The
follow-up plan (`WAVE-NEXT-REVISED.md` §Schema-Gap 1) lays out 4 steps
for adding `CandidateRate`. ADR-0170 sequences in front of that work:
**first widen the injector contract to support the existing union
fully (CandidateOperation), then extend the union with CandidateRate
in a separate ADR.**

### 3. Existing `_initial_admissible` gate

`generate/math_candidate_graph.py` runs `_initial_admissible(c)` on
every injected candidate. That gate is `CandidateInitial`-specific.
Widening to `CandidateOperation` requires the parallel
`roundtrip_admissible(c)` gate (which exists for parser operations) be
applied to injected operations.

This is a real implementation concern but mechanically tractable: the
admissibility dispatch becomes:

```python
if isinstance(c, CandidateInitial):
    admissible = _initial_admissible(c)
elif isinstance(c, CandidateOperation):
    admissible = roundtrip_admissible(c)
```

The branch is one new line per check site; the gating semantics are
identical to what the parser already enforces.

## Open questions (must resolve in implementation ADR/PR)

1. **Atomic widening vs per-injector**: do we widen the return type
   in one PR (mechanical, no behavior change) and let each future
   injector PR add a category-specific test for its emission shape?
   Or bundle widening with the first acquisition-verb-emitting
   injector (DCS-S1)?

   *Recommendation:* widen first as a no-behavior-change PR. Existing
   `_INJECTORS` table entries continue to return only
   `CandidateInitial`; the change is a type-level relaxation. Then
   future injectors gain the ability without each one paying the
   widening cost.

2. **`CandidateOperation` admissibility**: confirm that
   `roundtrip_admissible(c)` accepts an operation whose surface span
   covers a single-statement acquisition (no separate "more" or
   subtractive operand). The existing parser path generates these,
   so the predicate already accepts them — but verify before relying
   on it.

3. **Branch-disagreement across parser + injector**: when the regex
   parser updates to handle multi-word units (e.g., "Pokemon cards"),
   it would emit `CandidateOperation(Nicole, add, 400, Pokemon cards)`
   for the same sentence the DCS injector emitted. The
   `_collapse_per_sentence_ties` mechanism handles ties; verify it
   collapses identical operations cleanly. If not, the wider parser
   work needs to coordinate with the injector path.

4. **CandidateRate sequencing**: ADR-0170 is the type widening on the
   *current* `SentenceChoice` union (`CandidateInitial | CandidateOperation`).
   Adding `CandidateRate` is a separate (downstream) ADR — call it
   ADR-0171. ADR-0170 ships first because it unblocks DCS-S1, A3, A4
   without waiting on the rate-type design.

5. **Test pattern**: every per-category injector PR after ADR-0170
   must pin both the admitted-graph shape AND the case 0050 hazard
   (no widening of admissions on the hazard canary).

## ADR-0166 three-question test

- **Q1 — Capability**: A widened injector contract that lets
  per-category injectors emit `CandidateOperation` in addition to
  `CandidateInitial`. Specifically unblocks DCS-S1 acquisition verbs
  (the largest single subset of the 21-case DCS bucket), A3
  multiplicative composition, A4 temporal aggregation. The capability
  is mechanism, not measurement — it enables follow-up injector PRs
  to ship lift.
- **Q2 — Lane**: `evals/gsm8k_math/train_sample/v1` is the regression
  surface. Each follow-up injector PR runs its own before/after delta
  on the existing report. No new canonical lanes (ADR-0166 still
  gates).
- **Q3 — Invariant**: `wrong == 0` preserved by the existing
  five-layer safety net (ADR-0163.D.2): matcher narrowness, extraction
  correctness, injection correctness (`_initial_admissible` /
  `roundtrip_admissible`), propose-time replay gate, multi-branch
  decision rule. ADR-0170 extends layer 3's dispatch but doesn't
  weaken any layer.

## Implementation outline (subsequent PRs, not this one)

> **Shipped-status reconciliation (2026-06-15, mastery-v2 Step 2).** This
> section was authored as a forward plan; parts have since landed. **W1 (type
> widening) and W2 (DCS-S1 acquisition → `CandidateOperation(add)`) are SHIPPED
> to serving** (`_INJECTORS`, PR #377; wrong=0 held, train_sample 4/0/46 — 6
> committed cases exercise the acquisition path). The multiplicative-aggregation
> injector also shipped (WAVE-A). The **rate/currency and temporal categories
> remain DEFERRED** — they need the `CandidateRate` / `apply_rate` schema work
> (ADR-0171). The sealed-injector lane (ADR-0186, PR #487) **post-dates W2** and
> hosts *future* sealed capabilities only — W2 was never in it (the
> `recognizer_anchor_inject.py` lane comment is reconciled to match).

**ADR-0170-impl-W1** *(SHIPPED)* — Type widening, no behavior change:
- Change `inject_from_match` return type to
  `tuple[CandidateInitial | CandidateOperation, ...]`
- Update `_INJECTORS` value type
- Update admissibility dispatch in `math_candidate_graph.py` to
  branch on the candidate type
- Pinning test: existing `inject_discrete_count_statement` still
  emits only `CandidateInitial`; behavior byte-identical pre/post.

**ADR-0170-impl-W2** *(SHIPPED — PR #377, serving `_INJECTORS`, wrong=0)* —
First operation-emitting injector (DCS-S1):
- Extend matcher's `_POSSESSION_VERBS` to accept acquisition verbs OR
  add a separate `_ACQUISITION_VERBS` set
- Injector emits `CandidateInitial` for `has/have/had` (existing) AND
  `CandidateOperation(add)` for acquisition verbs (new)
- Tests pin both paths; case 0050 hazard pin remains

**ADR-0170-impl-W3** — A1 currency_amount reimplementation:
- Sandbox config note: ensure `additionalDirectories` includes
  `/tmp/wt-*` paths for any future dispatched agent
- Injector emits `CandidateInitial` for `<ProperNoun> earns|charges
  $<amount>` (new verbs beyond `_INITIAL_HAS_RE`'s coverage)

**ADR-0170-impl-W4** — A3 multiplicative_aggregation:
- Per A3 design: emit `CandidateInitial(outer × inner, inner_unit)`
  pre-computed product (matches solver's defaults-from-zero semantics)

**ADR-0170-impl-W5** — A4 temporal_aggregation:
- Requires `apply_rate` primitive in the algebra (separate ADR work)
- Without that primitive, injector continues to refuse explicitly

Each impl PR is small, focused, regression-tested, and ships with its
own before/after eval delta.

## What ADR-0170 does NOT do

- It does not widen the `SentenceChoice` union (that's ADR-0171 for
  `CandidateRate`).
- It does not add new eval lanes (ADR-0166 still gates).
- It does not propose any non-deterministic mechanism.
- It does not weaken wrong=0 or the five-layer safety net.
- It does not mandate that all four blocked injectors ship — each is
  its own follow-up PR with its own go/no-go decision.

## Cross-references

- [ADR-0163.D.2](./ADR-0163.D.2-discrete-count-statement.md) (the
  original parsed_anchors → solver-state ADR; ADR-0170 widens its
  injector contract)
- [ADR-0131.G.1] — branch-disagreement discipline that ADR-0170 must
  preserve
- [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md) — parallel
  teaching-corridor mechanism; ratification path independent of
  injector contract
- [ADR-0167-FOLLOWUPS](../handoff/ADR-0167-FOLLOWUPS.md) §7 — the
  four-finding source
- [WAVE-NEXT-REVISED](../handoff/WAVE-NEXT-REVISED.md) §Schema-Gap
  1/3 — the categories this ADR unblocks
- [DCS-S1 finding](../handoff/DCS-S1-FINDING.md) — the investigation
  that surfaced the contract gap
- PR #369 — A2's schema-refusal artifact documenting `Rate` follow-up
