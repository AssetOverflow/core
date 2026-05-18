# ADR-0038: Hedge Injection as a Runtime-Level Affordance

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0028-surface-preferences.md`](../decisions), [`ADR-0036-safety-refusal-policy.md`](ADR-0036-safety-refusal-policy.md), [`ADR-0037-per-predicate-ethics-refusal.md`](ADR-0037-per-predicate-ethics-refusal.md)

## Context

ADR-0036 chose typed refusal over hedge injection for safety violations
because conflating refusal with hedging would blur audit:

> Hedge injection would blur the boundary between hedging
> (alignment-score driven) and refusing (predicate-driven). The same
> surface change could mean two different things. Audit becomes
> ambiguous.

That choice was correct *for refusal*.  But it left an open question:
once `EthicsCheck` predicates fire runtime-checkably for low alignment
(`acknowledge_uncertainty`) or ungrounded scope (`disclose_limitations`),
a deployment might want **softer remediation** than full refusal —
some way to *qualify* the surface without replacing it.

ADR-0037 introduced `refusal_commitments` as the opt-in for per-predicate
escalation to refusal.  This ADR introduces its sibling
`hedge_commitments`: opt-in for runtime-level hedge **prepend**.

## Decision

Add an optional `hedge_commitments` field to the ethics pack JSON
schema.  Each entry must be a declared `commitment_id`.  When *any*
runtime-checkable violation of a commitment in `hedge_commitments`
fires this turn, the runtime prepends the manifold's preferred hedge
phrase (`preferred_hedge_soft`, falling back to
`preferred_hedge_strong`) to `ChatResponse.surface`.

### Mutual exclusion with refusal

A commitment **cannot** appear in both `refusal_commitments` and
`hedge_commitments`.  This is enforced at load time:

```python
overlap = refusal & hedge
if overlap:
    raise EthicsPackError("commitments cannot appear in both ...")
```

The two remediations are escalation siblings, not stackable layers.
Pack authors pick one per commitment: hedge (soft) or refuse (hard).

### Refusal supersedes hedge in code path order

Even though pack schema forbids per-commitment overlap, the runtime
still gives refusal priority globally: if **any** safety boundary or
opted-in ethics commitment fires refusal, the surface is the typed
refusal — hedge injection is skipped for the turn.  This preserves
the invariant "refusal is total."

### Stub path does not hedge

The stub-path surface (`_UNKNOWN_DOMAIN_SURFACE = "I don't know —
insufficient grounding for that yet."`) is already a disclosure
surface.  Prepending a hedge ("Perhaps I don't know — …") would read
as a confused double-disclosure.  Hedge injection runs **only on the
main articulation path**.  Stub-path refusal *does* still fire (per
ADR-0036) because refusal is a hard stop, not a qualifier.

### Evidence preservation

Same discipline as ADR-0036: hedge changes only the user-facing
`surface` field.  `walk_surface` (token-walk evidence) and
`articulation_surface` (realizer output) are preserved unchanged.
An auditor reading a hedged turn sees:

* original surface (walk_surface / articulation_surface),
* hedged user-facing surface (with prepended hedge),
* ethics_verdict (with the violating commitment).

### Idempotent on prefix

`inject_hedge()` is idempotent: if the surface already begins with
the hedge phrase (case-insensitive match), no double-prepend occurs.
This is a defensive property — the assembler's existing
`SurfaceContext`-driven hedge logic (ADR-0028) may have already
hedged the surface, and runtime injection should not duplicate.

### No effect on refusal bookkeeping

Hedge injection does **not** set `_last_refusal_was_typed`.  Hedging
is not a refusal — the `no_silent_correction` safety predicate cares
about typed refusals specifically, and a hedge should not be miscounted
as one.

## Consequences

### Positive

* **Soft remediation channel.**  A medical-domain pack can opt
  `acknowledge_uncertainty` into hedging without committing to full
  refusal.  Deployment authors get a middle tier between audit-only
  and refuse.
