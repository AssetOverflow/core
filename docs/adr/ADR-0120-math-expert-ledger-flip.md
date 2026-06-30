# ADR-0120 (math, ledger flip) — Mathematics-Logic Domain Promoted to `expert`

**Status:** Accepted — first `expert`-tier domain in the capability ledger
**Date:** 2026-05-23
**Author:** CORE main agent (Opus 4.7) + reviewer (shay-j)
**Depends on:** ADR-0120 (expert tier contract), ADR-0120-math
(composer, PR #194), ADR-0131.4 (composite math gate, PR #188),
ADR-0114a.{1,2,3,4,5,6,7,8,9,10} (obligation auditors)
**Predecessor PRs:** #173, #176-#180, #182-#194

> **Reconciliation note (ADR-0200, 2026-06-02).** This flip was **valid when it
> was made** (2026-05-23 / #267): code + evidence reproduced the signed digest
> `4c46f530...` exactly, and the empirical verdict below was correct *at that
> commit*. It has since **auto-reverted to `audit-passed`.** The GSM8K coverage
> probe drifted (`3/47 -> 4/46`, PRs #310/#488), changing the evidence-derived
> digest to `02f6d3c8...`; the signature no longer matches and the composer
> refuses — ADR-0120's documented fail-closed property firing as designed.
> **Current ledger status: `audit-passed`.** The empirical block below is
> preserved as the historical record. See
> [ADR-0200](ADR-0200-expert-claim-reconciliation.md) and the
> [claims ledger](../claims_ledger.md).

---

## Context

After all 10 ADR-0114a obligation auditors + the ADR-0131.4 composite
gate + the ADR-0120-math composer (#194) landed, three pieces
remained before the first-ever ledger flip:

1. The reviewer signature itself (operator-only action).
2. The capability ledger's `_EXPERT_DOMAIN_STATUSES` tuple still
   topped out at `"audit-passed"`; the `expert` tier was reserved
   but never wired into the row construction.
3. A digest-stability bug: PR #194's composer baked absolute
   filesystem paths into the `claim_digest`, which would have made
   any operator's signature fail on any other operator's checkout.

This PR closes all three.

## Decision

### 1. Reviewer signature (operator action by shay-j)

`docs/reviewers.yaml` now carries the signed
`math_expert_claims` entry:

```yaml
math_expert_claims:
  - domain_id: mathematics_logic
    evidence_lanes:
      - math_symbolic_equivalence/v1 (public)
      - math_symbolic_equivalence/v1 (sealed)
      - math_teaching_corpus/v1
      - math_bounded_grammar/v1
    evidence_revision: "adr-0120-math:reviewed:2026-05-23"
    signed_by: shay-j
    claim_digest: "94149794e8c19896851e062cf1f921cfa9ba04770b674bc3b4c33023f7c7331b"
```

### 2. Ledger row gains an `expert` tier

`core/capability/reporting.py`:

- `_EXPERT_DOMAIN_STATUSES` extended with `"expert"` (now 6 tiers).
- New `_EXPERT_COMPOSERS: dict[str, str]` registry — per-domain
  module name of the expert composer. Currently only
  `mathematics_logic → core.capability.expert_promotion_math`.
- New `expert` predicate computation in `_compute_domain_row`:
  - Gated on `audit_passed=True` (strict super-tier).
  - Calls the registered composer's
    `evaluate_math_expert_promotion()` and reads
    `promote_admitted` as the verdict.
  - Fail-closed on exception or missing composer.
- New `expert_reason` field on the row mirroring `audit_passed_reason`.
- `status = "expert"` when the predicate passes.
- `predicates: { ..., "expert": <bool> }` added.

### 3. Path-stability fix (digest filesystem-independence)

Both `core/capability/composite_math_gate.py` and
`core/capability/expert_promotion_math.py` now use a `_rel(path)`
helper that returns the **repo-root-relative POSIX string**
instead of `str(path)`. The `claim_digest` SHA-256 commits to
these relative strings, so:

- Operator A on `~/work/core` and Operator B on `/srv/checkouts/core`
  now compute the **same digest** for identical evidence.
- Re-signing isn't needed on every checkout.
- The `evidence_revision` field tells operators when the bundle
  semantically changed; the digest tells them whether their on-
  disk bytes still match what the signer endorsed.

### 4. Reviewer-registry allow-list extended (regression fix)

`ALLOWED_TOP_LEVEL_KEYS` in `core/capability/reviewers.py` now
includes `"math_expert_claims"`. PR #194 added the section to
`docs/reviewers.yaml` but **didn't extend the loader's allow-list**
— a real regression that silently broke the `audit_passed`
predicate for all 3 prior domains (mathematics_logic, physics,
systems_software) since the loader rejected the whole file and
the catch-all `_load_registry_for_expert_demo` returned an empty
registry. This PR's `test_allowed_top_level_keys_includes_math_expert_claims`
regression-pins the fix.

## Empirical verdict on current main (after this PR)

```
$ python3 -c "from core.capability import ledger_report; \
              import json; r = ledger_report(); \
              row = next(d for d in r['domains'] if d['domain'] == 'mathematics_logic'); \
              print(json.dumps({k: row[k] for k in ('domain','status','predicates','expert_reason')}, indent=2))"

{
  "domain": "mathematics_logic",
  "status": "expert",
  "predicates": {
    "seeded": true,
    "grounded": true,
    "reasoning_capable": true,
    "audit_passed": true,
    "expert": true
  },
  "expert_reason": "ADR-0120-math composer admitted"
}
```

**`mathematics_logic` is now the first `expert`-tier domain in the
capability ledger.**

## GSM8K — honest disclosure unchanged

The same `core capability math-expert-promote` artifact carries the
GSM8K probe's `honest_disclosure` block, which today reports
`admission_rate: 0/50, wrong: 0, safety_rail_intact: true,
substrate: candidate_graph`. **GSM8K does not gate** per ADR-0131;
it's reported as honest disclosure. Probe admission lift will
accumulate naturally as the parser layer matures (bounded pronoun
coreference is the highest-leverage next item — ~28% of GSM8K
refusals would route through it).

## What this PR does NOT do

- Does NOT promote any other domain. The pattern transfers, but
  each domain needs its own composer module + reviewer-registry
  section.
- Does NOT auto-promote on subsequent evidence-bundle changes. If
  any B-lane re-runs (different correct/wrong/refused counts), the
  composer's digest changes and the existing signature stops
  matching — the verdict flips back to "awaiting reviewer
  signature" and the ledger row drops back to `audit-passed`. This
  is the load-bearing safety property.
- Does NOT remove the auto-mode safeguard that blocks the
  composer-agent from self-signing. The signature stays a
  human-only action; this PR carries the signature only because
  the reviewer (shay-j) explicitly performed it.

## Trust boundary

- **Reads**: full obligation auditor reports + composer evidence +
  `docs/reviewers.yaml` (transitively via the existing registry
  loader)
- **Writes**: artifact path only (default
  `evals/math_expert_claims/v1/expert_claims_math_v1_signed.json`)
- No new dynamic imports beyond what `_EXPERT_COMPOSERS` declares
  (a single allow-listed module name); the lookup is fail-closed
  if a domain isn't registered.
- Pure deterministic — verified by digest reproducibility +
  artifact byte-equality + filesystem-independence tests.

## Tests

`tests/test_mathlogic_expert_ledger_flip.py` — 12 tests:

| Group | What it pins |
|---|---|
| Allow-list regression | `math_expert_claims` is in `ALLOWED_TOP_LEVEL_KEYS`; reviewers.yaml loads after fix |
| Tier wiring | `expert` is in `_EXPERT_DOMAIN_STATUSES`; ordered after `audit-passed`; `mathematics_logic` composer registered |
| Path-stability | `_rel()` returns repo-relative POSIX; falls back to absolute outside repo; composer + composite-gate digests use relative paths only |
| Snapshot pass | `mathematics_logic.status == "expert"`; `predicates.expert == True`; row carries `expert_reason` |
| Other domains | non-mathematics_logic domains keep `expert: False` (no composer wired) |
| Refusal mode | without a matching signature, composer reports `promote_admitted: False` with awaiting-signature message |

Plus the prior #194 snapshot test updated to reflect the new
post-signature state (`promote_admitted: True`).

Full regression: **174/174 tests pass** across this PR's tests +
ADR-0120 composer (#194) + all 5 obligation auditors + composite
gate + existing expert-demo / reviewer-registry / ADR-0110 / ADR-0111
/ ADR-0121 (math/physics/deferred).

## CLAUDE.md PR-checklist

- **Capability added:** first ledger flip to `expert` tier;
  per-domain composer registry pattern future domains can adopt;
  fixed two real bugs (path-instability + allow-list regression)
  surfaced during the flip.
- **Invariant proving field validity:** ledger reports `expert`
  iff and only iff signed evidence + every auditor pass;
  composer digest filesystem-independent; allow-list permits
  schema extension without silent failure.
- **CLI/eval proving the lane:**
  `python3 -m core.cli capability math-expert-promote` +
  `pytest tests/test_mathlogic_expert_ledger_flip.py`.
- **Avoided hidden normalization / stochastic / approximate /
  unreviewed mutation:** Yes. The signature is operator-only;
  the auto-mode safeguard explicitly blocks the agent from
  self-signing; the bug fixes preserve every existing invariant.
- **Trust boundary:** read-only inputs from documented paths;
  single deterministic write; signature remains the only gate
  switch; mismatched signature refused with explicit diagnostic.
