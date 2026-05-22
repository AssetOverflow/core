# ADR-0097 — Mathematics-Logic Reasoning-Capable Ratification

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0093, ADR-0096

---

## Context

The mathematics/logic substrate is more complete than recent planning
documents acknowledged:

- `language_packs/data/en_mathematics_logic_v1/` ships with manifest,
  lexicon, glosses.
- `teaching/domain_chains/mathematics_logic_chains_v1.jsonl` exists.
- `evals/elementary_mathematics_ood/` exists.
- `docs/gaps.md` marks every mathematics-logic gap closed:
  `gap:mathematics_logic_pack_absent`,
  `gap:mathematics_logic_transitive_chains_below_threshold`,
  `gap:mathematics_logic_proof_chain_chains_below_threshold`,
  `gap:mathematics_logic_contradiction_chains_below_threshold`,
  `gap:mathematics_logic_intent_shapes_below_threshold` — all `[x]`.

What is missing is the formal ratification step under ADR-0091. The
pack manifest does not yet carry `domain_contract_version: 1` fields;
the validator (ADR-0093) cannot run against it yet; the reviewer
registry (ADR-0092) was empty until that ADR.

This ADR is the first concrete domain claim under the Domain Pack
Contract. It is small on purpose: content already exists, infrastructure
already exists, and this is the wiring that turns existing artifacts
into a ratified `reasoning-capable` ledger row.

---

## Decision

Ratify `en_mathematics_logic_v1` as `reasoning-capable` under
ADR-0091 by emitting the contract fields into its manifest and passing
`core capability domain-contract validate en_mathematics_logic_v1`.

### Manifest additions

```jsonc
{
  "domain_contract_version": 1,
  "domain_id": "mathematics_logic",
  "axioms": null,
  "rules": null,
  "teaching_chains": ["mathematics_logic_chains_v1"],
  "eval_lanes": [
    {
      "lane": "elementary_mathematics_ood",
      "version": "v1",
      "splits": ["dev", "public", "holdout"]
    },
    {
      "lane": "inference_closure",
      "version": "v1",
      "splits": ["dev", "public", "holdout"]
    },
    {
      "lane": "fabrication_control",
      "version": "v1",
      "splits": ["dev", "public", "holdout"]
    }
  ],
  "reviewers": ["shay-j"],
  "known_gaps": [],
  "provenance": "adr-0097:reviewed:2026-05-21"
}
```

`axioms` and `rules` stay `null` at v1. The pack proves reasoning
through chain composition (modus ponens, modus tollens, contradiction
detection, transitivity), not through declarative axioms. A future
ADR may add explicit axioms; this one does not.

### Required existing evidence (no new content)

- `mathematics_logic_chains_v1.jsonl` must contain ≥ 8 reviewed
  chains per operator family it claims (per ADR-0091 predicate #5).
  If it does not, ratification is blocked. Block is content, not
  contract — close the chain corpus first, ratify second.
- ≥ 3 intent shapes present (per predicate #6). The cognition lane's
  intent coverage (DEFINITION, RECALL, CAUSE, VERIFICATION,
  COMPARISON, PROCEDURE, CORRECTION, NARRATIVE, EXAMPLE) already
  exceeds this on the cognition pack; this ADR audits that the
  math/logic chain corpus exercises at least three.
- Three-split eval lane referenced. `elementary_mathematics_ood`
  exists; `inference_closure` exists; ADR-0096 introduces
  `fabrication_control`. Holdout paths verified non-empty.

### What this ADR does not do

- Does not introduce new lemmas, chains, or evals.
- Does not promote to `expert-demo`. That requires audit-tour-equivalent
  reports — separate ADR.
- Does not modify the runtime. Pack mounting behavior is unchanged.

---

## Invariant

`mathematics_logic_reasoning_capable_ledger_row` — running
`core capability ledger` emits a row for `domain_id: mathematics_logic`
with `status: reasoning-capable`, with provenance pointing at this
ADR, and refuses to advance to `expert-demo` until a future ADR
attaches the required reports.

---

## Lane

No new lane. Existing lanes carry the evidence:

- `elementary_mathematics_ood/` (positive coverage)
- `inference_closure/` (composition)
- `fabrication_control/` (negative control, ADR-0096)
- `evals/domain_contract_validation/` (ADR-0093 confirms predicates fire)

CLAIMS.md Tier 2 gains one row pointing at the four lanes and this
ADR.

---

## Trust Boundary

Manifest edit is a reviewed proposal. Checksum refresh per
ADR-0027/0029 discipline. No runtime mount path changes. No new
filesystem writes outside the manifest and its checksum companion.

---

## Consequences

- First `reasoning-capable` row in the capability ledger backed by an
  ADR-0091-validated pack.
- Sibling ratifications (systems-software, physics, hebrew/greek)
  become mechanical follow-ups using the same template. Each one is
  its own ADR but each is small.
- The public showcase demo (ADR-0099) gains a real domain to draw
  Scene 4 from.

---

## PR Checklist

- Capability added: first ratified `reasoning-capable` domain claim.
- Invariant proved: `mathematics_logic_reasoning_capable_ledger_row`.
- Lanes proving it: four existing lanes plus ADR-0093 contract validator.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none. Ratification is the reviewed proposal.
- Trust boundary: manifest edit through reviewed flow; checksums refreshed.
