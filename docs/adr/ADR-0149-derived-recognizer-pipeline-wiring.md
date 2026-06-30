# ADR-0149 — Integrate DerivedRecognizer into CognitiveTurnPipeline

**Status:** Accepted
**Date:** 2026-05-25
**Work item:** W-007

---

## Context

ADR-0143 introduced deterministic `DerivedRecognizer` derivation and matching.
ADR-0144 gave `CognitiveTurnPipeline` an epistemic graph carrier and an optional
`recognizer` constructor slot. ADR-0146 added persisted engine state, including
`RecognizerRegistry`. ADR-0148 / W-003 wired vault promotion so `COHERENT`
entries can eventually become recognition evidence.

The missing edge was live admission: the runtime had a registry, but the
pipeline never consulted it. A populated registry was therefore inert unless a
test or caller manually passed a recognizer to `CognitiveTurnPipeline`.

---

## Decision

`RecognizerRegistry.first_admitted()` returns the first registered recognizer in
deterministic insertion order, or `None` when empty.

`ChatRuntime` now exposes `first_admitted_recognizer()`, gated by
`RuntimeConfig.recognition_grounded_graph`. When the flag is false, the method
returns `None` and the turn path is byte-behavior compatible with the previous
runtime.

`CognitiveTurnPipeline` uses an explicitly supplied recognizer first. When no
recognizer is supplied, it asks the runtime for the first admitted recognizer.
If the registry is empty, recognition remains absent and the existing
intent-derived graph path is used.

`ChatRuntime.record_recognition_example(tokens, bundle)` records deterministic
training pairs for test harnesses and future automated collection. At
`checkpoint_engine_state()`, after the vault promotion boundary, a non-empty
pending example set is passed to `derive_recognizer()` and the result is
registered before engine-state persistence.

---

## Null-Drop

`recognition_grounded_graph=False` means the registry is ignored, no recognizer
is passed to the pipeline, and pending examples are not derived at checkpoint.
The default therefore preserves the previous turn behavior.

---

## Follow-Up

Automated example collection is intentionally out of scope. `derive_recognizer()`
requires `(TokenSequence, FeatureBundle)` pairs with span-level evidence, not
teaching corpus templates. The follow-up path is:

```text
finalize_turn -> FeatureBundle with evidence spans -> record_recognition_example -> checkpoint derivation
```

That follow-up makes the registry self-populating; this ADR makes the registry
live and replay-persistent.
