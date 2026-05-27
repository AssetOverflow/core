# DCS-S1 Finding — Injector Contract Is the Substrate Bottleneck

**Date:** 2026-05-27
**Status:** Finding; no implementation. Routes work to ADR-0170.
**Parent:** `docs/handoff/WAVE-NEXT-REVISED.md`
**Result:** DCS-S1 (proper-noun possession sub-shape expansion) cannot
ship meaningful lift on current GSM8K without first widening the
`inject_from_match` return-type contract. Same schema gap A3
(multiplicative) and A4 (temporal) identified.

---

## What was investigated

The Wave-Next-Revised plan named **DCS-S1** as the next tractable
sub-shape: extend the existing v1 `inject_discrete_count_statement`
injector to cover more of the 21 `discrete_count_statement` refusals
on the GSM8K train_sample.

The hypothesis: most DCS refusals are proper-noun possessions whose
extraction fails for one of a few narrowable reasons (verb whitelist,
clause-split markers, single-quantity rule). Loosening the matcher +
extending the injector to cover those would lift several cases.

## What the data actually shows

All 21 DCS-refused cases were enumerated and the triggering statements
inspected. The structural breakdown:

| Sub-shape pattern in DCS-refused statements | Count |
|---|---:|
| Acquisition verb (`collected`, `donated`, `bought`) — not in possession whitelist | ~5 |
| Multi-clause / enumeration (`and`, `then`, `,`) | ~8 |
| Pronoun subject (`he`, `she`, `they`) | ~4 |
| Comparative reference (`twice as many`, `half of`) | ~3 |
| Anonymous subject (`There are`, `The guests`) | ~3 |
| Other (modal verbs, copula, multi-verb) | ~4 |

(Buckets overlap — many cases hit multiple narrowness rules.)

**Critical observation:** of the 21 cases, **zero** are pure S1-only
blockers. Every single one has additional blockers downstream in the
same problem. Even if the DCS injector admitted the first sentence,
sentences 2/3/4 carry their own refusals.

Concrete trace — case `gsm8k-train-sample-v1-0023`:

```
S1: "Nicole collected 400 Pokemon cards."
    → would inject Nicole=400 if `collected` were in possession verbs
S2: "Cindy collected twice as many, and Rex collected half of Nicole and Cindy's combined total."
    → multi-clause + comparative reference; will refuse on current rules
S3: question with `If Rex divided...` conditional prefix
    → conditional prefix recovery exists but answer still requires S2's admission
```

Admitting S1 alone does not close the case. The bottleneck moves from
S1 to S2; no admission-lift is delivered.

## The architectural blocker

To admit `"Nicole collected 400 Pokemon cards"` as initial state, three
edits would be needed:

1. Add `collected` to `_POSSESSION_VERBS` (matcher narrowness in
   `generate/recognizer_match.py`)
2. Extend `_locate_possession_verb` in the injector
3. Add `collect, collects, collected` to `CandidateInitial.__post_init__`
   whitelist in `generate/math_candidate_parser.py`

**ADR-0131.G.1 explicitly removed `collected/bought/saved/buys/makes`
from initial-anchor extraction** — they were routed exclusively to
`ADD_VERBS` (operation extraction) to avoid branch disagreement when
the same sentence could produce both `CandidateInitial(Sam=5)` AND
`CandidateOperation(Sam, add, 5)`.

The solver "defaults from zero for operations" so
`Sam collected 5 apples. How many does Sam have?` → `0 + 5 = 5`. That
discipline is load-bearing for wrong=0 in the regex path.

The right architectural fix is not to break ADR-0131.G.1. It's to teach
the **DCS injector** to emit `CandidateOperation(add)` for acquisition
verbs — the same kind of state-introducing operation the parser
already emits for them.

**But:** `inject_from_match`'s return type is
`tuple[CandidateInitial, ...]`. It cannot emit `CandidateOperation`.
Widening the contract is the prerequisite.

## The pattern — fourth time this gap appears

Wave-Next surfaced four schema gaps. All four trace back to the same
substrate-level constraint: the recognizer-injector path can only
emit `CandidateInitial`.

| Brief | What needed emission | Available type | Blocker |
|---|---|---|---|
| **A2** rate_with_currency | `CandidateRate` (carries `Rate(value, num_unit, den_unit)`) | None — `Rate` not in `SentenceChoice` union | Schema gap (PR #369) |
| **A3** multiplicative_aggregation | `CandidateInitial(outer × inner)` OR `CandidateOperation(multiply)` | `CandidateInitial` works for product semantics; but other cases need composition | Half-blocked |
| **A4** temporal_aggregation | `CandidateOperation(apply_rate, ...)` | `apply_rate` primitive doesn't exist | Algebra-level gap |
| **DCS-S1** | `CandidateOperation(add)` for acquisition verbs | Injector returns only `CandidateInitial` | Schema gap (this finding) |

This is no longer four separate sub-shape problems. It's **one substrate
bottleneck affecting all four categories**. The right artifact is a
contract-widening ADR — see [ADR-0170](../decisions/ADR-0170-injector-contract-widening.md).

## What this PR ships

- This finding doc (`docs/handoff/DCS-S1-FINDING.md`)
- `docs/decisions/ADR-0170-injector-contract-widening.md` — the scoping
  ADR that names the contract change and the four categories it unblocks

What this PR does NOT ship:
- Any DCS-S1 implementation (it's blocked on ADR-0170)
- Any matcher/extractor edits
- Any test changes
- Any pack changes

## Recommended next move

ADR-0170 ratification, then a small focused PR implementing the
contract widening (no behavior change, type-only). Then a follow-up
wave (DCS-S1 acquisition, A1 currency, A2 rate, A3 multiplicative,
A4 temporal) can ship in parallel — each as a focused injector PR
against the widened contract.

That's the actual lift-per-risk path. Until ADR-0170 lands, no
recognizer-injector work other than `CandidateInitial`-only narrow
possession can ship cleanly.

## Cross-references

- [WAVE-NEXT-REVISED](./WAVE-NEXT-REVISED.md) — parent plan; needs an
  update pointing to ADR-0170 as the prerequisite
- [ADR-0170](../decisions/ADR-0170-injector-contract-widening.md) — the
  scoping ADR this finding routes to
- PR #369 (A2) — first observation of the gap; documents `Rate`
  extension steps
- ADR-0131.G.1 — the original branch-disagreement discipline that
  forces acquisition verbs to be operations, not initials
- ADR-0167-FOLLOWUPS §7 — Wave-Next findings backlog
