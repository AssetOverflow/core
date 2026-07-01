# ADR-0028: Identity Surface Wiring — Pack-Driven Hedge & Claim Strength

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`identity_packs.md`](../identity_packs.md), [`ADR-0027-identity-packs.md`](ADR-0027-identity-packs.md), [`runtime_contracts.md`](../runtime_contracts.md)

## Context

ADR-0027 landed swappable identity packs and wired them into the runtime through `chat/runtime.py::ChatRuntime`. The identity manifold is now load-bearing in two ways: `PersonaMotor.from_identity_manifold` biases every field walk, and `IdentityCheck.check()` produces an `IdentityScore` whose `alignment` field is passed to the surface assembler as `SurfaceContext.identity_alignment`.

But the *surface* effect of swapping packs is invisible. The pre-ADR-0028 `_apply_hedge` consults only the alignment scalar:

```python
if alignment < 0.4:  return f"It seems that {surface}"
if alignment < 0.5:  return f"Perhaps {surface}"
return surface
```

So `default_general_v1` and `precision_first_v1` on the same prompt produce the same hedge decision — both manifolds get hit with similar alignment scores by ordinary input. The pack swap changes upstream scoring and motor bias but does not change the assembled string, which is the user-visible artifact.

This is the "known limit 1" recorded in [`identity_packs.md`](../identity_packs.md): *"Identity does not yet visibly differentiate articulation at the realizer."* ADR-0028 closes that gap.

## Decision

The pack carries surface-shaping preferences alongside its axes. The assembler consults those preferences at the same site it currently consults `alignment`. No upstream pipeline code changes. No motor / field-bias / generation-walk code changes. No CLAUDE.md invariant is touched: the change is deterministic, surface-only, contains no sampling, no normalization, no hot-path repair.

### Schema extension (pack v1)

A new optional `surface_preferences` block on the identity pack:

```json
"surface_preferences": {
  "hedge_threshold_strong": 0.40,
  "hedge_threshold_soft": 0.50,
  "preferred_hedge_strong": "It seems that",
  "preferred_hedge_soft": "Perhaps",
  "claim_strength": "balanced",
  "qualified_band_high": 0.75,
  "preferred_qualifier": "In some cases,"
}
```

The block is **optional** — absent it, the loader supplies defaults that reproduce pre-ADR-0028 behavior byte-for-byte. This keeps the schema bump backwards-compatible at the *pack format* level even though every pack's canonical SHA changes when the block is added.

### Surface algorithm

Three nested bands ordered by descending hedge strength. Given an alignment scalar `a` and pack preferences `prefs`:

1. **Strong hedge:** `a < prefs.hedge_threshold_strong` → prepend `prefs.preferred_hedge_strong`.
2. **Soft hedge:** `a < prefs.hedge_threshold_soft` → prepend `prefs.preferred_hedge_soft`.
3. **Marginal band:** `prefs.hedge_threshold_soft <= a < prefs.qualified_band_high`. Behavior depends on `claim_strength`:
   - `"qualified"` → prepend `prefs.preferred_qualifier`.
   - `"affirmative"` → leave bare.
   - `"balanced"` → leave bare.
4. **Above marginal band:** `a >= prefs.qualified_band_high` → leave bare regardless of `claim_strength`.

The thresholds must satisfy `hedge_threshold_strong <= hedge_threshold_soft <= qualified_band_high`; the loader enforces this ordering.

### Three shipping pack profiles

| Pack | strong | soft | qual_high | claim_strength | Hedge phrases |
|---|---|---|---|---|---|
| `default_general_v1` | 0.40 | 0.50 | 0.75 | balanced | "It seems that" / "Perhaps" / qualifier unused |
| `precision_first_v1` | 0.55 | 0.70 | 0.85 | qualified | "Arguably," / "In some cases," / "Under certain conditions," |
| `generosity_first_v1` | 0.20 | 0.30 | 0.50 | affirmative | "It seems that" / "Perhaps" / qualifier unused |

Result: at `alignment = 0.45`, default and precision both hedge but with different phrases; generosity leaves bare. At `alignment = 0.80`, precision qualifies; default and generosity leave bare. Visible divergence on identical trajectories — proven by `tests/test_identity_surface_divergence.py`.

### Implementation

- `core/physics/identity.py`: new `SurfacePreferences` dataclass; `IdentityManifold` gains a `surface_preferences: SurfacePreferences = SurfacePreferences()` field with defaults that reproduce pre-ADR behavior.
- `packs/identity/loader.py`: `_build_surface_preferences()` parses and bounds-checks the new block; missing block uses defaults; threshold ordering enforced; `claim_strength` constrained to `{"balanced", "qualified", "affirmative"}`.
- `generate/surface.py`: `SurfaceContext` gains seven new fields (defaults preserve pre-ADR behavior); `_apply_hedge` takes the full context, not just a float, and implements the four-band algorithm above; the legacy module-level `HEDGE_STRONG_THRESHOLD` / `HEDGE_SOFT_THRESHOLD` constants are retained as the default values for `SurfaceContext` so existing imports still resolve.
- `chat/runtime.py::ChatRuntime._build_surface_context`: lifts `self.identity_manifold.surface_preferences` into the constructed `SurfaceContext`.
- `packs/identity/*.json`: three v1 packs gain `surface_preferences` blocks tuned to their roles.
- `scripts/ratify_identity_packs.py`: no change needed; runs again idempotently. Pack body changes → `pack_source_sha` changes → MasteryReport regenerated → companion `.mastery_report.json` rewritten → embedded `mastery_report_sha256` updated.

