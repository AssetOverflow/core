# ADR-0143: Teaching-Derived Structural Recognition via Multi-Resolution Anti-Unification

**Status:** Accepted
**Date:** 2026-05-24
**Scope doc:** [teaching-derived-recognition-scope](./teaching-derived-recognition-scope.md)
**Related:** ADR-0142 (epistemic state taxonomy), ADR-0144 (PropositionGraph — integration gate)

---

## Context

CORE's recognition path currently uses hand-coded regex patterns that the engine
neither derived nor can introspect. These patterns store finds rather than
teaching finding. The thesis requires the engine's capacity to recognize
proposition structure to emerge from reviewed teaching examples — not from
hand-authored scaffolding.

The recognition scope document (v2, 2026-05-24) evaluated four candidate
mechanisms and selected **Mechanism D: multi-resolution anti-unification over
token sequences** as the only option that is simultaneously deterministic,
exact, structural, introspectable, and well-defined on token sequences. The
scope committed the spike to a two-phase acceptance test.

This ADR records the decision to implement Mechanism D and defines the output
contract that all recognition work must conform to.

## Decision

**Adopt multi-resolution anti-unification over token sequences as the
recognition mechanism.**

The recognizer is derived deterministically from a reviewed teaching example
set. It operates at two resolutions:

1. **Chunk level** — anti-unify at noun-phrase / verb-phrase / quantifier-phrase
   chunks. If every chunk resolves with complete feature evidence, emit the
   bundle.
2. **Word-level fallback** — for any chunk that fails at chunk level, drop to
   word-by-word anti-unification on just that chunk and attempt to lift the
   relevant feature slot.

At both resolutions, the recognizer refuses rather than guesses when evidence
is absent or contradictory. Refusal is the primary signal for what to learn
next.

## Output contract

Every recognition output is a `RecognitionOutcome` (defined in
`recognition/outcome.py`). The contract is frozen; implementers must not
add alternative output types.

```
RecognitionOutcome:
  state:           EVIDENCED | UNDETERMINED | CONTRADICTED | AMBIGUOUS
  proposition:     FeatureBundle | None
  refusal_reason:  ShapeRefusal | FeatureEvidenceRefusal | FeatureConsistencyRefusal | None
  provenance:      RecognitionProvenance
```

**Invariants:**
- `state == EVIDENCED` → `proposition` is a complete `FeatureBundle` with
  evidence on every feature; `refusal_reason` is `None`.
- Any refusal state → `proposition` is `None`; `refusal_reason` is a typed
  instance naming exactly what is missing or contradictory.
- `provenance` is always present. It carries `mechanism`, `teaching_set_id`
  (SHA-256 of the canonical example set), and `resolution_level`.

**Epistemic states emitted.** Recognition produces only this subset of the
ADR-0142 taxonomy: EVIDENCED (admitted), UNDETERMINED (shape refused),
CONTRADICTED (feature contradiction), AMBIGUOUS (unresolvable ambiguity).
VERIFIED and DECODED are downstream of substrate cross-reference work and are
never emitted by the recognizer itself.

## Three-layer refusal

| Layer | Class | Trigger |
|---|---|---|
| 1 — Shape | `ShapeRefusal` | Input does not match any derived pattern |
| 2 — Feature evidence | `FeatureEvidenceRefusal` | Shape matched; a required feature has no evidence span |
| 3 — Feature consistency | `FeatureConsistencyRefusal` | Two evidence spans contradict each other on the same feature |

Every layer produces a deterministic, typed, introspectable refusal. The engine
does not approximate or default — it points at exactly which substrate is
missing.

## Feature bundle requirements

Every `BoundFeature` in an admitted bundle carries:
- `name`: the feature dimension (agent, relation, count, unit, polarity,
  modality, tense, intentionality, ...)
- `value`: the typed feature value (str | int | float)
- `evidence`: an `EvidenceSpan` (token indices + verbatim text) or a
  `NegativeEvidence` record (for features established by absence, e.g.
  `polarity=affirmative` from the absence of a negator)

No silent defaults. If a feature cannot be evidenced, the recognizer refuses
at Layer 2.

## Determinism requirements

- `derive_recognizer(examples)` → byte-identical `DerivedRecognizer` on the
  same input across runs.
- `recognize(recognizer, tokens)` → byte-identical `RecognitionOutcome` on
  the same recognizer and input across runs.
- `DerivedRecognizer` must be serializable to/from JSON for replay.
- `teaching_set_id` is SHA-256 of the sorted canonical example token sequences;
  it must be byte-identical across runs on the same examples.

## Acceptance test (two-phase spike)

### Phase 1 — Mechanism on uniform examples

Four teaching examples (all `has`-relation, all affirmative, all actual-
modality — see scope doc). Derived recognizer must:

1. Admit `"A baker has 24 loaves"` with full feature bundle and evidence spans.
2. Refuse `"John gave 5 apples to Mary"` with `ShapeRefusal` (Layer 1).
3. Produce byte-identical output on both cases across two runs.
4. Every feature in the admitted bundle has non-None evidence.

Phase 1 pass → Phase 2 is warranted. Phase 1 fail → mechanism is wrong.

### Phase 2 — Variation lifting and adversarial robustness

Eight teaching examples (varying polarity / modality / tense / intentionality).
Derived recognizer must:

1. Admit three positive variation cases with correct feature bundles.
2. Refuse five adversarial cases at the correct refusal layer (Layer 2 or 3).
3. Produce byte-identical output across two runs.

Full test cases in scope doc.

## What this ADR does NOT commit

- **Storage layer.** Where derived recognizers live (pack / vault / substrate
  state) is deferred to the ADR that follows the spike.
- **Integration into Engine A.** Gated on ADR-0144 (PropositionGraph). Until
  then, the recognizer is a standalone module.
- **Parsing framework.** Token-sequence anti-unification is the starting point;
  syntactic parse trees are a fallback if token-level fails.
- **Counter-evidence vocabulary.** `"Alleged"`, `"claimed"`, `"(this is a lie)"`
  are refused at Layer 2/3 on first encounter. Teaching-loop consumption of
  those refusals as correction candidates is its own future scope.
- **Lens-conditional recognition.** How different anchor lenses interact with
  derived recognizers is deferred.

## Consequences

- All future recognition work targets `RecognitionOutcome`. No alternative
  output contract is permitted without a new ADR.
- Refusal is first-class. Every refusal carries a typed reason consumable by
  the teaching loop. Silent failure is a bug.
- The recognizer is not a classifier. It does not assign a proposition type
  directly — type emerges from the feature bundle via a downstream mapping
  that is itself derived from teaching.
- Integration into the runtime is gated on ADR-0144. Until then, the spike
  lives in `recognition/` as a standalone testable module.
