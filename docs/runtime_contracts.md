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
