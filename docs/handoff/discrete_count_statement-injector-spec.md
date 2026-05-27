# `discrete_count_statement` Injector Specification Audit

**Dispatch source:** `docs/handoff/GPT55-MOBILE-DISPATCH.md` Task 2
**Mode:** docs-only audit/specification; no code, test, pack, or engine-state mutation
**Branch:** `docs/gpt55-task-2-dcs-injector-spec`

---

## Executive summary

The mobile dispatch asked for a specification audit of the
`discrete_count_statement` injector, assuming the current state was:

```text
21/47 GSM8K refusals are category=discrete_count_statement
recognizer matches broadly
inject_from_match returns empty tuple
```

Current `main` has moved beyond that assumption.

`generate/recognizer_anchor_inject.py` now implements a v1
`discrete_count_statement` injector, and `generate/recognizer_match.py`
contains a refusal-preferring extraction path for the canonical
`<ProperNoun> has|have|had <count> <counted_noun>` shape.

Therefore this document is a reconciliation spec:

1. What the dispatch expected.
2. What current `main` actually contains.
3. Which `discrete_count_statement` sub-shapes remain unresolved.
4. Which follow-up injector work is still justified.

The recommendation is **do not broaden the existing injector blindly**.
Keep v1 narrow. The next safe increment is a separate D.2.x spec for
one sub-shape at a time, beginning with **proper-noun possession with a
single static count and no clause split** if any remaining refused cases
still expose that exact shape after the current v1 injector is measured.

---

## Source inventory

| Artifact | Role | Relevant observation |
|---|---|---|
| `evals/gsm8k_math/train_sample/v1/report.json` | post-eval per-case verdicts | 50-case sample reports `correct=3`, `refused=47`, `wrong=0`; it does not expose recognizer category names in this artifact. |
| `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` | reader refusal taxonomy | Current taxonomy is by reader `missing_operator`, not recognizer category. It reports `multi_quantity_composition=8`, `quantity_extraction=11`, `pre_frame_filler_sentence=9`, etc. |
| `generate/recognizer_match.py` | recognizer match/extraction | `discrete_count_statement` now has extraction logic, not only detection. Empty anchors remain the safe fallback. |
| `generate/recognizer_anchor_inject.py` | recognizer anchor injection | v1 injector exists for `ShapeCategory.DISCRETE_COUNT_STATEMENT`; all other listed recognizer categories still skip-only. |
| `evals/gsm8k_math/train_sample/v1/cases.jsonl` | source problem text | The examples that resemble DCS work are heterogeneous: simple possession, multi-quantity possession, operations, temporal counts, rates, and composition. |

---

## Current implementation state

### Matcher state

`generate/recognizer_match.py` documents `RecognizerMatch.parsed_anchors` as
the value channel from recognizer match to downstream injection. For setup-only
recognizers, empty anchors are intentional; for DCS, current code attempts
single-anchor extraction.

The current DCS matcher:

- requires `anchor_kind == "discrete_count"`
- requires at least one quantity marker
- rejects currency symbols
- rejects per-unit framing
- rejects temporal-quantifier framing
- calls `_try_extract_discrete_count_anchor(...)`
- returns one populated anchor when extraction succeeds
- returns empty anchors as a detection-only fallback when extraction fails

The fallback is still important: empty anchors mean the recognizer may have
detected a shape, but the injector must refuse to build a candidate.

### Injector state

`generate/recognizer_anchor_inject.py` now has a v1 DCS injector.

Its doctrine is correct and should be preserved:

- pure deterministic injector
- refusal-preferring
- no LLM/embedding/classifier
- per-category boundary
- empty tuple on unsupported categories or unsupported DCS sub-shapes
- `CandidateInitial` only when the anchor can become an
  `InitialPossession`
- existing `_initial_admissible` remains the structural safety net

This means the stale dispatch assumption “DCS has no injector” is no longer
true on current `main`.

---

## DCS sub-shape taxonomy from current sample

The current 50-case sample shows several surfaces that a broad
`discrete_count_statement` recognizer could detect but that should not all
share one injector.

