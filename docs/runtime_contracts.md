# Runtime Contracts

This document freezes the runtime contracts used by chat, telemetry, memory,
and future teaching work.  It exists to prevent contract drift between tests,
runtime code, and future cognitive pipeline work.

## Field invariant

CORE state is a versor field.  Runtime code must preserve the core closure
contract:

```text
versor_condition(F) < 1e-6
```

If a propagation path violates this invariant, fix the operator path or the
explicit closure boundary that owns the transition. Do not hide violations by
changing tests or silently downgrading the invariant.

## ChatResponse contract

`ChatResponse.surface`
: The selected user-facing response. This is the exact string returned by
  `ChatRuntime.respond()` and should match what the user receives.

`ChatResponse.walk_surface`
: The manifold/token-walk evidence surface. It is trace evidence for what the
  field traversal produced. It is not necessarily the user-facing response.

`ChatResponse.articulation_surface`
: The proposition/realizer surface. This is the structured linguistic
  realization of the current proposition or proposition graph.

Current selection policy:

```text
surface = articulation_surface
walk_surface = retained telemetry/evidence
```

Future realizer work may change the selection policy, but must update this
document and the contract tests in the same PR.

## TurnEvent contract

`TurnEvent.surface`
: Exact emitted user-facing response for the turn.

`TurnEvent.walk_surface`
: Exact manifold/token-walk evidence surface for the turn.

`TurnEvent.articulation_surface`
: Exact proposition/realizer surface for the turn.

`TurnEvent.vault_hits`
: Actual count of recall hits applied during generation. Never hardcode this.

`TurnEvent.flagged`
: Mirrors `IdentityScore.flagged` for filtering and trace inspection.

## Identity contract

Identity checks are telemetry/gating signals. A flagged identity score must not
silently erase useful generation unless an explicit hard-block policy is
configured and tested.

Canonical call style:

```python
IdentityCheck().check(trajectory, manifold)
```

Legacy constructor injection:

```python
IdentityCheck(manifold=manifold).check(trajectory)
```

is supported temporarily and emits `DeprecationWarning`. New code must not use
it.

## Memory and teaching contract

Session memory can be immediate and local to the running context.

Reviewed memory must be explicit: user corrections or teaching examples become
reviewed memory only through the reviewed teaching loop.

Pack mutation is proposal-only until reviewed. Runtime correction capture must
not directly rewrite language packs, frames, identity axes, or operator code.

Identity manifold mutation by user prompt or correction is forbidden.

## Testing policy

Tests should protect load-bearing behavior:

- versor closure
- deterministic replay
- runtime response/telemetry contracts
- memory correctness
- identity protection
- teaching/correction safety
- articulation contract

Avoid tests that preserve stale constructors, private helper shapes, or exact
formatting that is not part of a documented contract.

## Epistemic surface (ADR-0021)

CORE exposes a typed `epistemic_status` on the teaching and lexicon
surfaces.  The status is a **position in the revision graph**, not a
source-trust tier:

| Status        | Meaning                                                                                  |
|---------------|------------------------------------------------------------------------------------------|
| `COHERENT`    | Fits current field geometry; no incoherence with reviewed claims detected at admission. |
| `CONTESTED`   | Incoherent with at least one reviewed claim; review pending; not load-bearing.           |
| `SPECULATIVE` | Proposed; not yet reviewed for coherence; admissible only as a candidate.                |
| `FALSIFIED`   | Incoherent under accumulated evidence; eligible for Stage-3 inversion; retained.         |

### Non-hardening invariant

No reviewed claim or proposition-graph edge ever becomes unrevisable.
No `final`, `frozen`, `axiom`, or `permanent` flag exists or may be
added on the runtime data model.  The closest such property in the
architecture is the *mathematical* closure check
`versor_condition(F) < 1e-6` — never an epistemic seal on a claim.
The invariant is enforced by `tests/test_epistemic_invariants.py`.

### Curator review rule

`epistemic_status` transitions are computed from coherence with the
existing reviewed field — not asserted by source authority.  At v1 the
judgment is curator-mediated, with one rule:

> The curator's only admissible reasoning is *geometric*: does the
> claim cohere with already-reviewed claims, or does it produce
> incoherence?  Source credentials, popularity, or institutional
> position must not be invoked as justification.

### Schema surfaces

| Surface                                 | Field                                  | Default at creation   |
|-----------------------------------------|----------------------------------------|-----------------------|
| `teaching.PackMutationProposal`         | `epistemic_status: EpistemicStatus`    | `SPECULATIVE`         |
| `teaching.ReviewedTeachingExample`      | `epistemic_status: EpistemicStatus`    | `SPECULATIVE`         |
| `language_packs.schema.LexicalEntry`    | `epistemic_status: str`                | `"coherent"` (seed)   |
| `core.cognition.trace.compute_trace_hash` | `teaching_epistemic_status: str`     | `""` if no proposal   |

Promotion of a proposal's status uses the immutable updater
`PackMutationProposal.with_status(...)` — original is never mutated.

The status of the load-bearing proposal in a turn is folded into
`trace_hash` so replay detects when a downstream surface was produced
under a different epistemic frame than at the time of recall.

## Test organization target

Future test moves should follow this taxonomy:

| Area | Destination |
|---|---|
| versor closure, holonomy, motors, null cone, energy physics | `tests/algebra/` or `tests/physics/` |
| chat runtime, config, async runtime, identity gate telemetry | `tests/runtime/` |
| articulation, proposition, surface assembly, future pipeline | `tests/cognition/` |
| correction capture, reviewed memory, consolidation | `tests/teaching/` |
| language pack loading and seed pack invariants | `tests/packs/` |

Do not reorganize tests as a standalone churn PR unless it directly reduces
contract ambiguity or unlocks a cognitive subsystem.
