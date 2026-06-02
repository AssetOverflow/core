# ADR-0200 — Expert-Claim Reconciliation: Record the Fail-Closed Revert as Designed Behavior

**Status:** Proposed (review-gated — every claim/test change below awaits operator ratification)
**Date:** 2026-06-02
**Author:** CORE main agent (Opus 4.8) + reviewer (shay-j)
**Depends on:** ADR-0120 (expert tier contract + ledger flip), ADR-0131.4 (composite math gate), ADR-0131.5 (GSM8K probe retirement), ADR-0113 (audit-passed naming), ADR-0119.7 (sealed GSM8K)
**Companion:** [`docs/claims_ledger.md`](../claims_ledger.md)

---

## 1. Context

On 2026-05-23, `mathematics_logic` was signed and promoted to the `expert`
ledger tier (ADR-0120 ledger flip) — the first-ever flip. As of 2026-06-02 the
live ledger reports it as **`audit-passed`**, and the expert composer refuses:

> `reviewer claim_digest mismatch — registry has '4c46f530…', evidence-derived
> digest is '02f6d3c8…'; the evidence bundle has changed since the signature was
> added.`

This is **not a regression to fix.** It is ADR-0120's load-bearing safety
property firing exactly as documented ("Does NOT auto-promote on subsequent
evidence-bundle changes … the verdict flips back … and the ledger row drops back
to `audit-passed`. This is the load-bearing safety property"). The system
**revoked its own expert claim** when its evidence drifted.

The problem this ADR solves is **documentary drift**, not engine behavior: several
committed artifacts still assert the flip *succeeded*, contradicting the live,
honest machine state. A skeptical external reader who diffs the README against
`reviewers.yaml` against the ledger sees three different stories. This ADR makes
the human-authored artifacts tell the **same** true story the engine tells.

## 2. Proven root cause (Week-1a investigation, 2026-06-02)

The digest divergence is **genuine single-source evidence-drift, not a
non-determinism defect.** Evidence chain (all reproducible on `c058d96`):

| Test | Result | Conclusion |
|---|---|---|
| Derive 3× in-process + 2 fresh subprocesses (`PYTHONHASHSEED=0,1`) | all `02f6d3c8…` | **deterministic** — no defect |
| `git log` of all 7 digest/obligation modules since signing (#267) | **0 changes** | **no method drift** |
| Re-derive inside a worktree at the signing commit (#267) | reproduces `4c46f530`, `VALID-AT-ITS-COMMIT: True` | signature was sound when signed |
| Restore signing-era probe bytes **in-place** at the canonical path | reproduces `4c46f530` exactly | the probe is the **sole** drift source |

The single moved input is `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json`
(GSM8K admission `3/47 → 4/46` via PRs #310, #488 — both *after* signing). The
four *gating* B-lanes are unchanged (185/14/40/50, `wrong=0`).

**Implication for the determinism claim:** the digest is byte-deterministic at any
fixed commit. "Byte-identical replay" is safe to assert.

## 3. The safe-direction wrinkle (documented; fix deferred)

`composite_math_gate._compute_claim_digest` commits the GSM8K `honest_disclosure`
block into the gating digest. But ADR-0131 explicitly designates GSM8K as
**non-gating** disclosure. So improving a purely informational coverage metric
invalidates the expert signature even though every *gating* criterion still
passes (`technical_pass=True`).

This is a coupling smell, but it **fails toward `audit-passed`, never toward a
false `expert`** — so it is **not a `wrong=0` hazard**. Per the project's
no-scope-creep discipline, the fix (scope the digest to *gating* inputs only) is
**deferred to a future ADR**. This ADR only records the wrinkle so a future
reviewer does not rediscover it cold.

## 4. Decision — reconcile per artifact type

Reconciliation principle: **artifacts that describe HISTORY keep their content
with a dated "valid-at … auto-reverted … current = audit-passed" note (keep the
receipt; keep the mismatch-refusal firing); artifacts that assert CURRENT MACHINE
STATE reconcile to the truth.**

| Artifact | Type | Action | Rationale |
|---|---|---|---|
| `docs/reviewers.yaml` `math_expert_claims` entry | history (receipt) | **Keep the entry**; add a quarantine comment block (valid-at 2026-05-23; auto-reverted; do not re-sign). | The entry's *mismatch* is what makes the ledger refuse — keeping it keeps the safety mechanism visibly firing. |
| `ADR-0120-math-expert-ledger-flip.md` | history | Add a dated header note: valid at 2026-05-23/#267; auto-reverted; current ledger = `audit-passed`; see ADR-0200. | A decision record stays true to its moment; the note prevents misreading it as current state. |
| `evals/math_expert_claims/v1/expert_claims_math_v1_signed.json` | **current state** | **Regenerate** → `promote_admitted: false`, `reviewer_signature_matches: false`. | A machine-generated current-state file with a committed `true` is the live overclaim. The receipt survives in git history + the quarantined registry entry. |
| `README.md` §"Path to expert" + line-81 test count | current state | Reconcile the "next gate" narrative to the built-attempted-reverted story; verify/correct the test count. | The ledger table is already accurate; only the narrative tense and the test count are stale. |
| `docs/decisions/README.md` | current state | Repoint any "math = expert" reference to `audit-passed`. | Index must match the ledger. |
| `tests/test_mathlogic_expert_ledger_flip.py`, `tests/test_adr_0120_math_expert_promotion.py` | current state | Flip 3 currently-RED "is-expert" assertions into **fail-closed-revert** assertions (status==audit-passed; expert_reason explains the digest mismatch; `reviewer_signature_matches is False`). | These assert current machine state; reconciling them to the truth converts 3 red overclaim-tests into green mechanism-proving tests. |

### 4.1 Cascade safety (verified)

- **Regenerating the signed JSON does not cascade:** it is **not** SHA-pinned
  (absent from `scripts/verify_lane_shas.py` and `scripts/generate_claims.py`),
  no test reads its bytes, and only `core capability math-expert-promote` writes
  it. The digest `4c46f530` appears only in the JSON itself and the (quarantined)
  `reviewers.yaml` entry.
- **The 3 red tests are pre-existing** (red since the #310/#488 drift), not caused
  by this reconciliation. They are folded in here so the expert-claim surface is
  reconciled as one unit.

## 5. What this ADR does NOT do

- Does **not** re-sign the expert claim. Re-signing `02f6d3c8` would re-assert an
  expert claim that (a) rests on CORE-authored lanes, not external GSM8K, and
  (b) would be immediately re-broken by the next parser improvement. The honest
  posture is `audit-passed` with the receipt preserved.
- Does **not** change any eval gate, threshold, or safety boundary.
- Does **not** fix the disclosure-in-digest coupling (§3) — deferred.
- Does **not** weaken any invariant. `wrong=0`, determinism, exact recall, and
  versor closure are untouched.

## 6. Trust boundary

- **Reads:** the capability ledger, the committed evidence bundle, `reviewers.yaml`.
- **Writes:** documentation + the one regenerated current-state artifact + two
  test files — all under operator ratification, on a branch, via PR. Nothing
  lands on `main` directly.
- No dynamic imports, no network, no normalization, no stochastic path.

## 7. Consequences

- The README, the ledger, `reviewers.yaml`, and the tests tell **one** true story:
  `audit-passed`, expert auto-reverted, fail-closed working.
- CI gains 3 green mechanism-proving tests where it had 3 red overclaim tests.
- A future ADR may scope the promotion digest to gating inputs only (§3).
- The reconciliation is the substrate for the CTO brief, whose honesty narrative
  leads with this revert: *a non-gating metric drifted and the system revoked its
  own expert claim — refuse-rather-than-guess applied to CORE's own status.*

## 8. CLAUDE.md PR-checklist

- **Capability/boundary protected:** restores claim↔machine-state coherence; keeps
  the fail-closed refusal visibly firing; preserves every invariant.
- **Invariant proving field validity:** the ledger reports `expert` iff a signed
  digest re-derives — and it currently, correctly, does not.
- **CLI/eval proving the lane:** `uv run core capability ledger` (status =
  audit-passed); `uv run pytest tests/test_mathlogic_expert_ledger_flip.py tests/test_adr_0120_math_expert_promotion.py`.
- **Avoided hidden normalization / stochastic / approximate / unreviewed mutation:**
  Yes — documentation + one deterministic regeneration; no engine change.
- **Trust boundary:** read-only inputs; writes are review-gated on a branch.
