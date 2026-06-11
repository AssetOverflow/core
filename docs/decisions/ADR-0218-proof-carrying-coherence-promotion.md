# ADR-0218 — Proof-Carrying Coherence Promotion (logical arm of ADR-0021 v2)

**Status:** Proposed — NOT ratified. No runtime mutation-path code is
authorized by this document. The PR that introduces this ADR ships only
(a) this proposal and (b) executable proof obligations
(`tests/test_proof_carrying_promotion_obligations.py`, strict-xfail) plus a
new structural invariant (INV-29) that pins the *current* promotion-site
surface before any new promoter exists.
**Date:** 2026-06-11
**Authors:** drafted by agent for architect review (Joshua Shay ratifies)
**Governing issue:** [docs/issues/proof-carrying-coherence-promotion.md](../issues/proof-carrying-coherence-promotion.md)
**Depends on:** ADR-0021 (Epistemic Grade Policy), ADR-0201/0202 (ROBDD
canonicalizer + representation contract), ADR-0203/0204/0205 (proof_chain
phases 2.1–2.3), the propositional entailment operator
(`generate/proof_chain/entail.py`, phase 2.4 — see §Context numbering note),
ADR-0148 (vault promotion policy wiring), INV-21/22/23.

---

## Context

PR #691 corrected the doctrine: a system's own *asserted* output has no
standing, but a claim *deductively entailed* by an already-`COHERENT`
premise set can be machine-certified as a coherence judgment, because for
that subclass the entailment proof **is** the coherence judgment ADR-0021 §3
requires. The governing issue specifies the capability; this ADR proposes
the rulings the issue (§9) demands before any code.

### What exists today (verified 2026-06-11, main@187b008b)

- **Sound + complete propositional engine.**
  `generate/proof_chain/entail.py::evaluate_entailment_with_trace` decides
  `premises ⊨ query` on the ADR-0201 ROBDD keystone. Refusal-first:
  inconsistent premises and out-of-regime input refuse, never guess.
- **A deterministic proof-evidence artifact already exists.**
  `EntailmentTrace` carries `premise_keys`, `conjunction_key`, `query_key`,
  `entailment_check_key`, `refutation_check_key` and a `canonical_json()`
  serialization. Replay re-verification = recompute from `(premises, query)`
  and compare byte-for-byte.
- **proof_chain Phase 2 is NOT a pending prerequisite — it shipped.**
  The issue (§5, §8 P2) treats binding-graph wiring, acyclicity refusal, and
  modus_ponens as a prerequisite still to build. As of ADR-0203/0204/0205
  (all Accepted, 2026-06-02) plus the phase-2.4 entailment operator, all of
  it is implemented and tested (`tests/test_proof_chain_*.py`,
  `tests/test_deductive_logic_entail.py`, `evals/deductive_logic/` SHA-pinned
  lane). What P2 still owes is narrower: a *promotion certificate* binding an
  `EntailmentTrace` to concrete vault entries, plus its replay verifier.
- **Numbering note (cleanup owed, not done here):** the entail.py module
  docstring attributes phase 2.4 to "ADR-0206", which collides with the
  committed `ADR-0206-response-governance-bridge.md`. Phase 2.4 has no
  committed ADR of its own. The PR that lands P2 must fix that docstring to
  cite this ADR's §Interface instead.

### The precedent the issue missed: ADR-0148 already automates a promotion

`VaultStore.promote_eligible_entries(policy)` (ADR-0148, Accepted
2026-05-25) already flips `SPECULATIVE → COHERENT` **in place**, gated by an
energy/coherence-residual policy, called from `chat/runtime.py` behind
`RuntimeConfig.vault_promotion_enabled` (default `False`). Two consequences:

1. "Promotion is curator-mediated today" is not strictly true — an
   energy-arm precedent exists. This ADR positions the logical arm beside
   it, not as the first automation.
2. **ADR-0148 exposed a blind spot in INV-21.** INV-21's AST scan catches
   `*.store(...)` calls. An in-place `epistemic_status` metadata mutation is
   *not* a `store()` call, so the most natural implementation shape for a
   promoter — flip the status on an existing entry — would silently bypass
   the one-mutation-path invariant as written. The issue names INV-21 as
   "highest risk"; in fact INV-21 *cannot see* the riskiest shape.
   **Therefore this proposal introduces INV-29 now** (status-transition
   sites are allowlisted), in the same PR as this document, so the boundary
   exists *before* any promoter does.

## Decision (proposed — each item requires ratification)

### D1. Extend the existing mutation owner; do not add a write path

Promotion is an epistemic-status *transition*, not a new vault write. The
split mirrors ADR-0148's accepted shape — policy decides, vault mutates:

- `teaching/proof_promotion.py` (new, P3): **pure decision logic.** Builds
  and verifies the certificate; performs **no mutation** and holds no vault
  write access. Not a parallel learning path: it produces a decision object
  consumed by the single mutation owner.
- `vault/store.py` (existing INV-21/INV-29 allowlisted module): gains one
  method, `apply_certified_promotion(entry_index, certificate)`, which
  **independently re-verifies the certificate** (recompute the entailment
  trace; compare byte-for-byte; re-check premise statuses) before flipping
  the entry's status. A certificate that does not re-verify mutates nothing.

No INV-21 allowlist change. INV-29's allowlist stays `{vault/store.py}`.

### D2. The reading stays curator-mediated in the first cut

The hazard-bearing step is the NL→proposition reading, not the deduction
(issue §4). P3 ships with:

- Every premise's propositional form is a **curator-certified reading**
  stored with the vault entry (`reading_certified: true` + the certified
  form), never proposer-supplied at decision time.