* **Schema-enforced mutual exclusion.**  Load-time error makes it
  impossible to ship a pack where the same commitment claims both
  remediations.
* **Runtime path stays minimal.**  Three helper functions
  (`should_inject_hedge`, `build_hedge_prefix`, `inject_hedge`), all
  pure.  ChatRuntime adds a single conditional after the refusal
  branch.
* **Evidence preserved.**  Same audit discipline as refusal: original
  surfaces retained on the response and turn event.
* **Backward compatible.**  Default pack ships `hedge_commitments: []`;
  no behavior change for unmodified deployments.

### Negative / risks

* **Hedge phrase source is the identity manifold, not the ethics pack.**
  This means swapping ethics packs while keeping identity packs fixed
  produces the same hedge phrasing.  Acceptable today: the manifold's
  `surface_preferences` is the canonical hedge home (ADR-0028).  A
  future ADR could let ethics packs override phrasing per commitment.
* **Hedge runs only on main path.**  Stub-path hedge would be a
  double-disclosure.  Tests gate runtime-end-to-end hedge assertions
  on `rt.turn_log` populated.
* **Idempotent-on-prefix means assembler hedges suppress runtime
  hedges.**  Correct (no double-hedge), but it means the *signal* of
  "did the runtime inject this hedge or did the assembler?" is lost
  from the surface alone.  Audit consumers should rely on the
  ethics_verdict, not on the surface, to determine whether the
  injection path fired.
* **Ratification round-trip on schema change.**  Same cost as
  ADR-0037: adding `hedge_commitments` to the default pack required
  re-ratifying its mastery report.

## Verification

* `tests/test_hedge_injection.py` — 22 tests covering: loader bounds
  (empty default, unknown id rejected, mutual exclusion rejected,
  split-allocation OK); pure helpers (`should_inject_hedge` with
  pack/verdict/opt-in/evidence combinations; `build_hedge_prefix`
  with default manifold + None; `inject_hedge` happy path, empty
  prefix, empty surface, idempotent on prefix, case-insensitive
  idempotency); ChatRuntime integration (default pack does not
  inject; opt-in pack injects on violation; walk_surface preserved;
  refusal supersedes hedge; hedge does not flip
  `_last_refusal_was_typed`).
* Combined pack-layer suite: **154 tests, all green** (safety pack +
  safety check + ethics pack + ethics check + turn-loop verdicts +
  safety refusal + ethics refusal opt-in + hedge injection).
* CLI suites unchanged: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent_accuracy 100%, versor_closure_rate
  100% — baseline preserved.

## Open questions deferred to a future ADR

1. **Per-commitment hedge phrases sourced from the ethics pack.**
   Today the manifold owns hedge phrasing.  A future commitment-keyed
   override would let ethics packs say "for `defer_high_stakes_to_human_review`,
   use *'Before proceeding,'* instead of *'Perhaps'*."
2. **Hedge strength tiers.**  Today a single hedge fires regardless
   of how many commitments violated.  A pack could opt commitments
   into specific strength tiers (`hedge_soft` vs `hedge_strong`).
3. **Verdict surface for "was hedge injected this turn."**  Today
   only the ethics_verdict carries the signal; downstream consumers
   inferring "hedge fired" must inspect both the verdict and the
   prefix.  A `hedge_injected: bool` field on `ChatResponse` /
   `TurnEvent` would make audit simpler.
4. **Stub-path soft disclosure with hedge.**  The current "I don't
   know — insufficient grounding" surface is fixed.  A pack might
   want to inject domain-specific disclosure phrasing on stub.
   Deferred until packs need it.
5. **Interaction with assembler hedges (ADR-0028).**  Today
   idempotent-on-prefix prevents double-hedging; a future ADR could
   make the relationship explicit (e.g., assembler is responsible
   for alignment-score-driven hedges; runtime is responsible for
   ethics-violation-driven hedges; never both fire on the same turn).
