# Scope: Derived Recognizer Storage

**Status:** Draft v2 / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-24 (v1: initial draft; v2: substrate-liveness audit + HITL machinery cross-reference + forever-running prerequisite reframe + substrate-destination sketch + LOW corrections)
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Companions:** [teaching-derived-recognition-scope](./teaching-derived-recognition-scope.md), [epistemic-state-taxonomy-scope](./epistemic-state-taxonomy-scope.md)
**Substrate (load-bearing):** ADR-0006 (field energy operator), ADR-0014 (vault promotion policy), ADR-0144 (proposition-graph epistemic carrier)
**Destination:** Mechanism C-class substrate residency (deferred — gated on text-embedding scope)

---

## Why this document exists

ADR-0144 added the `EpistemicGraph` carrier and ADR-0143 / the recognition
spike (PRs #224, #226) shipped the deterministic anti-unifier and multi-
resolution decoding. The `DerivedRecognizer` defined in
`recognition/anti_unifier.py` is a frozen serializable dataclass that the
pipeline accepts as a parameter (`core/cognition/pipeline.py:121`). Nothing
in main constructs, persists, or shares one across sessions.

The teaching-derived-recognition scope deferred the storage question with
three candidates (pack / vault / substrate). That candidate set was drafted
without acknowledging the existing thermodynamic substrate already
implemented under ADR-0006 + ADR-0014. **This scope corrects that
omission.** The storage question collapses once the existing substrate is
in view.

This document defines the question. The answer belongs to the ADR that
follows.

---

## What the existing substrate already provides

The thermodynamic / crystallization dynamics the project committed to
exist as designed-and-partially-implemented architecture. The honest
status follows.

### Substrate liveness audit

| Concern | Mechanism | Status | Verification |
|---|---|---|---|
| Region excitation | Injection pressure raises `EnergyClass` | **Live** | `FieldEnergyOperator` called by `ingest/gate.py:292`, `field/propagate.py:26`, `language_packs/compiler.py:72` |
| Cooling | `recency = clamp(activation_count,0,8)/8 * exp(-age/12)` contribution | **Live** | `core/physics/energy.py:94`, exercised via callers above |
| Crystallization gate | E0/E1 = `vault_candidate`; promotion requires `coherence_residual ≤ residual_threshold` (default 0.05) | **Dormant** | `VaultPromotionPolicy` defined in `core/physics/learning.py`, but `core.physics.learning` is imported by **no module outside `core/physics/`** as of 2026-05-24 |
| Re-activation on recall | Vault recall transiently raises region to E2, then cools | **Specified, not verified live** | Documented in ADR-0006 §"Integration Points"; no code path traced from vault recall back to energy re-injection |

This is a meaningful correction to v1, which described the entire lattice
as live. The honest read: the **energy half** of the substrate is wired
and load-bearing; the **promotion / crystallization half** is spec-in-code
that nothing calls. Vault content today exists in the vault because
something else put it there, not because the promotion gate evaluated it.

### What this means for the recognizer-storage ADR

The ADR that follows this scope must deliver **both**:

1. **Wire the dormant promotion path** so it actually decides what
   crystallizes (this is a load-bearing change in its own right, not a
   recognizer-specific concern), AND
2. **Extend the promotion path for recognizers as content type**
   (recognizer-specific measurements per the section below).

Treating (1) as "already in place" is the v1 overclaim this revision
corrects. The recognizer-storage ADR may legitimately decide to scope (1)
into a sibling ADR — but it cannot assume (1) is already done.

### What the substrate does not yet specify (independent of liveness)

- **Recognizers as content type.** ADR-0006/0014 were written for field
  regions excited by injection pressure. A derived recognizer is a typed
  pattern, not a field region. The mapping is open whether or not the
  promotion path is wired.
- **Drop-off / deprecation.** Promotion (when implemented) is
  one-directional. The substrate has no policy for *removing* crystallized
  content that has been at E0 long enough to be deemed deprecated.

These two gaps plus the wiring debt are the load-bearing unknowns this
scope frames.

---

## Prerequisite: forever-running runtime

**Forever-running engine, with reboot as a recovery event, not a
control-flow boundary.** Modern computers reboot occasionally; that does
not justify frontloading work into startup or treating session boundaries
as architectural primitives. The engine's capability state is meant to
accumulate over its lifetime and survive reboot without being rebuilt from
scratch.

**Honest status of this prerequisite in the current codebase.**
CORE today is session-bounded: `core chat` is a CLI invocation; each call
builds a fresh `ChatRuntime` instance (`chat/runtime.py`); packs and
teaching corpora are loaded fresh per invocation; vault is on-disk and
persists across invocations but is reloaded each time. There is no
long-lived process. The forever-running runtime is **the destination
architecture**, not a current property — and it is its own scope, not
something the recognizer-storage ADR can or should land alone.

Naming it as a prerequisite (not an assumption) means: the
recognizer-storage ADR is gated on the runtime-model scope existing and
committing to forever-running. If that scope lands later or commits
differently, this scope's framing has to be revisited.

**Operational consequences for storage** (assuming the prerequisite holds):

- Anything cheap to rebuild from primitives MAY be in-memory only; reboot
  cost is bounded.
- Anything expensive to rebuild (HITL-ratified accumulated capability)
  MUST persist; reboot reloads, does not re-derive.
- "Re-derive on demand per session" is not a valid pattern — there is no
  per-session demand boundary.
- HITL is the narrow async entrypoint for ratification, never bypassed,
  never required for runtime continuation.

---

## The reframed question

> **How does a derived recognizer participate in the existing
> field-energy / vault-promotion lattice, and what extension is needed
> to support HITL-gated drop-off?**

Not "where does it live" — that question dissolves once the substrate is
in view. The answer is "in the same place every other crystallizable
artifact lives, subject to the same thermodynamic dynamics, plus one
extension."

---

## Three measurements that need definition

The existing substrate operates on field regions via three measurements:
excitation, coherence residual, and cool-down. For recognizers to
participate, the recognizer-specific analogs of each must be defined.

### Measurement 1 — Recognizer excitation

**Natural map:** a `recognize()` call that returns an admission outcome
raises the recognizer's energy class; refusals do not.

**Framing note — temporal direction.** Field-region excitation in
ADR-0006 is driven by *inputs the region receives* (injection pressure).
The "admission raises energy" framing above treats *outputs the
recognizer produces* as the excitation signal — opposite temporal
direction. The spike should validate this is the right map: if
recognizer-as-input-consumer ("the recognizer was applied to this
input") is the better analog of "the region received injection," then
attempted-application is the natural metric, not admission. Both
candidates below; the framing direction is itself one of the open
questions.

**Open question:** does *attempted* application (regardless of outcome)
count as excitation, or only admission? Attempted-counts model favors
recognizers that *get tried* often (good for discovery); admission-counts
model favors recognizers that *succeed* often (good for reliability).
Spike should measure both and pick the one whose cool-down dynamics match
the operator's intuition.

### Measurement 2 — Recognizer coherence residual

**Non-obvious.** For a field region, coherence residual is geometric (the
operator's output deviation from coherence). A typed pattern with slots
has no such geometry.

**Candidate definitions** (spike must pick or compose):

- **Anti-unifier stability under teaching addition.** Add one held-out
  example to the teaching set, re-derive, measure structural delta. Low
  delta = high coherence. Implementable; spike-testable.
- **Admit/refuse precision against held-out.** Measure false-admit vs.
  false-refuse rate against a separate held-out set. Operator-meaningful
  but requires the held-out set to be HITL-curated.
- **Multi-resolution agreement.** A recognizer admits at chunk level;
  does word-level resolution produce a consistent feature bundle? Chunk-
  word agreement = high coherence.

**Risk:** if no candidate is well-defined, recognizers cannot be promoted
via the existing `VaultPromotionPolicy` and need a parallel promotion
policy. The spike must surface this rather than paper over it.

### Measurement 3 — Recognizer promotion criteria

**Natural extension of `VaultPromotionPolicy.decide()`.** Same shape
(cooled + coherent ⇒ promote), parameterized by content type. Either:

- **Single policy, content-type-aware.** Extend `VaultPromotionPolicy`
  with a `content_type` parameter; per-type thresholds.
- **Sibling policy.** New `RecognizerPromotionPolicy` with the same
  decision shape. Less coupling, more duplication.

ADR decides. Scope does not commit.

---

## The drop-off extension (sibling ADR)

The existing substrate promotes to vault but does not deprecate out of it.
A forever-running learning system needs drop-off, or it accumulates
unbounded crystallized state.

### Cross-reference to existing HITL machinery

The project already has a HITL ratification path for teaching artifacts:

- **ADR-0057** (teaching-chain proposal + review + replay-equivalence
  gate) establishes the shape: engine proposes → automated gate
  (replay-equivalence) → operator review → ratified-or-rejected →
  append-only proposal log.
- **`teaching/store.py`** implements `PackMutationProposal` and
  `TeachingStore` for the proposal-and-storage half.
- **`teaching/review.py`** implements `ReviewOutcome` (`ACCEPTED` /
  `REJECTED_IDENTITY` / `REJECTED_EMPTY`) and `review_correction()` for
  the review half.
- **ADR-0055 / ADR-0056** (inter-session memory + contemplation) supply
  the proposal-generation half from the discovery side.

Drop-off should **reuse this machinery wherever the shape fits**, not
invent a parallel review path. The shape that fits:

- **Proposal generation:** new — recency-driven (engine notices a
  crystallized recognizer that hasn't been excited for N turns), not
  correction-driven. A `DeprecationCandidate` analogous to
  `PackMutationProposal` but flowing in the deletion direction.
- **Automated gate:** new — *not* replay-equivalence (deletion is not a
  surface change in the same way). Candidate gates: "zero admissions on
  any held-out corpus we still have," "no recognizer-composition
  references from active recognizers." The drop-off ADR specifies.
- **Operator review:** **reuse** — extend `ReviewOutcome` enum with
  `ACCEPTED_FOR_DELETION` (or a parallel `DeprecationReviewOutcome` enum
  if mixing creates ambiguity), reuse `review_*` plumbing where the
  signatures match.
- **Append-only log:** **reuse** — the same append-only discipline
  ADR-0057 establishes for proposals applies to deprecation decisions.

The drop-off ADR's load-bearing originality is the *trigger* (recency)
and the *gate* (not replay-equivalence). The *review-and-log* half is a
small extension to existing machinery, not a parallel path.

### Proposed shape (not committed)

1. Crystallized recognizers carry a recency telemetry field (last
   excitation timestamp + cumulative excitation count).
2. A `DeprecationPolicy` analog of `VaultPromotionPolicy` evaluates
   crystallized entries against a deprecation threshold (e.g., zero
   excitations for N turns AND zero admissions for M turns).
3. Deprecation candidates surface as `DeprecationCandidate` proposals
   into the existing teaching-review machinery (extended where needed).
4. Once HITL ratifies deletion, the entry is removed from the persistence
   layer and the decision is recorded in the append-only log.

**Non-negotiable:** HITL is the narrow entrypoint, never bypassed. The
engine MAY propose deletion. The engine MAY NOT delete autonomously.

**HITL latency as load-bearing constraint.** In a forever-running engine
the operator is not always available. The drop-off ADR must specify what
happens when deprecation candidates accumulate faster than HITL can
review them: a queue cap, a rate limit on proposal generation, an
operator alert, or a no-op (let the queue grow). This is more than
backpressure plumbing — it is a real constraint on whether the system
can self-regulate memory growth without an operator in the loop.

This extension is sized for its own ADR (parallel to ADR-0014, building
on ADR-0057). The storage scope names it but does not specify it.

---

## What this scope explicitly rejects

- **Recognizer-specific pack format** (`en_math_recognizers_v1`). Packs
  are cold startup-loaded artifacts; conflating a *capability* (live,
  accumulating) with a *pack entry* (frozen, manifested) breaks the
  forever-running model.
- **Vault as recognizer container without acknowledging the substrate.**
  An earlier draft of this scope proposed "vault with fixed lookup mode"
  — that was an independent reinvention of crystallization without
  recognizing ADR-0006/0014. The recognizer is *crystallized via the
  existing dynamics*, not stored as a vault content entry with a parallel
  lookup mode.
- **Per-session re-derivation.** No session boundary in the forever-
  running model. Re-derivation on reboot is acceptable for the in-memory
  registry of *not-yet-crystallized* recognizers; crystallized
  recognizers reload from disk.
- **Approximate match for recognizer lookup.** Exact structural match
  only. The hot/cold distinction is a *storage* property, not a *match*
  property; both hot and cold paths return byte-identical structural
  matches.

---

## Substrate-resident destination — sketch (illustrative, not committed)

The scope names substrate-residency (Mechanism C-class) as the
destination once text-embedding scope lands. To keep that destination
honest rather than an IOU, a one-paragraph sketch of what it could
plausibly look like:

A substrate-resident recognizer is a structural feature of Engine A
itself — not a stored pattern that the engine *consults*, but an
algebraic operator the engine *is*. Two non-exclusive candidates worth
spike-testing once text-embedding exists:

- **Recognizer as versor.** Anti-unification produces a versor `V_R`
  whose sandwich application `V_R · F · reverse(V_R)` on a field state
  `F` derived from text returns a state whose grade/null-cone
  characteristics indicate admission. Refusal is failure of versor
  closure on the input region. Lookup is geometric application, not
  table search.
- **Recognizer as null-cone region.** The recognizer defines a region
  in the null cone; admission is exact intersection of the input
  region with the recognizer region (per ADR-0006's exact-CGA
  discipline, no approximate hull). Hot vs. cold becomes a property of
  *which regions are currently materialized* in the runtime manifold
  versus serialized to vault for re-thaw.

Both shapes preserve byte-identical replay, both admit exact match (no
approximate predicates), both compose via existing CGA primitives. The
sketch is illustrative; the actual ADR for substrate-residency will live
downstream of text-embedding scope and will revise this gesture against
whatever embedding semantics actually land.

The point of including the sketch in *this* scope is to prevent
"substrate-resident" from becoming a forever-deferred destination with
no shape. Naming a shape — even tentatively — keeps the destination
honest.

---

## What this scope does NOT commit

- **Which coherence-residual definition wins.** Three candidates; spike
  decides.
- **Single-policy vs. sibling-policy promotion.** ADR decides.
- **Drop-off thresholds.** Sibling ADR decides.
- **In-memory registry data structure.** Implementation detail; the scope
  commits to "recognizers participate in the lattice," not to a specific
  Python class.
- **Substrate-resident form.** Mechanism C-class, deferred until text-
  embedding scope. Named here as the destination so it remains explicit
  rather than forgotten.
- **Cross-process / multi-tenant concerns.** Out of scope; assume single
  forever-running engine instance for now.

---

## Determinism requirements (non-negotiable)

The recognizer-storage layer must preserve:

1. **Byte-identical replay.** Same teaching examples + same input stream
   ⇒ same admissions, same refusals, same feature bundles, same trace
   hashes.
2. **Reboot-equivalent state.** State after `(boot, run N turns, reboot,
   reload)` is byte-identical to state after `(boot, run N turns)` minus
   process-memory artifacts.
3. **No drift repair, no hot-path normalization, no approximate match.**
   Per CLAUDE.md's normalization rules — the storage layer is a forbidden
   site for these patterns.

---

## Risks the spike / first ADR must surface

- **No clean coherence-residual for typed patterns.** If none of the three
  candidate definitions survives spike measurement, recognizers cannot
  cleanly join the existing promotion lattice and need a parallel one.
  Surface honestly; do not paper over.
- **Cold-path latency (general vault concern, not recognizer-specific).**
  Reading a crystallized artifact from disk on re-thaw inherits whatever
  performance characteristics current exact-CGA vault recall already
  has. Recognizers do not introduce a new latency class — they inherit
  the existing one. Surface here only because if vault recall is slow
  enough to matter for *content*, it will matter equally for
  *recognizers*. Measure once; the measurement applies to both.
- **HITL queue backpressure.** If recognizers crystallize faster than
  HITL can ratify deprecation, the registry grows unbounded. The drop-off
  ADR must specify a backpressure policy (queue cap? rate limit?
  operator alert?).
- **Excitation counting under teaching corpus changes.** If teaching
  examples change, recognizer identity changes (`teaching_set_id`
  hashes the tokens). Excitation history attached to the old
  `teaching_set_id` does not transfer. Acceptable cost or load-bearing
  problem? Spike measures.

---

## Open questions for follow-up scopes

- **Recognizer composition.** When two recognizers admit the same input
  with overlapping but distinct feature bundles, what is the composition
  rule? (Intersection? Union? HITL arbitration?)
- **Cross-recognizer interference.** Does excitation of recognizer A
  affect recognizer B's energy if A and B share teaching examples? Field
  regions interact geometrically; recognizers' analog is undefined.
- **Substrate migration path.** When text-embedding scope lands and
  Mechanism C becomes viable, what is the migration discipline for
  crystallized recognizers? In-place re-encoding? Parallel substrate-
  resident copies?
- **Multi-recognizer admission.** Today the pipeline accepts one
  `DerivedRecognizer`. The forever-running engine has many. Dispatch /
  ranking / fall-through is downstream of this scope but tightly
  coupled.

---

## Summary

The recognizer-storage question reframes once ADR-0006 and ADR-0014 are
in view. Recognizers are a new content type that should participate in
the existing thermodynamic lattice — but with the honest caveat that
only the *energy half* of that lattice is live today; the
*promotion-to-vault gate* is spec-in-code that nothing currently calls.

The recognizer-storage ADR therefore has to deliver three things, not
one: wire the dormant promotion path, define the three recognizer-
specific measurements (excitation counting, coherence residual,
promotion criteria), and name the HITL-gated drop-off extension as a
sibling ADR that reuses ADR-0057's review machinery rather than
inventing a parallel one. Substrate-residency (sketched, not committed)
is the destination once text-embedding scope lands. Forever-running
runtime is a *prerequisite* (its own scope), not a current property.

The scope's commitment is to **the question reframed against the
existing substrate, with the substrate's actual liveness honestly
audited**. Answers belong to the spike and the ADR that follows.
