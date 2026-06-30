# ADR-0120 — First `expert` Promotion Contract

**Status:** Proposed (contract-only; no domain promoted with this ADR)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Type:** Contract — defines the `expert` ledger tier and the gate that
governs every future promotion to it.
**Depends on:** ADR-0091, ADR-0092, ADR-0106, ADR-0109, ADR-0113,
ADR-0114, ADR-0114a, ADR-0119, ADR-0119.1, ADR-0119.2, ADR-0119.3,
ADR-0119.4, ADR-0119.5, ADR-0119.6, ADR-0119.7, ADR-0119.8

---

## Context

ADR-0113 reserved the `expert` namespace for a future ledger tier
above `audit-passed`. ADR-0114 laid out the seven-phase arc toward
that tier. ADR-0114a enumerated the ten anti-overfitting proof
obligations any `expert` promotion must satisfy. Phase 5 (ADR-0119
and its eight sub-phases) shipped the substrate that mechanically
gates each obligation for the `gsm8k_math` lane.

**All ten ADR-0114a obligations are now discharged on main for the
gsm8k_math lane.** The remaining work is the *promotion contract* —
the artifact that composes the obligations + the lane gate +
reviewer-signed evidence into a single decision that flips a domain
row from `audit-passed` to `expert`.

ADR-0120 ships that contract. It does **not** itself promote any
domain. ADR-0121 will be the first attempt at a worked promotion;
following the ADR-0107 honest-deferral pattern, that attempt may
refuse on a named architectural blocker (current measurement:
0/1319 correct on sealed real GSM8K). That refusal IS the contract
working as designed.

The point of the contract is to **make every future `expert` claim
falsifiable in advance** — the gate refuses or accepts, never
rubber-stamps.

---

## Decision

### The `expert` ledger status

A sixth tier added to `_EXPERT_DOMAIN_STATUSES` in
`core/capability/reporting.py`:

```text
blocked → seeded → grounded → reasoning-capable → audit-passed → expert
```

A domain row carries `predicates.expert = True` only when **every
condition below holds simultaneously**. Failure on any single
condition demotes the row to `audit-passed`. No partial credit; no
"mostly passing"; no exception flags.

### The 10-obligation composition gate

The promotion gate (`evaluate_expert_promotion` in
`core/capability/expert_promotion.py`, new module) requires:

| # | Obligation (ADR-0114a) | Operational check |
|---|---|---|
| 1 | Sealed-holdout discipline | Every lane attached to the domain has an age-encrypted holdout in `evals/<lane>/holdouts/v1/cases.jsonl.age`; the runner refuses to score without `CORE_HOLDOUT_KEY` |
| 2 | OOD surface variation ≥ 0.95 of public | `ood_score.py`'s OOD/public ratio for the domain's lanes ≥ 0.95 |
| 3 | Replay-equal trace | Every `correct` outcome in the lane report carries a `trace_hash`; ADR-0117 verifier confirms byte-equal replay |
| 4 | Typed refusal + `wrong == 0` | Lane report's `wrong_count_is_zero` is `True` on both public and sealed holdout splits |
| 5 | Reasoning-isolation perturbation suite | `perturbation_score.py`'s invariance-preserving rate == 1.0 AND invariance-breaking predictable-change rate == 1.0 |
| 6 | Compositional-depth curve | `depth_curve.py` produces a per-bucket curve; `accuracy(N) ≥ accuracy(depth_1) · (1 − ε)^(N − 1)` for ε = **0.05** (see §"Threshold rationale" below) |
| 7 | Frontier-baseline comparison | `comparison_v1.json` exists with ≥ 3 frontier citations dated 2023 or later; CORE measurement embedded |
| 8 | Adversarial generation; misparse zero | `adversarial/score.py` reports `wrong == 0` across all families; ≥ 30 cases × ≥ 8 families |
| 9 | Determinism | Two runs of the lane runner produce byte-equal `LaneReport.canonical_bytes()` |
| 10 | Operation provenance via pack | Every `SolutionTrace.steps[*].pack_lemma_id` resolves to a real lexicon entry in the domain's operator pack |

Plus three contract-level gates that compose the obligations:

| Gate | Threshold | Rationale |
|---|---|---|
| `audit_passed_holds` | `predicates.audit_passed == True` | Cannot skip the audit tier |
| `correct_rate_minimum` | `correct_rate ≥ 0.60` on the lane's public split AND on the sealed holdout split | See §"Threshold rationale" below |
| `signed_expert_claim` | A reviewer-signed `expert_claims` entry exists in `docs/reviewers.yaml` whose evidence-bundle digest reproduces byte-for-byte | Mirrors ADR-0106 `audit_passed_claims` pattern exactly |

### Threshold rationale

#### `correct_rate ≥ 0.60`

Three candidate floors considered:

| Threshold | Frame | Verdict |
|---|---|---|
| ≥ 0.40 | "Competent middle-school student" | Too low — beats grade-school average but does not exceed weak open-source LLMs. "Expert" loses meaning. |
| **≥ 0.60** | "Above weak open-source LLMs; matches the 'wedge' framing" | **Chosen.** Forces real architecture work, but ratifiable in principle within 2-3 parser-expansion ADRs. |
| ≥ 0.85 | "Frontier-LLM territory" | Too high — would defer the first promotion indefinitely. The gate-as-process story dies. Future amendment can raise the bar as CORE catches up. |

The 0.60 floor is intentionally **above current measurement (0/1319
on real GSM8K)** so the first promotion attempt (ADR-0121) defers
honestly. That deferral is the contract demonstrating its load-
bearing behavior — same load-bearing demonstration ADR-0107 + ADR-0110
provided for `audit-passed`.

A future ADR-0120a amendment may raise the floor (e.g., to 0.85
once CORE reliably catches frontier territory) without changing
the contract's structure.

#### Depth-curve ε = 0.05

The flatness bound: `accuracy(N) ≥ accuracy(depth_1) · (1 − ε)^(N − 1)`.

At ε = 0.05:
- depth_1 = X → depth_8 ≥ X · 0.95⁷ ≈ X · 0.698
- For depth_1 = 0.95: depth_8 ≥ 0.66
- For depth_1 = 0.60: depth_8 ≥ 0.42

Calibrated so a system genuinely reasoning compositionally (like
CORE's deterministic solver) easily passes — current depth-curve on
the public split is 1.0 across all depths 1–8, so flatness ratio is
1.0 (well within ε = 0.05). A frontier LLM with typical 8-step
decay (~30% from depth 1 to depth 8) would fail.

ε = 0.05 may be tightened in a future amendment.

#### Why correct + refused == total (already enforced by `gsm8k_capability_shape`)

The lane gate (ADR-0119.8) already requires
`correct + refused == cases_total` per split. ADR-0120 inherits this
implicitly — a lane that misroutes any outcome cannot reach the
shape gate. No separate ADR-0120 check needed.

### Operational mechanics

`evaluate_expert_promotion(domain_id, registry, lane_reports,
ood_report, perturbation_report, depth_curve_report, frontier_report,
adversarial_report) -> ExpertPromotionVerdict`:

- `passed: bool`
- `reason: str` (empty on pass; first failed check on fail)
- `obligation_results: tuple[(name: str, passed: bool, detail: str), ...]`
- `derived_digest: str | None` (the signed-claim digest the gate
  expected; matches `expert_claims[domain_id].claim_digest` on pass)

The function is pure: same inputs → byte-equal verdict.

### `expert_claims` registry

Adds a third top-level key to `docs/reviewers.yaml`:

```yaml
expert_claims:
  - domain_id: <id>
    evidence_lanes: [<lane_id>, ...]
    evidence_revision: "adr-NNNN:reviewed:YYYY-MM-DD"
    signed_by: <reviewer_id>
    claim_digest: "<64-char SHA-256 hex>"
    correct_rate_at_promotion: <float>
    holdout_correct_rate_at_promotion: <float>
```

The two extra fields (`correct_rate_at_promotion`,
`holdout_correct_rate_at_promotion`) lock in the public number at
promotion time. Future re-runs of the lane must produce a
correct_rate within ε = 0.02 of the locked value (regression
protection); a larger drift demotes the row to `audit-passed`
pending re-promotion.

---

## Templated path for subsequent domains

Once a domain reaches `expert` once, the path for the next
candidate is mechanical:

1. **Substrate per domain.** Author the parser / solver / verifier /
   realizer for the domain (this is genuine engineering, not a
   templated ADR). Each is its own ADR.
2. **Lane scaffolding.** Mirror ADR-0119.2..0119.8 for the new
   lane: corpus, runner, frontier comparison, adversarial,
   depth-curve, sealed test, lane gate.
3. **ADR-0114a obligations.** Discharge each obligation per-lane
   (most can reuse the ADR-0119.x harnesses with new shape entries).
4. **`expert_claims` signing.** Compute digest, sign in reviewers.yaml.
5. **Promotion ADR.** Mirror ADR-0124's structure (the systems_software
   audit-passed promotion is the template for any future promotion ADR).

