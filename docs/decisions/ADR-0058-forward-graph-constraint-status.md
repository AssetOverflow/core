# ADR-0058 — `forward_graph_constraint`: Engaged but Inert on Today's Cognition Lane

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0046](./ADR-0046-forward-graph-constraint.md) introduced
`build_graph_constraint` — the function that converts a
`PropositionGraph` into an `AdmissibilityRegion` *before* `generate()`
runs.  [ADR-0047](./ADR-0047-wire-forward-graph-constraint.md) wired
it into the chat hot path behind an opt-in
`RuntimeConfig.forward_graph_constraint` flag (default `False`) and
ran the A/B characterisation on the 13-case public cognition split:

| Metric                                 | Flag OFF | Flag ON | Δ |
|----------------------------------------|----------|---------|---|
| `intent_accuracy`                      | 100.0 %  | 100.0 % | 0 |
| `surface_groundedness`                 | 15.4 %   | 15.4 %  | 0 |
| `term_capture_rate`                    | 0.0 %    | 0.0 %   | 0 |
| `versor_closure_rate`                  | 100.0 %  | 100.0 % | 0 |
| Cases producing non-trivial constraint | n/a      | 6 / 13  | — |

The architectural finding: **narrowing which tokens the walk may visit
did not change which surface gets emitted on this lane.**  The
surface-grounding gap lived downstream of propagation.  That scoping
drove the next four ADRs — [0048](./ADR-0048-pack-grounded-surface.md)
through [0053](./ADR-0053-cognition-lane-closure.md) — which closed
the cognition public split at **100.0% surface_groundedness / 91.7%
term_capture_rate** by working in the realizer / surface-assembly
layer, not in propagation.

This ADR closes the loop on ADR-0047's open question by **deciding
not to flip the flag's default**, and by promoting the null-lift
observation from a historical A/B reading to a regression-tested
invariant.

---

## Decision

1. **`forward_graph_constraint` remains opt-in with default `False`.**
   No production identity pack — including `precision_first_v1`
   (which would be the natural home for a precision-narrowing
   structural constraint) — opts into the flag.

2. **No `runtime_preferences` block is added to identity packs.**  No
   path is opened today for identity packs to override
   `RuntimeConfig` fields.  Such a path would require:

   - A new schema field in pack JSON.
   - Re-ratification of every identity pack (mastery seal).
   - Loader work to expose runtime preferences.
   - `ChatRuntime` composition work to merge pack prefs into the
     active `RuntimeConfig` at boot.

   Doing that infrastructure for an `engaged_but_inert` feature
   would let the wiring lead the lift — and lock in
   pack-to-runtime coupling at an abstraction level we may regret
   when the constraint *does* matter downstream.

3. **The ADR-0047 null-lift finding becomes a CI-enforced invariant.**
   `tests/test_forward_graph_constraint_null_lift.py` runs the full
   cognition public split twice — flag OFF vs ON — and asserts every
   watched metric is pair-wise identical.  If a downstream change in
   the realizer / surface-assembly layer ever moves a metric on the
   flag flip, this test fails and the architectural assumption that
   the constraint is observably inert on this lane gets re-examined
   as a deliberate transition rather than silent drift.

---

## Why this is the right call today

- **The lift hasn't arrived.**  ADR-0047 measured 0 Δ on every public-
  split metric with the flag flipped.  The 6/13 cases that produced a
  non-trivial constraint label did not produce a different surface.
  Opting `precision_first_v1` into the flag today would not move any
  observable cognition-lane number.
- **The infrastructure cost is real.**  Pack-to-runtime preference
  composition is a load-bearing architectural decision, not a
  one-line wiring change.  When the lift arrives — when constraint-
  aware realizer logic exists downstream — that's the right context
  in which to design the composition path, because the requirements
  will be clearer.
- **The invariant test is real epistemic work.**  Pinning the null-
  lift as CI-enforced turns "observed once during ADR-0047" into
  "structurally true across the codebase's evolution."  If
  constraint-aware realizer logic later moves a metric on the flag
  flip, the test surfaces it as the transition it is.

---

## What is and isn't open

### What this ADR does not foreclose

- A future ADR that wires constraint-aware behaviour into the
  realizer or surface-assembly layer.  Once that work exists, the
  null-lift test in this ADR will fail (intentionally), and a
  follow-up ADR will document the transition + design the
  pack→runtime composition path.
- Operator opt-in via `RuntimeConfig(forward_graph_constraint=True)`
  on a per-call or per-deployment basis remains available; this ADR
  only addresses the *default* and the *pack-level* configuration.

### What this ADR explicitly closes

- The ADR-0047 follow-up question "should this become default-on or
  pack-opt-in?" is answered with **neither, yet**.
- The question "should identity packs carry runtime config
  preferences?" is deferred until at least one such preference has
  demonstrated lift.

---

## Verification

```
tests/test_forward_graph_constraint_wiring.py        5 passed   (ADR-0047 wiring)
tests/test_forward_graph_constraint_null_lift.py     2 passed   (ADR-0058 invariant)

  test_cognition_lane_metrics_identical_with_flag_flipped
    Runs the public cognition split twice (flag OFF, flag ON) and
    asserts intent_accuracy / surface_groundedness / term_capture_rate /
    versor_closure_rate are pair-wise identical.  ~3s wall-time.

  test_default_config_keeps_flag_off
    RuntimeConfig().forward_graph_constraint is False — the
    production-default contract.
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`)
is unaffected: this ADR adds no runtime behaviour; it only adds a
regression test and a doctrinal decision.

---

## Cross-References

- [ADR-0046](./ADR-0046-forward-graph-constraint.md) — the constraint
  primitive (`build_graph_constraint`).
- [ADR-0047](./ADR-0047-wire-forward-graph-constraint.md) — the
  hot-path wiring + opt-in flag + original A/B characterisation.
- [ADR-0048](./ADR-0048-pack-grounded-surface.md) through
  [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the realizer /
  surface-assembly work that produced the actual cognition-lane lift,
  validating that the gap lived downstream of propagation.
- [ADR-0027](./ADR-0027-identity-packs.md) — the identity-pack
  contract whose schema this ADR explicitly chooses not to extend.
