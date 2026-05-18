# Safety Packs — Reference

**Status:** Operational reference. Update when pack format, loader contract, or composition rules change.
**Last updated:** 2026-05-17
**Companion docs:** [`decisions/ADR-0029-safety-packs.md`](decisions/ADR-0029-safety-packs.md), [`identity_packs.md`](identity_packs.md)

## What a safety pack is

A safety pack carries the boundaries CORE will **never** cross, regardless of which identity pack is selected. Where identity packs encode *who* CORE is, safety packs encode *what CORE will not do*. The two layers compose at runtime: `manifold.boundary_ids = safety.boundary_ids ∪ identity.boundary_ids`.

Three properties distinguish safety packs from identity packs:

| Property | Identity pack | Safety pack |
|---|---|---|
| Swappable at runtime | Yes (`--identity X`) | **No** |
| Multiple packs available | Yes | **Exactly one** |
| Failure to load | Falls back to default; warns | **Fail-closed; refuses startup** |
| Schema | `value_axes`, `surface_preferences`, etc. | `boundary_ids`, `boundary_descriptions` |
| Directory | `packs/identity/` | `packs/safety/` |

## Shipping safety pack (v1)

| Pack id | Description | Ratified |
|---|---|---|
| `core_safety_axes_v1` | Always-loaded core boundaries: no fabricated source, no hot-path repair, no identity override, no silent correction, preserve versor closure. | `ee1249acdf8c273aeb656d803c37ef915e536d85f177f5cc18c6e2f6c995ce29` |

## Pack format (v1)

```json
{
  "pack_id": "core_safety_axes_v1",
  "version": "1.0.0",
  "description": "Always-loaded, never-replaceable core safety boundaries.",
  "schema_version": "1.0.0",
  "mastery_report_sha256": "...",
  "boundary_ids": [
    "no_fabricated_source",
    "no_hot_path_repair",
    "no_identity_override",
    "no_silent_correction",
    "preserve_versor_closure"
  ],
  "boundary_descriptions": {
    "no_fabricated_source": "Citations must point to a real source span; the system never invents provenance.",
    "no_hot_path_repair": "...",
    "no_identity_override": "...",
    "no_silent_correction": "...",
    "preserve_versor_closure": "..."
  }
}
```

### Field semantics

| Field | Required | Meaning |
|---|---|---|
| `pack_id` | yes | Pack identifier. Convention: `<slug>_v<major>`. |
| `version` | yes | Semver. |
| `description` | yes | Human-facing one-liner. |
| `schema_version` | yes | Currently `"1.0.0"`. |
| `mastery_report_sha256` | yes (production) | SHA of the companion `<pack_id>.mastery_report.json`. Empty only in development; production refuses. |
| `boundary_ids` | yes | Non-empty list of unique boundary identifier strings. |
| `boundary_descriptions` | yes | Dict mapping each `boundary_id` to a human-readable rationale. |

### Loader bounds (enforced)

- `boundary_ids` must be a non-empty list of unique non-empty strings.
- `pack_id` must not contain `/` or `..`.
- `schema_version` must equal `"1.0.0"`.
- In production mode (default), `mastery_report_sha256` must be non-empty, the companion report must exist, its `report_sha256` must match, and its self-seal must verify via `formation.hashing.verify_seal`.

## Loader contract

```python
from packs.safety.loader import load_safety_pack, SafetyPackError, DEFAULT_SAFETY_PACK

pack = load_safety_pack(
    pack_id=DEFAULT_SAFETY_PACK,    # default — callers should rarely pass anything else
    search_paths=None,               # default: ["./packs/safety"]
    require_ratified=True,           # production default
)
```

Returns a `SafetyPack` (frozen dataclass) with fields `pack_id`, `version`, `description`, `boundary_ids` (frozenset), `boundary_descriptions` (dict), `mastery_report_sha256`, `ratified`.

`SafetyPackError` inherits from `RuntimeError`, not `ValueError`. Missing safety pack is a fail-closed runtime condition, not a recoverable input error. Do not catch and continue.

