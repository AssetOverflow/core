# ADR-0138 — Comparative-Reference Layer

**Status:** Draft (design-only)
**Date:** 2026-05-23
**Parent:** [ADR-0136](./ADR-0136-statement-layer-corridor.md)
**Informed by:** [ADR-0136.S3-post-rescan](./ADR-0136.S3-post-rescan.md), [ADR-0136.S2-post-rescan](./ADR-0136.S2-post-rescan.md) (ADR-0137 deferral note)
**Supersedes (in scope):** [ADR-0137](../decisions/) — closed without merging; reopened here in a lighter, shape-driven form

---

## Context

The S.x corridor is bounded. Each phase ships one closed regex shape and
yields 0–1 admissions + ~1 barrier shift. After S.0/S.1/S.2/S.3 the
GSM8K probe sits at **3/50 admitted, wrong=0**, with the next-largest
blockers fragmented across heterogeneous shapes:

```
compound_statement      5  (heterogeneous — see ADR-0136.S.3 deferred list)
novel_initial_form      5  (S.4 candidate)
fraction_operand        4  ← target of this ADR
novel_initial_verb      4
compound_comparative    3  ← target of this ADR
conditional_question    3
context_filler          3  (correctly refused)
```

The seven cases under `fraction_operand` + `compound_comparative` are
not seven separate regex shapes. They share a common deep structure:
**a value-bearing phrase whose value is relative to either a numeric
anchor in the same sentence or a referenced quantity from a previous
sentence.**

Per-case decomposition:

| Case | Shape | Anchor source |
|---|---|---|
| 0005 | `decrease to 3/4 of its temperature` + `current temperature is 84` | sentence-internal numeric |
| 0029 | `keyboard cost three times greater than the cost of the mouse` + `mouse cost $16` | sentence-internal numeric |
| 0041 | `75% of the 2nd pan` (after `2 pans…16 pieces per pan`) | sentence-internal referent |
| 0043 | `father gave twice as much as her mother` (after `mother gave $4`) | prior-sentence quantity |
| 0010 | `Marion has 1/4 more than what Yun currently has, plus 7` | **prior-sentence derived quantity** |
| 0004 | `Half of the kids…` + `1/4 of the kids going to soccer camp…` + `750 kids…in the afternoon` | inverse: known sub-quantity, unknown total |
| 0036 | `as much again as Wednesday, Thursday and Friday combined` | multi-term aggregate reference |

0005 and 0041 admit sentence-internal grounding. **0029 is the
forcing case for cross-sentence binding** — its comparative
("three times greater than the cost of the mouse") in one sentence
resolves against a literal anchor ("the mouse cost $16") in a later
sentence, with no ambiguity. 0043 requires a similar chain
(`twice as much as her mother` after `mother gave $4`). 0010 is
genuinely *ambiguous English* — its expected dataset answer
requires a non-standard parse of "1/4 more than X"; this ADR
refuses on it (see §Scope). 0004 and 0036 require additional
machinery (inverse arithmetic, multi-term aggregation) and are out
of scope.

**Why this ADR, not S.x.** S.x ships one regex shape per phase. The
comparative-reference cluster is one *deep* structure with multiple
*surface* shapes. Treating each surface as a separate S.x phase wastes
effort and produces a forest of overlapping regexes. A small typed
layer that represents the deep structure once and consumes multiple
surfaces is the right unit of work.

**Why not ADR-0137 as drafted.** The closed-and-deferred ADR-0137
proposed a generic `DeferredCandidate` / `BindingProof` apparatus for
any kind with open slots. Its deferral reason stands: subsuming the
S.1/S.2 short-circuits (which are joins of grounded candidates, not
deferred bindings) wouldn't have used the machinery. Now that
gsm8k-0010 has surfaced a *real* deferred-binding case, the right
response is not to revive the generic apparatus. It is to ship a
**typed reference layer** with one shape — `QuantityReference` — that
specifically handles cross-sentence quantity lookup, and to keep the
machinery as light as the actual problem.

