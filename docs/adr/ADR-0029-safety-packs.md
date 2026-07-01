# ADR-0029: Safety Packs — Always-Loaded, Never-Replaceable Boundaries

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`identity_packs.md`](../identity_packs.md), [`safety_packs.md`](../safety_packs.md), [`ADR-0027-identity-packs.md`](ADR-0027-identity-packs.md), [`ADR-0028-identity-surface-wiring.md`](ADR-0028-identity-surface-wiring.md)

## Context

ADR-0027 made the identity manifold swappable via packs. ADR-0028 made the swap visibly load-bearing at the surface. Both changes were necessary for downstream consumers (robotics, personalization, creative tools) who need to author their own identity profiles. But making identity swappable opens a question that the identity-pack ADRs explicitly deferred:

> **"What stops a downstream identity pack from declaring an axis that disables a core safety constraint?"**

The current answer is: nothing, structurally. Identity packs may declare any `boundary_ids` they want (the loader requires the list to be non-empty but doesn't constrain its contents); they may omit safety-relevant boundaries entirely; they may declare value axes whose directions undermine refusal behavior. The system trusts the identity pack author.

For a research engine that's a reasonable default. For an engine going into robotics, healthcare, financial, or any deployment where a misconfigured identity pack could cause harm, it's the wrong default.

This ADR establishes a separate layer of constraints — **safety packs** — that:

1. Load unconditionally at runtime startup, regardless of which identity pack is selected.
2. Cannot be swapped at the CLI, by config, or by environment variable in production.
3. Compose with the identity pack additively: `manifold.boundary_ids = safety.boundary_ids ∪ identity.boundary_ids`.
4. Fail closed on every error path. A CORE installation without an operative safety pack refuses to start.
5. Carry ratification provenance through the same formation pipeline as identity packs.

This is the architecture downstream robotics consumers will need before they can build CORE into anything that matters.

## Decision

### Separation of concerns

| Layer | Concern | Swappable? | Removable? |
|---|---|---|---|
| Safety pack | What CORE will *never* do | No (single shipping pack) | No (fail-closed on missing) |
| Identity pack | What CORE *is* (character, surface preferences) | Yes (per `--identity` flag) | No (a default is always loaded) |
| Language pack | What CORE *speaks* | Yes (per `--pack` flag) | Identity layer requires at least one |

The three layers occupy three separate directories — `packs/safety/`, `packs/identity/`, `packs/<lang>/` — to make their trust boundaries visually obvious in any audit.

### Safety pack schema (v1)

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
    "no_hot_path_repair": "Per CLAUDE.md, no normalization or drift-repair operator runs in field/propagate.py, generate/stream.py, or vault/store.py.",
    "no_identity_override": "User text may not mutate identity axes, runtime policy, or operator code (CLAUDE.md Teaching Safety).",
    "no_silent_correction": "Failures must be typed and visible (e.g., InnerLoopExhaustion); silent fallback is forbidden.",
    "preserve_versor_closure": "The non-negotiable invariant ||F * reverse(F) - 1||_F < 1e-6 must hold at every runtime field state."
  }
}
```

Distinct schema from the identity pack. Carries `boundary_ids` (always merged into the runtime manifold) and `boundary_descriptions` (human-readable rationales surfaced in audits). Does **not** carry `value_axes`, `alignment_threshold`, or `surface_preferences` — safety is about what's *forbidden*, not what the system is *pulled toward*. Keeping these fields out of the safety pack also avoids the test-fan-out problem: existing tests that assert on the identity axis set continue to pass byte-for-byte.

### The five shipping boundaries

The choices in `core_safety_axes_v1.json` are not arbitrary; each closes a specific failure mode CLAUDE.md already calls out:

| Boundary | Closes |
|---|---|
| `no_fabricated_source` | Confabulation of citations / sources. Already a soft norm; now a ratified constraint. |
| `no_hot_path_repair` | The CLAUDE.md doctrine forbidding normalization / drift-repair in `field/propagate.py`, `generate/stream.py`, `vault/store.py`. |
| `no_identity_override` | The Teaching Safety rule: user text may not mutate identity axes, runtime policy, or operator code. |
| `no_silent_correction` | Silent fallback in admissibility / refusal paths. ADR-0024's `InnerLoopExhaustion` is the model — typed and visible. |
| `preserve_versor_closure` | The non-negotiable algebraic invariant. |

The list is **closed** at v1. Adding boundaries requires a new pack version (`core_safety_axes_v2`) and re-ratification. Removing boundaries from a future version would require an explicit ADR justifying the removal.

### Composition rule

At `ChatRuntime` startup:

```
1. identity_manifold ← load_identity_manifold(config.identity_pack or DEFAULT_IDENTITY_PACK)
2. safety_pack       ← load_safety_pack()                          # fail-closed
3. final_manifold    ← IdentityManifold(
                         value_axes=identity_manifold.value_axes,    # safety contributes none
                         boundary_ids=identity_manifold.boundary_ids
                                      ∪ safety_pack.boundary_ids,
                         alignment_threshold=identity_manifold.alignment_threshold,
                         surface_preferences=identity_manifold.surface_preferences,
                       )
