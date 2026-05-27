# ADR-0169 — CompositionClaim Ratification Doctrine

**Status:** Proposed (doctrine/scoping ADR; no runtime mutation in this PR)
**Date:** 2026-05-27
**Author:** Shay
**Parent:** [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md)
**Related:** ADR-0056, ADR-0057, ADR-0114a, ADR-0164, ADR-0165, ADR-0166, ADR-0168, ADR-0172, ADR-0167 FOLLOWUPS §1

---

## Context

ADR-0167 scoped the first math-teaching corridor to `LexicalClaim` only.
ADR-0168 extended doctrine to `FrameClaim` — bounded frame-opening
admissibility under deterministic replay-constrained ratification.

`CompositionClaim` is the next sub-type in the queue from ADR-0167
FOLLOWUPS §1 and is, by counted audit evidence, the highest-leverage
remaining handler:

- 12 `quantity_extraction` refusals
- 8 `multi_quantity_composition` refusals

— **20 of 47** audit refusals in `evals/gsm8k_math/train_sample/v1/audit_brief_11.json`,
all carrying `refusal_reason="incomplete_operation"`.

> **Correction note.** ADR-0167 FOLLOWUPS §1 priority hint quoted
> "8+11 = 19 cases" for CompositionClaim. The actual audit count in
> `audit_brief_11.json` is **12 + 8 = 20** (`quantity_extraction` = 12,
> `multi_quantity_composition` = 8). This ADR uses the audit count.

`CompositionClaim` is qualitatively different from both LexicalClaim and
FrameClaim.

A `LexicalClaim` says:

> "surface form X belongs to lexical category Y"

A `FrameClaim` says:

> "surface form X opens (or does not open) a semantic frame of class K"

A `CompositionClaim` says:

> "surface pattern X composes a set of recognized quantities into a
> single derived quantity under composition category C"

That is an **arithmetic-chain admissibility decision**.

A `CompositionClaim` decides whether a frame which already recognized
its slots is permitted to fold multiple bound quantities into one
operand for downstream solver invocation. The hazard is direct and
asymmetric:

- a mistaken lexical entry creates noise
- a mistaken frame opener creates false reasoning structure
- a mistaken composition pattern **admits arithmetic errors**

A wrong composition does not pollute the graph topology. It pollutes
the operand fed to the solver. That is closer to the `wrong > 0`
surface than any prior sub-type.

This is the first ADR-0167 sub-type whose failure mode is:

> producing a numerically wrong but structurally well-formed answer

That is materially worse than refusal and materially worse than
graph fabrication, because the operator-facing trace looks correct.

---

## Prior ADR compatibility audit

This ADR is not final until it remains compatible with prior ADR doctrine.
The following audit was performed before opening implementation work.