---

## Decision

### 1. Three typed phrase structures, no generic deferred-candidate apparatus

Introduce three frozen, slotted dataclasses representing the deep
structure of comparative/fractional phrases:

```python
@dataclass(frozen=True, slots=True)
class FractionOperand:
    """A fraction-shaped operand: 1/4, half, 75%, 3/4, etc."""
    numerator: int                  # e.g. 1
    denominator: int                # e.g. 4
    of_target: ReferenceTarget | None  # e.g. "the 2nd pan", "the kids"
    source_span: str

@dataclass(frozen=True, slots=True)
class ComparativeOperand:
    """A comparison: 'three times greater than X', '1/4 more than X',
    'twice as much as X', 'half as long as X'."""
    direction: Literal["more", "less", "times_greater", "times_as_much",
                       "fraction_more", "fraction_less"]
    modifier: FractionOperand | int | float  # the multiplier or addend
    anchor: ReferenceTarget                  # what's being compared to
    source_span: str

@dataclass(frozen=True, slots=True)
class ReferenceTarget:
    """An anchor: either a literal numeric value visible in the same
    sentence, or a typed reference to a quantity introduced earlier."""
    kind: Literal["literal", "quantity_reference"]
    literal_value: int | float | None          # set when kind == 'literal'
    quantity_reference: QuantityReference | None  # set when kind == 'quantity_reference'

@dataclass(frozen=True, slots=True)
class QuantityReference:
    """A typed cross-sentence reference: 'what Yun currently has',
    'the cost of the mouse', 'the 2nd pan', 'her mother [gave]'."""
    entity: str | None             # named entity (Yun), or None for "the X" descriptors
    descriptor: str | None         # 'the 2nd pan', 'the cost of the mouse'
    qualifier: str | None          # 'currently', 'initially'
    source_span: str

    @property
    def needs_binding(self) -> bool:
        return True
```

These types are **descriptive only** at the first pass. They carry no
admissibility check on their own; they are slots that the binding pass
(§3) closes.

### 2. Extractor responsibilities (first pass)

Three new extractor functions in `generate/math_candidate_parser.py`,
each producing typed phrases rather than full candidates:

- `extract_fraction_operands(sentence)` → `list[FractionOperand]`
- `extract_comparative_operands(sentence)` → `list[ComparativeOperand]`
- (`QuantityReference` is constructed inside the above two when their
  anchor is non-literal.)

These extractors emit phrases. They do **not** produce
`CandidateInitial` or `CandidateOperation` directly. Promotion happens
in the binding pass.

### 3. The binding pass (lighter than ADR-0137's draft)

