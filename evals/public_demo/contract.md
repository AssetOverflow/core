# evals/public_demo — Lane Contract

**ADR:** ADR-0099
**Invariants:**
- ``public_showcase_pure_composition``
- ``public_showcase_all_claims_supported``
- ``public_showcase_json_byte_equality``

## Purpose

Prove that ADR-0099's `core demo showcase` is a single 30-second
artifact composing four invariants (determinism, honest unknown,
reviewed learning, multi-hop with trace) **without introducing any
new mechanism**. Every claim it makes is backed by an existing,
shipped, separately-tested adapter.

## Cases

- ``determinism_run_to_run_byte_equality`` — two consecutive
  showcase runs produce byte-identical JSON (after stripping
  ``total_runtime_ms``). SHA-256 pinned.
- ``all_claims_supported`` — single run reports
  ``all_claims_supported=True`` and every scene reports
  ``all_claims_supported=True``.
- ``runtime_under_budget`` — total runtime ≤ 30 seconds on the
  reference dev hardware.
- ``pure_composition_no_new_mechanism`` — grep gate over
  ``core/demos/showcase.py``'s import graph refuses any symbol whose
  module path is not within the existing shipped packages
  (``core/``, ``chat/``, ``generate/``, ``language_packs/``,
  ``teaching/``, ``evals/`` for adapter-lane bridges).

## Determinism

Two showcase runs produce identical JSON bytes when
``total_runtime_ms`` is excluded (timing is the one legitimate piece
of non-determinism — every other field is pinned by the showcase
contract and the underlying adapter byte-equality from ADR-0098).

## Exit code

Non-zero on any case whose actual outcome diverges from the case spec.
