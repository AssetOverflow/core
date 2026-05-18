# ADR-0033: Ethics Packs — Swappable Domain Commitments

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`../ethics_packs.md`](../ethics_packs.md), [`ADR-0027-identity-packs.md`](ADR-0027-identity-packs.md), [`ADR-0029-safety-packs.md`](ADR-0029-safety-packs.md)

## Context

[ADR-0027](ADR-0027-identity-packs.md) made identity swappable: each deployment selects an identity pack carrying value axes, weights, surface preferences. [ADR-0029](ADR-0029-safety-packs.md) added safety packs as an always-loaded, never-replaceable sibling that contributes universal red lines.

What neither ADR established is a third layer: **domain-specific ethical commitments**. A medical deployment commits to "no diagnosis without clinician review"; a legal deployment commits to "attorney-client privilege preserved"; a financial deployment commits to "fiduciary disclosure on conflicts of interest." These are not universal red lines (safety) and not directional value axes (identity) — they are propositional pledges scoped to a deployment context.

The runtime today has nowhere to put them. They end up either crammed into the identity pack (where they don't fit — identity is geometric) or smuggled into application code (where they vanish from the manifold and cannot be audited).

## Decision

Introduce **ethics packs** as a third pack layer at `packs/ethics/`, sibling to identity and safety.

### Position in the three-layer hierarchy

| Layer | What it carries | Swappable? | Failure mode | Shape |
|---|---|---|---|---|
| Identity | Value axes, weights, surface preferences | Yes (`--identity`) | Fall back to default | Geometric (directions) |
| Safety | Universal red lines | **No** (exactly one) | **Fail-closed** | Propositional (boundaries) |
| Ethics | Domain-specific commitments | Yes (per deployment) | Fall back to default | Propositional (commitments) |

Ethics packs are swappable like identity packs (a deployment selects which one) but propositional like safety packs (commitment ids unioned into the manifold). They fill the niche of "what this deployment commits to in its domain" that the existing two layers cannot occupy.

### Schema (v1)

```json
{
  "pack_id": "default_general_ethics_v1",
  "version": "1.0.0",
  "description": "...",
  "schema_version": "1.0.0",
  "domain": "general",
  "mastery_report_sha256": "...",
  "commitment_ids": ["acknowledge_uncertainty", "..."],
  "commitment_descriptions": {"acknowledge_uncertainty": "...", "..."}
}
```

`domain` is restricted to `{"general", "medical", "legal", "financial", "robotics", "custom"}` at v1 — informational/audit only; no behavior change is gated on it yet. The enumeration exists so a deployment authoring a domain pack records its scope explicitly.

`commitment_ids` is a non-empty unique list of strings. Each id must have a description. The "commitment" vocabulary (vs. "boundary") is deliberate: safety boundaries are red lines ("never X"); ethics commitments are affirmative pledges ("we hold ourselves to Y"). The two framings are dual but distinct, and the source pack should be honest about which it is encoding. At runtime composition they all end up as ids in `IdentityManifold.boundary_ids`.

### Composition

`ChatRuntime` startup, after this ADR:

```python
identity = load_identity_manifold(config.identity_pack or DEFAULT_IDENTITY_PACK)
safety   = load_safety_pack()                            # fail-closed
ethics   = load_ethics_pack(config.ethics_pack or DEFAULT_ETHICS_PACK)
final.boundary_ids = (
    identity.boundary_ids
    | safety.boundary_ids
    | ethics.commitment_ids
)
```

The composition is **monotone**: each layer adds, none can remove. Safety boundaries remain inviolate regardless of which identity or ethics pack is loaded.

### Failure semantics

Ethics packs follow **identity-pack semantics**, not safety-pack semantics:

- `EthicsPackError` inherits from `ValueError` (like `IdentityPackError`), not `RuntimeError`.
- A missing or malformed *requested* ethics pack falls back to the *default* ethics pack — the runtime warns implicitly via the `ethics_pack_id` attribute (which records what actually loaded, not what was requested).
- Only when **both** the requested pack and the default are unloadable does `EthicsPackError` propagate and crash startup.
- `CORE_ALLOW_UNRATIFIED_ETHICS=1` mirrors the identity-pack escape hatch for development.

The reasoning: ethics is deployment-specific *configuration*, not a universal floor. Safety is the universal floor; ethics is one notch above it. A deployment that mis-specifies its ethics pack should land on the general default, not refuse to start.

### Default pack

`packs/ethics/default_general_ethics_v1.json` ships with five commitments suitable for a general deployment:

1. `acknowledge_uncertainty` — surface confidence rather than projecting false certainty.
2. `defer_high_stakes_to_human_review` — flag irreversible/high-stakes decisions for human review.
3. `disclose_limitations` — say when a topic exceeds grounded knowledge or appropriate scope.
4. `no_manipulation` — persuade by reasoning, not by exploiting biases.
5. `respect_user_autonomy` — present options and tradeoffs; do not prescribe where reasonable people may differ.

These are intentionally minimal and additive — domain packs are expected to add (and never to remove) commitments. A medical pack would add `informed_consent_required_before_disclosure`, `no_diagnosis_without_clinician_review`, etc. on top of (not in place of) the general defaults — though authoring a domain pack means writing the full commitment list; v1 has no "extends" mechanism for pack inheritance, and "additive on top" is operational discipline rather than a structural guarantee.

### Ratification

`scripts/ratify_ethics_pack.py` mirrors `scripts/ratify_safety_pack.py`: each commitment id becomes a `ConceptCandidate`, the canned override-attempt counters drive `every_override_rejected`, and the `identity_anchor` template's gates are authoritative. The default pack is ratified at SHA `81fc9b61c828…`.

Idempotent: re-running with no pack edits is a no-op.

### What this ADR does NOT do

Explicit scope limits:

- **No EthicsCheck surface.** A `packs.ethics.check.EthicsCheck` registry-of-predicates parallel to `SafetyCheck` (ADR-0032) is a natural next step, but is not part of this ADR. v1 ethics is observational-by-omission: commitments compose into the manifold and surface in audit; predicate-level checking comes later.
- **No deliberation logic.** The "ethics as deliberation surface" interpretation (multi-candidate trajectory selection, typed-tradeoff evaluation) is a separate architectural problem that needs multi-trajectory articulation first.
- **No governance mechanism.** Who has authority to author/edit an ethics pack is sociotechnical policy; this ADR is the technical substrate.
- **No domain-driven behavior.** The `domain` field is audit-only at v1; the runtime does not gate behavior on it.
- **No pack inheritance/composition.** A medical pack must declare its full commitment list, not "extends default_general_ethics_v1 with [...]". Pack inheritance is a possible future ADR if the duplication becomes burdensome in practice.

## Consequences

### Positive

- **Three-layer architecture is now complete and orthogonal.** Identity says *who*, safety says *what we won't do*, ethics says *what we commit to in this domain*. Each is independently ratified, each composes into the manifold, none can override another's contribution.
- **Domain deployments have a clean configuration point.** Robotics, medical, legal, financial deployments author one ethics pack rather than scattering deployment-specific ethical reasoning across application code.
- **Auditable.** Every commitment surfaces in `IdentityManifold.boundary_ids` with a description and a ratified mastery report. An auditor reviewing a deployment can read one ethics pack and know what the deployment pledges.
- **Forward-compatible with EthicsCheck.** When the predicate surface lands, it will register against the same `commitment_ids`; the loader and composition do not need to change.

### Negative / risks

- **Three layers is more than two.** Operators now have to understand identity vs. safety vs. ethics distinctions. The docs need to be clear about which is which, and when to author each. Mitigated by `docs/ethics_packs.md` and the side-by-side comparison table above.
- **Vocabulary risk.** "Commitment" vs. "boundary" is a real semantic distinction at the pack-schema level, but at runtime they all live in the same `boundary_ids` set. A reader who only sees the composed manifold cannot recover which layer contributed which id without consulting the source packs. Audit logs that record the source layer would close this gap; deferred to a future ADR.
- **Failure-mode asymmetry.** Identity falls back; safety fails closed; ethics falls back. A future contributor might expect ethics to fail closed by analogy with safety. The ADR is explicit about why it does not.

## Verification

- `tests/test_ethics_packs.py` — 20 tests covering loader happy path, bounds checks, ratification (production-mode rejection of unratified packs, override accepted with `require_ratified=False`), discovery, and `ChatRuntime` composition under each of the three identity packs.
- `scripts/ratify_ethics_pack.py` runs idempotently and produces a verifiable self-sealed mastery report at `packs/ethics/default_general_ethics_v1.mastery_report.json` (SHA `81fc9b61c828…`).
- Existing test suites unaffected: cognition, teaching, runtime, formation, smoke continue green at the same revision.
- The combined identity/safety/ethics surface suite (`test_identity_packs`, `test_safety_pack`, `test_safety_check`, `test_ethics_packs`, plus surface-divergence and score-decomposition) totals 128 tests, all green.
