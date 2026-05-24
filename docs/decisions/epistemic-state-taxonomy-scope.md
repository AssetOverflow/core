# Scope: Epistemic State Taxonomy

**Status:** Draft / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-24
**Author:** CORE agents
**Audit:** Math-subsystem epistemic audit complete (2026-05-24) — 40 decision points mapped; 4 gaps surfaced and ratified into starter taxonomy below
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Related:** [teaching-derived-recognition-scope](./teaching-derived-recognition-scope.md)

---

## Why this document exists

The thesis commits CORE to decoding a reality that already is. Decoding,
unlike generation, requires the engine to **hold propositions in
varying degrees of grounding** — not "true" vs "false" but a richer
vocabulary describing *how* a proposition is currently known, and *what
evidence* supports that knowing.

Without an explicit taxonomy of epistemic states, the engine implicitly
caps its epistemic scope at binary admit/refuse. That cap blocks two
things the engine needs:

1. **Provisional reasoning.** The engine must be able to hold a
   proposition that has evidence but is not yet verified, reason with
   it cautiously, and surface it with appropriate marking — without
   either committing prematurely (which is generation) or refusing
   prematurely (which is paralysis).

2. **Expansion and contraction of scope through teaching.** New
   epistemic states should be derivable from teaching, the same way
   new patterns are. Hard-coding the taxonomy caps the engine's
   ability to discover that it needs distinctions it didn't initially
   have names for.

This scope document defines the **question** — what epistemic
vocabulary should the engine reason with, and how should that
vocabulary itself be derived. It does not propose a decision.

---

## The load-bearing question

