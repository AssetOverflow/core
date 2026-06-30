# ADR-0154 — DerivedRecognizer producer wiring (W-020b)

Status: accepted
Date: 2026-05-25

## Context

ADR-0149 (W-007) wired the `DerivedRecognizer` registry's **consumer**
side: `runtime.first_admitted_recognizer()` is read by
`CognitiveTurnPipeline.__init__` and feeds the optional
recognition-grounded graph at `pipeline.py` ~line 217 (gated by
`recognition_grounded_graph`, default off).

The **producer** side — capturing `(tokens, bundle)` from admitted
turns so `derive_recognizer` at checkpoint can anti-unify them into
tighter recognizers — was never connected in production code.
`runtime.record_recognition_example` had zero non-test callers:

```bash
$ grep -rn record_recognition_example --include="*.py" | grep -v test
chat/runtime.py:703:    def record_recognition_example(
```

Consequence: `_pending_recognizer_examples` stayed permanently empty,
so the conditional at `chat/runtime.py:684-691` —

```python
if (
    self.config.recognition_grounded_graph
    and self._pending_recognizer_examples
):
    recognizer = derive_recognizer(...)
    ...
```

— never fired, even with the flag enabled. The registry could only
grow via tests calling `record_recognition_example` directly.
Observed symptom: a 103-turn session wrote `recognizers.jsonl` as
empty even though recognition was running.

## Decision

In `CognitiveTurnPipeline.run`, at the admitted-recognition boundary
(directly after `EpistemicGraph` construction), call
`runtime.record_recognition_example(raw_tokens, _rec_outcome.proposition)`.

- **Producer fires unconditionally** when a turn is admitted — the
  bucket is filled regardless of `recognition_grounded_graph`. This
  means flipping the consumer flag later is not a cold start.
- **Consumer stays opt-in** behind the same flag — no change to
  `checkpoint_engine_state`'s `derive_recognizer` gate.
- `hasattr` guard on `runtime.record_recognition_example` keeps the
  pipeline tolerant of non-`ChatRuntime` runtimes (test doubles,
  alternative shells).

## Invariants

- Refused recognition: no producer call (gated inside
  `if _rec_outcome.admitted:`).
- No attached recognizer: no recognition runs at all, no producer
  call.
- Per-turn FeatureBundle is the validated proposition emitted by
  `recognize` — no shape massaging in the pipeline.
- `recognize` is unchanged; `derive_recognizer` is unchanged; trace
  hash bytes are unchanged for any given turn.

## Out of scope

- **Bootstrap of the very first recognizer.** This ADR closes the
  loop *given* a recognizer is attached. No path in production code
  seeds the first recognizer from operator review or reviewed
  teaching examples; that is a substrate-liveness concern tracked
  separately under the ADR-0143 / substrate-liveness audit family.
- **Unbounded growth of `_pending_recognizer_examples` when the
  consumer flag stays off.** With flag=False, the producer
  accumulates forever. Acceptable for short sessions; a future
  bound (LRU or cap) should ship before long-running operators
  enable the producer with the consumer off.

## Validation

`tests/test_adr_0154_recognizer_producer_wiring.py`:
- admitted turn appends `(tokens, bundle)` to the producer queue
  (flag=False so the queue is not drained at checkpoint)
- producer fires when consumer flag is off
- refused turn does not populate the queue
- end-to-end loop: with flag=True, an admitted turn feeds the
  producer queue, then `checkpoint_engine_state` drains it via
  `derive_recognizer` and registers the result
- multiple admitted turns accumulate in order

CLI lanes: `core test --suite cognition` (120 + 1 skipped),
`core test --suite smoke` (67), recognition phase 1/2 + refusal
propagation (25) all green.

## Closure

After this ADR, the DerivedRecognizer registry can grow from live
traffic. The remaining gap is bootstrap — getting the first
recognizer into the registry without test-only injection. That is a
substrate-liveness scope concern, not W-020b.
