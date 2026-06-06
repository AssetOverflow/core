# Passive Tabletop Falsification Lab Protocol

## Purpose

The tabletop lab is an offline evidence source for ADR-0211 falsification. It is
not a live robotics stack and it does not authorize CORE-controlled actuation.

## Hardware Target

- Event camera for sparse brightness-change deltas.
- RGB/depth camera for reference visual frames.
- AprilTag calibration board and object tags for pose witness evidence.
- IMU/contact/proprioception logger for afferent sensorimotor evidence.

## First Lab Mode

Only passive, human-moved objects are allowed. The lab records logs, imports
them offline, compiles afferent units, builds `ObservationFrame`s, and runs
falsification scenarios.

```text
passive environment movement
  -> offline witness logs
  -> deterministic import
  -> afferent compilers
  -> ObservationFrame sequence
  -> FalsificationScenario report
```

## Acceptance Gates

- The same captured log imports to the same frame-sequence hash.
- AprilTag/GTSAM-style pose outputs remain witness evidence only.
- Event-vision and sensorimotor deltas remain compiler-native.
- No raw camera frame, event stream, PCM, trajectory, or actuator trace enters
  `ObservationFrame` or falsification traces.
- No CORE motor command path is mounted.

## Deferred

Repeated capture statistics, hardware-noise envelopes, live device readers,
robot actuation, and motor decoder work require later ADRs. Exact replay remains
the first gate.