| Prior ADR | Load-bearing rule | ADR-0169 compatibility result |
|---|---|---|
| ADR-0056 | Contemplation is cognitive only; no corpus mutation; reviewed evidence boundaries matter | Compatible. ADR-0169 keeps composition evidence proposal-only during contemplation; no corpus mutation. |
| ADR-0057 | Replay-equivalence is precondition, not permission; operator accept required; proposal logs append-only; reviewed-corpus evidence floor for cognition `TeachingChainProposal` | Compatible with constraint. CompositionClaim MUST use the math-specific proposal/ratification adapter (see ADR-0169.1) to preserve ADR-0057 discipline without laundering audit evidence as cognition corpus evidence. |
| ADR-0114a | Zero wrong, typed refusal, adversarial misparse=0, determinism, operation provenance | Compatible *and* elevates wrong=0 to first-class concern: composition is the closest sub-type to the arithmetic surface, so case 0050 and recognized-but-uninjectable hazards are mandatory pins. |
| ADR-0164 | Incremental reader over semantic categories; no hidden best guess; new categories/rules require ADR | Compatible. CompositionClaim ratifies reviewed composition-pattern membership only; no dynamic pattern synthesis. |
| ADR-0165 | Regex only at lexeme level; never grammar templates | Compatible with care. Composition patterns are *structural shape patterns* over already-recognized quantity slots, not grammar templates over raw text. Pattern catalog stays at the *bound-slot composition* level (e.g. `each <count> @ <one_unit_cost>` once both slots are bound), not at the sentence level. |
| ADR-0166 | Capability before measurement; no new eval lanes ahead of operators | Compatible. ADR-0169 is doctrine/capability scoping only and explicitly forbids new eval lanes in the implementation PR. |
| ADR-0167 | Audit rows become teaching evidence; LexicalClaim first; harder sub-types require their own ADR | Compatible. ADR-0169 is the explicit follow-on sub-type ADR called out in FOLLOWUPS §1. |
| ADR-0168 | FrameClaim is bounded frame-opening; allowlisted categories; refusal-first; proposal-only mutation | Compatible. CompositionClaim is **downstream of** FrameClaim and consumes already-opened frames; it never invents frames. |
| ADR-0172 | Math-corpus decomposition mechanism — contemplation, decomposer, workbench corridor (Tier 1.5) | Compatible. ADR-0169 introduces the next `change_kind` (`composition_reclassification`) and the next ratifiable handler in the corridor ADR-0172 established. |

### Resolved tension: ADR-0057 evidence floor

ADR-0057's ordinary `TeachingChainProposal` eligibility requires at
least one `source="corpus"` evidence pointer. Math-domain
CompositionClaims originate from audit/refusal artifacts, not from the
cognition teaching corpus.

ADR-0169 therefore does **not** weaken ADR-0057.

Implementation MUST use the math-specific proposal/ratification
adapter (`MathCompositionClaimProposal`) defined in ADR-0169.1, whose
evidence floor is `MathReaderRefusalEvidence` plus replay-admissibility
evidence, while preserving ADR-0057's append-only / replay /
operator-review discipline.

What is forbidden:

- treating audit evidence as cognition corpus evidence
- bypassing the reviewed-evidence floor
- auto-accepting because replay passed
- mutating runtime composition behavior outside the proposal/review boundary
- creating a second sub-type adapter that mimics ADR-0057 without these gates

This section is the compatibility trip-wire for any implementation PR.

---

## Decision

`CompositionClaim` ratification is permitted only as a deterministic,
replay-equivalent, operator-reviewed proposal surface with explicit
hazard pins and category allowlists.

This ADR does **not** approve runtime implementation.

This ADR defines:

- what a `CompositionClaim` is
- what it is allowed to mutate
- what it is forbidden to mutate
- the replay obligations required before implementation
- the initial safe composition-category surface
- the explicit non-goals

Implementation is deferred to a follow-on PR (CC-2 in
`docs/handoff/COMPOSITIONCLAIM-BRIEF-PACK.md`) that must prove the
acceptance gates below.

---

## Definition of a CompositionClaim

A `CompositionClaim` is a reviewed assertion that a structural
shape pattern over already-bound quantity slots composes those
quantities into one derived operand under a named composition
category.

Canonical shape:

```text
(surface_pattern, composition_category, polarity)
```

Where:

- `surface_pattern` is a deterministic structural pattern over
  already-recognized slots (e.g. `bound(count) bound(unit_cost)`),
  not a regex over raw text;
- `composition_category` is one entry of the
  `SAFE_COMPOSITION_CATEGORIES` allowlist;
- `polarity` is `"affirms"` (this pattern composes under category C)
  or `"falsifies"` (this pattern does NOT compose, refuse).

Examples (initial scope only):

| Pattern (shape over bound slots) | Category | Meaning |
|---|---|---|
| `bound(count) × bound(unit_cost)` | `multiplicative_composition` | total cost = count × unit_cost |
| `bound(qty_a) + bound(qty_b)` (independent named quantities in same frame) | `additive_composition` | aggregate = qty_a + qty_b |
| `bound(initial) − bound(removed)` | `subtractive_composition` | remainder = initial − removed |

