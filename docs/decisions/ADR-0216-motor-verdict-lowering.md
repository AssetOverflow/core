# ADR-0216: Motor Verdict Lowering Prerequisite

**Status:** Proposed
**Date:** 2026-06-06
**Domains:** `sensorium/efferent.py`, `sensorium/registry.py`, future motor packs
**Depends on:** ADR-0198, ADR-0211

## Context

ADR-0198 added the `ModalityRegistry.decode()` efferent path and intentionally
left real motor emission fail-closed. The current `DefaultEfferentGate` checks
capability and vector shape only; it does not lower a motor versor into the
safety, ethics, and tool-scope verdicts required for real action.

## Decision

No physical motor decode is authorized until a dedicated implementation provides
a verdict-enforcing gate:

```text
(32,) motor versor
  -> MotorActionIntent
  -> authority + safety + ethics + tool-scope verdicts
  -> admit/refuse before SurfaceDecoder.decode()
```

`MotorActionIntent` is a semantic action predicate bundle, not an actuator
command. A `VerdictEnforcingEfferentGate` must expose
`enforces_action_verdicts=True` and fail closed on absent authority, absent
verdict coverage, or any refusal.

## Non-Goals

- No actuator driver.
- No robot interface.
- No trajectory executor.
- No sandbox opt-in on a physical path.
- No ObservationFrame or CRDT write for emitted motor commands.

## Required Proof

- The gate refuses before decoder invocation on missing authority or failed
  verdicts.
- Traces include hashes, authority hash, policy hash, and verdict only.
- No decoded command payload, trajectory, ndarray, or bytes object enters traces.
- Physical action remains disabled until a later motor decoder ADR and lab
  safety contract.
