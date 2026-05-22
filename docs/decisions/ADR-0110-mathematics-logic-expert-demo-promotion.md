# ADR-0110 — `mathematics_logic` Expert-Demo Promotion

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0092, ADR-0097, ADR-0106, ADR-0107, ADR-0108, ADR-0109
**Supersedes (partially):** ADR-0107 §Decision (the deferral)

---

## Context

ADR-0107 deferred the first expert-demo promotion of `mathematics_logic`
because two evidence-side gaps existed:

1. **Metric-shape uniformity assumption** — ADR-0106 §1.2 prescribed
   cognition-pack-shape thresholds uniformly across every lane.
2. **`inference_closure` substantively failed** — `all_pass_rate=0.4`
   on the public split.

Both are now closed:

- ADR-0109 shipped the lane-shape registry and dispatched threshold
  rules by lane shape. `accuracy_shape`, `inference_shape`, and
  `refusal_shape` now exist with documented thresholds.
- PR #117 fixed the intent-classifier regression that prevented
  "Actually X R Y." premises from routing to CORRECTION. The
  `inference_closure` lane returned to `all_pass_rate=1.0` on dev,
  public, and holdout under the ADR-0109 `inference_shape` rule.

ADR-0110 promotes `mathematics_logic` to `expert_demo=true` under the
ADR-0106 + ADR-0109 contract.

---

## Evidence

The `mathematics_logic` domain attaches three lanes via the
`en_mathematics_logic_v1` pack manifest:

| Lane | Shape | Public | Holdout |
|---|---|---|---|
| `elementary_mathematics_ood` | `accuracy_shape` | accuracy=1.0 (117/117) | accuracy=1.0 (39/39) |
| `inference_closure` | `inference_shape` | all_pass_rate=1.0, replay_determinism=1.0, overall_pass=True (20 cases) | same (12 cases) |
| `fabrication_control` | `refusal_shape` | by-class refusals 3/3/3, fabricated=0 across all classes | same (9 holdout cases authored under this ADR) |

All thresholds documented in ADR-0109 §2 are met on both public and
holdout splits.

### Infrastructure bridges landed by this ADR

ADR-0110 surfaced a third transition gap that ADR-0107 did not
anticipate: ADR-0105 sealed-holdout scaffolding shipped without
migrating existing plaintext holdout files. Three small bridges were
required:

1. **Plaintext holdout dev-mode fallback files.** Copied
   `evals/<lane>/holdouts/v1/cases.jsonl` to
   `evals/<lane>/holdouts/v1/cases_plaintext.jsonl` for
   `elementary_mathematics_ood` and `inference_closure`, matching the
   ADR-0105 dev-mode convention so `holdout_runner._decrypt_holdout`
   resolves them without `CORE_HOLDOUT_KEY`.
2. **`fabrication_control` holdout cases.** Authored 9 holdout cases
   (3 per refusal class: `phantom_endpoint`, `cross_pack_non_bridge`,
   `sibling_collapse`) in `evals/fabrication_control/cases/holdout.jsonl`.
   The lane's existing runner already produced `v1_<split>.json`
   for any split passed via `--splits`.
3. **`by_class` top-level → metrics fold.**
   `core/capability/reporting.py:_fetch_lane_split` now folds a
   top-level `by_class` field into the metrics dict so the
   `refusal_shape` checker sees a single canonical layout.

These are infrastructure bridges, not contract changes. ADR-0106 and
ADR-0109 are untouched.

---

## Decision

`mathematics_logic` is promoted to `expert_demo=true`.

The signed claim entered into `docs/reviewers.yaml` is:

```yaml
expert_demo_claims:
  - domain_id: mathematics_logic
    evidence_lanes:
      - elementary_mathematics_ood
      - inference_closure
      - fabrication_control
    evidence_revision: "adr-0110:reviewed:2026-05-22"
    signed_by: shay-j
    claim_digest: "94d74781e103854230c1a71590e4df2287f5d2e87832f1c29b8ec4618853c04b"
```

