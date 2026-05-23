# ADR-0121 — `mathematics_logic` `expert` Promotion — Deferred (first attempt)

**Status:** Accepted (the deferral is the decision)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:** ADR-0107 (the same pattern for `audit-passed`),
ADR-0110 (math audit-passed promotion), ADR-0114, ADR-0114a,
ADR-0119 (+ all 8 sub-phases), ADR-0120 (first `expert` promotion
contract)
**Supersedes:** none

---

## Context

ADR-0120 defined the `expert` promotion contract: a 13-check gate
that composes ADR-0114a's 10 anti-overfitting obligations with three
contract-level requirements (`audit_passed` holds, `correct_rate ≥
0.60` on public AND sealed holdout, signed `expert_claims` entry
with reproducible digest).

This ADR is the **first worked attempt** at promoting a domain
under that contract. Following the doctrine the project has now
established **twice** (ADR-0107 → ADR-0110 for math audit-passed;
ADR-0122 → ADR-0124 for systems_software audit-passed), the first
attempt may defer honestly on a named architectural blocker. That
deferral is the contract working as designed — not a setback.

The candidate is `mathematics_logic` because:
- It is already at `audit-passed` (ADR-0110)
- Its lanes carry the most complete substrate (ADR-0119 + 8 sub-phases)
- It has the only sealed external benchmark (real GSM8K test, ADR-0119.7)
- The framing arc started here (ADR-0114 picked it as the first
  expert-capability target)

---

## Attempt

Evaluating each ADR-0120 gate against the live state of `main`:

### ADR-0114a obligations (10 of 10 pass)

| # | Obligation | Live measurement | Threshold | Pass? |
|---|---|---|---|---|
| 1 | Sealed-holdout discipline | `gsm8k_math/holdouts/v1/cases.jsonl.age` exists; runner refuses without `CORE_HOLDOUT_KEY` | encrypted seal in place | ✓ |
| 2 | OOD surface variation ≥ 0.95 of public | OOD/public ratio = 1.00 (150/150 across 3 transform families) | ≥ 0.95 | ✓ |
| 3 | Replay-equal trace | ADR-0117 verifier passes on every public-split correct outcome | byte-equal replay | ✓ |
| 4 | Typed refusal + `wrong == 0` | public 150/150 correct, **0 wrong**; sealed 0/1319 correct, **0 wrong** | `wrong == 0` both splits | ✓ |
| 5 | Reasoning-isolation perturbation suite | invariance-preserving 207/207, invariance-breaking 17/17 | 1.0 each | ✓ |
| 6 | Compositional-depth curve flatness | depth 1–8 all at rate 1.0 on public (perfectly flat) | `accuracy(N) ≥ accuracy(d1)·0.95^(N-1)` | ✓ |
| 7 | Frontier-baseline comparison | `comparison_v1.json` with 3 citations dated 2023+; CORE measurement embedded | ≥3 citations, dated 2023+ | ✓ |
| 8 | Adversarial generation; misparse zero | 38 cases × 12 families; correct 5, **wrong 0**, refused 33 | `wrong == 0` | ✓ |
| 9 | Determinism | runner + solver + verifier + realizer all byte-equal across two runs | byte-equal | ✓ |
| 10 | Operation provenance via pack | every step's `pack_lemma_id` resolves in `en_arithmetic_v1` | resolves | ✓ |

All 10 obligations discharged.

### ADR-0120 contract-level gates (1 pass, 2 fail)

| Gate | Live measurement | Threshold | Pass? |
|---|---|---|---|
| `audit_passed_holds` | `predicates.audit_passed == True` (since ADR-0110) | must hold | ✓ |
| `correct_rate_minimum` (public ≥ 0.60) | public correct_rate = 1.0 (150/150) | ≥ 0.60 | ✓ |
| `correct_rate_minimum` (holdout ≥ 0.60) | **sealed-holdout correct_rate = 0.0 (0/1319)** | ≥ 0.60 | **✗** |
| `signed_expert_claim` | no `expert_claims` entry for `mathematics_logic` | signed claim required | **✗** |

