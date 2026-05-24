# Scope: Teaching-Derived Structural Recognition

**Status:** Draft v2 / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-24 (v1: initial draft; v2: feature-bundle reframe + adversarial robustness + multi-resolution decoding)
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Companion:** [epistemic-state-taxonomy-scope](./epistemic-state-taxonomy-scope.md)
**Related:** ADR-0139 (algebraic substrate), ADR-0140 (additive group closure)

---

## Why this document exists

The thesis commits CORE to a single load-bearing principle: the engine's
competence is the **capacity to find, comprehend, and rationalize** —
not a library of founds. Hand-coded patterns, hand-authored pack data,
and pre-computed answers are inert; they store finds, not finding.

The GSM8K corridor violated this principle by adding regex patterns the
engine neither derived nor introspects. The lift program (ADR-0139 →
0145) corrects the *solving* side. This scope addresses the *recognition*
side — how the engine derives its own capacity to parse input into typed
propositions, without that capacity being scaffolded from hand-coded
patterns.

This scope document is the prerequisite for that work. It defines the
question. The answer belongs to the spike and the ADR that follows.

**v2 revision history.** Scope-time review on 2026-05-24 surfaced three
gaps that required rewriting v1:

1. **Feature-bundle reframe.** v1 used `InitialPossession` as the
   recognition target — pre-deciding the proposition category. v2
   replaces that with feature-bundle outputs whose type *emerges* from
   the lifted features.
2. **Adversarial robustness via evidence-bound lifts.** v1 had no
   defense against inputs that surface-match a pattern but evidence
   different content. v2 requires every feature lift to carry a span
   pointer, with contradiction-detection and counter-evidence handling
   as load-bearing structural commitments.
3. **Multi-resolution decoding.** v1 operated at one level. v2 commits
   to chunked-first / word-by-word-fallback as the recognition strategy,
   producing typed feature lifts at multiple resolutions.

Per [[feedback-scope-time-is-cheap]], surfacing these at scope time
saved the implementation from being shaped wrong. The same discipline
applies to whoever reviews this v2.

---

## The load-bearing unknown

> **Can structural generalization from N reviewed teaching examples
> produce a deterministic recognizer that:**
>
> 1. lifts a typed feature bundle from an unseen input whose structure
>    is consistent with the examples,
> 2. refuses unseen inputs whose structure is inconsistent OR whose
>    feature evidence is incomplete, contradictory, or counter-qualified,
> 3. replays byte-identically across runs, and
> 4. introspects — every lifted feature carries an evidence-span
>    pointer; every refusal carries a typed reason; every state
>    transition is auditable?

The four conditions are tight on purpose. Without (1), the recognizer
isn't decoding. Without (2), it can be fooled by surface resemblance.
Without (3), it's generating. Without (4), it's an LLM in deterministic
clothing.

---

## What "recognition" means concretely

Recognition is the operation that takes raw input text and produces a
**typed feature bundle** — or refuses with a typed reason. The
proposition's category (Possession / Desire / Future-Possession /
Negated-Possession / etc.) is a *consequence* of the lifted features,
not a pre-existing slot the engine fills.

For input "John has 5 apples":

```
FeatureBundle:
  agent:           span(0:4)  →  "John"
  relation:        span(5:8)  →  "has"
  quantity:        span(9:10) →  5
  object:          span(11:17) → "apples"
  polarity:        evidence(absence of negator across input) → affirmative
  modality:        evidence(bare verb form at span 5:8)      → actual
  tense:           evidence(present-tense morphology of "has") → present
  intentionality:  evidence(lexical content of "has")        → possession
```

Each feature has an **evidence span** (or evidence-derivation reason for
features inferred from absence, like polarity). No silent defaults. If a
feature can't be evidenced from the input, the bundle is incomplete and
the recognizer refuses.

The eventual proposition type (Possession, in this case) is computed
from the bundle by a downstream mapping that is itself derived from
teaching — not stipulated by the recognizer.

### How variations decode

| Input | What changes from baseline | Resulting proposition type |
|---|---|---|
| "John has 5 apples" | (baseline) | Possession |
| "John hasn't 5 apples" | polarity: negative | Negated-Possession |
| "John has not 5 apples" | polarity: negative (multi-word form) | Negated-Possession |
| "John may have 5 apples" | modality: possible | Conditional-Possession |
| "John might have 5 apples" | modality: possible (variant marker) | Conditional-Possession |
| "John will have 5 apples" | tense: future, modality: certain | Future-Possession |
| "John wants 5 apples" | intentionality: desire | Desire (different type entirely) |