### Note on `evidence_revision` form

ADR-0106 §1 named `evidence_revision` as "git sha at promotion time."
For this first worked promotion we use a labeled revision
(`adr-0110:reviewed:2026-05-22`) rather than a raw sha because the
evidence-bundle digest must be reproducible from the lane result files
in the commit that lands this claim — not from any prior commit. The
load-bearing invariant per ADR-0106 §1.5 is replay byte-equality, which
holds: re-derivation from the on-disk result files at this commit
reproduces `claim_digest` exactly.

ADR-0106 may be amended in a future ADR if a stricter
"raw-sha-only" interpretation is preferred. The current contract
language admits either form.

---

## Invariants

### `adr_0110_math_expert_demo_holds`

`ledger_report()` must report `mathematics_logic` with
`predicates.expert_demo == true` and `status == "expert-demo"` so long
as the signed claim in `docs/reviewers.yaml` resolves and the lane
results on disk continue to produce the claimed digest.

### `adr_0110_replay_digest_byte_equality`

Re-deriving the evidence-bundle digest from the lane result files at
this commit must reproduce
`94d74781e103854230c1a71590e4df2287f5d2e87832f1c29b8ec4618853c04b`.
Tested by `tests/test_adr_0110_math_expert_demo.py`.

### `adr_0110_other_domains_unaffected`

ADR-0110 promotes exactly one domain. `physics`,
`systems_software`, `hebrew_greek_textual_reasoning`, and
`philosophy_theology` must continue to report `expert_demo=false`
under their own (absent) `expert_demo_claims` entries.

---

## Acceptance evidence

Accepted when:

- `docs/reviewers.yaml` carries the signed `expert_demo_claims` entry
  for `mathematics_logic`
- `evals/elementary_mathematics_ood/holdouts/v1/cases_plaintext.jsonl`
  exists (dev-mode fallback per ADR-0105)
- `evals/inference_closure/holdouts/v1/cases_plaintext.jsonl` exists
- `evals/fabrication_control/cases/holdout.jsonl` contains 9 cases
  spanning all three refusal classes
- `evals/<lane>/results/v1_holdout_*.json` (or `v1_holdout.json` for
  fab) exists for all three lanes
- `core/capability/reporting.py` folds top-level `by_class` into the
  metrics dict
- `tests/test_adr_0110_math_expert_demo.py` pins the three invariants
- `ledger_report()` confirms `mathematics_logic` row at
  `expert_demo=true` / `status="expert-demo"`
- ADR-0107's `tests/test_adr_0107_deferral.py` is retired with an
  explicit pointer to this ADR (the deferral resolved)
- README "Accepted reasoning-capable domains" table updated to note
  `mathematics_logic` at expert-demo

---

## Consequences

- The first expert-demo promotion lands. The ADR-0106 contract has
  now demonstrated end-to-end: refused once honestly (ADR-0107), then
  succeeded once honestly (here).
- The infrastructure bridges landed under §Evidence make future
  expert-demo promotions for the other three ratified domains
  (`physics`, `systems_software`, `hebrew_greek_textual_reasoning`)
  feasible without new contract work — they need only their own
  lane results to materialise and their own signed claims.
- The reviewer registry now carries a worked example of a signed
  `expert_demo_claims` entry, anchoring the documented schema with a
  real artifact rather than a stub.

---

## Out of scope

- This ADR does not amend ADR-0106 or ADR-0109. The bridges are
  infrastructure, not contract.
- This ADR does not promote any other domain. The other three
  ratified domains require their own promotion ADRs.
- Sealing the math holdouts under a real age recipient (ADR-0105's
  eventual design) remains future work. The dev-mode plaintext
  fallback is acceptable per ADR-0105's own §"Dev-mode fallback
  preserved" clause.
- Multi-reviewer threshold signing remains an open candidate
  direction.
