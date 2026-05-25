# W-015 Investigation: session/context.py unitize root cause

## Question

What is the source of the versor-condition drift that `session/context.py:236`
corrects, and which of the three resolution paths applies?

## Evidence collected

Instrumented `_anchor_pull` to record `versor_condition(pulled_F)` immediately
before `unitize_versor(pulled_F)`. Ran `tests/test_session_coherence.py`,
`tests/test_achat.py`, `tests/test_chat_runtime.py`, and
`tests/test_warmed_session_lane.py` (4,138 samples total across 25 tests).

| Band | Count | % |
|---|---|---|
| < 1e-6 (invariant satisfied — unitize is near no-op) | 1,912 | 46% |
| [1e-6, 1e-3) (small drift) | 0 | 0% |
| [1e-3, 1) (large violation) | 2,201 | 53% |
| ≥ 1 (massive violation) | 25 | 1% |

**Distribution is strictly bimodal**: no samples fall in [1e-6, 1e-3). The
maximum observed pre-unitize versor_condition is **38.58**; median is **0.19**
across the dirty half.

The 1,912 "clean" samples correspond to calls where `_slerp_toward`'s near-
parallel fallback fires (`theta < 1e-6`), i.e., the field has not drifted from
the anchor — `result ≈ (1-α)·F + α·target ≈ F`, so vc is preserved. The 2,226
dirty samples are turns with non-negligible field-to-anchor angle.

## Upstream trace

Call chain leading to the unitize:

```
SessionContext.respond()                  session/context.py:321
  └→ generate(self.state, ...)            generate/stream.py (generate())
       └→ GenerationResult(
            final_state=_close_final_state(current)  stream.py:641
          )                               # unitizes F → vc < 1e-6
  └→ SessionContext.finalize_turn(result) session/context.py:337
       └→ _hemisphere_consistent_field(result.final_state)  context.py:272
            # negates F if wrong hemisphere — vc-preserving
       └→ _anchor_pull(oriented_state)    context.py:273
            └→ _slerp_toward(field_state.F,
                             self._anchor_field,
                             _ANCHOR_PULL_ALPHA)      context.py:235
                 # ← SOURCE OF VIOLATION
            └→ unitize_versor(pulled_F)               context.py:236
                 # ← THE SITE UNDER INVESTIGATION
```

`_close_final_state` (`generate/stream.py:132–140`) calls `unitize_versor` and
ensures `result.final_state.F` satisfies vc < 1e-6 on entry. The hemisphere
flip preserves vc. **The sole source of the violation is `_slerp_toward`.**

`_slerp_toward` (`session/context.py:38–64`) performs spherical linear
interpolation (slerp) on the 32-component multivector representation. Slerp
traces a geodesic on **S³¹** (the unit sphere in 32D), not on the **Spin
sub-manifold** embedded within Cl(4,1). For any non-negligible angle θ between
F and anchor, the slerp output is a point on S³¹ that is not a proper versor —
the versor condition `|v·rev(v) − 1|` can diverge far from zero. The strict
bimodal distribution (no samples in [1e-6, 1e-3)) confirms this: either θ ≈ 0
(clean) or the slerp leaves the versor manifold dramatically (dirty).

This pattern is explicitly noted at `generate/stream.py:218–219`:

> *"by construction (versor_condition stays < 1e-6), unlike a linear blend
> `weight·V + (1-weight)·identity` which violates closure."*

Stream.py avoids linear blending for exactly this reason. `_slerp_toward` is
the same category of error applied to an anchor-pull operation.

## Cross-check: field/operators.py:_unitize_f32

`field/operators.py:69` defines `_unitize_f32`, used by `GraphDiffusionOperator`
and `ConstraintCorrectionOperator` to close blend-then-unitize steps in the
field propagation pulse loop. This is an **independent concern**: it lives
inside operator-pipeline boundaries (L1 audit flagged it as pulse-only
normalization), whereas `session/context.py`'s site is at the session
finalization boundary. The two sites share the same class of error (blending on
the wrong manifold) but operate at different layers and have different fix paths.

## Verdict

**(c) Upstream construction violation.** The drift is not small and consistent
(ruling out (a)) and is not a near-no-op (ruling out (b)). The source is
`_slerp_toward` at `session/context.py:38–64`: it interpolates on S³¹ rather
than on the Spin group, producing off-manifold state with vc up to 38.58 for
non-negligible field-to-anchor angles.

## Recommended next action

Replace `_slerp_toward` with proper **rotor geodesic interpolation** via the
Lie group exponential map:

```
R_rel = R_anchor · reverse(R_current)
R_step = exp(α · log(R_rel))
result  = R_step · R_current
```

This stays on the versor manifold by construction (same principle as
`rotor_power` used at `generate/stream.py:220`), eliminating the need for
`unitize_versor` in `_anchor_pull`. The fix lives entirely in `session/context.py`
(replace `_slerp_toward` + remove the `unitize_versor` call). Sized as a small
focused PR; a test asserting `versor_condition(_anchor_pull(s).F) < 1e-6`
without the closing unitize would verify the fix without altering the invariant.
`algebra/versor.py` already exposes `versor_apply` and `reverse`; `rotor_power`
lives in `generate/stream.py` — the implementation is straightforward once the
operator algebra is right.
