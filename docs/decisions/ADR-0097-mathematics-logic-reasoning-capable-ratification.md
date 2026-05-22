# ADR-0097 — Mathematics-Logic Reasoning-Capable Ratification

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096

---

## Acceptance evidence

Accepted after `mathematics_logic` became a mechanically ratified `reasoning-capable` ledger row:

- `language_packs/data/en_mathematics_logic_v1/manifest.json` carries Domain Pack Contract v1 fields.
- `teaching/domain_chains/mathematics_logic_chains_v1.jsonl` supplies reviewed active chains.
- `core/capability/domain_contract_predicates.py` verifies all nine ADR-0091 predicates.
- `tests/test_adr_0097_mathematics_logic_ratification.py` pins:
  - all nine predicates pass for `en_mathematics_logic_v1`
  - the ledger row status is `reasoning-capable`
  - provenance points at `adr-0097:reviewed:*`
  - `expert_demo` remains false
  - declared lanes include `elementary_mathematics_ood`, `inference_closure`, and `fabrication_control`

---

## Context

The mathematics/logic substrate is structurally complete:

- `language_packs/data/en_mathematics_logic_v1/` ships with manifest,
  lexicon, glosses.
- `teaching/domain_chains/mathematics_logic_chains_v1.jsonl` exists.
- `evals/elementary_mathematics_ood/` exists.
- `docs/gaps.md` marks mathematics-logic gaps closed.

This ADR is the first concrete domain claim under the Domain Pack
Contract. It turns existing artifacts into a ratified
`reasoning-capable` ledger row.

---

## Decision

Ratify `en_mathematics_logic_v1` as `reasoning-capable` under
ADR-0091 by emitting the contract fields into its manifest and passing
domain-contract validation.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "mathematics_logic",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["mathematics_logic_chains_v1"],
  "eval_lanes": [
    {"lane": "elementary_mathematics_ood", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "inference_closure", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1", "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0097:reviewed:2026-05-21"
}
```

`axioms` and `rules` stay `null` at v1. The pack proves reasoning
through chain composition, not through declarative axioms. A future ADR
may add explicit axioms; this one does not.

### Required evidence

- `mathematics_logic_chains_v1.jsonl` contains ≥ 8 reviewed chains per claimed operator family.
- ≥ 3 intent shapes are present.
- Three-split eval lane references exist for positive coverage, composition, and negative control.

### What this ADR does not do

- Does not introduce new lemmas, chains, or evals.
- Does not promote to `expert-demo`.
- Does not modify runtime mount behavior.

---

## Invariant

`mathematics_logic_reasoning_capable_ledger_row` — running
`core capability ledger` emits a row for `domain_id: mathematics_logic`
with `status: reasoning-capable`, provenance pointing at this ADR, and
`expert_demo: False` until a future ADR attaches audit-tour-equivalent
reports.

---

## Lane

Existing lanes carry the evidence:

- `elementary_mathematics_ood/` — positive coverage
- `inference_closure/` — composition
- `fabrication_control/` — negative control
- `evals/domain_contract_validation/` — predicate validation

---

## Trust Boundary

Manifest edit is a reviewed proposal. Checksum refresh follows pack discipline.
No runtime mount path changes. No new filesystem writes outside the manifest and its checksum companion.

---

## Consequences

- First `reasoning-capable` row in the capability ledger backed by an ADR-0091-validated pack.
- Sibling ratifications become mechanical follow-ups using the same template.
- The public showcase demo (ADR-0099) gains a real domain to draw Scene 4 from.
