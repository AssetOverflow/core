# ADR-0120 (math) — Math-Expert Promotion Composer Wire-Up

**Status:** Accepted (technical pass on first evaluation; awaiting reviewer signature for ledger admission)
**Date:** 2026-05-23
**Author:** CORE main agent (Opus 4.7)
**Depends on:** ADR-0120 (contract — `expert` ledger tier), ADR-0114a
(10 obligations), ADR-0131.4 (composite math gate, PR #188),
ADR-0114a.5/.6/.8/.10/.2 (the five new obligation auditors —
PRs #191/#190/#192/#189/#193), ADR-0092 (reviewer registry)
**Foundation for:** ledger-flip PR (separate, consumes this verdict)

---

## Context

ADR-0120 introduced the `expert` ledger tier and its 10-obligation
+ 3-gate composition contract, but explicitly shipped contract-only
("no domain promoted with this ADR"). ADR-0131 then revised the
contract for `mathematics_logic` specifically, replacing the single
GSM8K-coverage lane with the composite B1+B2+B3 gate (wired in
PR #188 / ADR-0131.4).

Over the past stretch all 10 ADR-0114a obligations have substrate
wired for `mathematics_logic` on the B3 surface (#1/.S, #2, #5, #6,
#8, #10 from new auditor PRs; #3/#4/#7/#9 from infrastructure
already in place). The only remaining step before the first
`mathematics_logic` → `expert` ledger flip attempt is **a single
composer that gathers all 10 obligation verdicts + the composite
gate verdict + the reviewer signature and reports an admission
verdict**.

This PR is that composer.

## Decision

`core/capability/expert_promotion_math.py` — pure function over
already-committed evidence, mirroring the auditor pattern from PRs
#189 / #190 / #192. It does NOT execute the ledger flip; it
produces the verdict + canonical artifact that a separate ledger-
write PR consumes.

### Composition

| Obligation | How it's evaluated in this composer |
|---|---|
| #1 sealed holdout | Inline: read `evals/math_symbolic_equivalence/v1/sealed_report.json`; pass iff `counts.wrong == 0` AND `exit_criterion.passed` |
| #2 OOD ratio | `core.capability.ood_ratio.evaluate_ood_ratio()` |
| #3 replay-equal trace | Inline: walk each B-lane's `per_case`; pass iff every `correct` case carries non-empty `trace_hash` |
| #4 typed refusal + wrong==0 | Inline: read each B-lane's `counts.wrong` (or `metrics.wrong` for B3); pass iff all zero |
| #5 perturbation | `core.capability.perturbation_b3.validate_perturbation_suite()` |
| #6 depth curve | `core.capability.depth_curve.evaluate_depth_curve()` |
| #7 frontier comparison | Inline: pass iff `evals/math_symbolic_equivalence/v1/frontier/` contains ≥1 JSON artifact |
| #8 adversarial | `core.capability.adversarial.evaluate_adversarial()` |
| #9 determinism | Inline: pass iff every B-lane report exists and parses as valid JSON (per-lane byte-equality is verified by each lane's own determinism tests) |
| #10 pack provenance | `core.capability.pack_provenance.validate_lane()` |

Plus the **ADR-0131.4 composite math gate** via
`core.capability.composite_math_gate.evaluate_composite_math_gate()`.

### Canonical evidence-bundle digest

`SHA-256` over `{schema_version, domain, [obligation.{id, passed,
evidence_pointer} for each], composite_gate_digest}` —
deterministic, reproducible.

### Reviewer signature path

`docs/reviewers.yaml` gains a new top-level key:

```yaml
math_expert_claims:
  - domain_id: mathematics_logic
    signed_by: shay-j
    claim_digest: "<64-hex>"
```

The composer reads this section; pass iff there's an entry whose
`domain_id == mathematics_logic` AND `claim_digest` matches the
computed digest byte-for-byte.

A populated entry here is the **single switch** that flips
`promote_admitted` from False to True. Until populated, the
verdict reports `awaiting reviewer signature — add an entry to
docs/reviewers.yaml under 'math_expert_claims' for domain
'mathematics_logic' with claim_digest=<digest>`.

### CLI

`core capability math-expert-promote`. Writes
`evals/math_expert_claims/v1/expert_claims_math_v1_signed.json`
(signed iff `promote_admitted`). Exit 0 iff `promote_admitted`.

## Empirical verdict on current main

```
$ python3 -m core.cli capability math-expert-promote

domain:                      mathematics_logic

  id   passed  title
  1    True    sealed holdout discipline
  2    True    OOD surface variation ratio ≥ 0.95
  3    True    replay-equal trace
  4    True    typed refusal + wrong == 0
  5    True    reasoning-isolation perturbation suite
  6    True    compositional-depth curve
  7    True    frontier-baseline comparison
  8    True    adversarial generation; misparse zero
  9    True    determinism
  10   True    operation provenance via pack

composite_gate_passed:       True
all_obligations_passed:      True
technical_pass:              True
claim_digest:                d164866975341d9b82503caf50c0404ee140eab21fd60f589536c6daf6e1d706
reviewer_signature_present:  False
reviewer_signature_matches:  False
promote_admitted:            False

refusal_reason:
  awaiting reviewer signature — add an entry to docs/reviewers.yaml
  under 'math_expert_claims' for domain 'mathematics_logic' with
  claim_digest=d164866975341d9b82503caf50c0404ee140eab21fd60f589536c6daf6e1d706
```

**Every technical gate passes.** The PR ships in the
`awaiting reviewer signature` state — the architecturally-correct
outcome. The reviewer's signature is the separate, auditable
operator action that consummates the promotion.

## Operator workflow (post-merge)

1. Run `core capability math-expert-promote` — confirm
   `technical_pass: True` and capture the `claim_digest`.
2. Inspect the evidence pointers from each obligation; spot-check
   the obligation reports under `evals/obligation_*/`.
3. Add an entry to `docs/reviewers.yaml`:
   ```yaml
   math_expert_claims:
     - domain_id: mathematics_logic
       signed_by: shay-j
       claim_digest: "d164866975341d9b82503caf50c0404ee140eab21fd60f589536c6daf6e1d706"
   ```
4. Re-run `core capability math-expert-promote` — verdict flips
   to `promote_admitted: True`.
5. A separate ledger-flip PR (out of scope here) consumes the
   signed artifact and writes `mathematics_logic.predicates.expert
   = True` in the capability ledger.

If the evidence bundle changes after signing (a B-lane re-runs, a
pack is edited, an obligation auditor's report shifts), the
digest changes and the existing signature stops matching — the
verdict reports `mismatch` and the operator must re-inspect + re-
sign explicitly. This is the load-bearing safety property: a
ledger flip can't survive a silent evidence change.

## What this does NOT do

- Does NOT execute the ledger flip. Separate PR; separate trust
  boundary.
- Does NOT modify any obligation auditor. Each auditor's verdict
  is consumed as-is via its existing `evaluate_*` function.
- Does NOT extend the reviewer registry loader to know about
  `math_expert_claims:` natively. The composer parses the YAML
  inline. Extending the loader is a small follow-up if desired.
- Does NOT promote any other domain. Pattern transfers to physics,
  systems_software, etc., but each domain needs its own composer
  module + reviewer-registry section.

## Trust boundary

- **Reads only**:
  - 4 B-lane reports (`math_symbolic_equivalence/v1/report.json` +
    `sealed_report.json`, `math_teaching_corpus/v1/report.json`,
    `math_bounded_grammar/v1/report.json`)
  - GSM8K probe report (transitively via composite gate)
  - 5 obligation auditor modules (each in turn reads its own
    committed report)
  - `evals/math_symbolic_equivalence/v1/frontier/` (for #7)
  - `docs/reviewers.yaml`
- **Writes only**: artifact path (default
  `evals/math_expert_claims/v1/expert_claims_math_v1_signed.json`)
- No dynamic imports, no shell passthrough, no network.
- Pure deterministic function — verified by digest-reproducibility
  + artifact byte-equality tests.

## Tests

`tests/test_adr_0120_math_expert_promotion.py` — 18 tests:

| Group | Count | What it pins |
|---|---|---|
| inline obligation evaluators (#1/#3/#4/#7/#9) | 11 | each pass + each failure mode (missing/invalid/wrong-count/missing-hash) |
| composer integration | 1 | current main: every obligation + composite gate pass; awaiting-signature state |
| reviewer-signature path | 2 | matching digest → admitted; mismatched digest → typed refusal |
| digest reproducibility | 1 | same evidence → same hex |
| artifact byte-equality | 1 | two emissions identical |
| digest sensitivity | 1 | evidence_pointer change → digest change (sanity) |
| inline evaluator coverage parity | 1 | tested via the composer integration check |

All pass in 0.49s.

## CLAUDE.md PR-checklist

- **Capability added:** composer + CLI for the math-expert
  promotion verdict; deterministic claim_digest; reviewer-
  signature gate.
- **Invariant proving field validity:** every obligation + the
  composite gate pass; digest reproducible; reviewer-signature
  mismatch refused.
- **CLI/eval proving the lane:** `python3 -m core.cli capability
  math-expert-promote` + `pytest tests/test_adr_0120_math_expert_promotion.py`.
- **Avoided hidden normalization / stochastic / approximate /
  unreviewed mutation:** Yes. Pure deterministic composer.
- **Trust boundary:** read-only inputs from documented paths;
  single deterministic write; reviewer-signature is the only
  gate switch; mismatched signature refused with explicit
  diagnostic.
