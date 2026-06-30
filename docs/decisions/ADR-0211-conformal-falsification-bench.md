# ADR-0211: Conformal Falsification Bench

**Status:** Accepted
**Date:** 2026-06-06
**Domains:** `sensorium/environment/`, `evals/environment_falsification/`
**Depends on:** ADR-0198, ADR-0208, ADR-0209

## Context

ADR-0208 established `ObservationFrame` as a deterministic bundle of already
compiled afferent units. ADR-0209 established sensorimotor feedback as afferent
evidence. ADR-0198 established that real motor emission is fail-closed until a
verdict-enforcing efferent gate exists.

The missing contract was falsification: a replayable way to say, "this expected
environmental evidence was or was not observed," without turning observation
frames into fusion, memory mutation, hardware control, or learned truth.

## Decision

CORE will use the Conformal Falsification Bench as a Python-reference replay
contract:

```text
hypothesis / plan
  -> ExpectedObservationFrame
  -> actual ObservationFrame
  -> FalsificationRun
  -> replay-stable report
```

The v1 bench is exact and binary:

- `SUPPORTED` when every expected slot is present with the expected merge key and
  no unexpected slot appears.
- `FALSIFIED` when any expected slot is missing, changed, or accompanied by
  unexpected evidence.

## Contract

- `ObservationFrame` remains afferent-only evidence, not fusion and not a
  mutable world model.
- `ExpectedObservationFrame` and `FalsificationRun` are replay artifacts, not
  learned truth, reviewed memory, or pack mutation proposals.
- v1 verdicts are only `SUPPORTED` and `FALSIFIED`.
- No probabilistic confidence, numeric tolerance, hardware-noise envelope, or
  learned latent is part of the v1 verdict.
- No motor/efferent unit, actuator trace, raw pixel buffer, PCM buffer, event
  payload, decoded action payload, Vault mutation, or `generate/*` dependency is
  allowed in the bench.
- Public API names are stable:
  `ObservationUnitRef`, `ExpectedObservationFrame`, `FalsificationResidual`,
  `FalsificationRun`, `build_expected_observation_frame`, and
  `compare_expected_to_observation`.

## Consequences

The bench gives CORE a falsifiable environmental replay surface before any
hardware, motor, native backend, or learned world model is admitted. Later event
vision, witness-log import, tabletop lab, and motor governance work must feed or
consume this contract rather than bypass it.

## Proof Obligations

- Expected frame hashes are order-invariant and duplicate-safe.
- Raw payloads and efferent units are rejected before traces are built.
- Missing, unexpected, or changed evidence yields `FALSIFIED`.
- Exact matched evidence yields `SUPPORTED`.
- The bench does not import `generate`, mutate Vault, or call
  `ModalityRegistry.decode`.
- `core eval environment-falsification --json` is hash-pinned.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