A single new control-flow stage between first-pass extraction and the
existing Cartesian product. Its only job: **resolve `QuantityReference`
slots against prior-sentence grounded candidates**, then promote
fully-grounded `ComparativeOperand` / `FractionOperand` phrases into
`CandidateInitial` (when they describe an entity's quantity) or
slot-fillers for question candidates (when they describe a value asked
about).

The binding pass:

1. Iterates over `ComparativeOperand` + `FractionOperand` phrases in
   sentence order.
2. For each phrase with a non-literal anchor, looks up the
   `QuantityReference` against the cumulative grounded-candidate set
   from earlier sentences.
3. Resolves only when the reference is **unique** — single matching
   (entity, descriptor) → single quantity. Ambiguous references refuse
   the resolution (drop, not best-effort).
4. Computes the resolved value via the comparative/fractional rule:
   - `times_greater(N, anchor)`: `anchor * (N + 1)` (interpretation
     pinned by ADR-0138; *N times greater* is ambiguous in English and
     we pick one closed reading — see §Non-negotiables).
   - `times_as_much(N, anchor)`: `anchor * N`
   - `fraction_more(F, anchor)`: `anchor * (1 + F)`
   - `fraction_less(F, anchor)`: `anchor * (1 - F)`
   - `more(N, anchor)`: `anchor + N`
   - `less(N, anchor)`: `anchor - N` (refuses on negative result)
5. Promotes the resolved value into the existing `CandidateInitial`
   path via the same round-trip filter.

No `DeferredCandidate` type. No `BindingProof` type. The pass is a
deterministic lookup-and-promote operation. Replay determinism comes
from the same JSON-sort-keys serialization the cognition eval already
uses.

### 4. Sentence-internal grounding (no binding pass needed)

When `ComparativeOperand.anchor.kind == "literal"`, the value is
extracted in the first pass without involving the binding pass. This
handles the 0005 / 0029 cases (sentence-internal numeric anchor) and
0041 (sentence-internal referent + same-sentence quantity).

### 5. ADR-0137 supersession

The closed ADR-0137 is **superseded in scope** by this ADR. The
deferral note in `ADR-0136.S2-post-rescan.md` stands; the binding
machinery this ADR proposes is the answer to its "reopen criterion."
This ADR is lighter because it commits to **one** typed reference
shape (`QuantityReference`) rather than a generic `DeferredCandidate`
apparatus.

The S.1/S.2 short-circuits in `parse_and_solve` **stay** as joins of
grounded candidates. They are not retrospective binding and this ADR
does not subsume them. (The canonical-runner staleness issue is fixed
separately by teaching the runner to score short-circuit admissions.)

---

## Scope

### In scope (this ADR + its implementation phases)

- `FractionOperand`, `ComparativeOperand`, `ReferenceTarget`,
  `QuantityReference` type machinery
- First-pass extractors for the closed surface set:
  - `<N> times greater than <anchor>`
  - `<N> times as much/many/long as <anchor>`
  - `<fraction> more than <anchor>` (where `<fraction>` ∈ {1/2, 1/4,
    3/4, half, twice} or `<N>%`)
  - `<fraction> less than <anchor>`
  - `<fraction> of <descriptor>`
  - `<N>% of <descriptor>`
- Binding pass: sentence-order lookup of `QuantityReference` against
  prior grounded candidates with unique-match gating
- Probe lane `RC1_comparative_reference` with the three cleanly
  in-scope cases (0029, 0041, 0010) plus negative probes (0005 — see
  below — 0004, 0036, 0043)
- ADR-supersession note added to ADR-0136.S2-post-rescan.md
  acknowledging that 0137's reopen criterion is met by 0138

### Out of scope (deferred to follow-up ADRs)

- **Inverse arithmetic** (case 0004): "750 kids are afternoon, 1/4 are
  morning → total = 1000" requires solving for the unknown total from a
  known sub-quantity. Different machinery (inverse fraction inference).
- **Multi-term aggregate references** (case 0036): "as much again as
  Wednesday, Thursday and Friday combined" requires summing multiple
  prior quantities through a single reference. Probably ADR-0139.
- **Self-reference** (case 0005): "decrease to 3/4 of *its*
  temperature" — note this case is *in* the in-scope set as a
  *negative probe*: the binding pass must **refuse** on self-references
  (`its` resolves to the same entity whose value is being computed,
  yielding a circular binding). Confirm in the lane that 0005 still
  refuses.

Wait — re-examining 0005: "Addison mountain's temperature will
decrease to 3/4 of its temperature. If the current temperature is 84
degrees, what will the temperature decrease by?" The anchor *is*
sentence-internal — "the current temperature is 84." The "its" refers
to "Addison mountain's temperature" which is given as 84. So 0005 is
actually in scope under sentence-internal grounding once the
question-form is parsed. **Reclassified to in-scope.** Negative probes
remain 0004 and 0036.

### Cases this ADR is expected to admit

| Case | Expected outcome | Mechanism |
|---|---|---|
| 0005 | **admit (answer=21)** | sentence-internal fraction-of-anchor + question-resolution rule |
| 0029 | **admit (answer=64)** | cross-sentence `QuantityReference` resolution: comparative in sentence 2 ("three times greater than the cost of the mouse") resolved against sentence 3's literal ("the mouse cost $16") |
| 0041 | partial — likely still refuses | needs sentence-internal referent resolution; depends on whether `_INITIAL_HAS_RE` or its sibling grounds "2 pans" with a per-pan quantity |
| 0043 | partial — needs chain (mother + father + total + purchase) | the comparative `twice as much as her mother` resolves cleanly; total-aggregation across the rest is multi-term, out of scope |

Honest expected admission delta: **+1 to +2** (0005, 0029 at high
confidence; 0041 and 0043 partial credit only if the linguistic
structure composes with existing extractors).

**On gsm8k-0010 (the case that surfaced the forcing function).** The
forcing case for cross-sentence binding turned out to be **0029, not
0010**. 0010's sentence 2 ("Marion has 1/4 more than what Yun
currently has, plus 7") has a genuinely ambiguous English reading.
The dataset's expected answer is 9, which requires parsing the phrase
as `(1/4) * Yun + 7 = (1/4)*8 + 7 = 9` — treating "1/4 more" as
"1/4 [of what Yun has]" rather than "1/4 *more than* [Yun's
quantity]." The natural English reading
(`Yun * (1 + 1/4) + 7 = 17`) disagrees with the dataset.

