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

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