The claim concerns:

- composition admissibility for a *recognized* slot tuple
- which operator binds those slots into one operand
- composition refusal stability when the pattern does not apply

It does NOT assert:

- frame admissibility (that is FrameClaim)
- entity identity
- quantity correctness (the slots are already bound)
- reference resolution (that is ReferenceClaim)
- slot completion (that is SlotClaim)
- solver validity

Those remain separate sub-types.

---

## Why CompositionClaim is dangerous

Composition patterns sit immediately upstream of solver invocation.

- a lexical error may fail to ground
- a frame error may fabricate a graph
- **a composition error feeds a wrong number to a correct solver**

The principal hazard is:

```text
recognized-and-well-formed-but-wrongly-composed operand
```

This is the asymmetric failure mode that produces:

- a structurally clean trace
- a typed, frame-opened, slot-bound graph
- an operator-plausible suggested CLI
- and a numerically wrong answer

Specifically threatening:

- GSM8K train-sample case **0050** (the canary preventing `pre_frame_filler`
  fixes from drifting into `wrong > 0`) — case 0050 illustrates how a
  composition mis-assignment can land a graph that *looks* admissible
- recognized-but-uninjectable skip-only fallback
- partial-graph greed promoted to full graph by a permissive
  composition pattern
- multi-quantity initial-state frames silently collapsing 3 distinct
  quantities into a sum that the original story did not require

The system must therefore prefer:

```text
refuse > leave the operand unbound > compose under an unproven pattern
```

at all times.

---

## Initial safe category scope

Initial implementation scope MUST be allowlist-only.

No freeform composition invention.
No dynamic pattern synthesis.
No embedding-nearest-pattern fallback.
No "majority vote" across competing categories.

Initial safe categories:

| Category | Scope |
|---|---|
| `multiplicative_composition` | `bound(count) × bound(one_unit_cost)` — produces a total under a single named unit semantic |
| `additive_composition` | sum of *independent* named quantities sharing the same frame and unit (e.g. apples + apples) |
| `subtractive_composition` | initial − removed, both bound in the same frame, sharing unit |

Allowlist (canonical):

```text
SAFE_COMPOSITION_CATEGORIES = {
    "multiplicative_composition",
    "additive_composition",
    "subtractive_composition",
}
```

Explicitly excluded initially:

| Deferred category | Reason |
|---|---|
| `distributive_composition` | requires nested frame interaction; multi-operator semantics |
| `ratio_composition` | unit-changing operation; demands SlotClaim for the denominator unit |
| `comparative_composition` | demands ReferenceClaim and ordering semantics |
| `percentage_composition` | requires `fraction_percentage_literal` recognizer (separate sub-type) |
| `unit_conversion_composition` | requires `unit_binding` slot doctrine (SlotClaim) |
| `time_composition` | `compound_time_literal` is its own recognizer concern |
| `chained_composition` | composition-of-compositions; explicitly deferred until the three primitives prove stable |

The decomposer dispatch table (`teaching/math_contemplation.py`, see
CC-3) maps the audit's `(refusal_reason, missing_operator)` pairs into
`composition_reclassification` only when the target category is in
`SAFE_COMPOSITION_CATEGORIES`. Anything else routes to
`injector_sub_shape` (the catch-all) — refuse-first.

---

## Mutation boundary

A `CompositionClaim` ratification MAY mutate only:

- reviewed composition-pattern registries:
  `language_packs/data/en_core_math_v1/compositions/{category}.jsonl`
- proposal-layer artifacts (append-only proposal log)

A `CompositionClaim` ratification MUST NOT directly mutate:

- solver logic
- parser traversal order
- decomposer dispatch (heuristic changes ship as their own reviewed PR,
  not as a side effect of ratification)
