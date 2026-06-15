# Afferent → Field Ingest Seam — Scope & Decision Brief

**Status:** scope (decision-gated; field-touching, CLAUDE.md sanctioned-site implication) ·
**Context:** frontier survey move #2, after the always-on process (#747/#748/#752) + its
long-horizon soak (#757) closed the *idle* lived-spine. This is the proposed next edge:
give the always-on life a **stream of experience** by folding compiled afferent
observations into the live cognitive field.

## The gap it would close

The always-on heartbeat lives, holds closure, and resumes — but it is a continuously
**idling** life: `idle_tick` drains a finite backlog + saturates deductive closure, then
does no work forever (proven by the convergence gate H3 in `evals/l10_always_on`). There is
**no afferent input channel** into the idle loop. Separately, the sensorium is fully built
as a compiler/frame/merge substrate but is **never wired to the field** — ADR-0208's own
pipeline arrow (`ObservationFrame → … → field / recall / cognition`) stops at the merge.
This seam is the missing edge in `listen → comprehend → … → replay`.

## What is confirmed (geometric feasibility)

- **Units carry a field-shaped target.** `CompilationUnitLike` (sensorium/compiler/protocol.py:28)
  exposes `versor: np.ndarray` — a real CL(4,1) multivector — alongside `versor_condition`.
  A live `ObservationFrame`'s units therefore expose targets in the field's algebra.
- **The sanctioned pull pattern applies directly, closure-preserving BY CONSTRUCTION.** The
  exemplar is `session/context.py::_session_anchor_pull`:
  ```
  R       = word_transition_rotor(field_state.F, target)   # rotor toward target
  R_step  = rotor_power(R, α)                               # fractional, stays on Spin manifold
  pulled  = versor_apply(R_step, field_state.F)             # apply — no post-hoc unitize
  ```
  It explicitly *replaced* the rejected `_slerp_toward` (which broke closure and needed a
  forbidden post-hoc `unitize_versor`). An afferent pull toward `unit.versor` is structurally
  identical → preserves `versor_condition < 1e-6` by construction, adds no normalization site.
- **Home:** `session/context.py` (the already-sanctioned site that owns the field), a new
  opt-in `observe(frame)` that pulls the field toward each unit's versor by a fractional
  step. Default off → serving + existing behavior byte-unchanged.

## The load-bearing wrinkle (the decision)

**Closure-preservation is necessary but NOT sufficient.** The sanctioned anchor-pull moves
the field toward a **session concept-attractor** — a target in the *cognitive* semantic
frame, carrying meaning ("the field anchors toward the session's concept"). An afferent
unit's versor is in the *same algebra* (CL(4,1)) but:

> **Is the sensorium's CGA embedding semantically COMMENSURABLE with the cognitive field —
> or merely same-algebra, different meaning?**

- If **commensurable**: pulling the field toward `unit.versor` is genuine perception →
  cognitive state (decoding doctrine: the observation is real, the field moves toward it).
  The seam is clean and meaningful.
- If **not** (same algebra, unrelated embedding): the pull is geometrically valid but
  **semantically empty** — the field drifts toward an arbitrary point. That is exactly the
  *degenerate fit* the field-as-standing-hand doctrine forbids ("geometrically-realizable
  structure only; never force a degenerate fit").

This question is unestablished in the code: the sensorium compiles units into CL(4,1) but
nothing today asserts that embedding shares the cognitive field's semantic frame (they were
built as **disjoint** tracks — CLAUDE.md: the afferent arc "is disjoint from the GSM8K
serving path"). Wiring afferent → field is the *first* connection of the two.

## Decisions for ratification (Shay reviews the design)

1. **Commensurability ruling (the crux).** Is the sensorium CGA embedding intended to be
   commensurable with the cognitive field? Three honest paths:
   - **(a) Commensurable by construction** — if the modality packs project into the *same*
     concept manifold the cognition field uses, the pull is meaningful → build the seam.
     (Needs: evidence/assertion that the projection shares the frame, e.g. a shared
     concept-attractor basis, before any pull is wired.)
   - **(b) Bridge required** — define an explicit, falsifiable map from a unit's versor to a
     cognitive-field target (a grounded embedding), so the pull is toward a *meant* point.
     Larger; an ADR + a commensurability gate.
   - **(c) Not yet** — keep the tracks disjoint; the always-on life stays idle-converging for
     now; the stream-of-experience comes from a different intake (the autonomous
     determination-frontier — roadmap Step 5 — which feeds *symbolic* new questions, not
     afferent versors). Lower geometric risk, advances the telos via comprehension.

2. **Sanctioned-site clause.** If (a)/(b): extend `session/context.py`'s CLAUDE.md clause to
   cover afferent-observation pull (closure-preserving by construction AND semantic =
   perception→field), with the same bright-line justification. A CLAUDE.md amendment.

3. **ADR.** Completing ADR-0208's arrow (`ObservationFrame → field`) is the first
   afferent→cognitive-core connection; it likely warrants an ADR (extend 0208 or new),
   given the tracks were deliberately disjoint.

4. **Falsifiable gate (regardless of path).** Any pull that "preserves closure" is only
   proven if a test fails when it doesn't: a soak guard (sibling to `evals/l10_always_on`)
   asserting (i) `versor_condition < 1e-6` every observed beat, (ii) the same frame sequence
   → byte-identical field digest (determinism), (iii) a *commensurability* assertion — the
   field moves **toward** the observation (`dist(F, target)` decreases), not arbitrarily.

## Recommendation

The geometry is clean; the **semantics are the gate**. Recommend **ruling on decision 1
first** — do not wire a field pull until the commensurability question is answered, or the
seam risks a closure-valid-but-meaningless fit. If commensurability isn't yet established
(likely), the higher-leverage telos move is path **(c)**: the autonomous
determination-frontier intake (feed the idle heartbeat *symbolic* new questions it can
`determine` + commit wrong=0 / propose HITL) — which needs no field-embedding ruling and
directly converts the idle life into a learning one. The afferent→field seam then follows
once the embedding frame is established.