| Sub-shape | Examples from sample | Candidate primitive | Current safety stance | Follow-up fit |
|---|---|---|---|---|
| Simple static possession | `Yun had 20 paperclips initially`; `Dennis collected 10 rocks`; `Martha has 20 apples` | `CandidateInitial(InitialPossession(...))` only when verb is static possession and one quantity | v1 should admit only `has/have/had`; operation verbs defer | Possible narrow D.2.x expansion only for additional static possession verbs after proof |
| Multi-quantity initial state | `Francine has five full boxes ... and 5 loose crayons`; `Malcolm has 240 followers ... and 500 followers ...`; `Ella has 4 bags with 20 apples ... and six bags with 25 apples ...` | Multiple `CandidateInitial`s or composition graph | Current v1 must refuse; one anchor would be partial graph admission | CompositionClaim / multi-quantity composition, not DCS v1 |
| Temporal count aggregation | `Sidney does 20 jumping jacks on Monday, 36 on Tuesday...`; `Bob can shuck 10 oysters in 5 minutes` | Rate/aggregation operation, not initial possession | Must not map to DCS initial possession | Temporal aggregation injector, separate category |
| Operation sentence with count | `He bench presses 15 pounds for 10 reps and does 3 sets`; `He lost 3 pounds in March and 4 pounds in April` | Operation/composition, often multi-quantity | DCS must refuse; wrong=0 hazard if treated as initial state | FrameClaim + CompositionClaim, not DCS |
| Quantity extraction from descriptive/event setup | `Marnie makes bead bracelets`; `Jason has a carriage house that he rents out`; `John adopts a dog...` | Often no direct quantity or not math state | DCS should not force extraction | QuantityExtraction or setup-only handling |
| Compound numeric literal | `a hundred ladies` | Lexical/primitive numeric parsing | Not a DCS injector issue until numeric primitive exists | CompoundNumericLiteral first |

---

## Root cause: detection breadth vs injection narrowness

The DCS detector is intentionally broader than the injector.

That is acceptable only if the empty-anchor path remains refusal-preferring.
The hazard is not broad detection by itself. The hazard is **partial injection**:

```text
recognizer detects a quantity-bearing count sentence
injector builds one InitialPossession
remaining quantities/operations are silently ignored
downstream Cartesian product forms a solvable-but-wrong graph
```

The current v1 guardrails correctly prevent this by refusing extraction when:

- more than one numeric token is present
- clause split markers appear
- the subject is not a single proper noun
- the verb is not `has/have/had`
- the noun is not in the observed counted-noun set
- the count kind is outside the observed set

These conditions should not be relaxed inside the same injector without a new
ADR/spec and hazard pins.

---

## Proposed parsed-anchor shapes

### A. Existing v1: single static possession

Valid only for:

```text
<ProperNoun> has|have|had <count> <counted_noun>
```

with exactly one numeric token and no clause split.

Parsed anchor:

```json
{
  "kind": "discrete_count",
  "subject_role": "Yun",
  "count_token": "20",
  "count_kind": "integer",
  "counted_noun": "paperclips"
}
```

Maps to:

```text
CandidateInitial(
  InitialPossession(entity=subject_role, quantity=Quantity(value, counted_noun))
)
```

Admissibility checks:

- `CandidateInitial.__post_init__`
- `InitialPossession` invariants
- `_initial_admissible`
- graph completeness
- multi-branch disagreement refusal

### B. Deferred: multi-quantity initial state

Example:

```text
Francine has five full boxes of crayons and 5 loose crayons
```

Potential anchors would need to preserve two quantities and their relation:

```json
{
  "kind": "multi_quantity_initial",
  "subject_role": "Francine",
  "quantities": [
    {"count_token": "five", "unit": "boxes", "modifier": "full"},
    {"count_token": "5", "unit": "crayons", "modifier": "loose"}
  ],
  "composition": "container_plus_loose"
}
```

