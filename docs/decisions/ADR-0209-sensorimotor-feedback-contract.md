# ADR-0209: Sensorimotor Feedback Is Afferent

**Status:** Accepted — implementation landed (afferent scope)
**Date:** 2026-06-04
**Implementation:** `sensorium/sensorimotor/` (PR #540) + `sensorium/adapters/sensorimotor.py`, `packs/sensorimotor/sensorimotor_core_v1/` (PR #541). Proof obligations are covered by falsifiable tests in `tests/test_sensorimotor_contract.py` (deterministic unit + merge key, IR replay, idempotent delta merge, **no `decode`/`decode_batch` path**, hash-only trace with no command/trajectory payload) and `tests/test_sensorimotor_pack_manifest.py`.
**Domains:** `sensorium/sensorimotor/`, `sensorium/protocol.py`, future robotics integrations
**Depends on:** ADR-0013, ADR-0198, ADR-0208

## Decision

CORE will treat proprioception, tactile/contact state, actuator state feedback,
and action result evidence as **afferent sensorimotor input**. Motor commands
remain **efferent** and are governed separately by `EfferentGate`.

```text
proprioception / contact / actuator feedback
  -> sensorimotor compiler
  -> SensorimotorCompilationUnit
  -> ObservationFrame

field action intent
  -> EfferentGate + AuthorityToken
  -> governed decode / refusal
  -> environment effect
  -> result feedback re-enters as sensorimotor input
```

## Contract

The v1 afferent signal is quantized and replayable:

```text
ProprioceptiveSignal
  pose_q
  velocity_q
  force_torque_q
  contact_q
  actuator_state_q
  source_sha256
  canonical_sha256
```

The compiler emits:

```text
SensorimotorIR
SensorimotorCompilationUnit
ContentAddressedDelta
```

No decoder, trajectory executor, actuator driver, robot interface, tool call, or
skill invocation is introduced by this contract.

## Consequences

This reserves the correct robotics shape without making unsafe action emission
look like ordinary perception. A robot can later close the loop through
environment orchestration, but the two halves remain type-separated:

- sensorimotor feedback is evidence;
- motor command is authorized action;
- action results become new evidence only after they re-enter through an
  afferent compiler.

## Proof Obligations

- Same canonical proprioceptive signal produces identical unit and merge key.
- IR replay reproduces the projection.
- Sensorimotor deltas merge idempotently.
- Sensorimotor compiler exposes no decode path.
- Trace records contain no command or trajectory payload.
