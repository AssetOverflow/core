# Ethics Packs — Reference

**Status:** Operational reference. Update when pack format, loader contract, or composition rules change.
**Last updated:** 2026-05-17
**Companion docs:** [`decisions/ADR-0033-ethics-packs.md`](decisions/ADR-0033-ethics-packs.md), [`identity_packs.md`](identity_packs.md), [`safety_packs.md`](safety_packs.md)

## What an ethics pack is

An ethics pack carries the **propositional commitments** a deployment pledges in its domain. Where identity packs encode *who* CORE is and safety packs encode *what CORE will never do*, ethics packs encode *what this deployment commits to in its domain* — informed consent in medical, attorney-client privilege in legal, fiduciary disclosure in financial, etc.

At runtime composition, `commitment_ids` are unioned into `IdentityManifold.boundary_ids` alongside identity and safety contributions:

```
manifold.boundary_ids = identity.boundary_ids ∪ safety.boundary_ids ∪ ethics.commitment_ids
```

The composition is monotone: every layer adds; none can remove.

## How ethics packs differ from identity and safety

| Property | Identity | Safety | Ethics |
|---|---|---|---|
| Swappable at runtime | Yes (`--identity X`) | **No** | Yes (`ethics_pack="..."`) |
| Multiple packs available | Yes | **Exactly one** | Yes |
| Failure to load requested pack | Fall back to default | **Fail-closed; refuses startup** | Fall back to default |
| Schema field | `value_axes` | `boundary_ids` | `commitment_ids` |
| Shape | Geometric (directions) | Propositional (red lines) | Propositional (pledges) |
| Directory | `packs/identity/` | `packs/safety/` | `packs/ethics/` |
| Exception class | `IdentityPackError` (ValueError) | `SafetyPackError` (RuntimeError) | `EthicsPackError` (ValueError) |

Ethics packs follow identity-pack semantics (swappable, falls back) rather than safety-pack semantics (fail-closed). Safety is the universal floor; ethics is deployment configuration above it.

## Shipping ethics pack (v1)

| Pack id | Domain | Description | Ratified |
|---|---|---|---|
| `default_general_ethics_v1` | general | Five propositional commitments for general deployments. | `81fc9b61c828fdd4926ac9eb212883ffd72c032a0ddb6a4b8d988783c98ae98d` |

### Default commitments

| Commitment id | Pledge |
|---|---|
| `acknowledge_uncertainty` | Surface confidence rather than projecting false certainty. |
| `defer_high_stakes_to_human_review` | Flag irreversible/high-stakes decisions for human review. |
| `disclose_limitations` | Say plainly when a topic exceeds grounded knowledge or appropriate scope. |
| `no_manipulation` | Persuade via reasoning, not exploitation of cognitive biases or social pressure. |
| `respect_user_autonomy` | Surface options and tradeoffs; do not prescribe where reasonable people may differ. |

## Pack format (v1)

```json
{
  "pack_id": "default_general_ethics_v1",
  "version": "1.0.0",
  "description": "...",
  "schema_version": "1.0.0",
  "domain": "general",
  "mastery_report_sha256": "...",
  "commitment_ids": [
    "acknowledge_uncertainty",
    "..."
  ],
  "commitment_descriptions": {
    "acknowledge_uncertainty": "...",
    "..."
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
| `domain` | yes | One of `general`, `medical`, `legal`, `financial`, `robotics`, `custom`. Audit-only at v1. |
| `mastery_report_sha256` | yes (production) | SHA of the companion `<pack_id>.mastery_report.json`. |
| `commitment_ids` | yes | Non-empty list of unique commitment identifier strings. |
| `commitment_descriptions` | yes | Dict mapping each `commitment_id` to a human-readable pledge. |

### Loader bounds (enforced)

- `commitment_ids` must be a non-empty list of unique non-empty strings.
- `pack_id` must not contain `/` or `..`.
- `schema_version` must equal `"1.0.0"`.
- `domain` must be in the allowed set.
- In production mode, `mastery_report_sha256` must be non-empty, the companion report must exist, its `report_sha256` must match, its self-seal must verify via `formation.hashing.verify_seal`, and `ratified` must be `True`.

## Loader contract

```python
from packs.ethics.loader import load_ethics_pack, EthicsPackError, DEFAULT_ETHICS_PACK

pack = load_ethics_pack(
    pack_id=DEFAULT_ETHICS_PACK,
    search_paths=None,
    require_ratified=True,
)
```

Returns an `EthicsPack` (frozen dataclass) with fields `pack_id`, `version`, `description`, `domain`, `commitment_ids` (frozenset), `commitment_descriptions` (dict), `mastery_report_sha256`, `ratified`.

`EthicsPackError` inherits from `ValueError`. A missing requested pack is recoverable — `ChatRuntime` falls back to `DEFAULT_ETHICS_PACK`. Only when both the requested pack and the default are unloadable does the runtime refuse to start.

### Development override

```bash
CORE_ALLOW_UNRATIFIED_ETHICS=1 python -m core.cli chat
```

Bypasses **only** the seal-verification check. Missing files / empty commitments / malformed JSON still fail.

## Composition at runtime

`ChatRuntime.__init__` after ADR-0033:

```python
identity_manifold = load_identity_manifold(config.identity_pack or DEFAULT_IDENTITY_PACK)
safety_pack       = load_safety_pack()                              # fail-closed
try:
    ethics_pack = load_ethics_pack(config.ethics_pack or DEFAULT_ETHICS_PACK)
except EthicsPackError:
    if requested == DEFAULT_ETHICS_PACK:
        raise
    ethics_pack = load_ethics_pack(DEFAULT_ETHICS_PACK)              # fallback