The substantive blocker is the **sealed-holdout correct_rate gate**.
The signed-claim gate is downstream — no reviewer signs a claim
whose underlying measurement doesn't meet the contract.

---

## Decision

`mathematics_logic` is **NOT promoted to `expert`.** The contract
refuses. The ledger row remains at `audit-passed`.

The gate's named blocker:

> "lane `gsm8k_math` correct_rate on sealed holdout = 0.0 (0/1319),
> below contract threshold 0.60."

This is the contract working as designed. ADR-0120 §"Threshold
rationale" deliberately set the floor above current measurement
specifically so the first promotion attempt would defer honestly.

---

## What this proves (and what it doesn't)

### Proves

- The substrate is complete enough that the gate has *all the inputs
  it needs to make a decision* — there's no "missing obligation"
  excuse. All 10 ADR-0114a obligations are mechanically verifiable
  on disk. The deferral is a substantive judgment about capability,
  not a process gap.
- CORE's wrong-zero discipline holds against a real external
  benchmark. On 1,319 real GSM8K test problems, the system refuses
  every one it can't grammar-handle without confabulating on a
  single one. That property is more rare and more valuable than the
  correct_rate gate.
- The contract is genuinely falsifiable. A weaker gate would have
  rubber-stamped the promotion on the strength of the obligations
  alone. ADR-0120's floor refuses honestly.

### Does NOT prove

- That CORE will never reach `expert` on math. It explicitly will,
  once the parser grammar covers enough GSM8K-style constructions
  to lift the sealed-holdout correct_rate above 0.60.
- That the 0.60 floor is the right number forever. ADR-0120 §"Open
  candidate directions" notes that the floor may be raised in a
  future amendment as CORE catches up.
- Anything about the other audit-passed domains (physics,
  systems_software). They have their own promotion ADRs ahead of
  them and their own substrate gaps.

---

## What would unlock the promotion

A multi-ADR **parser-expansion arc** lifting the sealed-GSM8K
correct_rate from 0.0 to ≥ 0.60. Each ADR in the arc adds one
construction class to the parser grammar:

1. **Rate / per-unit reasoning** ("Each item costs $2; X buys 4")
2. **Comparison phrasing** ("X has 3 more than Y")
3. **Percentage / fraction** ("Half the apples", "20% of N")
4. **Time-modal / temporal** ("How long does it take?")
5. **Multi-step conditional** ("If X then ...")
6. **Set / collection language** ("The students who passed ...")
7. **Aggregation / summation** ("In total, after N steps ...")
8. **Unit conversion** ("How many minutes in an hour ...")

Each ADR ships:
- A grammar extension (parser + solver + verifier + realizer
  updates)
- A re-measurement on the sealed holdout (single number: new
  `correct_rate`)
- An ADR-0118a OOD re-measurement (no surface-feature regression)
- An ADR-0125 perturbation re-measurement (no invariance regression)
- An ADR-0119.5 adversarial re-measurement (no new misparses)

**The honest-fitting discipline:** every expansion is graded on
ADR-0114a #2 / #5 / #8 BEFORE the correct_rate lift counts. A
correct_rate lift accompanied by an OOD regression IS a regression,
not progress. This is the structural defense against silent
overfitting to the sealed holdout.

Estimated number of expansion ADRs to reach 0.60: 4–8. Honest
acknowledgment: nobody knows in advance. The arc lifts the number,
each lift gets reviewed against the anti-overfit obligations,
eventually crosses 0.60 — or doesn't, in which case the contract
remains refusing and we update the ADR-0114 roadmap with the
learned constraint.

---

## Invariants

### `adr_0121_math_remains_at_audit_passed`

`ledger_report()` reports `mathematics_logic` with `status ==
"audit-passed"` and `predicates.audit_passed == True`. The
hypothetical `predicates.expert` either does not exist yet (until
ADR-0120a implementation lands) or is `False`. Tested by
`tests/test_adr_0121_math_expert_deferred.py`.

### `adr_0121_sealed_correct_rate_below_floor`

