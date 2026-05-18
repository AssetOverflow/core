# ADR-0027: Identity Packs — Load-Bearing, Swappable, Ratified

**Status:** Accepted (2026-05-17) — Phases 1–6 complete; Phase 7 (this doc + the operational reference) complete; deep realizer wiring tracked as a follow-up ADR.
**Author:** Joshua Shay + planner pass
**Companion docs:** [`docs/identity_packs.md`](../identity_packs.md), [`docs/teaching_order.md`](../teaching_order.md), [`ADR-0010 IdentityManifold (implicit)`](#), [`ADR-0017-agency-scope.md`](ADR-0017-agency-scope.md), [`ADR-0021-epistemic-grade-policy.md`](ADR-0021-epistemic-grade-policy.md)

## Context

CORE's `IdentityManifold` (`core/physics/identity.py`) is already load-bearing in the runtime: `PersonaMotor.from_identity_manifold()` builds a non-identity CGA motor from a manifold's `value_axes`; `IdentityCheck.check()` scores every reasoning trajectory against the manifold; the score feeds into surface context.

But the manifold itself is hardcoded. `chat/runtime.py::_default_identity_manifold()` constructs three axes (`truthfulness`, `coherence`, `reverence`) inline — no configuration, no swapping, no per-deployment customization. Meanwhile a second identity surface exists in `evals/identity_divergence/axes/{axis_a,axis_b}.yaml` with a richer descriptive schema (preferences, modal style, hedges) but only drives a mock articulator inside the divergence eval — not the real pipeline.

Three problems follow from the hardcoding:

1. **Robotics, personalization, and creative-tool builders cannot author identity profiles** without editing CORE Python code, defeating the trust boundary that says only reviewed teaching mutates the runtime.
2. **The identity-divergence eval cannot prove what the user actually experiences**, because the mock used in the eval is not the production path.
3. **The shipping default cannot be deliberate.** Today's three axes were chosen by an engineer at line 531 of `runtime.py`. They happen to be reasonable, but their authorship has no provenance, no ratification, no review.

The architecturally correct fix is to make the identity manifold the contents of a *pack* — same as language packs, anchored under `packs/identity/` — loaded at runtime, swappable by flag, and (when ratified) carrying a signed `MasteryReport` from the formation pipeline.

## Decision

1. **Define a content-addressed identity-pack format** at `packs/identity/<pack_id>.json`. The pack contains the inputs required to construct an `IdentityManifold`: `value_axes` (each with `axis_id`, `name`, `direction`, `weight`, `theological_note`), `boundary_ids`, `alignment_threshold`, plus pack metadata (`pack_id`, `version`, `description`, `mastery_report_sha256` optional).
2. **Ship three packs at v1:**
   - `identity.default_general_v1` — the *new* shipping default. Initially carries the *exact three axes currently hardcoded* (`truthfulness`, `coherence`, `reverence`) so the default is a byte-for-byte behavioral no-op for existing users. Free to evolve later by version bump.
   - `identity.precision_first_v1` — specialization example A, lifted from `axis_a.yaml` semantics into `ValueAxis` direction vectors.
   - `identity.generosity_first_v1` — specialization example B, lifted from `axis_b.yaml`.
3. **Replace `_default_identity_manifold()` with a loader**: `packs.identity.loader.load_identity_manifold(pack_id)`. The default pack id lives in `core/config.py` (`DEFAULT_IDENTITY_PACK = "default_general_v1"`) so deployments can override without code edits.
4. **Add a `--identity <pack_id>` CLI flag** to `core pulse`, `core chat`, and `core trace`. Robotics / app builders supply ratified packs in their deployment's `packs/identity/` overlay; the loader is path-aware.
5. **Identity packs are first-class artifacts under the formation pipeline.** Each pack ships with a companion `<pack_id>.mastery_report.json` produced by rendering a SubjectSpec through the `identity_anchor` template, composing, compiling, running, and ratifying. Promote stamps the `MasteryReport` SHA into the pack's `mastery_report_sha256` field; loaders verify the seal at load time when present. Unratified packs (development / experimentation) are loadable but tagged `ratified: false` in the resulting manifold and excluded from production deployments by the runtime's startup gate.
6. **Identity-pack mutation goes through `teaching/review.py`** (same path ADR-0021 mandates for all pack mutation). Adding a new identity pack to `packs/identity/` requires a reviewed promote step. The runtime never writes to `packs/identity/`; the pipeline does, once.
7. **Safety axes are NOT identity packs.** A future `packs/identity_safety/core_safety_axes_v1.json` will be *always* loaded alongside whatever identity pack is selected, never replaceable, ratified with the strictest possible adversarial set. That work is scoped to a follow-up ADR; this ADR only establishes the swappable-identity layer.

## Consequences

### Positive

- **Identity is now load-bearing AND falsifiable in the real runtime**, not just in the eval mock. The identity-divergence claim can be retested against the production pipeline by swapping packs at the CLI.
- **The shipping default has provenance.** `identity.default_general_v1` is ratified through `identity_anchor` template → MasteryReport → signed pack. The choice of axes is auditable.
- **Downstream consumers get the configurability they need** (robotics, personalization, creative tools) without touching CORE Python.
- **Hardcoded identity is removed from `chat/runtime.py`** — one fewer source of un-auditable behavior in the runtime shell.
- **The trust boundary doctrine extends naturally** — identity-pack changes go through the same reviewed teaching path as everything else.

### Negative / risks

- **Loader becomes a new trust boundary.** Identity packs are JSON files read at startup; a malicious pack could declare zero axes (collapsing identity) or extreme directions (skewing every walk). Mitigated by (a) requiring `mastery_report_sha256` and self-seal verification in production mode, (b) bounding axis directions and alignment thresholds at load time, (c) refusing to load packs with empty `value_axes`.
- **The descriptive schema in `axis_a.yaml` / `axis_b.yaml`** (preferences, modal style, hedges) is **not** preserved by the v1 pack format — those fields don't map onto `ValueAxis`. They remain useful for the eval-layer mock and as authoring hints for future realizer-side wiring (P3 below); the v1 pack only carries what the runtime can *currently* consume.
- **`core pulse --identity X` will not yet produce a measurably different surface** on every prompt, because the existing realizer doesn't actively differentiate articulation by axis identity — it scores alignment but doesn't, for example, choose hedged vs. affirmative phrasing. The differentiation lives in `PersonaMotor.from_identity_manifold` (which biases field walks) and in `IdentityScore` (which feeds surface context). Visible divergence requires wiring axes more deeply into the realizer. **This is a known follow-up (P3 below).**

### Scope limits (explicit non-goals for this ADR)

- **P3 — Deep realizer wiring.** Making the chosen pack visibly change phrasing (hedged vs. affirmative, narrow vs. broad scope, etc.) requires realizer changes beyond identity loading. This ADR establishes the loading mechanism; deep realizer wiring is a separate ADR.
- **Safety axes.** Always-loaded, never-replaceable safety axes are a follow-up.
- **Identity composition.** Multiple-pack overlays (e.g., `--identity general,domain_medical`) are deferred until single-pack wiring is proven.
- **Cross-language packs.** Whether identity packs are language-specific or language-neutral is deferred. v1 packs are language-neutral.

## Implementation phases

| Phase | Work | Exit criterion |
|---|---|---|
| **1. Pack format + loader** | Define `packs/identity/` JSON schema; implement `packs.identity.loader.load_identity_manifold(pack_id, *, search_paths=None)`; bounds checking; helpful errors for missing/malformed packs. | Loader can construct an `IdentityManifold` identical to the existing hardcoded one. |
| **2. Author three v1 packs** | Author `default_general_v1.json`, `precision_first_v1.json`, `generosity_first_v1.json`. | Three JSON files committed; each loads cleanly through Phase-1 loader. |
| **3. Replace hardcoded constructor** | `chat/runtime.py::_default_identity_manifold()` calls the loader using `core.config.DEFAULT_IDENTITY_PACK`. | All existing runtime / cognition / smoke tests still pass. |
| **4. CLI flag** | Add `--identity <pack_id>` to `core pulse` (`scripts/run_pulse.py`) and `core chat` / `core trace`. Threaded into the runtime constructor. | `core pulse --identity precision_first_v1 "..."` runs without error; identity score reflects different axes. |
| **5. Formation ratification** ✅ | Author one `SubjectSpec` per pack; render through `identity_anchor` template; compile, run, ratify; write companion `<pack_id>.mastery_report.json`. Implemented as `scripts/ratify_identity_packs.py` (idempotent). | **Complete (2026-05-17).** All three v1 packs ship with a verified self-sealed MasteryReport: `default_general_v1` → `0b77357f…`, `precision_first_v1` → `5f5000db…`, `generosity_first_v1` → `91716117…`. Loader now defaults to production mode (`require_ratified=None`); chat runtime no longer passes `require_ratified=False`. |
| **6. Tests** | Pack loader unit tests; round-trip default test (loaded pack ≡ previous hardcoded manifold); CLI smoke test (pulse runs under each pack); divergence smoke test (pulse outputs differ between default and precision_first on a known prompt — even if only via score). | All pass; full formation/cognition/smoke suites still pass. |
| **7. Documentation** | `docs/identity_packs.md` reference; README §Identity Packs paragraph; `docs/teaching_order.md` Layer 1 cross-reference; memory file. | Documentation lands in the same PR. |

## Alternatives considered

1. **Leave identity hardcoded; build downstream-customization elsewhere.** Rejected: it strands robotics/personalization/creative builders in the "must edit CORE" hole, and leaves the eval-vs-runtime fork unfixed.
2. **Adopt the `axis_a.yaml` descriptive schema as the pack format.** Rejected: it carries hedge preferences and modal style that the runtime doesn't yet consume, so most of the file would be dead weight at load time. We can extend the pack format in v2 if and when the realizer learns to use those fields.
3. **Allow identity pack mutation at runtime via the chat surface.** Rejected: violates ADR-0021 and the CLAUDE.md Teaching Safety rule that no user text may mutate identity axes or runtime policy.
4. **Use language packs as identity packs (multi-purpose packs).** Rejected: language packs already do enough; combining concerns produces tangled invariants and harder-to-audit drift.

## Verification

This ADR is satisfied when:
- `chat/runtime.py` contains no hardcoded `ValueAxis` instances.
- `packs/identity/` contains three ratified packs.
- `core pulse --identity default_general_v1 "Q"` is behaviorally indistinguishable from `core pulse "Q"`.
- `core pulse --identity precision_first_v1 "Q"` produces a different `identity_score.deviation_axes` than the default.
- The identity-divergence eval can swap mock identities for real ones by referencing pack ids.
- Tests covering all of the above pass in CI.
