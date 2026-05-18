# ADR-0036: Safety-Only Typed Refusal Policy

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0032-safety-check-surface.md`](ADR-0032-safety-check-surface.md), [`ADR-0034-ethics-check-surface.md`](ADR-0034-ethics-check-surface.md), [`ADR-0035-turn-loop-verdict-surfacing.md`](ADR-0035-turn-loop-verdict-surfacing.md)

## Context

ADR-0035 wired `SafetyCheck` and `EthicsCheck` into the turn loop as
**observation only** — verdicts attach to `ChatResponse` and `TurnEvent`
but do not change behavior. The closing notes flagged refusal /
re-articulation as the natural follow-up *once real verdict data
flowed*.

With one ADR's worth of verdict surfacing in the runtime, two scope
axes had to be decided before wiring refusal:

1. **Trigger scope.** Safety only? Safety + ethics? Per-predicate?
2. **Refusal shape.** Typed refusal surface? Hedge injection?
   Re-articulation via planner retry?

The decision was made jointly with the user, surfaced via an explicit
scope question before any code landed.

## Decision

**Safety-only typed refusal.** A `SafetyVerdict` with at least one
`runtime_checkable=True, upheld=False` result replaces
`ChatResponse.surface` with a deterministic typed refusal string.
Ethics violations remain audit-only.

### Why safety only

Safety is the universal floor (ADR-0029): five fixed boundaries, never
swappable, fail-closed on load. Ethics is deployment configuration
above that floor (ADR-0033): swappable per-deployment, falls back to
default. Wiring ethics into refusal would let pack-swappers silently
change the runtime's refusal behavior by editing a JSON file — exactly
the coupling we want to avoid. Safety is the architectural place to
encode "the floor never moves."

A future ADR can revisit per-predicate ethics refusal once individual
ethics commitments have empirical violation rates from real corpora.

### Why typed refusal (not hedge injection, not re-articulation)

* **Typed refusal** is deterministic, audit-detectable by prefix, and
  preserves replayability. The refusal carries the violated
  boundary ids in lex order. Same violation → same bytes.
* **Hedge injection** would blur the boundary between
  alignment-score-driven hedging (ADR-0028 surface preferences) and
  predicate-driven refusal. The same surface change could mean two
  different things. Audit becomes ambiguous.
* **Re-articulation** via planner retry is deterministic too, but the
  planner has no refusal-bias hint surface today — retry with
  unchanged inputs yields the same surface. Deferred to a future ADR
  that first lands evidence-threading through the planner.

### Why only `runtime_checkable=True` violations refuse

A predicate that reports `runtime_checkable=False` is honestly stating
"I have no evidence to make a real claim." Refusing on no-evidence
predicates would refuse on architectural absence, not behavioral
violation. The ADR-0032/0034 honest-reporting discipline means
`runtime_checkable` is exactly the gate for "did we observe a real
violation."

### What the runtime contract looks like now

`chat/refusal.py`:

* `TYPED_REFUSAL_PREFIX = "I cannot proceed — safety boundary violated: "`
* `build_refusal_surface(verdict) -> str | None` — pure function, no I/O.
* `violated_runtime_checkable(verdict) -> tuple[str, ...]` — lex-sorted helper.
* `is_typed_refusal(surface) -> bool` — audit helper.

`chat/runtime.py` — both the main turn path and `_stub_response`
invoke `build_refusal_surface(safety_verdict)` after the verdict is
computed. On a non-None return:

* `ChatResponse.surface` = typed refusal
* `ChatResponse.walk_surface` = unchanged (audit evidence preserved)
* `ChatResponse.articulation_surface` = unchanged (realizer evidence preserved)
* `TurnEvent.surface` = typed refusal (main path only; stub path bypasses turn_log by design)
* `runtime._last_refusal_was_typed = True` — so the next turn's
  `no_silent_correction` predicate has live evidence.

### Surface contract integrity

The runtime surface contract from CLAUDE.md says:

```
surface = articulation_surface  (selected user-facing response)
walk_surface = retained telemetry/evidence
```

Refusal changes the *selection* (`surface` no longer equals
`articulation_surface`); it does not corrupt the evidence
(`walk_surface` and `articulation_surface` retain what the runtime
would have said). An auditor reading a refusal turn sees:

* what the runtime *would have* surfaced (walk_surface / articulation),
* what it *did* surface (typed refusal),
* and *why* (safety_verdict).

This is the same audit shape as a non-refusing turn — no new contract.

## Consequences

### Positive

* **First load-bearing pack-layer behavior.** The pack-layer surface
  now has a way to actually stop the runtime from emitting bad output,
  not just label it.
* **Deterministic.** Same forced violation → byte-identical refusal
  string. Replay invariant preserved.
* **Audit-complete.** Every refusal carries the verdict and the
  preserved walk/articulation evidence. No silent refusals.
* **Bookkeeping closes the loop on `no_silent_correction`.** When the
  runtime refuses, it sets `_last_refusal_was_typed=True`, so the
  next turn's predicate has live evidence of typed refusal.
* **Cheap.** One pure function call per turn. Test suites and
  cognition eval unchanged.

### Negative / risks

* **No per-predicate refusal opt-out.** All `runtime_checkable=True`
  safety violations refuse. If a future safety pack introduces a
  predicate that should be observe-only, the surface needs a
  per-predicate `audit_only` flag. Acceptable today: the v1 safety
  pack has five boundaries and refusing on each is the right semantics.
* **Hedge injection is *not* the refusal path.** A high-confidence
  emission with low alignment score still passes through unhedged
  unless the manifold's `surface_preferences` choose to hedge. This
  is correct: hedging is a surface preference (ADR-0028), refusal is
  a safety boundary. Conflating them was rejected.
* **Stub path refusal happens but `TurnEvent` is not emitted.** Same
  pre-existing limit as ADR-0035. Audit completeness for stub paths
  is a separate ADR.

## Verification

* `tests/test_safety_refusal.py` — 20 tests covering: pure refusal
  builder (none, all-upheld, non-checkable violation, single
  violation, determinism, lex order); helpers
  (`violated_runtime_checkable`, `is_typed_refusal`); ChatRuntime
  integration (ordinary turn unchanged, forced violation emits
  refusal, walk_surface preserved, articulation_surface preserved,
  verdicts still attached, `_last_refusal_was_typed` bookkeeping,
  `TurnEvent.surface` carries the refusal); ethics violations do
  NOT trigger refusal; stub-path refusal.
* Combined pack-layer surface suite: **116 tests, all green**
  (safety pack + safety check + ethics pack + ethics check +
  turn-loop verdicts + refusal).
* CLI suites unaffected: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent_accuracy 100%, versor_closure_rate 100%
  (baseline preserved).

## Open questions deferred to a future ADR

1. **Per-predicate ethics refusal.** Pack-schema flag to opt specific
   ethics commitments into refusal once empirical violation rates are
   available.
2. **Hedge-injection as a separate surface affordance.** A
   below-threshold alignment score could prepend the manifold's hedge
   without triggering refusal. Today this is partially handled by
   the assembler's `SurfaceContext`; lifting it to a runtime-level
   decision is its own ADR.
3. **`TurnEvent` for stub paths.** Audit completeness across the
   refusal-on-stub path.
4. **Refusal telemetry sink.** A structured log emitter consumes
   refusals for operational dashboards.
5. **`core chat --show-verdicts` CLI flag.** Per-turn verdict and
   refusal printout for manual audit.
6. **Refusal-bias planner retry.** Re-articulation as a deliberate
   re-plan with refusal context threaded in. Deferred until
   evidence-threading through the planner lands.