final_boundary_ids = (
    identity_manifold.boundary_ids
    | safety_pack.boundary_ids
    | ethics_pack.commitment_ids
)
```

`ChatRuntime` exposes `runtime.ethics_pack` and `runtime.ethics_pack_id` for audit.

## Authoring a deployment ethics pack

1. Author the pack JSON. Pick a `domain`; list `commitment_ids` your deployment pledges; supply descriptions.
2. Place at `packs/ethics/<pack_id>.json`.
3. Run `python scripts/ratify_ethics_pack.py` (idempotent — produces the companion `.mastery_report.json`).
4. Test under production semantics: `python -m pytest tests/test_ethics_packs.py`.
5. Commit both files (`<pack_id>.json` and `<pack_id>.mastery_report.json`) atomically.
6. Select the pack at runtime: `RuntimeConfig(ethics_pack="<pack_id>")` or a CLI flag (future ADR).

### Anti-patterns

- **Don't use an ethics pack to encode safety boundaries.** Universal red lines belong in the safety pack. Ethics is for *deployment-specific* commitments.
- **Don't use an ethics pack to encode identity.** Value axes and directional preferences belong in the identity pack.
- **Don't omit the general defaults in a domain pack.** A medical/legal/financial pack should *add* to the five general commitments, not replace them. v1 has no `extends` mechanism — duplicate the general commitments and add the domain-specific ones.
- **Don't gate runtime behavior on `domain` at v1.** It's audit-only.

## Versioning policy

| Change | Version bump |
|---|---|
| Description text edits | Patch (`v1.0.0` → `v1.0.1`) |
| Adding a commitment | Minor (`v1.0.0` → `v1.1.0`) |
| Removing a commitment | Major + new pack ID (`<slug>_v2`) |
| Schema format change | Major + new `schema_version` |

## EthicsCheck — structural surface (ADR-0034)

A centralized, observational surface for evaluating commitments at runtime, parallel in shape to `SafetyCheck` (ADR-0032). Produces an `EthicsVerdict`; does not refuse. Wiring violations into refusal / re-articulation paths is a future ADR.

```python
from packs.ethics import EthicsCheck, EthicsContext

check = EthicsCheck()  # ships with default predicates for the five v1 commitments
ctx = EthicsContext(
    alignment_score=score,
    hedge_emitted=hedged,
    high_stakes_topic=is_high_stakes,
    recommended_human_review=review_recommended,
    grounded_in_evidence=grounded,
    disclosure_emitted=disclosed,
    prescribed_single_answer=prescriptive,
    presented_options_count=n_options,
)
verdict = check.check(ctx, ethics_pack)
# verdict.upheld: bool, verdict.violated_commitments: frozenset[str]
# verdict.results: tuple of per-commitment EthicsCheckResult
```

Every `EthicsContext` field is `None`-default. Predicates over fields the caller didn't populate return `upheld=True, runtime_checkable=False` — absence of evidence is not evidence of pledge violation. `ChatRuntime` exposes a pre-constructed instance as `runtime.ethics_check`; the turn loop does not auto-invoke it at v1.

### Default predicates per v1 commitment

| Commitment | Runtime-checkable? | What it checks |
|---|---|---|
| `acknowledge_uncertainty` | Yes (when supplied) | `alignment < hedge_threshold_soft` requires `hedge_emitted=True` |
| `defer_high_stakes_to_human_review` | Yes (when supplied) | `high_stakes_topic=True` requires `recommended_human_review=True` |
| `disclose_limitations` | Yes (when supplied) | `grounded_in_evidence=False` requires `disclosure_emitted=True` |
| `no_manipulation` | **No** | aggregate property; enforced by realizer design + review |
| `respect_user_autonomy` | Yes (when supplied) | `prescribed_single_answer=True` requires `presented_options_count >= 2` |

`no_manipulation` is the structural analogue of `no_hot_path_repair` in SafetyCheck. Honest `runtime_checkable=False` rather than a silent pass.

### Custom predicates

```python
check = EthicsCheck()
check.register("my_domain_commitment", my_predicate)
```

Unknown commitments default to `upheld=True, runtime_checkable=False, reason="no predicate registered for commitment"`. Surfaces in audit; doesn't crash.

## Known limits / future ADRs

1. ~~**No `EthicsCheck` predicate surface** parallel to `SafetyCheck`.~~ **Closed by [ADR-0034](decisions/ADR-0034-ethics-check-surface.md) (2026-05-17).** v1 is observational; turn-loop auto-invocation and refusal wiring are future ADRs.
2. **No deliberation surface.** Ethics-as-deliberation (multi-candidate trajectory selection, typed-tradeoff evaluation) needs multi-trajectory articulation first.
3. **No pack inheritance.** Domain packs must declare full commitment lists; no `extends` mechanism.
4. **No domain-driven behavior.** `domain` is audit-only.
5. **No CLI flag** for `--ethics <pack_id>` yet — `RuntimeConfig(ethics_pack=...)` only. Future ADR.
6. **English-only commitment descriptions** at v1.
7. **No cross-surface verdict aggregation.** Identity / Safety / Ethics produce three independent verdicts; no unified bundle type. Future convenience ADR if call sites grow.

## Cross-reference index

- Pack format spec: this doc §"Pack format (v1)".
- Loader contract: this doc §"Loader contract".
- Decision records: [ADR-0033](decisions/ADR-0033-ethics-packs.md), [ADR-0034](decisions/ADR-0034-ethics-check-surface.md).
- Identity composition: [`identity_packs.md`](identity_packs.md).
- Safety composition: [`safety_packs.md`](safety_packs.md).
- Safety predicate surface: [`safety_packs.md`](safety_packs.md) §SafetyCheck.
- Formation template used for ratification: `formation/templates/identity_anchor.py`.