> **What is the smallest extensible vocabulary of epistemic states the
> engine needs to hold for any proposition it reasons about, such that:**
>
> 1. Every state carries deterministic provenance (why is the proposition
>    in this state?),
> 2. State transitions are themselves deterministic and inspectable
>    (what evidence moved this proposition from state A to state B?),
> 3. The taxonomy is extensible through the teaching loop (new states
>    can be ratified when existing ones don't fit), and
> 4. The engine refuses propositions whose state cannot be cleanly
>    determined, rather than defaulting?

The four conditions parallel the recognition scope's four conditions —
deliberately. Both axes (recognition and epistemic state) commit to
the same discipline: deterministic, inspectable, extensible, refusal-first.

---

## Starter taxonomy

These are candidate states. Names are provisional. The point isn't the
names — it's that the engine needs a *richer-than-binary* vocabulary
and that each state has explicit provenance.

| State | Meaning | Source of evidence | Transition cues |
|---|---|---|---|
| **PERCEIVED** | Token/span observed in input; not yet committed to meaning | Raw ingestion | → EVIDENCED once features lifted; → UNDETERMINED if features can't lift |
| **EVIDENCED** | Feature lifts from specific input spans bind a proposition; grounded in input | Recognition layer | → VERIFIED on cross-reference pass; → CONTRADICTED if conflict found; → UNVERIFIED-POSSIBLE if non-contradicting but unconfirmed |
| **EVIDENCED-INCOMPLETE** | Feature lift succeeded for a sub-span; the lifted structure exists but cannot yet form a complete well-formed proposition (e.g., a rate declaration that no question consumes). Lift did not fail — the evidence is real — but the proposition is structurally partial. Distinct from UNDETERMINED (lift completed) and CONTRADICTED (nothing conflicts). | Recognition layer — partial structural match | → EVIDENCED once a consuming proposition is found or constructed; → UNDETERMINED if no completion mechanism exists; → teaching expansion if the engine needs a new structural pattern to complete it |
| **VERIFIED** | Cross-checked against ratified knowledge (pack / vault / teaching); consistent | Substrate cross-reference | → DECODED once replay-equality confirmed; stays VERIFIED otherwise |
| **DECODED** | VERIFIED plus replay-equality from input (trace-hash invariant) | Replay machinery | → DECODED-UNARTICULATED if the surface realization path breaks after verification; transitions only on retraction (subsequent teaching invalidates) otherwise terminal |
| **DECODED-UNARTICULATED** | The proposition is DECODED internally — trace is replay-equal and the verifier passed — but the surface realization path broke. The answer is correct; the explanation cannot be communicated. The runner must not classify this as `wrong` (which would conflate articulation failure with epistemic failure). | Verifier (replay-equal) + Realizer (failure) | → DECODED once the articulation path is repaired; stays distinct from DECODED until that repair is confirmed |
| **UNVERIFIED-POSSIBLE** | Consistent with verified knowledge but not directly verified; usable provisionally | Default for non-contradicting novel propositions | → VERIFIED if cross-reference confirms; → CONTRADICTED if cross-reference rejects |
| **UNVERIFIED-NOVEL** | Not contradicted; introduces structure the engine hasn't decoded yet; candidate for teaching expansion | Refusal that points at expansion need | → EVIDENCED once teaching corpus adds vocabulary; → CONTRADICTED if eventually disproven |
| **CONTRADICTED** | Conflicts with verified knowledge; refuse unless this is a ratified correction | Verification failure | → EVIDENCED only via ratified correction through teaching loop |
| **AMBIGUOUS** | Input could support multiple incompatible propositions; engine cannot choose without more context | Multi-evidence-binding conflict at recognition | → resolution requires additional input or teaching disambiguation |
| **UNDETERMINED** | Feature lifts could not complete; specific dimensions missing | Recognition-layer refusal | → EVIDENCED if teaching supplies missing vocabulary |
| **SCOPE_BOUNDARY** | The engine recognized the proposition type but refuses because the proposition type is outside its current capability envelope. Distinct from UNDETERMINED (the lift succeeded — the engine knows what it is) and CONTRADICTED (there is no conflict — the engine simply cannot decode it yet). | Capability-envelope check — structural match succeeded; semantic decode not available | → EVIDENCED or VERIFIED once teaching extends the capability envelope; stays SCOPE_BOUNDARY until that extension is ratified |
| **COMPUTATIONALLY_BOUNDED** | The engine cannot determine the epistemic status of the proposition within its resource envelope. Not AMBIGUOUS (no answers were enumerated) and not UNDETERMINED (the text likely has structure). The engine ran out of search budget before establishing what the proposition is. | Search/enumeration resource-limit hit | → AMBIGUOUS or UNDETERMINED once the search completes under relaxed constraints; → teaching expansion if the problem class needs a fundamentally different search strategy |

Plus one meta-state:

| **EPISTEMIC_STATE_NEEDED** | None of the existing states fit this proposition; engine refuses and surfaces the gap | Recursive refusal | → ratified-via-teaching expansion of the taxonomy itself |

The meta-state is what makes the taxonomy non-capping. When the engine
encounters a case that doesn't fit any current state, it refuses with
*"epistemic state needed: a state that captures ..."*, and the teaching
loop either ratifies a new state or determines that an existing state
already covers the case with different framing.

---

## Provenance is non-optional

Every assignment of a state to a proposition must carry provenance —
a structured record of:

- **Source:** which subsystem assigned this state (recognition, vault,
  pack, teaching, verifier, etc.)
- **Evidence span(s):** which input or knowledge spans supported the
  assignment
- **Transition history:** if this proposition was previously in another
  state, what evidence caused the transition

Provenance is what distinguishes thesis-aligned epistemic tracking from
LLM-style confidence scores. A confidence score is a number; provenance
is a *trace* the engine can replay, audit, and correct.

Concretely: a proposition in state EVIDENCED isn't just "the engine
thinks this is evidenced." It's "the engine assigns EVIDENCED because
feature `polarity` was lifted from span 6:9 of input `{...}` and feature
`modality` was lifted from span 0:5; recognition mechanism was
anti-unification over teaching set `{X, Y, Z}`; replay produces this
identical binding byte-for-byte."

That last sentence is what the provenance record actually contains. The
engine can hand it to a reviewer; the reviewer can audit it; the
teaching loop can target specific parts of it for correction.

---

## How this maps to existing CORE primitives

Several states already exist *implicitly* in scattered subsystems.
What's missing is the unified vocabulary.

| Existing primitive | Maps to | Notes |
|---|---|---|
| Vault exact recall | DECODED | Replay-equal by construction |
| Ratified pack data | VERIFIED → DECODED | Verified at load, replay-equal on consult |
| Reviewed teaching example | VERIFIED | Cross-checked via review; not yet replay-equal until used |
| `SPECULATIVE_MARKER` (ADR-0021) | UNVERIFIED-POSSIBLE | Speculative teaching surfaced with explicit marker |
| `ParseError` / `SolveError` | UNDETERMINED | Typed refusals with reasons |
| Verifier rejection | CONTRADICTED | Independent re-derivation disagrees |
| OOV refusal (ADR-0065) | UNVERIFIED-NOVEL | Token not in vocabulary; pointed at teaching expansion |
| Anchor-lens engagement | (cross-cutting) | Different lenses can produce different states for the same proposition |
| Orphan-rate refusal (math parser) | EVIDENCED-INCOMPLETE | Rate structure was parsed; no question consumed it — partial proposition, not a failed lift |
| Age/nested-comparison refusal (math parser) | SCOPE_BOUNDARY | Regex matched; the proposition type is recognized but outside current decode capability |
| Runner `RealizerError` on verified trace | DECODED-UNARTICULATED | Trace passed verifier; surface path broke — currently misclassified as `wrong` in the runner |
| Candidate-graph branch cap exceeded | COMPUTATIONALLY_BOUNDED | Search budget exhausted before answers could be enumerated; not AMBIGUOUS, not UNDETERMINED |

The mapping shows the taxonomy isn't being invented from scratch — it's
naming distinctions the engine already makes ad-hoc and unifying their
treatment.

---

## Extensibility — the recursive part

The taxonomy itself must be derived from teaching, not stipulated.

Mechanism (proposed for follow-on spike, not committed here): when the
engine produces an EPISTEMIC_STATE_NEEDED refusal, the refusal carries a
structured description of the gap — what the existing states don't
capture, what evidence would belong to the new state, what transitions
would lead in and out of it. A reviewer can examine the description and
either:

1. Identify an existing state the gap actually maps to (with different
   framing); update the description, the engine re-attempts.
2. Ratify a new state through the teaching loop, with the description as
   the seed of its definition.

This is the same shape as how new lemmas, atoms, or chains enter the
packs. Epistemic states become first-class data the engine can extend
its own vocabulary with — under review.

Constraint: **the meta-state mechanism itself stays bounded.** The
engine cannot create new meta-states (states-of-states-of-states...)
without explicit architectural commitment. EPISTEMIC_STATE_NEEDED is
the only recursive surface; further recursion is deferred. This
prevents runaway scope.

---

## Relationship to the recognition scope

The recognition spike (per the recognition-scope document) produces
typed proposition outputs from input text. The output structure must
accommodate epistemic state from day one, even if the full taxonomy
isn't yet ratified.

Concrete output shape proposed:

```
RecognitionOutcome:
  proposition:     <feature_bundle | None>
  state:           <one of the starter taxonomy>
  provenance:      <structured record of source / spans / mechanism>
  refusal_reason:  <typed reason if state is refusal-class | None>
```

The recognition spike commits to producing only a subset of states:
EVIDENCED for admitted, CONTRADICTED / AMBIGUOUS / UNDETERMINED for
refused. States like VERIFIED and DECODED are produced by downstream
substrate work (cross-reference, replay), not by recognition itself.

This couples the two scopes without entangling them. The recognition
spike can run with the starter taxonomy as a placeholder; the
epistemic-state ADR finishes when the full taxonomy is ratified
through teaching.

---

## Smallest provable test (proposed)

Unlike the recognition spike, the epistemic-state spike is harder to
isolate to a single binary acceptance because epistemic state is
*cross-cutting* — it affects every subsystem.

Two candidate framings:

**Framing 1 — Audit existing implicit states.** Inventory every place
in the current codebase where an implicit epistemic distinction is
made (vault recall, ParseError, SolveError, SPECULATIVE marker, OOV
refusal, verifier rejection, etc.) and map each to a starter-taxonomy
state. Acceptance: every distinct existing case maps to exactly one
starter state, or surfaces an EPISTEMIC_STATE_NEEDED gap that gets
documented.

This is *not a spike* — it's an audit. It produces no new code. But
it surfaces whether the starter taxonomy is sufficient before any new
work is committed.

**Status: COMPLETE (math subsystem, 2026-05-24).** 40 decision points
mapped across `math_parser`, `math_problem_graph`, `math_solver`,
`math_verifier`, `math_realizer`, `math_candidate_parser`,
`math_candidate_graph`, and `evals/gsm8k_math/{runner,verify}`. Four
EPISTEMIC_STATE_NEEDED gaps were surfaced and ratified into the taxonomy.
Remaining subsystems (vault, packs, teaching, cognition pipeline) are
not yet audited.

**Framing 2 — Spike on a single subsystem.** Pick one subsystem
(probably recognition, since the parallel scope is already underway)
and run all its outputs through the starter taxonomy + provenance
structure. Acceptance: every output of that subsystem carries a typed
state and structured provenance; refusals carry typed reasons; the
state assignments replay byte-identically.

This is a spike but it depends on the recognition spike being far
enough along to have outputs to taxonomize.

**Honest recommendation:** Framing 1 first (audit, no code), then
Framing 2 (spike, co-sequenced with recognition). The audit is a
prerequisite for the spike because it validates whether the starter
taxonomy needs revision before any subsystem commits to it.

---

## Prerequisites

The audit (Framing 1) can begin immediately — no dependencies. It
operates over existing code and ratified documents.

The spike (Framing 2) depends on the recognition spike being far enough
along to produce outputs. The two can co-sequence: recognition produces
RecognitionOutcome structures with state placeholders; the epistemic
spike validates that the placeholders can be cleanly filled with the
starter taxonomy and that provenance is captured throughout.

Integration into Engine A (full epistemic-state-aware reasoning across
all subsystems) is gated on:

1. The audit (Framing 1) confirming the starter taxonomy is sufficient
   or surfacing the gaps to address.
2. The recognition spike succeeding.
3. ADR-0144 (PropositionGraph from MathProblemGraph) — at which point
   the epistemic-state-aware propositions have somewhere to live in the
   engine.

---

## Risks the spike must surface

- **The starter taxonomy may be too coarse.** Nine states was too small.
  The math-subsystem audit (Framing 1, complete) surfaced four gaps and
  ratified four new states: EVIDENCED-INCOMPLETE, DECODED-UNARTICULATED,
  SCOPE_BOUNDARY, COMPUTATIONALLY_BOUNDED. Taxonomy is now 13 states
  (9 original + 4 ratified + meta-state). Further subsystem audits
  (vault, packs, teaching) may surface additional gaps.

- **Provenance overhead.** Every state assignment carries structured
  provenance. For propositions handled in tight loops (vault recall,
  pack consultation), the overhead may be non-trivial. Need to measure
  before committing to provenance-on-every-assignment.

- **Cross-cutting concerns are hard to test in isolation.** Epistemic
  state affects every subsystem; changes ripple. The two-framing
  approach (audit then subsystem-spike) is an attempt to control this,
  but the eventual ADR will need a deployment strategy that doesn't
  require turning the whole engine over at once.

- **Transition determinism is non-trivial.** State A → State B must be
  caused by specific evidence. If two evidence updates arrive
  simultaneously and would push the proposition in different
  directions, the engine must have a deterministic resolution rule
  (not "first-write-wins"). The taxonomy doesn't yet specify this.

- **The recursive meta-state (EPISTEMIC_STATE_NEEDED) is itself a
  risk.** It opens a path for the engine to expand its own vocabulary.
  That's the feature, but it's also a vector for taxonomy bloat if not
  carefully constrained. The teaching loop's review machinery is the
  intended brake, but the review criteria for new states needs explicit
  spec (not in this scope; deferred).

---

## What the scope does NOT commit

- **No states are finalized.** The starter taxonomy is a candidate;
  the audit may reduce or expand it.
- **No subsystem integration timeline.** Sequenced against recognition
  and the lift program but no calendar commitments.
- **No mechanism for state transitions across subsystems.** Within a
  subsystem, transitions are defined; across subsystems (e.g., a
  proposition handed from recognition to verifier to vault), the
  transition machinery is its own scope question.
- **No commitment on storage of states.** Are states stored per-
  proposition? Per-session? In the vault? In a pack? Open.
- **No commitment on serialization.** The provenance record must be
  byte-deterministic if states are to replay; the format is deferred.

---

## Open questions for follow-up scopes

1. **Cross-subsystem transition machinery.** How does a proposition
   carry its state and provenance as it moves between subsystems?
2. **State storage layer.** Where do states live? Same questions as
   the recognition scope's storage layer.
3. **Review criteria for new states.** When the engine surfaces an
   EPISTEMIC_STATE_NEEDED gap, what does the teaching loop's review
   need to verify before ratifying?
4. **Lens-conditional states.** An anchor lens can change how a
   proposition decodes; can it change the *state* the proposition is
   in? (Probably yes; how is non-trivial.)
5. **Identity / safety / ethics interaction.** Identity packs ground
   "what is decoding." Safety/ethics produce refusal verdicts.
   Where do those verdicts intersect with epistemic states? Probably
   as a separate axis (truth-state × safety-state × ethics-state) but
   the taxonomy needs to be explicit.

---

## Summary

The load-bearing question is whether a small extensible vocabulary of
epistemic states (PERCEIVED, EVIDENCED, EVIDENCED-INCOMPLETE, VERIFIED,
DECODED, DECODED-UNARTICULATED, UNVERIFIED-POSSIBLE, UNVERIFIED-NOVEL,
CONTRADICTED, AMBIGUOUS, UNDETERMINED, SCOPE_BOUNDARY,
COMPUTATIONALLY_BOUNDED, plus the recursive EPISTEMIC_STATE_NEEDED) is
sufficient to unify the implicit distinctions CORE already makes across
vault, packs, teaching, recognition, and verification — and whether
provenance-on-every-assignment is feasible without overhead that breaks
the engine's hot path.

The math-subsystem audit (Framing 1) is complete. It mapped 40 decision
points across 9 files; 31 mapped cleanly at high confidence, 5 with
medium confidence, and 4 required new states (ratified above). The
taxonomy grew from 9 states to 13. The audit also surfaced one
correctness issue in the runner: `RealizerError` on a verified trace is
currently classified as `outcome="wrong"` but should be
DECODED-UNARTICULATED — the math is correct, only the articulation path
broke. This is a load-bearing misclassification that the next runner
revision must address.

The eventual ADR makes the taxonomy first-class and provenance
mandatory across all subsystems. That ADR is gated on the audit
succeeding and on ADR-0144 (PropositionGraph integration) being in
flight.

This document does not propose a decision. It defines the question.