Running the lane runner against the sealed GSM8K test (decrypted
with `CORE_HOLDOUT_KEY`) yields `correct_rate < 0.60`. The
specific measurement today is `0.0` (0/1319). The test pins
"< 0.60" rather than the literal `0.0` so future parser-expansion
work that lifts the number doesn't break the test; the test fails
only when the gate would now pass (i.e., when this deferral ADR
should be superseded by a successful promotion).

### `adr_0121_no_signed_expert_claim_for_math`

`docs/reviewers.yaml` carries no `expert_claims` entry for
`mathematics_logic`. (The `expert_claims` key may not yet exist in
the registry — both states are valid representations of "not
promoted.")

### `adr_0121_other_obligations_still_pass`

The 10 ADR-0114a obligations all still pass for the gsm8k_math
lane. The deferral is on the correct_rate gate alone, not on a
substrate regression. Indirectly tested by the existing Phase 5
test suite (74 cases on main); this ADR adds a single roll-up
assertion that the existing tests collectively pass.

### `adr_0121_wrong_zero_holds_against_real_gsm8k`

The runner's `wrong` count on the sealed GSM8K test is 0. This is
the *load-bearing positive claim* of ADR-0121 — even though the
contract refuses, the wrong-zero discipline holds. Tested
directly.

---

## Acceptance evidence

- This ADR file exists in `docs/decisions/` and is linked from
  `docs/decisions/README.md`
- `tests/test_adr_0121_math_expert_deferred.py` pins the five
  invariants above; passes locally with `CORE_HOLDOUT_KEY` set;
  skips the decryption-dependent invariants gracefully without it
- `ledger_report()` continues to report `mathematics_logic` at
  `status == "audit-passed"` (no regression)
- README updated to mention the deferral

---

## Consequences

- The `expert` ledger tier remains unoccupied. No domain is at
  `predicates.expert == True` on main.
- ADR-0120's contract has now demonstrated its load-bearing behavior
  by refusing once. Same pattern as ADR-0107 demonstrated for
  audit-passed.
- The parser-expansion arc (Phase X of ADR-0114) is now the named
  bottleneck for the first `expert` promotion. Each expansion ADR
  is a concrete piece of work; the path is no longer abstract.
- External readers can read this ADR and see (a) the substrate is
  complete, (b) the gate refused honestly, (c) the specific number
  that needs to lift. That's a stronger story than "we promoted
  the domain because the substrate exists."

---

## Out of scope

- The parser-expansion ADRs themselves. Each construction class
  gets its own scoped ADR (estimated 4–8 total before the gate
  passes).
- The `evaluate_expert_promotion` module + reporting integration
  (ADR-0120a, separate PR).
- Any other domain's promotion (`physics`, `systems_software`).
  Both stay at `audit-passed`. Their own promotion ADRs are future
  work after `mathematics_logic` succeeds.
- Raising the 0.60 floor or tightening ε. Future ADR-0120 amendments
  if the calibration is ever revisited.
- The second-domain choice (`symbolic_logic` is recommended per
  ADR-0120 §"Open candidate directions" Phase 4; that work begins
  after this deferral resolves).

---

## Why "the contract refused" is the right outcome

The strongest claim CORE can make about any future `expert`
promotion is: **"this promotion happened because the gate accepted,
not because the substrate existed."** That distinction requires the
gate to have shown it CAN refuse. ADR-0107 demonstrated this for
`audit-passed`; ADR-0121 now demonstrates it for `expert`.

Every future `expert` claim — math, symbolic_logic, medical, any
domain — inherits this credibility. The reader who looks at a
future `expert` row in the ledger sees an artifact that:

1. Cleared all 10 ADR-0114a obligations
2. Cleared the contract-level gates (including correct_rate ≥ 0.60)
3. Reproduces from a signed digest
4. Could have been refused under the same gate (because the gate
   refused at least once before)

The deferral here is what makes that fourth property hold. Without
it, "expert" would be a status the project hands out by default to
any substrate-complete lane. With it, `expert` is something the
gate decided to accept — and the gate has a track record of saying
no.

Both the audit-passed and expert tiers now have at least one
worked refusal in their history. The promotion machinery is
demonstrably load-bearing across both ceilings.