- runtime graph execution
- arithmetic operators
- refusal logic
- graph verifier semantics
- frame-opener registries (those are FrameClaim's surface)
- lexical registries (those are LexicalClaim's surface)

The runtime consumes ratified composition data only through existing
reviewed pack-loading mechanisms.

No direct hot-path mutation. No live-running registry edits.

---

## Replay obligations

Before implementation, the following replay obligations must be proven.

### 1. Deterministic claim signature

Equivalent refusals MUST produce identical normalized claim signatures.

Canonical identity must include:

- normalized surface pattern (over bound-slot shape, not raw text)
- normalized composition category
- polarity
- audit-row digest
- refusal category (`incomplete_operation`)
- missing operator (`quantity_extraction` | `multi_quantity_composition`)

Equivalent evidence MUST deduplicate.

---

### 2. Replay equivalence

Ratified `CompositionClaim`s MUST replay identically across:

- in-process runs
- cross-process runs (subprocess test)
- reordered candidate queues (queue-order independence)
- repeated ingestion of the same audit evidence (idempotency)

No queue-order dependence.

---

### 3. wrong==0 preservation

The implementation must prove:

```text
new composition admission cannot silently convert a prior refusal
into an incorrect arithmetic answer
```

This specifically requires hazard pins for:

- **case 0050** (`gsm8k-train-sample-v1-0050`) — pin in
  `tests/test_math_composition_ratification.py::test_case_0050_hazard_pin`;
  the case must remain refused after any synthetic CompositionClaim
  ratification in the allowlist
- recognized-but-uninjectable fallback
- partial graph acceptance
- multi-quantity initial-state collapse (e.g. case 0042: 3 quantities)
- operand swap (subtractive composition with reversed minuend/subtrahend)

---

### 4. Refusal stability

Previously refusing cases MAY become:

- correctly admitted (with a verified arithmetic answer)
- still refused

They MUST NOT become:

- partially admitted
- ambiguously admitted
- non-deterministically admitted
- structurally admitted with a wrong operand

Refusal stability MUST be verified across the **full**
`audit_brief_11.json` corpus, not just the 20 composition cases.

---

## Partition guarantees

CompositionClaims inherit the ADR-0167 domain partition.

Math-domain composition claims:

- use math-domain replay gates
- use math-domain contemplation routing
- do not borrow cognition corpus evidence
- do not reuse cognition semantic-domain classifiers
- do not produce cognition `TeachingChainProposal` records

Cross-domain leakage is prohibited.

The cognition `TeachingChainProposal` flow MUST NOT see math
`MathCompositionClaimProposal` records and vice versa. This is a hard
partition test in the implementation PR (mirror
`tests/test_math_frame_ratification.py::test_partition_*`).

---

## Refusal-first doctrine

The system must continue preferring:

```text
refuse > speculate
```

throughout CompositionClaim processing.

Specifically forbidden:

- nearest-pattern guessing
- probabilistic fallback category selection
- majority-vote composition admission
- confidence-threshold operand coercion
- dynamic composition synthesis at runtime
- "best guess" multiplication vs addition when both slots present

A composition the engine cannot prove under an allowlisted category
remains a refusal event.

The teaching corridor exists precisely so the engine does not need to
invent arithmetic structure at runtime.

---

## Non-goals

This ADR does NOT approve:

- ReferenceClaim
- SlotClaim
- `distributive_composition`, `ratio_composition`,
  `comparative_composition`, `percentage_composition`,
  `unit_conversion_composition`, `time_composition`,
  `chained_composition`
- dynamic composition synthesis
- graph-schema replacement
- automatic composition learning
- runtime self-modification
- autonomous pack mutation
- embedding-derived arithmetic repair
- a reviewed math corpus substrate (deferred — see ADR-0169.1
  "Why not a reviewed math corpus first?")

This ADR also does NOT attempt to solve:

- generalized arithmetic reasoning
- open-ended quantity composition
- unit-changing operations
- multi-step arithmetic chains

The target is bounded deterministic composition admission for audited
GSM8K-style reasoning surfaces under three allowlisted primitives.

---

## Sequencing

Per ADR-0166:

### Q1 — Capability

Adds one new operator-ratifiable admissibility surface:

```text
bound-slot shape pattern -> reviewed composition category
```

using the existing audit → contemplation → replay → HITL corridor
established by ADR-0167 and ADR-0172.

### Q2 — Lane

**No new eval lane.**

Existing:

- GSM8K audit lane (`evals/gsm8k_math`)
- contemplation replay lane (`core eval math-contemplation`)
- wrong==0 gates
- determinism checks

remain the proof surface.

### Q3 — Invariant

Must preserve:

- `wrong == 0`
- replay equivalence
- deterministic claim hashing
- refusal-first semantics
- explicit operator ratification
- reviewed mutation only
- domain partition (math vs cognition)

The implementation PR passes only when all seven are mechanically proven.

---

## Acceptance gates for implementation PR

A future implementation PR (CC-2) must provide:

- deterministic claim canonicalization tests
- cross-process replay-equivalence tests (subprocess)
- queue-order independence tests (A→B == B→A ratify)
- duplicate ratification idempotency tests (`AlreadyRatified` on second call)
- evidence-tampering rejection tests
- **case 0050 hazard pin** — mandatory; mirror
  `tests/test_math_frame_ratification.py::test_case_0050_hazard_pin`;
  case 0050 must remain refused after any synthetic CompositionClaim
  ratification under the initial allowlist
- recognized-but-uninjectable regression pins
- refusal-stability regression suite across the **full**
  `audit_brief_11.json` corpus
- cross-domain partition tests (cognition `TeachingChainProposal` flow
  must NOT see math CompositionClaims and vice versa)
- no-corpus-mutation proof (cognition corpus bytes unchanged during
  math composition replay)
- no-runtime-hotpatch proof (solver / parser / decomposer / graph
  verifier bytes unchanged)
- audit-evidence-not-laundered-as-corpus test (the adapter must emit
  `source="math_audit"`, never `source="corpus"`)
- workbench dispatch test: `composition_reclassification` routes to
  `CompositionClaim`, not 501
- proposed_change_kind Literal accepts `composition_reclassification`
- W1 round-trip test extended for the new `change_kind`

without introducing:

- new eval lanes
- stochastic routing
- runtime graph guessing
- categories outside `SAFE_COMPOSITION_CATEGORIES`

---

## Relationship to ADR-0167 and ADR-0168

ADR-0167 established:

```text
audit rows become teaching evidence
```

ADR-0168 established:

```text
frame-opening semantics may become reviewed teaching evidence
```

ADR-0169 establishes:

```text
composition patterns over already-bound slots may become reviewed
teaching evidence — but only under deterministic replay-constrained
doctrine, and only inside an allowlisted category surface, because
composition errors are the closest sub-type to direct arithmetic
wrongness
```

The escalation is intentional:

- LexicalClaim teaches vocabulary
- FrameClaim teaches admissibility structure
- CompositionClaim teaches arithmetic-chain admissibility

Each step is materially more dangerous than the last and therefore
requires explicit doctrine before implementation.

---

## Decision

> CORE may extend the ADR-0167 teaching corridor from lexical and
> frame ratification into bounded composition-pattern ratification,
> provided:
>
> - replay equivalence remains deterministic
> - `wrong == 0` hazard pins hold (case 0050 mandatory)
> - composition categories remain explicitly allowlisted
> - runtime speculation remains prohibited
> - all mutation remains proposal-reviewed and replay-auditable
> - the math-domain proposal/ratification adapter (ADR-0169.1) is
>   used; audit evidence is never laundered as cognition corpus
>   evidence
>
> Refusal remains preferable to speculative arithmetic composition.

Reopening this ADR requires evidence that:

1. the replay obligations cannot be satisfied mechanically, or
2. a graph-schema approach supersedes sub-type ratification entirely, or
3. composition wrong-rate cannot be held at zero under the proposed
   allowlist (in which case the allowlist contracts, not expands).
