# CORE-AI Agent Instructions

## The Invariant (Read Before Touching Any Code)

Every field state F must satisfy:

    ||F * reverse(F) - 1||_F < 1e-6

This is checked by algebra/versor.py::versor_condition().

## What You Must Never Add

- Any normalization call outside ingest/gate.py
- Grade guards, grade monitors, or grade projection in the hot path
- Drift correction, correction thresholds, or correction timers
- ANN indexes, HNSW, cosine similarity, or approximate distance
- Field energy measurement or pseudoscalar accumulation checks
- Any function whose only job is to watch or repair another function

If you think you need one of these, you have an unclosed operation upstream.
Find it and close it.

## The Two Allowed Primitives

Field transition:  algebra/versor.py::versor_apply(V, F)  ->  V*F*reverse(V)
Distance metric:   algebra/cga.py::cga_inner(X, Y)        ->  -d^2 / 2

These are the only primitives. Everything else is built from them.

## Implementation Order

Do not skip steps. Run the invariant test after each step before writing the next.

1. algebra/cl41.py
2. algebra/versor.py         ->  tests/test_versor_closure.py must pass
3. algebra/cga.py            ->  tests/test_null_cone.py must pass
4. algebra/holonomy.py       ->  tests/test_holonomy.py must pass
5. ingest/gate.py
6. vocab/manifold.py
7. field/state.py + field/propagate.py
8. vault/store.py            ->  tests/test_vault_recall.py must pass
9. persona/motor.py          ->  tests/test_motor.py must pass
10. generate/stream.py
11. session/context.py

## Architecture in One Sentence

Raw input -> inject once -> versor on the manifold -> versor_apply every step ->
CGA inner product for recall and decoding -> persona motor for voicing -> done.
