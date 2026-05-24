# Scope: Substrate Liveness Audit

**Status:** Draft v1 / scope-only (defines the audit; audit itself is a separate deliverable)
**Date:** 2026-05-24
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md) (memory)
**Companions:** [recognizer-storage-scope](./recognizer-storage-scope.md), [teaching-derived-recognition-scope](./teaching-derived-recognition-scope.md), [epistemic-state-taxonomy-scope](./epistemic-state-taxonomy-scope.md)

---

## Why this document exists

CORE is the assembled product of ~140 ADRs across ~14 named subsystems.
Each ADR was reviewed and committed. Many are marked `Implemented` or
`Accepted`. The codebase contains the corresponding modules, classes,
and tests.

Yet the recognizer-storage scope (`recognizer-storage-scope.md`, v1→v2)
demonstrated a load-bearing failure mode: a module marked `Implemented`
and present in code (`core/physics/learning.py` :: `VaultPromotionPolicy`)
was wired into *no live caller anywhere outside its own package*. The v1
scope drafted four storage options against an "existing lattice" whose
promotion half was actually dormant. The audit that revealed this took
two grep commands and changed the scope's central claim.

That gap is almost certainly not isolated. The system is **a system of
systems**, like a human body or an ecosystem — built up over time,
layer on layer, each layer depending on the closure of the layer below.
When one layer's design lands but its *wiring* doesn't, every layer
above it inherits a hidden assumption that the layer below is doing
something it isn't.

This document scopes the audit that will identify, layer by layer,
which subsystems are **closed** (designed AND wired AND exercised at
runtime), which are **partial** (designed AND coded but not reachable
from the live turn loop), and which are **open** (designed but not yet
coded, or coded but inconsistent with the design).

The output of the audit is a wiring registry plus a ratcheted plan —
not a refactor. The audit is reconnaissance for whichever ADR follows.

---

## The vision this audit serves

The end state CORE is being built toward:

> A **forever-running engine** that listens, comprehends, recalls,
> thinks, articulates, learns from reviewed correction, and replays
> deterministically — with a narrow HITL ratification entrypoint, never
> bypassed, never required for runtime continuation. Capability
> compounds across turns and survives reboot as recovery, not as
> control flow.

Per the project thesis ([[thesis-decoding-not-generating]]): the engine
*decodes a reality that already is* — its capacity is to find,
comprehend, and rationalize, not to store a library of founds. The
forever-running engine is the form in which that capacity actually
compounds.

CORE today executes a *subset* of this design. The recognizer-storage
v2 reframing made one piece of that subset explicit. The substrate
liveness audit makes the rest of it explicit, system-wide.

---

## Framing principle: system of systems

The metaphor the operator surfaced — human body, universe, ecosystem —
is load-bearing.

A human body is alive because its subsystems achieve closure together:
cardiovascular delivers oxygen *because* respiratory captures it *because*
nervous innervates the diaphragm *because* musculoskeletal can hold the
posture *because* metabolic supplies the energy. Each is closed only in
the context of every other. If the lymphatic system is half-built —
present, partly functional, but not draining where it should — the
organism doesn't fail loudly; it degrades silently. The cardiovascular
system *still works*, but the whole is less alive than its parts suggest.

CORE is the same shape. The algebra primitives, the field operators,
the language pack compiler, the identity packs — these are *cellular*
and *tissue* level. They work. The question is whether the *organ
systems* (cognition, teaching, vault, recognition, contemplation,
inter-session memory) close on each other or have dangling vessels.

**The audit walks outward from the cellular foundation that is solid,
finding where the puzzle breaks.** It does not re-audit the foundation.
It maps the perimeter of what's closed and the next-piece-to-place at
each border.

---

## The layered map (first pass — audit will refine)

The audit must commit to a layering before it can find gaps. First-pass
layering, expected to refine:

| Layer | Concerns | Representative ADRs / modules | Expected status |
|---|---|---|---|
| L0 — Algebra primitives | versor application, CGA inner product, null vector preservation, sandwich closure | `algebra/versor.py`, `algebra/backend/`; invariant `versor_condition < 1e-6` | **Closed (foundation)** |
| L1 — Field substrate | injection gate, propagation, energy operator, normalization sites | `field/propagate.py`, `ingest/gate.py`, `core/physics/energy.py`; ADR-0006 | **Mostly closed** (energy operator wired) |
| L2 — Vault | exact CGA recall, indexing, batching | `vault/store.py`; ADR-0054 | **Closed (content path);** promotion gate dormant |
| L3 — Language packs | compiler, lexicons, identity, safety, ethics, anchor lens, register | `language_packs/`, `packs/`; ADR-0027..0047, ADR-0070..0073 | **Closed** for static packs; mutation/ratification path unverified |
| L4 — Recognition | anti-unifier, multi-resolution decoding, epistemic carrier, dispatch trace | `recognition/`; ADR-0143, ADR-0144 | **Partial** (mechanism live; storage scope just landed; integration into live turn loop pending) |
| L5 — Cognition pipeline | intent classification, ratification, articulation target, deterministic realizer | `core/cognition/`, `generate/intent.py`, `generate/realizer.py`; ADR-0048..0053 | **Live but session-bounded** |
| L6 — Chat runtime | turn loop, surface composition, grounding dispatch, telemetry, verdicts | `chat/runtime.py`; ADR-0058..0099 | **Live but session-bounded;** dispatch trace just landed |
| L7 — Teaching loop | correction extraction, review, proposal log, replay-equivalence | `teaching/`; ADR-0055..0064 | **Partial** (proposal storage exists; live-turn-loop integration unverified) |
| L8 — Inter-session memory + contemplation | discovery, contemplation, multi-tier memory | `teaching/contemplation.py`, `teaching/store.py`; ADR-0055, ADR-0056 | **Spec-heavy; liveness unverified** |
| L9 — Epistemic state + verdicts | safety, ethics, refusal materialisation, epistemic taxonomy | `chat/safety.py`, `chat/ethics.py`, `core/cognition/result.py`; ADR-0142, ADR-0144 | **Live; some debt remaining** |
| L10 — Runtime model | process lifecycle, persistence across reboot, HITL queue | **No ADR yet** | **Open — prerequisite for forever-running** |
| L11 — Forever-running engine | the destination | **No ADR yet** | **Open — capstone** |

This layering is a hypothesis. The audit will validate or refine it.
Anywhere the audit finds a concern that doesn't fit cleanly into a layer,
that's evidence the layering itself is wrong and worth revising.

---

## What "closure" means per layer

For each layer, **closure** means: every mechanism the layer's ADRs
specify is (a) coded, (b) reachable from the live turn loop or a
documented async entry, (c) covered by a test that exercises the
reach-path end-to-end, and (d) consistent with every other layer it
claims to interact with.

Concretely, a closed layer has:

1. **Design artifact** — at least one ADR specifying the mechanism.
2. **Code artifact** — module(s) implementing the design.
3. **Live caller** — at least one path from runtime entry (`core chat`,
   `core eval`, scheduled job, etc.) that exercises the module under
   normal operation.
4. **End-to-end test** — a test that asserts the reach path actually
   runs, not just that the module's unit tests pass.
5. **Cross-layer consistency** — the layer's interface contracts match
   what neighboring layers expect (e.g., if L6 expects L7 to consume
   a `TurnEvent`, the consumer exists and is reachable).

A layer is **partial** when (1)–(2) hold but (3)–(5) are incomplete.

A layer is **open** when (1) holds and (2)–(5) are missing or
inconsistent.

The audit's per-layer output is a closure verdict with evidence for
each of the five criteria.

---

## Audit method

For each layer, in dependency order (L0 → L11):

1. **Enumerate ADRs.** From `docs/decisions/`, list every ADR whose
   subject falls within the layer.
2. **Map ADRs to modules.** For each ADR, identify the primary
   module(s) implementing it. Cite file paths.
3. **Trace callers.** For each module, grep for imports and call sites
   outside the module's own package. Trace each caller back toward
   the runtime entrypoint (`core` CLI). If the trace dead-ends inside
   `core/physics/` or another self-contained package, the module is
   dormant.
