# evals/demo_composition — Lane Contract

**ADR:** ADR-0098
**Invariants:**
- ``demo_json_byte_equality``
- ``demo_composition_no_side_effects``

## Purpose

Prove that every adapter conforming to :class:`core.demos.DemoCommand`
satisfies ADR-0098's two structural rules:

1. **Deterministic JSON.** Running an adapter twice in the same
   process with identical inputs produces byte-identical JSON output.
2. **No global state mutation.** Running an adapter does not mutate
   load-bearing process state (telemetry sink module identity,
   ``CORE_*`` env vars, runtime module identity). Lazy imports of
   previously-unloaded modules are not considered mutations.

## Cases

The runner exercises each shipped adapter and asserts both invariants
hold:

- ``audit_tour_byte_equality`` — audit-tour adapter byte-equality
  across two runs.
- ``audit_tour_no_state_mutation`` — global state snapshot identical
  across the audit-tour run.
- ``register_tour_byte_equality`` — register-tour adapter byte-equality.
- ``register_tour_no_state_mutation`` — global state snapshot identical.
- ``orthogonality_tour_byte_equality`` — orthogonality-tour adapter
  byte-equality.
- ``orthogonality_tour_no_state_mutation`` — global state snapshot
  identical.
- ``composition_read_only`` — the showcase reads two adapter results
  and produces a composite claim set without mutating either.
- ``stateful_fixture_rejected`` — a deliberately-stateful fixture
  produces a non-zero divergence list (negative control).

The anchor-lens tour is the slowest shipped tour; its adapter is
exercised by ``tests/test_demo_composition.py`` rather than the lane
runner to keep the lane fast.

## Determinism

The lane emits ``results/v1_dev.json``. Two consecutive runs against
the same in-tree code produce byte-identical bytes (SHA-256 pinned).

## Exit code

Non-zero on any case whose actual outcome diverges from the case spec.