Each row differs from the baseline in exactly the features the input
*evidences*. The type label emerges from the feature combination.

---

## Multi-resolution decoding

Recognition operates at multiple resolutions, falling through from
coarse to fine until the input is either fully resolved or fully refused.

### Resolution 1 — Chunk-level anti-unification

The input is divided into chunks (noun-phrase, verb-phrase, quantifier-
phrase, object-phrase). The chunk-level recognizer matches each chunk
against derived chunk patterns. If every chunk resolves cleanly and all
features can be lifted from chunk-level evidence, the bundle is emitted.

### Resolution 2 — Word-level fallback for unresolved chunks

If any chunk fails to resolve (e.g., the verb-phrase chunk shape
matches but contains an unrecognized modal auxiliary), the recognizer
drops to word-level on *just that chunk*. Word-level anti-unification
identifies which words are feature-binding markers (negators, modal
auxiliaries, intent verbs) and lifts them to the appropriate feature
slot in the bundle.

### Resolution 3 — Refusal with structured reason

If word-level also can't resolve, the recognizer refuses with a typed
reason naming exactly:

- Which chunk(s) couldn't be resolved
- Which word(s) within those chunks lack vocabulary
- Which feature(s) consequently can't be lifted

The structured refusal is what the teaching loop targets. A refusal
that names "word 'should' at position 2 of verb-phrase chunk is not in
decoded modality vocabulary" points the teaching corpus at exactly the
gap. Refusal becomes the engine's primary signal for what to learn next.

This is the analog of how `find → comprehend → rationalize` works in
the thesis: chunked recognition is the *find* step; word-level
decomposition is the *comprehend* step; bundle assembly is the
*rationalize* step. All three are deterministic. Failure at any step
produces a typed refusal with auditable provenance.

---

## Three-layer refusal-first

Recognition refuses at three distinct levels, each with its own typed
reason class:

### Layer 1 — Shape level

The input doesn't match any decoded chunk pattern.

> *"Input shape unrecognized: no decoded pattern matches the token
> sequence at the chunk level. Closest patterns: \[X, Y, Z\]; nearest
> distance: D."*

### Layer 2 — Feature evidence level

The shape matches but a feature has no supporting span. No default is
assumed.

> *"Shape recognized, but feature `modality` has no evidence span in
> the input. Decoded modality markers require explicit lexical
> evidence; no markers detected and no default permitted."*

### Layer 3 — Feature consistency level

Every feature has evidence, but two pieces of evidence contradict each
other on the same feature.

> *"Feature `polarity` evidenced at span 5:8 as affirmative and at span
> 18:24 as negative. Contradiction; refuse with no admission."*

> *"Counter-evidence detected at span 30:45 ('this is a lie') against
> otherwise-admissible bundle at spans 0:29. No decoded vocabulary for
> counter-evidence handling; refuse and surface as teaching candidate."*

All three layers produce **deterministic, typed, introspectable**
refusals. The engine isn't denying — it's pointing at exactly which
substrate it lacks. That's what makes recognition refusable without
becoming paralysis.

---

## Adversarial robustness as a structural property

The three-layer refusal is what makes adversarial inputs harmless
without requiring an anti-adversarial layer.

The thesis-aligned reading: *the engine doesn't need to spot
adversarial inputs; it needs to not be tricked into admitting them.*
Those are different commitments. Spotting is an arms race. Not-being-
tricked is a structural property of the decoder.

An adversary using "something Possession-like to claim misleading
possession" succeeds only if the engine accepts surface resemblance as
decoding success. Evidence-bound lifts make surface resemblance
insufficient — the engine has to point at *where in the input* each
feature came from. "Blowing smoke" leaves nothing for the lifts to bind
to in the dimensions that matter (intentionality, modality,
factivity), so the engine refuses on those dimensions even when the
surface pattern matches.

This is structurally analogous to how the math substrate refuses to
substitute approximate recall for exact recall. The engine doesn't get
fooled because *substituting "looks-like" for "is" is forbidden at the
substrate level*, not because anti-fooling logic is bolted on.

---

## Candidate mechanisms — honest evaluation

