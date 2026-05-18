# Identity Packs — Reference

**Status:** Operational reference doctrine. Update when pack format, loader contract, or CLI flag semantics change.
**Last updated:** 2026-05-17
**Companion docs:** [`decisions/ADR-0027-identity-packs.md`](decisions/ADR-0027-identity-packs.md), [`teaching_order.md`](teaching_order.md), [`runtime_contracts.md`](runtime_contracts.md)

## What an identity pack is

An identity pack is the on-disk, content-addressed representation of an `IdentityManifold`. At runtime startup, CORE loads exactly one identity pack and uses it to construct the manifold that drives `PersonaMotor.from_identity_manifold()` and `IdentityCheck`. Replacing the pack replaces the model's identity surface without touching code.

Identity packs sit alongside language packs in the trust hierarchy:
- **Language packs** (`packs/en/`, `packs/grc/`, `packs/he/`, …) — what CORE *speaks*.
- **Identity packs** (`packs/identity/<pack_id>.json`) — *who* CORE is while speaking.
- **Safety packs** (future, `packs/identity_safety/`) — what CORE will *never* be, regardless of identity pack.

## Pack format (v1)

A single JSON file. Strings, ints, bools, lists, dicts only — same canonical-JSON discipline as the formation pipeline (no floats embedded in identifying fields; numeric direction vectors are floats but their canonical position in the file is fixed).

```json
{
  "pack_id": "default_general_v1",
  "version": "1.0.0",
  "description": "Balanced general identity. Default shipping pack.",
  "schema_version": "1.0.0",
  "mastery_report_sha256": "",
  "alignment_threshold": 0.45,
  "boundary_ids": [
    "no_fabricated_source",
    "no_hot_path_repair"
  ],
  "value_axes": [
    {
      "axis_id": "truthfulness",
      "name": "truthfulness",
      "direction": [1.0, 0.0, 0.0],
      "weight": 1.0,
      "theological_note": "Truth is treated as a fixed value axis, not a prompt preference."
    },
    {
      "axis_id": "coherence",
      "name": "coherence",
      "direction": [0.0, 1.0, 0.0],
      "weight": 1.0,
      "theological_note": "Operations must preserve field coherence under propagation."
    },
    {
      "axis_id": "reverence",
      "name": "reverence",
      "direction": [0.0, 0.0, 1.0],
      "weight": 1.0,
      "theological_note": "Depth-language handling remains bounded by source structure."
    }
  ]
}
```

### Field semantics

| Field | Required | Meaning |
|---|---|---|
| `pack_id` | yes | Unique identifier. Convention: `<slug>_v<major>`. |
| `version` | yes | Semver. Bumping `major` produces a new `pack_id`. |
| `description` | yes | Human-facing one-liner. Surfaces in `core pulse --list-identity-packs`. |
| `schema_version` | yes | Format version. Currently `"1.0.0"`. |
| `surface_preferences` | no | Pack-supplied surface hedge / claim-strength shaping (ADR-0028). Defaults preserve pre-ADR behavior. See §"Surface preferences" below. |
| `mastery_report_sha256` | no | SHA of the companion `<pack_id>.mastery_report.json`. Empty for unratified development packs; production deployments refuse to load packs with empty values. |
| `alignment_threshold` | yes | Float in [0, 1]. Passed to `IdentityManifold.alignment_threshold`. |
| `boundary_ids` | yes | List of boundary identifiers. Mirrors `IdentityManifold.boundary_ids`. |
| `value_axes` | yes | List of ≥ 1 axes. Each has: `axis_id`, `name`, `direction` (list of 3 floats in [-1, 1]), `weight` (float ≥ 0), `theological_note`. |

### Surface preferences (ADR-0028)

Optional block driving the assembler's hedge and claim-strength decisions:

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

Bands (in descending hedge strength):

1. `alignment < hedge_threshold_strong` → prepend `preferred_hedge_strong`.
2. `alignment < hedge_threshold_soft` → prepend `preferred_hedge_soft`.
3. `hedge_threshold_soft <= alignment < qualified_band_high` and `claim_strength == "qualified"` → prepend `preferred_qualifier`.
4. Otherwise leave the assertion bare.

Threshold ordering required: `hedge_threshold_strong <= hedge_threshold_soft <= qualified_band_high`. Loader enforces this.

`claim_strength` must be one of `{"balanced", "qualified", "affirmative"}`. `"balanced"` and `"affirmative"` skip the marginal-band qualifier; only `"qualified"` triggers it.

### Loader bounds (enforced)

- `len(value_axes) >= 1` — empty axes are refused.
- Each `direction` must have length 3 and each component in `[-1.0, 1.0]`.
- `weight` must be in `[0.0, 10.0]` — prevents a single axis from dominating arbitrarily.
- `alignment_threshold` must be in `[0.0, 1.0]`.
- `axis_id` values must be unique within a pack.
- Production mode requires `mastery_report_sha256 != ""` and the companion report's self-seal to verify; development mode (`CORE_ALLOW_UNRATIFIED_IDENTITY=1`) bypasses both.

## Loader contract

```python
from packs.identity.loader import load_identity_manifold

manifold = load_identity_manifold(
    pack_id="default_general_v1",        # required
    search_paths=None,                    # default: ["./packs/identity"]
    require_ratified=True,                # production default
)
```

Returns an `IdentityManifold` (from `core/physics/identity.py`). Raises `IdentityPackError` on missing pack, malformed JSON, bound violations, or unverified self-seal in production mode.