Per non-negotiable #2 of this ADR, **0010 must refuse**. Multiple
plausible parses of the same surface yield different numeric values;
the binding pass refuses rather than picks one. 0010 is reclassified
from "expected admission" to "negative probe" — it stays refused, and
the reason (ambiguity) becomes a regression assertion in the lane.

This is the right outcome under refusal-first discipline, and it
proves that the cross-sentence binding case must be justified by an
unambiguous example. **0029 is that example.**

---

## Non-negotiables

1. **`wrong == 0` remains a hard CI gate.** Across the binding eval
   lane and the GSM8K probe.
2. **Ambiguous reference → refuse the binding.** If `QuantityReference`
   has multiple matching prior candidates with different values, the
   resolution refuses; the problem refuses; no best-effort.
3. **Pinned English-reading convention for "N times greater."**
   English usage is ambiguous (some readers: `anchor + anchor * N`;
   others: `anchor * N`). This ADR pins the additive reading
   (`anchor * (N + 1)`) and **documents the choice in the ADR + the
   lane test**. If a downstream case appears that requires the other
   reading, refuses-then-revisit; do not silently pick the other.
4. **No new short-circuit path in `parse_and_solve`.** Promoted
   candidates flow through the existing graph machinery.
5. **No solver/graph/verifier changes.** Linguistic layer ends at
   candidate emission.
6. **Determinism.** Same input → byte-equal `BindingPassResult`s,
   byte-equal promoted-candidate set, byte-equal `report.json`.
7. **Closed surface vocabulary.** All comparative + fractional surface
   markers are enumerated. No wildcards. New markers require
   extending the closed set (in the same PR as the test case that
   forces them).

---

## Probe set

### Required admissions

| Case | Source | Why this exercises the layer |
|---|---|---|
| 0005 | GSM8K | sentence-internal fraction-of-anchor + literal-value path |
| 0029 | GSM8K | cross-sentence `QuantityReference` resolution; **the forcing case** for the binding pass |

### Required refusals (negative probes)

- **gsm8k-0010** — ambiguous English (`1/4 more than X` parses as
  either `X * (1 + 1/4)` or `(1/4) * X`); the binding pass must refuse
  per non-negotiable #2
- **gsm8k-0004** — inverse arithmetic (must continue to refuse pending
  ADR-0139)
- **gsm8k-0036** — multi-term aggregate reference (must continue to
  refuse pending ADR-0139)
