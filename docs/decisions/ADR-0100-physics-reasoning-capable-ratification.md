# ADR-0100 — Physics Reasoning-Capable Ratification

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Context

The physics substrate is structurally complete:

- `language_packs/data/en_physics_v1/` ships with manifest, lexicon, glosses.
- `teaching/domain_chains/physics_chains_v1.jsonl` exists.
- `evals/foundational_physics_ood/` exists with dev/public/holdouts.
- `docs/gaps.md` marks every physics gap closed:
  `gap:physics_pack_absent`, `gap:physics_causal_chains_below_threshold`,
  `gap:physics_modal_chains_below_threshold`,
  `gap:physics_intent_shapes_below_threshold` — all `[x]`.
- Chain coverage: causal=8, modal=8 (≥8 per claimed operator family ✓);
  five intent shapes populated (cause, comparison, correction, procedure,
  verification — ≥3 ✓).

What's missing is the ADR-0091 formal ratification step, matching the
template established by ADR-0097 for `mathematics_logic`.

---

## Decision

Ratify `en_physics_v1` as `reasoning-capable` under ADR-0091 by emitting
the contract fields into its manifest and passing
`core capability domain-contract validate en_physics_v1`.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "physics",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["physics_chains_v1"],
  "eval_lanes": [
    {"lane": "foundational_physics_ood", "version": "v1",
     "splits": ["dev", "public", "holdout"]},
    {"lane": "inference_closure", "version": "v1",
     "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1",
     "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0100:reviewed:2026-05-21"
}
```

Claimed operator families (`DOMAIN_OPERATOR_CLAIMS`): `causal`, `modal`.
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
provenance pointing at this ADR, and `expert_demo: False` until a
future ADR attaches the required audit-tour-equivalent reports.

---

## Lane

No new lane. The four existing lanes carry the evidence:

- `foundational_physics_ood/` (positive coverage)
- `inference_closure/` (composition)
- `fabrication_control/` (negative control, ADR-0096)
- `evals/domain_contract_validation/` (ADR-0093 confirms predicates fire)

---

## PR Checklist

- Capability added: second ratified `reasoning-capable` domain.
- Invariant proved: `physics_reasoning_capable_ledger_row`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none.
- Trust boundary: manifest edit through reviewed flow; checksums unchanged.