The contract change is one-time (this ADR). Subsequent promotions
are template-following.

---

## Invariants

### `adr_0120_expert_status_string_reserved`

Until the first successful promotion lands, no domain row carries
`predicates.expert == True`. Tested by an assertion against
`ledger_report()['domains']`.

### `adr_0120_gate_refuses_when_obligation_missing`

For every one of the ten obligations, a synthetic input where that
obligation's report is missing or below threshold produces
`verdict.passed == False` with a reason naming the obligation.
Tested as 10 parametrized cases.

### `adr_0120_gate_refuses_below_correct_rate_floor`

Synthetic inputs with `correct_rate < 0.60` on either public or
holdout refuse with a typed "below threshold 0.60" reason.

### `adr_0120_gate_refuses_below_depth_curve_floor`

Synthetic inputs where any depth bucket fails
`accuracy(N) ≥ accuracy(depth_1) · 0.95^(N-1)` refuse with a typed
"depth-curve below ε bound" reason.

### `adr_0120_signed_claim_required`

Without a signed `expert_claims` entry for the domain, the gate
refuses with "no expert_claims entry for this domain" (mirrors
ADR-0106 §"no audit_passed_claims entry" pattern).

### `adr_0120_digest_recompute_byte_equal`

The promotion gate's derived digest must equal the signed
`claim_digest` byte-for-byte. Same byte-equality discipline as
ADR-0106 §1.5.

### `adr_0120_correct_rate_at_promotion_is_locked`

`expert_claims[*].correct_rate_at_promotion` is the value
`evaluate_expert_promotion` saw when it signed. A future
re-derivation that deviates by more than ε = 0.02 demotes the row.

---

## Acceptance evidence

Accepted when:

- The ADR file exists in `docs/decisions/` and is linked from
  `docs/decisions/README.md`
- ADR-0120 is documentation + contract definition; the IMPLEMENTATION
  (the `evaluate_expert_promotion` module + tests + reporting layer
  integration) ships under ADR-0120a (a follow-up implementation
  ADR, mirroring how ADR-0106 contract and ADR-0093 enforcement were
  split)
- README.md updated to add `expert` to the documented ledger statuses

---

## Consequences

- The `expert` namespace reserved by ADR-0113 is now defined.
  Future capability claims have a concrete falsifiable gate.
- ADR-0121 (first worked promotion attempt; mathematics_logic) can
  now be drafted. It will likely defer honestly on the `correct_rate
  ≥ 0.60` gate — current measurement is 0/1319 on real GSM8K. That
  deferral is the contract working as designed; same load-bearing
  pattern as ADR-0107 → ADR-0110 for `audit-passed`.
- Each subsequent `expert` claim is a mechanical promotion ADR
  (mirror ADR-0124), not new contract work. The arc to multiple
  expert domains becomes a sequence of small PRs rather than
  one-off architectural decisions.
- The `audit-passed` tier remains the load-bearing CORE-vs-LLM
  claim. `expert` is the additional gate that says "and also
  competitive against a public capability benchmark."

---

## Out of scope (for this ADR)

The implementation of `evaluate_expert_promotion` and the reporting-
layer integration. That ships under **ADR-0120a** as a separate PR
to keep the contract change reviewable independently of the code.

Specific calibration of ε (depth-curve flatness) or the
correct-rate floor beyond the chosen 0.60. Both may be amended in
future ADRs as evidence accumulates.

Promoting any specific domain — that's ADR-0121 (math) and its
successors.

---

## Open candidate directions (the post-ADR-0120 sequence)

The natural sequence after this contract lands. Each item is its
own future ADR.

### Phase 1 — Make math's first promotion attempt honest