- The candidate claim's propositional form is likewise a curator-certified
  *reading* (certifying the translation is faithful certifies nothing about
  the claim's coherence — that is exactly the relocation: human certifies
  the reading, engine certifies the entailment).
- Any premise or claim without a certified reading → **refuse, no
  promotion.** Fail-closed is the only failure mode.

A structural (non-curator) reading check is future work and requires its own
ADR; it is out of scope here.

### D3. Exact admissibility predicate

`certify_promotion` promotes **iff all** of the following hold; any failure
refuses (claim stays `SPECULATIVE`):

```text
1. Every premise ref resolves to a stored vault entry, fresh-read at
   decision time, with epistemic_status == COHERENT.
2. Every premise form and the claim form are curator-certified readings
   (D2); forms are taken from the store, never from the proposer.
3. evaluate_entailment_with_trace(premise_forms, claim_form).outcome
   == ENTAILED.   (REFUTED / UNKNOWN / REFUSED never promote.)
4. The embedded EntailmentTrace re-verifies: recomputing from the stored
   forms reproduces canonical_json() byte-for-byte.
5. No proposer-supplied proof / status / confidence field is read by the
   decision. (Echo-and-ignore, as demos/epistemic_truth_state does for
   proposed_state.)
```

`REFUTED` does **not** auto-demote to `CONTESTED` in v1 — demotion is a
separate authority question, recorded as an open item, not smuggled in here.

### D4. The certificate is the audit artifact and folds into the trace hash

`PromotionCertificate` (provisional fields; the strict-xfail tests are the
executable spec and will be reconciled at P3):

```text
claim_form              — certified propositional form of the claim
premise_entry_ids       — vault identities of the premises
premise_forms           — certified forms, as read from the store
premise_statuses        — statuses observed at decision time
entailment_trace        — EntailmentTrace.as_dict()
engine_pin              — the deductive_logic lane SHA in force
decision / reason       — promoted | refused + closed reason vocab
```

The certificate's canonical JSON SHA-256 folds into the turn `trace_hash`
(ADR-0021 §Schema impact already requires status there). Replay re-verifies
the certificate, not just the status.

## Phasing (maps to the PR stack)

- **PR A (this PR).** This proposal + strict-xfail obligations + INV-29.
  No runtime change. Obligation tests xfail today; INV-29 and the honesty
  pins pass today.
- **PR B (landed: `generate/proof_chain/certificate.py`).**
  `PromotionCertificate` + builder + replay verifier as a pure,
  side-effect-free module with its own tests
  (`tests/test_proof_chain_certificate.py`). No promotion, no vault method,
  no status transition anywhere. Reconciliation against the PR-A wording
  ("retires the certificate-shaped xfails only"): every PR-A xfail marker
  binds to the P3 promoter (`teaching.proof_promotion`), which must not
  exist before ratification — so PR B retires **no** markers; the
  certificate-shaped halves of O1/O7 are instead proven for real in the
  dedicated test file.
- **PR C (requires this ADR ratified).** `certify_promotion` +
  `VaultStore.apply_certified_promotion` behind the existing mutation owner.
  Retires all the xfails (strict-xpass forces it); INV-21 allowlist
  unchanged; INV-29 allowlist unchanged; full + deductive lanes wrong=0.
- **PR D.** Local deterministic demo (`demos/` pattern): proposer submits
  claim + proof candidate; CORE ignores the candidate, recomputes, promotes
  or refuses on pinned verification only. No network, no model API, no side
  effects outside the demo arena.

## Proof obligations ↔ tests

| # | Obligation (issue §7) | Test (PR A) | State today |
|---|---|---|---|
| O1 | Entailed-from-COHERENT promotes; artifact re-verifies | `test_O1_*` | xfail(strict) |
| O2 | Consistent-but-not-entailed stays SPECULATIVE | `test_O2_*` | xfail(strict) |
| O3 | Any non-COHERENT premise → refuse | `test_O3_*` | xfail(strict) |
| O4 | Misread premise fails closed | `test_O4_*` | xfail(strict) |
| O5 | Proposer proof/status/confidence ignored, byte-identical decision | `test_O5_*` | xfail(strict) |
| O6 | No new mutation path | INV-21 (existing) + INV-29 (this PR) | passing |
| O7 | Determinism + replay re-verification | `test_O7_*` (promoter: xfail) + `test_pin_entailment_trace_*` (substrate: passing) | split |
| O8 | wrong=0 lanes stay green | existing lane gates + `verify_lane_shas` | passing |

Honesty pins (pass today, flip red the moment the feature is wired without
conscious review): `review_correction` carries status as an input and does
not compute it; `teaching.proof_promotion` does not exist.

## Trust boundary

The untrusted inputs are the proposer's claim text and anything the proposer
attaches (proof candidate, status, confidence). All of it is **data, never
authority**: forms come from curator-certified store state, the proof is
recomputed by the pinned engine, and the decision must be byte-identical
with and without proposer attachments. The reading-certification step is the
explicit hazard surface and refuses on any gap.

## Non-goals

- The geometric arm (`cga_inner ≥ τ`) — separate ADR-0021 v2 work.
- Promotion of generated/asserted output — permanently forbidden.
- Source authority or confidence weighting — permanently forbidden.
- Auto-demotion on REFUTED — open item, not in scope.
- Any structural (non-curator) reading certification — future ADR.

## Ratification checklist (architect)

- [ ] D1 split (pure decider / vault-owned mutation) over the alternative
      (new INV-21 allowlist entry).
- [ ] D2 first cut: reading stays curator-certified; entailment automated.
- [ ] D3 predicate exact as stated (including REFUTED → no transition).
- [ ] D4 certificate fields + trace-hash folding.
- [ ] INV-29 as the permanent transition-site boundary (already shipped in
      the proposing PR as a passing invariant; ratification confirms it).