### Development override

```bash
CORE_ALLOW_UNRATIFIED_SAFETY=1 python -m core.cli chat
```

Bypasses **only** the seal-verification check. Missing file / empty boundaries / malformed JSON still fail closed. Use only while authoring or editing the safety pack; never set in production.

## Composition rule

At `ChatRuntime` startup:

```python
identity_manifold = load_identity_manifold(config.identity_pack or DEFAULT_IDENTITY_PACK)
safety_pack       = load_safety_pack()                # fail-closed
final_manifold    = IdentityManifold(
    value_axes        = identity_manifold.value_axes,
    boundary_ids      = identity_manifold.boundary_ids | safety_pack.boundary_ids,
    alignment_threshold = identity_manifold.alignment_threshold,
    surface_preferences = identity_manifold.surface_preferences,
)
```

Safety contributes boundaries only. Identity contributes axes, threshold, surface preferences, and may add further boundaries. The runtime exposes the loaded safety pack as `ChatRuntime.safety_pack` for audit.

## Authoring a new safety pack

A safety pack is unique to a deployment. The shipping default is `core_safety_axes_v1`; downstream deployments may author their own stricter pack and place it at `packs/safety/<deployment_safety_id>.json`.

1. Author the pack JSON. List the boundary ids your deployment requires; supply descriptions explaining each.
2. Run `python scripts/ratify_safety_pack.py` (idempotent). Produces the companion `.mastery_report.json` and embeds the SHA in the pack.
3. **Test it under fail-closed semantics.** Run `python -m pytest tests/test_safety_pack.py` and verify all 15 tests pass.
4. **Commit both files** (`<pack_id>.json` and `<pack_id>.mastery_report.json`) atomically.

### Anti-patterns

- **Don't catch `SafetyPackError`.** A missing safety pack should crash the runtime, not silently degrade. The exception class deliberately doesn't inherit from `ValueError`.
- **Don't carry value axes in a safety pack.** Safety boundaries are not directional preferences. If you find yourself wanting axes, you want an identity pack.
- **Don't make boundary text user-facing without curation.** `boundary_descriptions` is for audit and operator visibility, not end-user prose.
- **Don't ship multiple safety packs.** The design is "exactly one shipping safety pack per CORE installation." Per-tenant safety packs are an architectural change requiring a future ADR.

## Versioning policy

| Change | Version bump |
|---|---|
| Description text edits | Patch (`v1.0.0` → `v1.0.1`) |
| Adding a boundary | Minor (`v1.0.0` → `v1.1.0`) |
| Removing a boundary | **Major + new ADR justifying the removal** (`core_safety_axes_v2`) |
| Schema format change | Major + new `schema_version` |

A new major version means a new `pack_id`. The old pack remains in the repo for replay and audit; the runtime loads whichever pack id is shipped (currently hardcoded in `packs.safety.loader.DEFAULT_SAFETY_PACK`).

## Known limits

1. **No `SafetyCheck` parallel to `IdentityCheck`.** Boundaries are enforced elsewhere in the pipeline (refusal paths, allowlist enforcement). A future structural safety-score surface would be valuable but isn't in scope here.
2. **No per-tenant safety packs.** Multi-tenant CORE deployments share one safety pack.
3. **No human-in-the-loop ratification step.** Operational discipline lives in PR review, not the code.
4. **English-only boundary descriptions** at v1.

## Cross-reference index

- Pack format spec: this doc §"Pack format (v1)".
- Loader contract: this doc §"Loader contract".
- Decision record: [ADR-0029](decisions/ADR-0029-safety-packs.md).
- Identity pack composition: [`identity_packs.md`](identity_packs.md).
- Trust-boundary doctrine: [`runtime_contracts.md`](runtime_contracts.md), CLAUDE.md "Security and Trust Boundaries".
- The formation template used for ratification: `formation/templates/identity_anchor.py`.