- **ADR-0121** — first worked attempt to promote `mathematics_logic`
  to `expert`. Likely defers on `correct_rate ≥ 0.60` (current real-
  GSM8K: 0/1319 ≈ 0.0). The deferral is the gate working. The ADR
  names the parser-expansion gap as the specific blocker.

### Phase 2 — Parser expansion to lift the math correct_rate

- Multi-ADR arc. Each ADR adds one construction class (rate /
  comparison / percentage / time-modal / etc.) and re-measures.
  Target: each ADR shows a delta improvement on the sealed-GSM8K
  number. No silent fitting to the holdout — every parser change
  is graded on Obligation #5 (perturbation invariance) and
  Obligation #8 (adversarial misparse zero) before the
  correct_rate lift counts.
- Continues until `correct_rate ≥ 0.60` on sealed GSM8K. Estimate:
  4–8 ADRs.

### Phase 3 — Math promotion succeeds

- **ADR-012N** — successful `mathematics_logic → expert` promotion.
  First domain at `expert_demo = false; audit_passed = true; expert
  = true`.

### Phase 4 — Second expert domain: `symbolic_logic`

**Recommended second pick.** Reasoning:

- Same machinery class as math: a propositional proof is structurally
  a `SolutionTrace`; each step applies an inference rule; pack lemma
  = rule id; replay verifies; tamper detection works.
- Estimated 60–70% of math's substrate cost — grammar simpler,
  fewer constructions, but real engineering work (~5–8 ADRs for
  parser/solver/verifier/realizer + lane scaffolding).
- Public benchmark: ProofWriter (Tafjord et al.), PrOntoQA (Saparov
  et al.), FOLIO. Frontier LLMs have reported (GPT-4 ~85% on
  ProofWriter zero-shot).
- The wedge story extends directly: "LLMs confabulate proof steps;
  CORE refuses or proves byte-equal."

### Phase 5 — Third expert domain: high-stakes refusal-centric

**Recommended third pick: medical-domain factual recall (NOT
diagnosis) OR legal contract analysis.** Reasoning:

- Different architectural shape (graph-of-facts retrieval, not
  arithmetic/proof). New substrate work: ~10–15 ADRs for the pack +
  retrieval engine + verifier + realizer.
- This is where the wedge sharpens to industry-grabbing. "CORE
  refuses unsupported medical claims; frontier LLMs confabulate
  them" is the most compelling possible "this matters" frame.
- Benchmark: MedQA-USMLE (multiple choice; verifiable) for medical;
  LegalBench narrower tasks for legal.
- Risk: a single high-profile misclassification destroys credibility.
  Worth the third slot — after two prior successful promotions have
  validated the substrate-generalization story.

### Phase 6 — Sequence flexibility

This sequence is the **recommended** path. If a strategic moment
demands a public-facing wedge sooner (e.g., investor demo, partner
deal), medical-second is defensible at higher risk. The contract is
indifferent to ordering — every promotion goes through the same
gate.

### Phase 7 — Multi-reviewer threshold signing

Open candidate frontier item carried over from ADR-0105. Currently
every signed claim has one reviewer. A future ADR may amend the
contract to require N-of-M reviewers for `expert` (vs single for
`audit-passed`). Not required by the contract as written; could be
added without breaking existing signed claims.

---

## Why this contract has the shape it does

The whole point of the gate is **falsifiability**. Every check above
can refuse. The combination of:

- An anti-overfit OOD requirement (#2)
- A perturbation suite (#5)
- A depth-curve flatness bound (#6)
- A frontier-baseline disclosure (#7)
- An adversarial misparse-zero check (#8)
- A wrong-zero discipline (#4)
- A sealed-holdout that wasn't seen during dev (#1, #7's data)

...makes "we cheated the gate" structurally hard. The gate refuses
a system that fits the dev set, fits the public set, fits the
holdout, OR misparses on adversarial probes, OR loses accuracy
sharply with reasoning depth. Each obligation closes a class of
overfit attack.

A domain that passes all ten plus the contract gates is not
guaranteed to be "good." It IS guaranteed to be auditable, replay-
deterministic, refusal-aware, surface-invariant, depth-stable,
adversarially robust, frontier-comparable, and reviewer-signed.
That is the wedge.
