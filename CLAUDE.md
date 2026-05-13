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

## Architecture in One Sentence

Raw input -> inject once -> versor on the manifold -> versor_apply every step ->
CGA inner product for recall and decoding -> persona motor for voicing -> done.
