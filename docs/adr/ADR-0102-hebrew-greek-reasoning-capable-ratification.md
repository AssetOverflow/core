# ADR-0102 — Hebrew-Greek Textual-Reasoning Reasoning-Capable Ratification

**Status:** Accepted
**Date:** 2026-05-21
**Accepted:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Acceptance evidence

Accepted after `hebrew_greek_textual_reasoning` became a mechanically ratified multi-pack `reasoning-capable` ledger row:

- `grc_logos_micro_v1`, `grc_logos_cognition_v1`, `he_logos_micro_v1`, and `he_core_cognition_v1` carry uniform Domain Pack Contract v1 fields.
- `teaching/domain_chains/hebrew_greek_textual_reasoning_chains_v1.jsonl` supplies reviewed active chains.
- `tests/test_adr_0100_0102_sibling_ratifications.py` pins:
  - all nine predicates pass for each of the four packs
  - the ledger row status is `reasoning-capable`
  - provenance points at `adr-0102:reviewed:*`
  - `expert_demo` remains false
  - claimed operators `causal` and `contradiction` meet chain coverage
  - declared lanes include `inference_closure` and `fabrication_control`
  - all four contracts are identical modulo pack identity

---

## Context

The hebrew_greek_textual_reasoning substrate is structurally complete
across four packs:

- `grc_logos_micro_v1`, `grc_logos_cognition_v1`, `he_logos_micro_v1`,
  `he_core_cognition_v1`.
- `teaching/domain_chains/hebrew_greek_textual_reasoning_chains_v1.jsonl`.
- `docs/gaps.md` marks relevant Hebrew/Greek textual-reasoning gaps closed.
- Chain coverage and intent-shape coverage satisfy ADR-0091 predicates.

Unlike `mathematics_logic`, `physics`, and `systems_software`, this is a
**multi-pack domain**. ADR-0091 predicates evaluate per pack; the ledger
row aggregates. Each of the four packs must carry the same domain
contract so per-pack validation passes uniformly.

---

## Decision

Ratify all four Hebrew/Greek packs as `reasoning-capable` under
ADR-0091 by emitting the contract fields into each manifest. Each pack
declares the same `domain_id`, `teaching_chains`, `eval_lanes`, and
reviewers, with a uniform provenance trail for this ratification.

### Manifest additions (all four packs)

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "hebrew_greek_textual_reasoning",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["hebrew_greek_textual_reasoning_chains_v1"],
  "eval_lanes": [
    {"lane": "inference_closure", "version": "v1", "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1", "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0102:reviewed:2026-05-21"
}
```

Claimed operator families: `causal`, `contradiction`. `axioms` and
`rules` stay `null` at v1.

### Eval lane scope

Only universal lanes (`inference_closure`, `fabrication_control`) are
declared. The language-specific fluency lanes currently ship dev/public
only; without sealed holdout splits they are not part of this
reasoning-capable ratification. A future ADR may add holdouts and attach
those lanes.

---

## Invariant

`hebrew_greek_reasoning_capable_ledger_row` — `core capability ledger`
emits a row for `domain_id: hebrew_greek_textual_reasoning` with
`status: reasoning-capable`, provenance pointing at this ADR, and
`expert_demo: False` until a future ADR attaches audit-tour-equivalent reports.

`hebrew_greek_pack_contracts_uniform` — all four packs declare identical
contract fields so multi-pack ratification cannot drift between packs
without an explicit ADR.

---

## Lane

Existing lanes carry the evidence:

- `inference_closure/` — composition
- `fabrication_control/` — negative control
- `evals/domain_contract_validation/` — predicate validation on each pack

---

## Consequences

- First multi-pack `reasoning-capable` domain ratification.
- Demonstrates the contract works for both single-pack and multi-pack domains.
- Future language-specific eval lanes can be added once they ship holdout splits.