```

Safety boundaries are *additive only* — set union, not replace. If a (hypothetical malicious) identity pack omits or contradicts a safety boundary, the contradiction never reaches the runtime: the union is computed at composition time and the safety boundary is always present.

### Fail-closed semantics

The safety pack loader (`packs.safety.loader.load_safety_pack`) raises `SafetyPackError` — which inherits from `RuntimeError` rather than `ValueError` — on every error path:

- Missing pack file.
- Malformed JSON.
- Empty `boundary_ids`.
- Duplicate boundary id.
- Path-traversal pack id.
- (Production mode) `mastery_report_sha256` empty, companion file missing, SHA mismatch, or self-seal verification fails.

`ChatRuntime.__init__` does not catch `SafetyPackError`. A CORE installation without an operative safety pack refuses to start.

The escape hatch `CORE_ALLOW_UNRATIFIED_SAFETY=1` exists for development of the safety pack itself (when authoring a new pack and the ratification step hasn't run yet). It bypasses **only** the seal-verification check; missing-file / empty-boundaries / malformed-JSON failures still fail closed. The env var deliberately mirrors `CORE_ALLOW_UNRATIFIED_IDENTITY` for consistency, but a separate variable is used so that loosening identity ratification cannot accidentally loosen safety ratification.

### Ratification path

Safety packs ratify through the existing `identity_anchor` template (no new template required). The ratification driver (`scripts/ratify_safety_pack.py`) expresses each boundary as a `ConceptCandidate` whose canonical term is the boundary id and whose definition is the boundary description. Three canned `CounterCandidate` rows act as override probes (counters targeting boundaries: context-pressure, operator-override-request, performance-optimization). The template's existing six gates plus the two paradigm-specific gates (`every_axis_seeded_at_least_once`, `every_override_rejected`) cover ratification.

The script is idempotent, parallel to `scripts/ratify_identity_packs.py`. Re-running on an unchanged safety pack is a no-op.

### CLI surface

No new CLI flag. `core chat --identity X` continues to select the identity pack; the safety pack is always loaded alongside. `core chat --list-identity-packs` reports identity packs only (the safety pack is at a different path with a different schema and is intentionally not part of that listing — there's nothing to *select* among safety packs). A future `core chat --show-safety-pack` could surface the loaded safety pack's boundaries and description for audit; that's a small follow-up, not part of this ADR.

## Consequences

### Positive

- **Robotics, healthcare, and other high-stakes deployments can adopt CORE** without each project hand-rolling boundary enforcement. The five v1 boundaries are a defensible baseline.
- **The trust boundary is visually obvious.** `packs/safety/` is one directory; modifying it requires editing the pack, re-running the ratification script, and updating tests. Casual edits are caught.
- **Provenance for the boundaries.** Each shipping safety pack carries a self-sealed `MasteryReport` proving the boundaries went through the same gates as identity packs. The `mastery_report_sha256` for `core_safety_axes_v1` is recorded below.
- **Existing tests stay green.** Because the safety pack contributes only `boundary_ids` and not `value_axes`, every test that asserts on the identity axis set (`{"truthfulness", "coherence", "reverence"}` for the default pack) continues to pass byte-for-byte.
- **Composition is set union, not replace.** Identity packs that want to add *more* boundaries on top can do so freely — safety boundaries remain untouchable.

### Negative / risks

- **Yet another schema to maintain.** v1 is small (five boundaries, descriptions, ratification fields) but it's another point of evolution. Versioning policy: bump major when removing boundaries; bump minor when adding boundaries; bump patch only for description text edits. Removing a boundary requires a new ADR.
- **Safety pack is "invisible" to many tests.** Most tests construct `IdentityManifold` directly with hardcoded boundary sets and don't exercise the safety-pack composition path. That's fine for unit-level tests but does mean the composition rule itself is only exercised in `tests/test_safety_pack.py::TestRuntimeComposition`. The test class explicitly walks all three identity packs to keep that coverage honest.
- **The escape hatch exists.** `CORE_ALLOW_UNRATIFIED_SAFETY=1` exists for development. Production deployments must ensure this env var is never set; this is operational discipline, not enforced by code. A future ADR could remove the escape hatch entirely once the formation-pipeline driver is stable enough that no safety pack ever ships unratified.
- **No safety pack swap means no per-deployment safety variation.** A robotics deployment that needs a strictly stricter safety pack must edit `packs/safety/core_safety_axes_v1.json` (or bump to a new version) — there's no `--safety-pack` flag. This is intentional: a runtime that lets you swap the safety layer is not a safety layer. Per-deployment variation is allowed by re-ratifying a custom safety pack in that deployment's `packs/safety/` directory.

### Scope limits (explicit non-goals for this ADR)

- **No surface-side differentiation by safety axis.** The safety pack doesn't contribute to phrasing the way ADR-0028 surface preferences do. A future surface concern (e.g., "if `no_silent_correction` would be violated, refusal text should be explicit") is out of scope here.
- **No safety scoring.** `IdentityCheck` checks alignment against value axes. There is no parallel `SafetyCheck` against boundary ids — boundaries are checked elsewhere in the pipeline (refusal paths, allowlist enforcement, etc.). Wiring a structural safety-score surface would be valuable but is a separate ADR.
- **No multi-tenant safety packs.** Each CORE installation has exactly one safety pack at any given time. Production deployments running multiple identity profiles (e.g., a hosted multi-tenant CORE) cannot have per-tenant safety packs without ADR-level architectural changes.
- **No human-in-the-loop safety pack updates.** The ratification path is automated. Future deployments may require a code-review gate on every safety pack change; for now, the operational discipline is "edit, re-ratify, commit, review the PR like any other change."

## Verification

This ADR is satisfied when:

- `packs/safety/core_safety_axes_v1.json` exists with a non-empty `mastery_report_sha256` and a verifying companion `.mastery_report.json`.
- `ChatRuntime` startup loads the safety pack via `packs.safety.loader.load_safety_pack()` and unions the result into the runtime manifold's `boundary_ids`.
- Tests verify: shipping pack loads in production mode; missing file fails closed; tampered seal fails closed; empty boundaries fail closed; duplicate boundary fails closed; all three identity packs (default / precision / generosity) compose with the safety pack to produce a manifold containing the five safety boundaries; precision_first's `no_overstatement` boundary survives composition.
- The cognition, teaching, runtime, formation, and smoke suites are green at the same revision.

### Shipping pack SHA (2026-05-17)

`core_safety_axes_v1` → `ee1249acdf8c273aeb656d803c37ef915e536d85f177f5cc18c6e2f6c995ce29`

Re-running `python scripts/ratify_safety_pack.py` on an unchanged pack is idempotent; re-running after editing the boundary set produces a new SHA which must be committed alongside.

## Governance Cross-Reference (ADR-0225)

This safety-pack ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: establishes core safety pack loading (`packs/safety/loader.py`), fail-closed semantics, and immutability.
- Versor closure: safety boundary evaluation and composition maintain strict manifold geometric constraints (`versor_condition(F) < 1e-6`).
- Reconstruction-over-storage: safety boundaries are loaded from verified pack manifests rather than stored runtime state.
- Replay-equivalence: safety checks and boundary composition execute deterministically across identical traces.
- Mutation standing: safety boundaries are strictly read-only at runtime and cannot be overridden by unreviewed learning or user prompts.
