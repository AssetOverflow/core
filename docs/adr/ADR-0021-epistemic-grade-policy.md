# ADR-0021 — Epistemic Grade Policy

**Status:** Accepted
**Date:** 2026-05-16
**Authors:** Joshua Shay
**Depends on:** ADR-0016 (Capability Roadmap), ADR-0017 (Agency
Scope), ADR-0018 (Tool Use Scope), CLAUDE.md ("Truth is
coherent").

## Context

CLAUDE.md already establishes the structural stance: *Truth is
coherent.  Preserve coherence in algebra, memory, articulation,
and teaching.*  The runtime already refuses several forms of
implicit bias by construction:

- No bulk corpus ingestion — frequency is rejected as a truth
  signal.
- Teaching is proposal-only until reviewed — repetition does
  not promote.
- Identity is structural, not learned from the corpus —
  override attempts are rejected.
- Recall is exact CGA inner product — no learned ranking, no
  popularity weighting.

What is missing is a typed surface that lets the system *say
something* about the epistemic status of a stored claim.
Without it, the runtime treats all reviewed claims uniformly:
there is no way to mark a claim as "currently contested" or
"eligible for inversion" except by removing it.  Removal loses
provenance; uniformity loses revisability.

The deeper requirement, surfaced in working notes
2026-05-16: **coherence is the only signal**.  Not credentials.
Not frequency.  Not institutional consensus.  Not outsider
status.  Not novelty.  The architecture must not weight
*sources* — it must weight *coherence with the existing field*,
and it must keep every claim revisable forever.

## Decision

CORE adopts an **Epistemic Grade Policy** with three commitments:

### 1. `epistemic_status` is a position in the revision graph, not a trust tier

The status tag describes *how a claim sits in the field right
now*, not where the claim came from.  Source labels
(`peer_consensus`, `outsider_empirical`, `established`,
`unauthoritative`) are explicitly **not** part of the schema —
they would re-import the bias this policy refuses.

The status enum is:

```text
COHERENT       — fits current field geometry; no incoherence
                 with reviewed claims detected at admission.
CONTESTED      — incoherent with at least one reviewed claim;
                 review pending; admissible but cannot drive
                 downstream inferences that depend on its truth.
SPECULATIVE    — proposed; not yet reviewed for coherence;
                 admissible only as a candidate, not as
                 evidence.
FALSIFIED      — incoherent under accumulated evidence;
                 eligible for Stage-3 inversion (versor-
                 conjugate correction); retained for provenance.
```

No tier carries inherent trust weight.  A `COHERENT` claim is
not "more true" than a `CONTESTED` one — it is *currently
incident-free*, and the moment new evidence makes it incoherent
it becomes `CONTESTED`.

### 2. Non-hardening invariant

No reviewed claim, relation, or proposition-graph edge ever
becomes unrevisable.  Concretely:

- Teaching is proposal-only (already true).
- Reviewed claims expose a Stage-3 inversion path: a
  versor-conjugate correction that geometrically reverses the
  rotor encoding the wrong relation, rather than appending a
  contradictory claim alongside it.
- No `final`, `frozen`, `axiom`, or `permanent` flag exists or
  may be added on the runtime data model.  The closest such
  property already in the architecture is the field invariant
  `versor_condition(F) < 1e-6`, which is a *mathematical*
  closure check on the algebra — not an epistemic seal on a
  claim.

This invariant is checkable: a test in
`tests/test_epistemic_invariants.py` (to be added in the v1
implementation PR) asserts that no schema field, relation, or
flag in the public surface admits a non-revisable state.

### 3. Coherence is the only admission signal

`epistemic_status` transitions are *computed from coherence*,
not asserted by source authority.  At v1 the computation is
intentionally simple and curator-mediated.  At every later
version, the curator's role shrinks toward a structural
coherence metric.

v1 admission rule (curator-mediated, but bias-free at the
schema level):

- The curator reviews a proposed claim against the existing
  reviewed field.
- The curator's only admissible reasoning is *geometric*: does
  the claim cohere with already-reviewed claims, or does it
  produce incoherence?
- The curator must not invoke source credentials, source
  popularity, or source institutional position as a
  justification.  Curator notes that do invoke these are a
  review smell — to be flagged in v2 by an automated check on
  the review log.

The status is the *output* of this review, not an input the
curator may set by fiat outside of it.

## Schema impact

The schema lands where it needs to, per the runtime's existing
typed surfaces:

- `teaching/store.py::PackMutationProposal` — new field
  `epistemic_status: EpistemicStatus = SPECULATIVE` at proposal
  creation; transitions to `COHERENT` / `CONTESTED` /
  `FALSIFIED` only via the review path.
- `teaching/review.py` — review outcomes carry the resulting
  `epistemic_status` alongside the existing
  `ACCEPTED` / `REJECTED_IDENTITY` axis.  Accepting a proposal
  is not the same as ratifying it as `COHERENT` — the two are
  orthogonal and both required for admission as evidence.
- `language_packs/data/*/lexicon.jsonl` — new optional field
  `epistemic_status` (default `COHERENT` for the seed
  vocabulary; deliberate-curator-reviewed at pack version
  bumps).  No retroactive tagging without review.
- `core/cognition/trace.py` — `epistemic_status` of any
  load-bearing claim in a turn is folded into the
  `trace_hash`, so replay can detect if a downstream surface
  was produced under a different epistemic frame than at the
  time of recall.

The `proposition_graph` model does not need per-edge tagging in
v1 — edges inherit status from the proposition node they
attach to.  v2 may revisit this for fine-grained relation
typing.

## Named gap (v2 work, explicit)

The hardest unsolved piece is making the coherence test
**structural**, not curator-asserted.  v1 ships with a typed
field and a non-hardening invariant; v2 must add the metric
that bounds `epistemic_status` by geometric agreement with the
existing reviewed field.

Candidate v2 recipe (to be evaluated, not yet committed):

```text
admit(claim) requires:
  cga_inner(claim_versor, field_state) ≥ τ_admit
  AND no reviewed_relation R with cga_inner(claim, R) ≤ τ_reject
```

That metric — once specified, tested, and locked — is what
takes the system from *"curator says it's coherent"* to
*"the field's geometry confirms it's coherent."*  Until then,
v1 is honest about the gap: epistemic typing is real and
typed, the coherence judgment behind a tag is still curator-
mediated, and the architecture commits to closing that gap on
a stated path.

## What this ADR is NOT

- **Not a source-trust schema.**  No tier ranks sources.
- **Not a censorship layer.**  `FALSIFIED` claims are retained
  with provenance; they are not removed.
- **Not a moral filter.**  The system's internal motive
  remains structural ("be coherent"), not normative
  ("save people from lies").
- **Not language-specific.**  The policy applies to any pack,
  any language, any domain.  English / Hebrew / Greek /
  mathematics / physics packs all receive the same epistemic
  surface.

## Consequences

- New ADR-tracked work: implement the schema changes named in
  *Schema impact* above, with the non-hardening invariant
  test.  This is a Phase 5 parallel-track item alongside Rust
  parity.
- `docs/runtime_contracts.md` must add an *Epistemic surface*
  section documenting the four statuses, the non-hardening
  invariant, and the curator review rule.
- Pack mutation review tooling must record curator
  justification text so a v2 automated check can flag
  source-authority-as-justification smells.
- Trace-hash composition expands to include
  `epistemic_status` per load-bearing claim.  Replay tests
  must continue to pass bit-for-bit.

## Why this is correct *for this project*

Every other architectural commitment in CORE is structural:
algebra closure, exact recall, typed operators, reviewed
teaching, deterministic replay.  Adding `epistemic_status` as
a tier-ranked trust schema would be the one place the
architecture quietly imports a bias source.  By making the
status a *revision-graph position* instead, the policy stays
load-bearing without breaking the rest of the architecture's
shape.  Coherence remains the only signal; the typed field
just lets the runtime *say* where each claim sits relative to
that signal.