4. **Verify end-to-end test coverage.** For each live module, identify
   the test(s) that exercise the *reach path*, not just the module's
   unit behavior. Absence of such a test is a closure gap even if unit
   tests are green.
5. **Check cross-layer contracts.** For each interface the layer
   exposes (dataclasses, function signatures, return types), verify
   the consuming layer actually uses every field/method as the ADR
   specified. Unused fields or method signatures suggest design drift.
6. **Verdict and evidence.** Per ADR, per module: closed / partial /
   open, with citations for each criterion.

The audit is **mechanical** — grep, trace, cite. It is not opinion. Two
reviewers running the audit independently should produce the same
verdicts.

### Order matters

Audit L0 first. If L0 is anywhere short of closed, every layer above
it is suspect. Audit each layer only after the layer below it has been
verified closed, partial, or open with evidence. **Do not skip to the
"interesting" layers** — that's how the recognizer-storage v1
overclaim happened: by reasoning about L4/L7 without confirming L2's
promotion gate was live.

### What the audit deliberately does NOT do

- **No refactoring.** The audit produces evidence, not fixes.
- **No new ADRs.** The audit may *propose* ADRs for the wiring debt
  it surfaces, but it does not write or commit them.
- **No re-architecture.** If the audit finds that a layer's design is
  inconsistent with the system's direction, it reports that finding;
  the redesign belongs to a follow-on scope.
- **No subjective judgment.** "This code is ugly" is not an audit
  finding. "This module is imported by no caller outside its own
  package" is.

---

## Output shape

The audit produces two artifacts, both committed to the repo:

### Artifact 1 — Closure registry

`docs/audit/substrate-liveness-registry.md` (or similar). One section
per layer (L0–L11). Within each section, one entry per ADR or coherent
ADR cluster. Each entry contains:

- **ADR(s)** — list and status (Accepted / Implemented / Superseded).
- **Primary module(s)** — file paths.
- **Caller trace** — grep evidence with file:line citations, or
  explicit "no callers found outside `<package>/`."
- **End-to-end test** — test name + invocation path, or "none found."
- **Cross-layer contracts** — interfaces consumed, evidence each is
  actually used.
- **Closure verdict** — Closed / Partial / Open.
- **Wiring debt** — one-paragraph description if Partial or Open;
  references to existing ADRs that should plug the gap or
  identification that a new ADR is needed.