### Backward compatibility

- **Pack format.** Packs without `surface_preferences` continue to load and produce pre-ADR behavior.
- **In-code `SurfaceContext()` construction.** Callers who instantiate `SurfaceContext()` directly (without going through `_build_surface_context`) get default values that reproduce pre-ADR behavior. The legacy module-level constants `HEDGE_STRONG_THRESHOLD = 0.4` and `HEDGE_SOFT_THRESHOLD = 0.5` are preserved as the defaults for those fields, so any test or code that imports those names continues to work.
- **Re-ratification cost.** The three v1 packs are re-ratified once when the new block is added. Their MasteryReport SHAs change (this is expected). The previous SHAs are recorded in ADR-0027 §"Phase 5"; the new SHAs are recorded in `docs/identity_packs.md` §"Shipping packs (v1)" and in the ADR-0027 phase table.

## Consequences

### Positive

- **The identity claim is now visibly load-bearing at the surface layer.** Pack swap → different assembled string on the same prompt. The `tests/test_identity_surface_divergence.py::TestPackSwapDivergence::test_same_alignment_different_surfaces` asserts this explicitly.
- **The realizer remains deterministic.** No new operator, no normalization, no sampling, no clock, no PID, no hash-randomization. Same `(prompt, alignment, pack)` triple → same surface bytes.
- **The pack format remains optional-block backward-compatible.** Authors writing new packs may omit `surface_preferences` if defaults suit them.
- **The divergence test makes regressions loud.** Any future change that re-routes `_apply_hedge` or strips the SurfaceContext fields will fail `test_same_alignment_different_surfaces` immediately.

### Negative / risks

- **Schema bump invalidates the three Phase-5 MasteryReports.** Cost paid once; re-ratification handled by the existing idempotent script. The previously-ratified SHAs from 2026-05-17 are superseded.
- **English-only differentiation.** `_assemble_he` and `_assemble_grc` do not currently consult `SurfaceContext` for hedge/claim-strength shaping; they call neither `_apply_hedge` nor anything sensitive to the new fields. Per-language hedging is a future concern; identity packs are language-neutral, so the same preferences will eventually drive the same logic in `_assemble_he` and `_assemble_grc` once those gain hedge support.
- **The marginal-band qualifier only fires for `claim_strength="qualified"`.** A future axis profile that wants to *expand* claims in the marginal band (e.g., add "Indeed," before a confident assertion) would require either a new `claim_strength` value or a separate field. Out of scope for ADR-0028.
- **`SurfaceContext` is now bigger.** Seven new fields. The dataclass remains frozen+slots so the cost is small, but every construction site (including tests that build a `SurfaceContext` directly) must accept that the defaults are non-trivial. We rely on the defaults reproducing pre-ADR behavior; the cognition / runtime / smoke suites verify this.

### Scope limits (explicit non-goals for this ADR)

- No depth-language (Hebrew, Koine Greek) hedging. Future work; new ADR.
- No `scope`, `qualification_level`, `modal_style`, or `hedge_preferences` (list) fields from the eval-layer YAMLs. Future work.
- No surface-side differentiation by axis-id (e.g., "the truthfulness axis is dominant → use evidential phrasing"). Future work, and likely requires a richer score-decomposition surface than today's scalar alignment.
- No new CLI verb. `core chat --identity <pack_id>` already exists.

## Verification

This ADR is satisfied when:
- `tests/test_identity_surface_divergence.py` passes, in particular `TestPackSwapDivergence::test_same_alignment_different_surfaces`.
- All three v1 packs ratify cleanly under the v1 schema with the `surface_preferences` block and load in production mode (`require_ratified=None`).
- The cognition / runtime / smoke / formation / teaching suites are green at the same revision.
- `tests/test_identity_packs.py` continues to pass (loader bounds checks, runtime wiring, ratification-script idempotency, tamper detection).

## Governance Cross-Reference (ADR-0225)

This identity surface wiring ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: surface context shaping (`chat/surface.py`) is deterministic and immutable under user interaction.
- Versor closure: surface shaping transforms do not violate geometric or manifold invariants (`versor_condition(F) < 1e-6`).
- Reconstruction-over-storage: surface preferences are derived at runtime from pack manifests.
- Replay-equivalence: exact surface string generation is reproducible across identical execution traces.
- Mutation standing: surface preference blocks are proposal-only until ratified.