Four mechanisms surfaced earlier. Each is evaluated against the four
conditions above and against the thesis. (Unchanged from v1 except where
multi-resolution decoding affects the choice.)

### Mechanism A — Graph intersection over example output structures

Useful as a sub-component (defining target shapes). Not sufficient on
its own because it doesn't tell the engine how to map input text to
feature bundles. **Keep as building block.**

### Mechanism B — Versor extraction from input-pair variation

Requires text embedding into the CGA manifold, which doesn't exist yet.
Blocked short-term. **Reconsider after text-embedding scope.**

### Mechanism C — Null-cone region carving

Same embedding issue as B, plus "convex hull on a null cone" tends
toward approximate predicates. **Defer.**

### Mechanism D — Anti-unification over token sequences (multi-resolution)

**Leading candidate.** Deterministic, exact, well-defined (Plotkin 1970,
Reynolds 1970), maps cleanly to existing CORE primitives. Multi-
resolution operation: anti-unify at chunk level first, drop to word
level for unresolved chunks. Produces a recognizer that's a typed
pattern with evidence-binding slots — readable, serializable,
introspectable.

Satisfies all four conditions on its face:

1. *Admits matching inputs* — the derived pattern matches inputs whose
   token sequences fit the constants-and-typed-slots structure with
   complete evidence.
2. *Refuses non-matching, incomplete-evidence, or contradictory inputs*
   — three-layer refusal.
3. *Replays byte-identically* — anti-unification is deterministic on the
   same input set; the resulting pattern is structural.
4. *Introspects* — every position in the pattern has clear origin;
   every refusal points at specific missing or conflicting evidence.

Doesn't violate the thesis: the engine derives the pattern, isn't given
it.

---

## Why not statistical alternatives

Same as v1, kept here for completeness:

- **Statistical grammar induction** (PCFGs) — approximate by
  construction. Confidence scores are explicit refusal-of-determinism.
  Violates thesis.
- **Bayesian inference over parse structures** — posteriors aren't exact
  predicates. Violates thesis.
- **Neural sequence-to-structure models** — the LLM-shaped option the
  thesis explicitly names as the trap.

Anti-unification is *the* mechanism in this space that is deterministic,
exact, structural, introspectable, and well-defined on token sequences
at multiple resolutions. That is why it survives evaluation.

---

## The smallest provable test (proposed)

Two-phase structure. Each phase has binary acceptance; later phases run
only if earlier phases succeed.

### Phase 1 — Mechanism on uniform examples

Test whether anti-unification can produce a deterministic introspectable
recognizer **at all**, on the easy case where examples are uniform
across feature dimensions.

**Teaching examples (4, all `has`-relation, all affirmative, all actual):**

```
"John has 5 apples"            → bundle{agent, relation:has, count:5, unit:apple,  polarity:+, modality:actual, tense:present, intentionality:possession}
"Mary has 3 books"             → bundle{agent, relation:has, count:3, unit:book,   polarity:+, modality:actual, tense:present, intentionality:possession}
"A school has 100 students"    → bundle{agent, relation:has, count:100, unit:student, polarity:+, modality:actual, tense:present, intentionality:possession}
"The library has 12 chairs"    → bundle{agent, relation:has, count:12, unit:chair, polarity:+, modality:actual, tense:present, intentionality:possession}
```

(Determiner variation included so anti-unifier sees the determiner slot
as variable rather than constant.)

**Positive held-out (1):**

```
"A baker has 24 loaves"  →  bundle{..., relation:has, count:24, unit:loaf, polarity:+, modality:actual, ...}
```

**Acceptance:** recognizer admits, produces full feature bundle with
evidence spans for every feature.

**Negative held-out (Phase 1 — shape level only):**

```
"John gave 5 apples to Mary"  → REFUSED at Layer 1 (shape unrecognized: different verb structure)
```

If Phase 1 passes, the mechanism works on the easy case and Phase 2 is
warranted. If Phase 1 fails, the mechanism is wrong and Phase 2 is moot.

### Phase 2 — Variation lifting and adversarial robustness

Test whether multi-resolution decoding lifts meaningful variation as
typed features rather than collapsing or refusing.

**Teaching examples (8, varying polarity / modality / tense / intentionality):**

