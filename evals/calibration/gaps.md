# calibration lane — architectural findings

This document records architectural gaps surfaced by the v1 calibration
lane.  These are real findings worth follow-up work; they are not
blockers for the v1 lane (which measures around them honestly), and
they are not weakened thresholds masquerading as passes.

## Finding 1: The ingest gate is geometric, not semantic

`vault/decompose.py:UnknownDomainGate` fires when CGA inner-product
recall against the vault returns no entry with score ≥ `UNKNOWN_FLOOR`
(0.15).  This is a *geometric* test in 32-dimensional Cl(4,1) versor
space, not a semantic test against pack vocabulary.

Empirical behavior observed during lane construction (fresh
`ChatRuntime` warmed with 7 in-pack queries):

- 6/42 hand-chosen OOD prompts (e.g. "qubit", "transistor",
  "nucleotide", "polynomial", "mutex") fired the gate.
- 36/42 OOD prompts did not fire because morphological grounding
  produced versors that scored above 0.15 against the warmed vault.

Additional drift effect: with the same priming, in-pack queries
*sometimes* fail to recall after several intermediate turns — vault
entries committed in earlier turns drift the recall geometry and the
fresh probe no longer reaches its anchor.

### Impact on this lane

The v1 lane intentionally avoids relying on the gate's semantic OOD
behavior.  Instead, it tests three deterministic signals that CORE
*does* produce reliably:

1. `vault_hits > 0` for queries with primed recall.
2. `vault_hits == 0` for queries on an empty vault.
3. `pack_mutation_proposal is not None` for correction intents with a
   primed prior turn.

These are sufficient to demonstrate the structural claim ("CORE emits
typed cognitive signals") without overclaiming semantic OOD detection.

### Suggested follow-up work

A semantic OOD layer could be added either:

- **At the gate**: extend `UnknownDomainGate.check()` to also consult
  the vocabulary, e.g. fire when no content tokens of the prompt match
  a pack `surface`/`lemma`/`stem`.  This adds a vocabulary-aware
  cross-check that doesn't replace the geometric check.
- **At the pipeline**: produce a separate `confidence` signal in
  `CognitiveTurnResult` that combines geometric and vocabulary
  signals.  Surfaces stay unchanged; downstream callers gain a richer
  typed evidence channel.

Either path should preserve replay determinism and avoid post-hoc
classifiers.  A v2 calibration lane could re-enable semantic OOD tests
once that signal exists.

## Finding 2: Pipeline overrides the gate's safety surface — RESOLVED 2026-05-17

`CognitiveTurnPipeline.run()` now gates the realizer override on
`(response.surface == _UNKNOWN_DOMAIN_SURFACE and response.vault_hits == 0)`.
When the gate fires, the safety stub is preserved as the user-facing
`surface`; the realizer's articulation still survives in `walk_surface`
as evidence.  Contract update in `docs/runtime_contracts.md`; new
contract test `tests/test_semantic_realizer_integration.py::
test_pipeline_honours_safety_stub_when_gate_fires`.

The original finding is preserved below for traceability.

### Original finding (now resolved)

`core/cognition/pipeline.py` overrides `response.surface` with
`realized_plan.surface` unconditionally when the realizer produced a
result.  The realizer always produces a result (it works from intent +
graph alone), so when the runtime gate fires and returns the
"I don't have field coordinates for that yet." stub, the pipeline
overrides it with realizer output.

The OOD marker survives in `result.walk_surface` (which is **not**
overridden), but the user-facing `result.surface` does not signal
no_grounding.

### Impact on this lane

The lane classifies on `vault_hits` (which is preserved by the
pipeline), not on `surface` (which is overridden).  This is the right
choice for v1 measurement; it avoids touching pipeline contract until
a deliberate decision is made about whether the realizer should
respect the gate's safety surface.

### Suggested follow-up work

A small, contained fix: in `CognitiveTurnPipeline.run()`, only
override `surface`/`articulation_surface` when the underlying response
is *not* an OOD stub.  This makes the user-facing surface honest about
no_grounding without affecting any other contract.  The
`docs/runtime_contracts.md` document should be updated in the same
change.
