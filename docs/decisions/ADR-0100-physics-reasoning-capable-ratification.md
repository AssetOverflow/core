# ADR-0100 — Physics Reasoning-Capable Ratification

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Acceptance evidence

Accepted after `physics` became a mechanically ratified `reasoning-capable` ledger row:

- `language_packs/data/en_physics_v1/manifest.json` carries Domain Pack Contract v1 fields.
- `teaching/domain_chains/physics_chains_v1.jsonl` supplies reviewed active chains.
- `tests/test_adr_0100_0102_sibling_ratifications.py` pins:
  - all nine predicates pass for `en_physics_v1`
  - the ledger row status is `reasoning-capable`
  - provenance points at `adr-0100:reviewed:*`
  - `expert_demo` remains false
  - claimed operators `causal` and `modal` meet chain coverage
  - declared lanes include `foundational_physics_ood`, `inference_closure`, and `fabrication_control`

---

## Context

The physics substrate is structurally complete:

- `language_packs/data/en_physics_v1/` ships with manifest, lexicon, glosses.
- `teaching/domain_chains/physics_chains_v1.jsonl` exists.
- `evals/foundational_physics_ood/` exists with dev/public/holdout coverage.
- `docs/gaps.md` marks physics gaps closed.
- Chain coverage and intent-shape coverage satisfy ADR-0091 predicates.

This ADR applies the ADR-0097 ratification template to the physics domain.

---

## Decision

Ratify `en_physics_v1` as `reasoning-capable` under ADR-0091 by emitting
the contract fields into its manifest and passing domain-contract validation.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "physics",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["physics_chains_v1"],
  "eval_lanes": [
    {"lane": "foundational_physics_ood", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "inference_closure", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1", "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0100:reviewed:2026-05-21"
}
```

Claimed operator families: `causal`, `modal`.
`axioms` and `rules` stay `null` at v1 — physics demonstrates reasoning
through reviewed causal/modal chain composition, not declarative axioms.

### What this ADR does not do

- Does not introduce new lemmas, chains, or evals.
- Does not promote to `expert-demo`.
- Does not modify runtime mount behavior.

---

## Invariant

`physics_reasoning_capable_ledger_row` — `core capability ledger` emits
a row for `domain_id: physics` with `status: reasoning-capable`,
provenance pointing at this ADR, and `expert_demo: False` until a future
ADR attaches audit-tour-equivalent reports.

---

## Lane

Existing lanes carry the evidence:

- `foundational_physics_ood/` — positive coverage
- `inference_closure/` — composition
- `fabrication_control/` — negative control
- `evals/domain_contract_validation/` — predicate validation

---

## Consequences

- Second ratified `reasoning-capable` domain.
- Demonstrates the ADR-0091 contract is not math-only.
- Provides an additional domain source for later showcase composition.