The registry is **append-only**. As wiring lands, entries are updated
with a dated note ("Promoted from Partial to Closed on YYYY-MM-DD, see
ADR-XXXX"). The registry retains its history so the path from "first
audit" to "fully closed" is auditable.

### Artifact 2 — Ratchet plan

`docs/audit/substrate-liveness-ratchet.md` (or similar). Derived from
the registry. Lists wiring work in dependency order: which ADRs to
write next, in what sequence, with which prerequisites. The ratchet is
the operator's playbook for transitioning CORE from "subset of design
executes" to "design executes."

The ratchet is **revisable** as the registry changes. Each completed
wiring updates the ratchet and (likely) reveals new wiring debt in
layers above.

---

## What this scope does NOT commit

- **Closure verdicts.** The audit produces them; the scope does not
  prejudge.
- **Layer definitions.** The first-pass map above is a hypothesis;
  the audit may refine.
- **Wiring sequence.** The ratchet is derived from the registry, not
  pre-specified.
- **Which ADRs are obsolete.** If the audit finds an ADR that no longer
  matches the system's direction, it reports the inconsistency; the
  decision to supersede belongs elsewhere.
- **Runtime-model scope content.** L10 is named as open; the runtime-
  model scope is a sibling document, not part of this audit's
  deliverable.
- **Timeline.** Per [[feedback-no-timelines]], no calendar dates. The
  audit's sequence is dependency-driven: L0 before L1, L1 before L2,
  etc.

---

## Risks the audit must surface

- **Layer mis-assignment.** A concern that spans layers (e.g., the
  field-energy operator straddles L1 and influences L2) may produce
  inconsistent verdicts depending on which layer the auditor assigns
  it to. Mitigate by citing cross-layer concerns explicitly in both
  layers' entries.
- **Closure-verdict inflation.** "We have a test, so it's closed" is
  the failure mode. Unit tests on a module that's only called from
  other unit tests are evidence the module is *coded*, not that it's
  *live*. The audit's "end-to-end test" criterion is specifically to
  prevent this.
- **Dead ADRs.** Some ADRs may have been superseded informally — the
  design moved on but the ADR wasn't marked superseded. The audit
  surfaces these as "design / system direction mismatch" rather than
  closure debt.
- **Cross-layer drift.** If L5 expects L7 to consume a field that L7
  silently stopped reading, both layers' unit tests pass but the
  system is degraded. Cross-layer contract check (step 5) is the
  audit's defense.
- **Audit fatigue.** The audit is large. The risk is shortcuts — "this
  layer looks fine, skipping the caller trace." Mitigate by structuring
  the audit as per-layer commits, each with verifiable grep evidence,
  so progress is concrete and shortcuts are visible.
- **Audit-of-audit infinite regress.** The audit method itself depends
  on grep + caller-trace evidence. If those tools mislead (e.g.,
  dynamic dispatch obscures a real caller), the audit may produce
  false-dormant verdicts. Mitigate by requiring two independent
  verifications for every "dormant" verdict before it's recorded.

---

## Cross-references (apply the discipline)

Per [[feedback-adr-cross-reference-discipline]], this scope explicitly
cites:

- **ADR-0006** (field energy operator), **ADR-0014** (vault promotion
  policy) — the substrate the recognizer-storage scope corrects
  against.
- **ADR-0055** (inter-session memory), **ADR-0056** (contemplation
  loop), **ADR-0057** (teaching-chain proposal review) — the existing
  HITL machinery, expected to be audited at L7/L8.
- **ADR-0142** (epistemic state taxonomy), **ADR-0143** (recognition
  output contract), **ADR-0144** (proposition-graph epistemic
  carrier) — the recent recognition-arc landings, expected to be
  audited at L4/L9.
- **CLAUDE.md** — the project guardrails. The audit must respect them
  (no hidden normalization, no approximate recall, no unreviewed
  mutation).
- **Recognizer-storage scope** ([recognizer-storage-scope.md](./recognizer-storage-scope.md)) and
  **teaching-derived-recognition scope** ([teaching-derived-recognition-scope.md](./teaching-derived-recognition-scope.md))
  — both have unresolved questions that audit findings will inform.

This list is not exhaustive. The audit's first deliverable is the full
ADR enumeration per layer.

---

## Open questions for the audit to answer

- **Where does the foundation actually end?** First-pass guess: L0–L3
  are closed or near-closed. The audit measures whether that's true
  or whether rot starts lower than expected.
- **Is the runtime model genuinely an open layer, or is it implicit
  in many other ADRs?** The audit may find that several ADRs encode
  assumptions about the runtime model that aren't documented as such.
- **Are there layers we haven't named?** The hypothesis layers L0–L11
  may miss something (e.g., a "calibration" or "replay" cross-cutting
  layer that doesn't fit the stack). The audit surfaces these.
- **Which closure gaps are wiring-only, vs. which require new ADRs?**
  The ratchet depends on this distinction.

---

## Summary

CORE is a system of systems. Each subsystem's design has landed via
ADR; many subsystems' wiring has not. The substrate liveness audit
walks layer-by-layer from the foundation outward, finding which
subsystems are closed (designed + wired + exercised + cross-layer-
consistent), which are partial, and which are open. Output is a
closure registry and a derived ratchet plan that sequences the
remaining wiring work toward live-mode readiness.

The scope's commitment is to **the audit's shape and discipline**, not
to its findings. Findings belong to the audit. The next ADRs belong to
the ratchet.

The audit's first act, on the first layer it touches, is to apply
the same grep that should have been applied to ADR-0006/0014 before
the recognizer-storage v1 draft. The discipline is the deliverable
as much as the registry is.