The loader is path-aware: deployments may supply `search_paths=("/srv/myapp/packs/identity", "./packs/identity")` so a robotics or app builder can ship overlay packs without touching CORE's own packs directory.

## CLI usage

```bash
core pulse "What is truth?"
# Loads default identity (currently default_general_v1).

core pulse --identity precision_first_v1 "What is truth?"
# Loads a specific pack. Pack must exist on the loader's search paths.

core pulse --list-identity-packs
# Lists discoverable packs with description + ratification status.

core chat --identity generosity_first_v1
# Same flag, applies to the chat surface.

CORE_DEFAULT_IDENTITY_PACK=precision_first_v1 core pulse "..."
# Environment override of the default. Takes precedence over the
# core/config.py constant; --identity on the command line takes
# precedence over the env var.
```

## Shipping packs (v1)

| Pack id | Role | Notes |
|---|---|---|
| `default_general_v1` | Ship default. Balanced. | Encodes the *exact* three axes (`truthfulness`, `coherence`, `reverence`) previously hardcoded in `chat/runtime.py`. Behavioral no-op vs. pre-ADR runtime. ADR-0028 surface_preferences: balanced; hedge thresholds 0.40/0.50/0.75. Ratified: `ddc1ba127231272660e6a435e177227558461b0278572a95635b416c3e1dec5a`. |
| `precision_first_v1` | Specialization example A. | Boosts `truthfulness` weight, narrows reverence direction. Surface: hedges sooner (0.55/0.70/0.85), uses "Arguably,"/"In some cases,"/"Under certain conditions,"; claim_strength=qualified. Source: `evals/identity_divergence/axes/axis_a.yaml`. Ratified: `cb5fb2323214a26afda33f2a67e22f38fe49f4763829d48ef67fd41241aba33c`. |
| `generosity_first_v1` | Specialization example B. | Boosts `coherence` weight, broadens reverence direction. Surface: hedges later (0.20/0.30/0.50); claim_strength=affirmative. Source: `evals/identity_divergence/axes/axis_b.yaml`. Ratified: `94f2f49e1b16c7498fb52b8f9864eecc198618933dc8381a01b809c146826db7`. |

Each ratified pack ships alongside a `<pack_id>.mastery_report.json` companion file. The loader, in production mode, verifies the companion's self-seal and cross-checks its `report_sha256` against the pack's `mastery_report_sha256`. To re-ratify after editing a pack's axes, run `python scripts/ratify_identity_packs.py` (idempotent — re-running on already-current packs is a no-op).

## Authoring a new identity pack (robotics / personalization / creative tools)

1. **Author the SubjectSpec.** Use `core formation new <subject_id>` to scaffold; edit to declare the pack's intent and identity axis constraints.
2. **Hand-author the candidate axes.** Use the `identity_anchor` template's expected input shape: `concepts` are axes (with `definition` = behavioral commitment), `counters` are override-attempt probes the pack must refuse.
3. **Ratify through formation.** Render → compose → compile → run → ratify. Produces a signed `MasteryReport`.
4. **Promote.** Promotion goes through `teaching/review.py`'s reviewed-apply path. The promote step writes both `<pack_id>.json` and `<pack_id>.mastery_report.json` to `packs/identity/`.
5. **Deploy.** The pack is now selectable by `--identity <pack_id>`. Distribute alongside your deployment's other artifacts.

### Anti-patterns

- **Don't author identity packs by hand-editing `packs/identity/`.** The runtime never writes there; neither should authors. All packs flow through formation so audit trails are intact.
- **Don't ship unratified packs (empty `mastery_report_sha256`) in production.** The loader's `require_ratified` flag exists to refuse them.
- **Don't try to override `boundary_ids` to weaken refusal.** Boundaries are the immutable contract; if your identity pack omits expected boundaries, the runtime refuses to load it.
- **Don't try to express safety constraints in an identity pack.** Safety axes belong in the (future) safety pack, always-loaded and never-replaceable.

## Known limits (read before designing around)

1. ~~**Identity does not yet visibly differentiate articulation at the realizer.**~~ **Closed by [ADR-0028](decisions/ADR-0028-identity-surface-wiring.md) (2026-05-17).** Pack `surface_preferences` now flow into the assembler's hedge and claim-strength decisions. `core chat --identity precision_first_v1 "Q"` produces a visibly different surface than the default pack on the same prompt at the same alignment. Hedging is English-only at v1; depth-language hedging is a future ADR.
2. **One pack at a time.** Multi-pack overlays (`--identity general,domain_medical`) are deferred to a follow-up ADR.
3. **No language-specific identity yet.** Packs are language-neutral. Per-language identity is a future concern.
4. **Safety axes are still in `chat/runtime.py`.** Once the safety pack ADR lands, safety boundaries will move out of `boundary_ids` and into a separately-loaded safety pack.

## Cross-reference index

- Pack format spec: this doc §"Pack format (v1)".
- Loader contract: this doc §"Loader contract".
- Decision record: [ADR-0027](decisions/ADR-0027-identity-packs.md).
- Teaching-order placement: [`teaching_order.md`](teaching_order.md) §"The Five-Layer Ordering Rule" Layer 1.
- Identity-divergence eval: `evals/identity_divergence/contract.md`.
- The geometric identity primitives: `core/physics/identity.py` (ADR-0010 implicit).
- The formation template that ratifies packs: `formation/templates/identity_anchor.py`.
