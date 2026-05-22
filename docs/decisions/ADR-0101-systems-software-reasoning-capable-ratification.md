# ADR-0101 — Systems-Software Reasoning-Capable Ratification

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Context

The systems_software substrate is structurally complete:

- `language_packs/data/en_systems_software_v1/` ships with manifest,
  lexicon, glosses.
- `teaching/domain_chains/systems_software_chains_v1.jsonl` exists.
- `evals/symbolic_logic/` exists with dev/public/holdouts (the
  closest in-tree lane for systems/software reasoning at v1).
- `docs/gaps.md` marks every systems_software gap closed:
  `gap:systems_software_pack_absent`,
  `gap:systems_software_transitive_chains_below_threshold`,
  `gap:systems_software_causal_chains_below_threshold`,
  `gap:systems_software_intent_shapes_below_threshold` — all `[x]`.
- Chain coverage: causal=8, transitive=8 (≥8 per claimed operator
  family ✓); five intent shapes populated (≥3 ✓).

What's missing is the ADR-0091 formal ratification step, matching the
template established by ADR-0097 for `mathematics_logic`.

---

## Decision

Ratify `en_systems_software_v1` as `reasoning-capable` under ADR-0091
by emitting the contract fields into its manifest and passing
`core capability domain-contract validate en_systems_software_v1`.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "systems_software",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["systems_software_chains_v1"],
  "eval_lanes": [
    {"lane": "symbolic_logic", "version": "v1",
     "splits": ["dev", "public", "holdout"]},
    {"lane": "inference_closure", "version": "v1",
     "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1",
     "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0101:reviewed:2026-05-21"
}
```

Claimed operator families (`DOMAIN_OPERATOR_CLAIMS`): `transitive`,
`causal`. `axioms` and `rules` stay `null` at v1 — systems-software
reasoning is demonstrated through reviewed causal/transitive chain
composition over invariants, boundaries, and dependencies.

### Eval lane choice — `symbolic_logic`

Systems-software lacks a dedicated v1 evaluation lane. `symbolic_logic`
is the closest in-tree fit: it pins reasoning over typed relations
(implication, contradiction, dependency) that the systems_software
chain corpus exercises. A future ADR may introduce a
`systems_software_design_ood` lane and supersede this declaration.

---

## Invariant

`systems_software_reasoning_capable_ledger_row` — `core capability
ledger` emits a row for `domain_id: systems_software` with
`status: reasoning-capable`, provenance pointing at this ADR, and
`expert_demo: False` until a future ADR attaches the required reports.

---

## Lane

No new lane. Existing lanes carry the evidence:

- `symbolic_logic/` (reasoning over typed relations)
- `inference_closure/` (composition)
- `fabrication_control/` (negative control, ADR-0096)
- `evals/domain_contract_validation/` (ADR-0093 confirms predicates fire)

---

## PR Checklist

- Capability added: third ratified `reasoning-capable` domain.
- Invariant proved: `systems_software_reasoning_capable_ledger_row`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none.
- Trust boundary: manifest edit through reviewed flow; checksums unchanged.