```
"John has 5 apples"            → polarity:+, modality:actual,  intentionality:possession
"Mary hasn't 3 books"          → polarity:-, modality:actual,  intentionality:possession
"The school has not 100 students" → polarity:-, modality:actual, intentionality:possession (multi-word negation)
"A library may have 12 chairs" → polarity:+, modality:possible, intentionality:possession
"John will have 5 apples"      → polarity:+, modality:certain, tense:future, intentionality:possession
"Mary wants 3 books"           → polarity:+, modality:actual,  intentionality:desire
"The school might need 100 students" → polarity:+, modality:possible, intentionality:requirement
"A baker offered 24 loaves"    → polarity:+, modality:actual, intentionality:offer
```

**Positive held-out (3 — variation lifting):**

```
"John doesn't have 5 apples"   → admit with polarity:- (multi-word negation form)
"Mary may need 3 books"        → admit with modality:possible, intentionality:requirement
"A baker will offer 24 loaves" → admit with tense:future, intentionality:offer
```

**Negative held-out (5 — adversarial robustness):**

```
"John has 5 apples but doesn't"        → REFUSED at Layer 3 (polarity contradiction across spans)
"John may or may not have 5 apples"    → REFUSED at Layer 3 (modality contradiction)
"Alleged possession of 5 apples"       → REFUSED at Layer 2 ('alleged' modality marker not in decoded vocabulary)
"John has 5 apples (this is a lie)"    → REFUSED at Layer 3 (counter-evidence parenthetical not decoded)
"John has either 5 or 6 apples"        → REFUSED at Layer 3 (quantity feature evidenced with two values)
```

**Acceptance:** recognizer admits all 3 positive variation cases with
correct feature bundles, refuses all 5 negative adversarial cases with
the specified typed reason class (Layer 2 or Layer 3 as indicated). No
silent defaults; no false admissions.

### Determinism gate (both phases)

Running the spike twice produces:
- Byte-identical derived recognizers
- Byte-identical admission/refusal decisions
- Byte-identical provenance records on every output

If any of these vary across runs, the spike fails regardless of
admission/refusal correctness.

---

## Output structure (commits to epistemic-state-scope shape)

Every recognition output is a `RecognitionOutcome` carrying:

```
RecognitionOutcome:
  proposition:     <feature_bundle | None>
  state:           <one of: EVIDENCED, CONTRADICTED, AMBIGUOUS, UNDETERMINED>
  provenance:      <structured: mechanism, teaching_set_id, evidence_spans, replay_seed>
  refusal_reason:  <typed reason if state is refusal-class | None>
```

The recognition spike produces only this subset of epistemic states
(EVIDENCED for admitted; CONTRADICTED / AMBIGUOUS / UNDETERMINED for
the three refusal layers). VERIFIED and DECODED are downstream of
substrate cross-reference work that doesn't exist yet.

This couples the recognition scope to the epistemic-state-scope without
entangling them. The output structure is ready for the full taxonomy
when the epistemic-state ADR lands; the recognition spike doesn't claim
to produce states it doesn't yet have evidence for.

---

## Prerequisites

The spike can be designed and prototyped before the lift program
finishes — anti-unification operates over token sequences independently
of how the resulting proposition is later solved.

The spike's *output* (a derived recognizer producing
RecognitionOutcomes) cannot be integrated into Engine A until
ADR-0144 exists (`PropositionGraph` from `MathProblemGraph`). Until
then, the derived recognizer would target Engine B's
`MathProblemGraph` and would have to be retargeted later.

Sequencing:

1. ADR-0140 (subtract) lands.
2. ADR-0141 (multiply) — concentrates remaining algebra risk.
3. Recognition Phase 1 runs in parallel with 0141.
4. ADR-0142 (Rate), ADR-0143 (compare).
5. Recognition Phase 2 runs in parallel with 0143.
6. ADR-0144 (`MathProblemGraph` → `PropositionGraph`).
7. Epistemic-state audit (Framing 1 from companion scope).
8. ADR-0145 (first GSM8K case end-to-end through Engine A) — uses lift
   substrate, derived recognizer, and ratified epistemic-state
   taxonomy together.

The spike does not block any of these. Integration is gated on
ADR-0144 and on the epistemic-state audit.

---

## Storage layer question (deferred)

Where does a derived recognizer live? Three candidates from v1, still
open:

- **In a pack** (e.g., `en_math_recognizers_v1`): ratified pack entries,
  checksums, teaching-loop review. Pros: fits ratification machinery.
  Cons: pack format needs new entry type.
