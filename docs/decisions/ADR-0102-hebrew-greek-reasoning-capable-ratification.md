# ADR-0102 — Hebrew-Greek Textual-Reasoning Reasoning-Capable Ratification

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096, ADR-0097

---

## Context

The hebrew_greek_textual_reasoning substrate is structurally complete
across four packs:

- `grc_logos_micro_v1`, `grc_logos_cognition_v1`,
  `he_logos_micro_v1`, `he_core_cognition_v1`.
- `teaching/domain_chains/hebrew_greek_textual_reasoning_chains_v1.jsonl`.
- `docs/gaps.md` marks every relevant gap closed:
  `gap:grc_he_glosses_absent`, `gap:grc_he_chains_absent`,
  `gap:grc_logos_micro_v1_gloss_coverage_below_threshold`,
  `gap:grc_logos_cognition_v1_gloss_coverage_below_threshold`,
  `gap:he_logos_micro_v1_gloss_coverage_below_threshold`,
  `gap:he_core_cognition_v1_gloss_coverage_below_threshold`,
  `gap:hebrew_greek_textual_reasoning_causal_chains_below_threshold`,
  `gap:hebrew_greek_textual_reasoning_contradiction_chains_below_threshold`,
  `gap:hebrew_greek_textual_reasoning_intent_shapes_below_threshold`
  — all `[x]`.
- Chain coverage: causal=8, contradiction=8 (≥8 per claimed operator
  family ✓); five intent shapes populated (≥3 ✓).

Unlike `mathematics_logic` / `physics` / `systems_software`, this is a
**multi-pack domain**: `DOMAIN_PACKS["hebrew_greek_textual_reasoning"]`
enumerates four packs. ADR-0091's predicates evaluate per pack; the
ledger row aggregates. Each of the four packs must carry the same
domain contract so the per-pack `core capability domain-contract
validate` passes uniformly.

---

## Decision

Ratify all four hebrew/greek packs as `reasoning-capable` under
ADR-0091 by emitting the contract fields into each manifest. Each pack
declares the same `domain_id`, `teaching_chains`, `eval_lanes`, and
reviewers; the only field that varies per pack is `provenance`
(remains pack-scoped audit trail).

### Manifest additions (all four packs)

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "hebrew_greek_textual_reasoning",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["hebrew_greek_textual_reasoning_chains_v1"],
  "eval_lanes": [
    {"lane": "inference_closure", "version": "v1",
     "splits": ["dev", "public", "holdout"]},
    {"lane": "fabrication_control", "version": "v1",
     "splits": ["dev", "public", "holdout"]}
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0102:reviewed:2026-05-21"
}
```

Claimed operator families (`DOMAIN_OPERATOR_CLAIMS`): `causal`,
`contradiction`. `axioms` and `rules` stay `null` at v1.

### Eval lane scope

Only universal lanes (`inference_closure`, `fabrication_control`) are
declared. The language-specific fluency lanes
(`evals/hebrew_fluency/`, `evals/koine_greek_fluency/`) currently ship
dev/public only — without a sealed holdout split they fail ADR-0091
predicate P7. Adding holdouts to those lanes is a separate ADR; until
that lands, the universal lanes alone are sufficient for
`reasoning-capable` status.

### Pre-existing manifest gap

The four hebrew/greek manifests currently lack a `provenance` field
entirely (unlike the three English domain packs). This ratification
fills that gap as a side-effect; future audits of pack provenance
trails across all packs become uniform.

---

## Invariant

`hebrew_greek_reasoning_capable_ledger_row` — `core capability ledger`
emits a row for `domain_id: hebrew_greek_textual_reasoning` with
`status: reasoning-capable`, provenance pointing at this ADR (uniform
across all four packs), and `expert_demo: False` until a future ADR
attaches the required reports.

`hebrew_greek_pack_contracts_uniform` — all four packs declare
identical contract fields (except provenance audit trail), so
multi-pack ratification cannot drift between packs without an
explicit ADR.

---

## Lane

No new lane. Existing lanes carry the evidence:

- `inference_closure/` (composition)
- `fabrication_control/` (negative control, ADR-0096)
- `evals/domain_contract_validation/` (ADR-0093 confirms predicates
  fire on each of the four packs)

---

## Consequences

- First multi-pack domain ratification. Demonstrates the contract
  works the same way for single-pack and multi-pack domains.
- All four hebrew/greek manifests gain a provenance field.
- Future language-specific eval lanes (Hebrew, Koine Greek) can be
  added to the contract once they ship holdout splits.

---

## PR Checklist

- Capability added: fourth ratified `reasoning-capable` domain,
  multi-pack.
- Invariants proved: `hebrew_greek_reasoning_capable_ledger_row`,
  `hebrew_greek_pack_contracts_uniform`.
- Hidden normalization / stochastic fallback / approximate recall /
  unreviewed mutation: none.
- Trust boundary: four manifest edits through reviewed flow;
  checksums unchanged.
