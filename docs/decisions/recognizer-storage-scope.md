# Scope: Derived Recognizer Storage

**Status:** Draft v1 / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-24
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

The thermodynamic / crystallization dynamics the project committed to are
not a deferred idea. They are implemented and load-bearing:

| Concern | Mechanism | Location |
|---|---|---|
| Region excitation | Injection pressure raises `EnergyClass` | `core/physics/energy.py` |
| Cooling | `exp(-age/12)` decay over turn count | `core/physics/energy.py` |
| Crystallization | E0/E1 = `vault_candidate`; promotion gated by coherence residual ≤ 0.05 | `core/physics/learning.py` (`VaultPromotionPolicy`) |
| Re-activation | Vault recall transiently raises region to E2, then cools again | ADR-0006 §"Integration Points" |

The model treats field regions (content) thermodynamically: hot/active
material lives in the field; settled-and-cooled material is promoted to
vault as the *crystallized form*; vault recall re-thaws transiently.

What the substrate does **not** yet specify:

- **Recognizers as content type.** ADR-0006/0014 were written for field
  regions excited by injection pressure. A derived recognizer is a typed
  pattern, not a field region. The mapping is open.
- **Drop-off / deprecation.** Promotion to vault is one-directional. The
  substrate has no policy for *removing* crystallized content that has
  been at E0 long enough to be deemed deprecated.

These two gaps are the load-bearing unknowns this scope frames.

---

## The runtime principle this scope assumes

**Forever-running engine, with reboot as a recovery event, not a
control-flow boundary.** Modern computers reboot occasionally; that does
not justify frontloading work into startup or treating session boundaries
as architectural primitives. The engine's capability state is meant to
accumulate over its lifetime and survive reboot without being rebuilt from
scratch.

Operational consequences for storage:

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

**Proposed shape** (not committed):

1. Crystallized recognizers carry a recency telemetry field (last
   excitation timestamp + cumulative excitation count).
2. A `DeprecationPolicy` analog of `VaultPromotionPolicy` evaluates
   crystallized entries against a deprecation threshold (e.g., zero
   excitations for N turns AND zero admissions for M turns).
3. Deprecation candidates surface to a HITL review queue; deletion only
   occurs after HITL ratification.
4. Once HITL ratifies deletion, the entry is removed from the persistence
   layer.

**Non-negotiable:** HITL is the narrow entrypoint, never bypassed. The
engine MAY propose deletion. The engine MAY NOT delete autonomously.

This extension is sized for its own ADR (parallel to ADR-0014). The
storage scope names it but does not specify it.

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
- **Cold-path latency.** Reading a crystallized recognizer from disk on
  re-thaw may be slow enough to matter under load. Measure before
  optimizing.
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

The recognizer-storage question dissolves once ADR-0006 and ADR-0014 are
in view. Recognizers are a new content type in the existing thermodynamic
lattice, subject to the existing excitation / cooling / coherence-settling
/ promotion / re-thaw dynamics. Three recognizer-specific measurements
need definition (excitation counting, coherence residual, promotion
criteria). One genuinely new extension — HITL-gated drop-off — sits in a
sibling ADR. Substrate-resident form remains the named destination.

The scope's commitment is to **the question reframed against the existing
substrate**. Answers belong to the spike and the ADR that follows.
