# ADR-0101 — Systems-Software Reasoning-Capable Ratification

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Acceptance evidence

Accepted after `systems_software` became a mechanically ratified `reasoning-capable` ledger row:

- `language_packs/data/en_systems_software_v1/manifest.json` carries Domain Pack Contract v1 fields.
- `teaching/domain_chains/systems_software_chains_v1.jsonl` supplies reviewed active chains.
- `tests/test_adr_0100_0102_sibling_ratifications.py` pins:
  - all nine predicates pass for `en_systems_software_v1`
  - the ledger row status is `reasoning-capable`
  - provenance points at `adr-0101:reviewed:*`
  - `expert_demo` remains false
  - claimed operators `transitive` and `causal` meet chain coverage
  - declared lanes include `symbolic_logic`, `inference_closure`, and `fabrication_control`

---

## Context

The systems_software substrate is structurally complete:

- `language_packs/data/en_systems_software_v1/` ships with manifest, lexicon, glosses.
- `teaching/domain_chains/systems_software_chains_v1.jsonl` exists.
- `evals/symbolic_logic/` exists with dev/public/holdout coverage as the closest in-tree lane for systems/software reasoning at v1.
- `docs/gaps.md` marks systems_software gaps closed.
- Chain coverage and intent-shape coverage satisfy ADR-0091 predicates.

This ADR applies the ADR-0097 ratification template to the systems/software domain.

---

## Decision

Ratify `en_systems_software_v1` as `reasoning-capable` under ADR-0091
by emitting the contract fields into its manifest and passing domain-contract validation.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "systems_software",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["systems_software_chains_v1"],
  "eval_lanes": [
    {"lane": "symbolic_logic", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "inference_closure", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1", "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0101:reviewed:2026-05-21"
}
```

Claimed operator families: `transitive`, `causal`. `axioms` and `rules`
stay `null` at v1 — systems-software reasoning is demonstrated through
reviewed causal/transitive chain composition over invariants, boundaries,
and dependencies.

### Eval lane choice — `symbolic_logic`

Systems-software lacks a dedicated v1 evaluation lane. `symbolic_logic`
is the closest in-tree fit: it pins reasoning over typed relations that
the systems_software chain corpus exercises. A future ADR may introduce a
`systems_software_design_ood` lane and supersede this declaration.

---

## Invariant

`systems_software_reasoning_capable_ledger_row` — `core capability
ledger` emits a row for `domain_id: systems_software` with
`status: reasoning-capable`, provenance pointing at this ADR, and
`expert_demo: False` until a future ADR attaches audit-tour-equivalent reports.

---

## Lane

Existing lanes carry the evidence:

- `symbolic_logic/` — reasoning over typed relations
- `inference_closure/` — composition
- `fabrication_control/` — negative control
- `evals/domain_contract_validation/` — predicate validation

---

## Consequences

- Third ratified `reasoning-capable` domain.
- Establishes systems/software as a ledger-ratified domain while preserving the known v1 eval-lane limitation.
- Provides another domain source for later evidence composition and showcase scenes.