This does **not** map to a single `CandidateInitial`. It needs a composition
primitive or a sequence of explicitly related initials. It belongs under
CompositionClaim / multi-quantity composition.

### C. Deferred: temporal count aggregation

Example:

```text
Sidney does 20 jumping jacks on Monday, 36 on Tuesday, ...
```

This is not initial possession. It is event count per temporal bucket.
It maps to an aggregation/rate primitive, not DCS.

### D. Deferred: operation sentence with count

Example:

```text
He bench presses 15 pounds for 10 reps and does 3 sets.
```

This needs operation-frame semantics and multiple operands. It is explicitly
outside DCS v1 because admitting only one anchor would produce a partial graph.

---

## Lift estimate

Because the current `report.json` no longer exposes recognizer categories and
`audit_brief_11.json` reports reader missing-operator labels rather than
recognizer labels, the dispatch claim “21/47 are DCS” cannot be verified from
current artifacts without re-running or consulting older engine-state reports.

Using the current audit taxonomy instead:

| Bucket | Count | DCS relevance | Safe lift estimate from DCS v1 |
|---|---:|---|---:|
| `multi_quantity_composition` | 8 | many look like broad DCS detections, but are composition hazards | 0 direct; needs CompositionClaim |
| `quantity_extraction` | 11 | some are count-bearing event/setup sentences, not static possession | 0-1 direct; likely separate extraction specs |
| `pre_frame_filler_sentence` | 9 | some contain count words, but frame-opener issue dominates | 0 direct; needs FrameClaim |
| `unit_binding` | 4 | quantities exist but unit/entity attachment failed | 0 direct; SlotClaim/unit binding |
| `compound_numeric_literal` | 1 | numeric primitive missing (`hundred`) | 0 until primitive lands |

The honest conclusion: current remaining lift from **DCS v1 alone** is likely
small unless a fresh run shows simple `has/have/had N noun` refusals still
present. The high-count opportunity has shifted to composition/quantity/frame
work.

---

## Sequencing recommendation

1. **Do not broaden DCS v1 in-place.** It is correctly narrow and
   refusal-preferring.
2. **Measure current DCS residuals after #315/#D.2-era changes.** The dispatch
   count is stale against current `main` artifacts.
3. **If simple static possession still refuses**, add a D.2.x micro-spec for
   one expansion only, such as additional static possession verbs
   (`owns/holds/contains`) **only if** `CandidateInitial` already accepts those
   anchors and case-level replay keeps wrong=0.
4. **Route multi-quantity initial states to CompositionClaim**, not DCS.
5. **Route operation/frame sentences to FrameClaim / quantity extraction**, not
   DCS.
6. **Route pronoun or implicit-unit cases to ReferenceClaim / SlotClaim**, not
   DCS.

First follow-up to ship, by lift-per-risk:

```text
CompositionClaim spec for multi_quantity_composition
```

not broader DCS.

Why: the current taxonomy has 8 multi-quantity composition cases and 11
quantity-extraction cases. Both are larger remaining barriers than simple DCS
static possession. But CompositionClaim must come after the ADR-0168/0168.1
proposal-adapter discipline stabilizes, because it is structurally riskier
than lexical or simple initial-state injection.

---

## Required implementation guardrails for any future DCS expansion

A future DCS implementation PR must prove:

- no wrong>0 on train-sample replay
- no partial graph admission when multiple quantities are present
- no pronoun-subject extraction without ReferenceClaim
- no operation-verb extraction into `InitialPossession`
- no clause-split extraction
- no currency/rate/temporal leakage into DCS
- duplicate recognizer matches remain deterministic
- empty-anchor fallback remains skip-only

Any expansion that violates one of these belongs in a different sub-type, not
DCS.

---

## PR-body summary recommendation

Recommendation: **defer new DCS injector expansion** until a current residual
DCS report is available. Current `main` already contains a narrow DCS injector,
and the remaining visible barriers are composition, quantity extraction,
FrameClaim, SlotClaim, and ReferenceClaim work.

This preserves wrong=0 and avoids turning `discrete_count_statement` into a
catch-all for count-bearing English.