- **In the vault**: exact-recall vault entries consulted at recognition
  time. Pros: existing recall path. Cons: vault currently for content,
  not capability.
- **As substrate (versor / graph) state**: recognizer becomes structural
  feature of Engine A itself. Pros: most thesis-aligned. Cons: requires
  substrate work that doesn't exist yet.

ADR decides. Scope does not commit.

---

## Risks the spike must surface (not pre-decide)

- **Generalization too narrow.** Anti-unifier may produce a pattern
  that admits only inputs almost identical to teaching. Measure;
  decide if more examples or richer anti-unification needed.
- **Generalization too broad.** False-admit rate against larger
  negative held-out set must be measured.
- **Chunk-level vs syntactic-level decision.** Token-sequence anti-
  unification ignores syntax. May need parse trees first. Defer
  decision to spike.
- **Evidence binding precision.** Every feature carrying a span is a
  strong claim. Some features (e.g., polarity from absence of
  negators) bind to *negative* evidence (no span). The provenance
  structure must accommodate this without weakening the
  "no silent defaults" rule.
- **Counter-evidence vocabulary.** Phase 2's negative held-outs assume
  the engine refuses on unrecognized modal markers ("alleged",
  "claimed") and counter-evidence parentheticals ("this is a lie").
  The first time the engine sees these, refusal with structured
  reason is required teaching input. The spike must produce
  refusals the teaching loop can consume.
- **Slot-type inference.** Recognizing `<COUNT>` as numeric and
  `<UNIT>` as noun requires either pack-resident type information
  (exists in `en_core_cognition_v1`) or derived type information
  (recursive scope creep). Spike surfaces which is needed.

---

## What the scope does NOT commit

- **No mechanism is selected.** Anti-unification (multi-resolution) is
  the leading candidate; spike tests it. Failure or fatal risk → re-
  evaluation.
- **No storage layer is selected.** Three candidates listed; ADR
  decides.
- **No integration timeline committed.**
- **No parsing framework selected.** Token-sequence first because
  simplest substrate; syntactic lift is fallback if token-level fails.
- **No commitment to the full epistemic-state taxonomy from this scope.**
  Recognition produces a subset (4 states); the full taxonomy is the
  companion scope's responsibility.

The scope's commitment is to **the question**. Answers belong to the
spike and the ADR.

---

## Open questions for follow-up scopes

Inherited from v1 (still deferred):

1. Text embedding into the CGA manifold.
2. Recursive derivation (recognizers-for-recognizers).

New from v2:

3. **Counter-evidence vocabulary as first-class teaching target.**
   "Alleged", "claimed", "(this is a lie)" need explicit teaching. The
   teaching loop's machinery for consuming Layer-3 refusals as
   correction candidates needs its own scope.
4. **Compositional epistemic states.** What does the engine do when
   recognition produces EVIDENCED but cross-reference produces
   CONTRADICTED? The transition machinery is the
   epistemic-state-scope's concern, but the recognition output
   structure must accommodate it.
5. **Lens-conditional recognition.** Different anchor lenses may
   produce different recognizers for the same teaching corpus
   (ἐπιστήμη lens vs. אמת lens may emphasize different features).
   How that interacts with this scope's deterministic-replay
   requirement is open.

---

## Summary

The load-bearing unknown for teaching-derived recognition is whether
deterministic structural generalization, operating at multiple
resolutions over a small ratified example set, produces a recognizer
that lifts typed feature bundles with evidence-bound provenance,
refuses cleanly at three layers (shape / feature evidence / feature
consistency), and replays byte-identically.

The leading candidate mechanism is **multi-resolution anti-unification
over token sequences** — the unique deterministic-exact-introspectable
option in the surveyed space.

The smallest provable test is a two-phase spike:

- Phase 1: 4 uniform examples → recognizer that admits matching unseen
  inputs at the shape level.
- Phase 2: 8 varied examples + 3 positive variation lifts + 5
  adversarial-style negative cases → recognizer with multi-resolution
  decoding and three-layer refusal.

Both phases require byte-identical replay across runs and structured
provenance on every output.

The spike can be designed in parallel with the lift program and does
not block active work. Integration into Engine A is gated on ADR-0144
and on the epistemic-state audit succeeding.

This document does not propose a decision. It defines the question.
Per [[feedback-scope-time-is-cheap]]: scope time is cheap. If a fourth
buried assumption is hiding here, surface it before the spike commits.
