# ADR-0035: Turn-Loop Verdict Surfacing for SafetyCheck and EthicsCheck

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0032-safety-check-surface.md`](ADR-0032-safety-check-surface.md), [`ADR-0034-ethics-check-surface.md`](ADR-0034-ethics-check-surface.md)

## Context

ADR-0032 and ADR-0034 landed the structural surfaces — `SafetyCheck` and `EthicsCheck` — as observational, registry-of-predicates classes parallel in shape to `IdentityCheck`. Both ADRs deliberately left **auto-invocation in the turn loop** as a follow-up.

The follow-up is overdue. An observation surface that no caller invokes is a label without a verdict. `ChatRuntime` constructs both checks at startup and exposes them on `self.safety_check` / `self.ethics_check`, but no path in the turn loop calls `.check(...)`. The pack-layer audit is uniformly silent regardless of what the turn actually did.

Two scope options were on the table:

1. **Surfacing only.** Auto-invoke both checks at end-of-turn, populate contexts from whatever evidence the runtime has, attach verdicts to `ChatResponse` and `TurnEvent` for audit. No behavioral change.
2. **Surfacing + refusal.** Same as above plus typed refusal on runtime-checkable violations.

The conservative choice — option 1 — was selected. Reasoning, from the implementation discussion:

> Most context fields are `None` by default and the runtime today only has evidence for ~3 of the ~10 fields across both surfaces (versor_condition, identity_manifold hashes, alignment_score, plus the unknown-domain signal). With sparse evidence, most violations are *unobservable* at v1 — wiring refusal now would refuse on a tiny fraction of theoretical violations while letting the rest slip silently through. The right sequence is to land the invocation point, observe what evidence actually surfaces across real turns, *then* decide refusal policy with that data in hand.

CLAUDE.md's "small, load-bearing PRs with clear evidence" doctrine maps to this.

## Decision

`ChatRuntime` invokes both checks at the end of every chat turn — both the main articulation path and the `_stub_response` path. Verdicts attach to `ChatResponse` and `TurnEvent` as new optional fields. No behavioral effect; no refusal; no re-articulation; no retry.

### Invocation sites

| Path | When invoked | What populates the context |
|---|---|---|
| Main articulation path | Just before constructing `TurnEvent` | `result.final_state`, `identity_score`, `walk_surface` |
| `_stub_response` | Just before constructing the `ChatResponse` | `field_state`, fixed ungrounded signal |

Stub paths trigger exactly when grounding is insufficient — i.e., when the `disclose_limitations` commitment is most active. Surfacing verdicts there preserves the contract "every `ChatResponse` carries a `SafetyVerdict` and `EthicsVerdict`" and gives `disclose_limitations` a stable runtime-checkable signal.

### Evidence the turn loop populates today

**SafetyContext (runtime-checkable in production):**

| Field | Source | Predicate it unlocks |
|---|---|---|
| `field_state.versor_condition` | `versor_condition(final_state.F)` via an `_FieldStateWithVersor` adapter | `preserve_versor_closure` |
| `last_refusal_was_typed` | `runtime._last_refusal_was_typed` (default `True`; reserved for future typed-refusal bookkeeping) | `no_silent_correction` |
| `identity_manifold_hash_before` | `runtime._identity_manifold_hash` — captured once at startup; manifold is never mutated | `no_identity_override` |
| `identity_manifold_hash_after` | recomputed at end-of-turn — equal by construction | `no_identity_override` |

**EthicsContext (runtime-checkable in production):**

| Field | Source | Predicate it unlocks |
|---|---|---|
| `alignment_score` | `IdentityScore.alignment` (zero on stub path) | `acknowledge_uncertainty` |
| `hedge_threshold_soft` | `identity_manifold.surface_preferences.hedge_threshold_soft` | `acknowledge_uncertainty` |
| `hedge_emitted` | `_surface_contains_hedge(walk_surface, identity_manifold)` — substring check against the manifold's hedge phrases (strong/soft/qualifier + per-axis variants) | `acknowledge_uncertainty` |
| `grounded_in_evidence` | `walk_surface != _UNKNOWN_DOMAIN_SURFACE` | `disclose_limitations` |
| `disclosure_emitted` | `walk_surface == _UNKNOWN_DOMAIN_SURFACE` (the inverse) | `disclose_limitations` |

**Not yet populated (predicates default to `runtime_checkable=False, upheld=True`):**

- `cited_source_shas` / `allowed_source_shas` — citation pipeline isn't wired into chat turns.
- `high_stakes_topic` / `recommended_human_review` — no high-stakes classifier.
- `prescribed_single_answer` / `presented_options_count` — no prescriptiveness classifier.

These fields surface in verdicts as `runtime_checkable=False` per the ADR-0032/0034 honest-reporting discipline. As classifiers land (future ADRs), the corresponding predicates become checkable without changing the surface contract.

### Hash-of-manifold helper

`_hash_identity_manifold(manifold)` produces a deterministic SHA-256 of the load-bearing manifold fields:

```python
payload = {
    "value_axes": [{"axis_id", "name", "direction", "weight"} for axis in manifold.value_axes],
    "boundary_ids": sorted(manifold.boundary_ids),
    "alignment_threshold": manifold.alignment_threshold,
}
sha256(canonical_json(payload))
```

Captured once at `ChatRuntime.__init__` and recomputed each turn. Because the runtime never mutates the manifold post-construction, before/after hashes are equal by construction — and that *is* the correct semantics for `no_identity_override`. An unequal hash would indicate the specific failure mode the predicate exists to surface.

### Surface contract changes

New optional fields, defaulting to `None`:

- `ChatResponse.safety_verdict: object` — `SafetyVerdict` on every non-error path; `None` only if a future path constructs `ChatResponse` directly without invoking the surface.
- `ChatResponse.ethics_verdict: object` — `EthicsVerdict` symmetric.
- `TurnEvent.safety_verdict: object` — present on every main-path turn; `None` on stub paths (which bypass `turn_log` by existing design).
- `TurnEvent.ethics_verdict: object` — symmetric.

The fields are typed as `object` to avoid forcing `core/physics/identity.py` and `chat/runtime.py` to import the pack layer at module-resolution time — the underlying types are `packs.safety.check.SafetyVerdict` and `packs.ethics.check.EthicsVerdict`. Callers downcast at the use site.

### What this ADR explicitly does NOT do

- **No refusal.** A runtime-checkable violation produces an audit verdict; the response is unchanged.
- **No re-articulation.** No retry path, no hedge injection on `acknowledge_uncertainty` violation, no escalation on `disclose_limitations` violation.
- **No logging integration.** Verdicts are attached to the data structures; emitting them to logs / telemetry is a downstream decision.
- **No CLI surface.** No `core chat --show-verdicts` flag yet.
- **No GenerationResult coupling.** Verdicts live on the chat-turn-shaped objects (`ChatResponse`, `TurnEvent`), not on `GenerationResult` — they belong to the turn, not the generation pass.
- **No cross-surface verdict bundle.** Three separate verdicts (identity / safety / ethics) per turn. A unified type is convenience sugar deferred to a future ADR.

## Consequences

### Positive

- **Audit no longer silent.** Every chat turn now produces three orthogonal verdicts (identity score + safety verdict + ethics verdict). An operator inspecting `runtime.turn_log[-1]` sees what each surface concluded.
- **Honest evidence-availability gradient.** Predicates report `runtime_checkable=False` where the runtime has no evidence, `runtime_checkable=True` where it does. Future ADRs that wire in more evidence (high-stakes classifier, citation pipeline, prescriptiveness detector) increase the checkable count without changing the surface contract.
- **Surface contract uniform across stub and main paths.** `disclose_limitations` is the first commitment where stub paths matter — and they correctly fire as `upheld=True` because stubs emit the unknown-domain marker.
- **Forward-compatible with refusal.** When the refusal-wiring ADR lands, the call site already exists; only the policy hook changes.
- **Cheap.** Auto-invocation is two predicate-registry passes per turn. No measurable cost on the smoke/cognition/runtime suites.

### Negative / risks

- **`_FieldStateWithVersor` adapter is a small piece of glue.** `FieldState` does not expose `versor_condition` as an attribute, so the SafetyCheck predicate cannot read it via `getattr` directly. The adapter is a frozen dataclass with one field. Mitigated: the adapter is one local class; if `FieldState` later carries the value natively, the adapter becomes a trivial removal.
- **`hedge_emitted` is substring-based.** A more rigorous detector (token-aware, hedge-phrase registry separate from the manifold) would catch edge cases. Acceptable at v1 because false negatives surface as `acknowledge_uncertainty` violations in audit — exactly where audit is supposed to direct attention — rather than passing silently.
- **Stub path does not append to `turn_log`.** Pre-existing behavior. The verdict is on the `ChatResponse` but the `TurnEvent` does not exist for stub turns. Documented as a known limit; a future ADR could append `TurnEvent` records for stub paths too if audit completeness becomes a priority.

## Verification

- `tests/test_turn_loop_verdicts.py` — 14 tests covering: verdicts attached to `ChatResponse` / `TurnEvent`; runtime-checkability of `preserve_versor_closure`, `no_identity_override`, `no_silent_correction`, `acknowledge_uncertainty`, `disclose_limitations`; `no_manipulation` honestly remaining non-runtime-checkable; hash determinism + before/after equality; hedge-detection happy and edge cases.
- Combined pack-layer test surface (loaders + checks + turn-loop) is **122 tests, all green**.
- CLI suites unaffected: smoke 67, cognition 121, teaching 17, runtime 19.

## Open questions deferred to a future ADR

1. **Refusal / re-articulation policy.** What does the runtime do with a violation? Refuse? Hedge? Log only? Per-pack policy? Per-predicate policy? Now that real verdict data flows, this can be decided empirically.
2. **TurnEvent for stub paths.** Should stub turns append a `TurnEvent` so audit completeness covers the entire turn stream?
3. **Verdict telemetry / logging.** A structured log sink that consumes verdicts is the next operational concern.
4. **CLI audit flag.** `core chat --show-verdicts` would print per-turn verdict summaries.
5. **Unified verdict bundle type.** A `TurnVerdicts` record grouping identity + safety + ethics for callers that want a single object.