- A synthetic ambiguous-reference case where two prior sentences
  introduce the same `(entity, unit)` with different values — must
  refuse (uniqueness gate)

### Axis cases (synthetic, ≥15)

Closed combinations of the surface vocabulary × anchor kinds:
- `<frac> of <literal>` ≥3
- `<frac> of <reference>` ≥3
- `<N> times as much as <literal>` ≥3
- `<N> times greater than <reference>` ≥3
- `<frac> more than <reference>` ≥3 (covers 0010's shape)

---

## Phased rollout

One branch per phase. The 2026-05-23 worktree-race lesson stands.

| Phase | Deliverable | Branch |
|---|---|---|
| 0138.D | This ADR | `docs/adr-0138-comparative-reference-layer` (this PR) |
| 0138.A | `generate/comparative/{types,extractors}.py` + tests for the type machinery and the closed surface vocabulary (no binding pass yet) | `feat/adr-0138-types-and-extractors` |
| 0138.B | Binding pass + `QuantityReference` resolution + 0010 admission + 0005/0029 admissions | `feat/adr-0138-binding-pass` |
| 0138.C | Eval lane `RC1_comparative_reference` + probe set | `feat/adr-0138-rc1-lane` |

Each phase is its own PR. Each must hold `wrong == 0`, preserve all
existing axis lanes (S.1, S.2, S.3, S.4 if landed), and not regress
the rescan-v3 invariants.

After 0138.B lands, run a rescan v4 to record barrier shifts and
update the post-rescan ADR.

---

## Open questions (deferred to implementation ADRs, not this one)

- **Promotion of fractional-of-set phrases.** "Half of the kids" with
  no prior quantification of "the kids" produces a refusal in 0138.B
  (no resolvable reference). Case 0004's full solution requires
  inverse arithmetic on this same shape. Future ADR-0139 (inverse
  arithmetic) will compose with this layer.
- **Pronoun resolution depth.** "Marion has 1/4 more than what *Yun*
  currently has" names Yun explicitly. Cases like "*he* has 1/4 more
  than what *she* has" need pronoun resolution against the prior-actor
  set. Out of scope; refuse on pronoun-anchored references until a
  future ADR.
- **Telemetry.** Whether `QuantityReference` resolution events emit
  into the existing turn-event telemetry sink. Probably no for now;
  cognition runtime is not consuming math problems on the hot path.

---

## Consequences

- The forcing function for retrospective binding (denied at #204
  closure, surfaced at #208 rescan v3) is met by a typed reference
  layer rather than a generic deferred-candidate apparatus. Smaller,
  more specific, easier to audit.
- The S.x corridor continues for shape-specific extensions
  (`novel_initial_form`, `novel_initial_verb`, the remaining
  `compound_statement` shapes). 0138 is *parallel* to S.x, not its
  replacement.
- The corpus of `comparative + fraction-of-quantity` problems is large
  in GSM8K's full set (not just the 50-case train sample). This
  layer's value compounds as the probe widens beyond the train sample.
- The pinned "N times greater = N+1 multiplier" reading is a CORE
  convention. If we later encounter a case that requires the other
  reading, the lane test will flag it and the closed-set decision
  becomes revisitable rather than buried.

---

## What this ADR is not

- Not a code change. No `generate/comparative/` module exists at merge
  time.
- Not a generic deferred-candidate framework. It commits to one typed
  reference shape (`QuantityReference`) and one binding rule
  (unique-match cross-sentence lookup).
- Not a replacement for the S.x corridor. The two are parallel.
- Not a license to add semantic guessing. Every comparative,
  fractional, and reference shape is a closed-set surface pattern with
  a deterministic resolution rule.
- Not in conflict with CLAUDE.md. The binding pass is exactly the
  shape of "comprehend → recall → think" — hold a typed reference,
  bind it deterministically when the prior quantity is grounded,
  refuse when ambiguous.
