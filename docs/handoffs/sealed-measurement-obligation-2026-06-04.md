<!-- handoff | sealed-measurement-obligation | 2026-06-04 | OPEN obligation — operator/CI action required | ADR-0207 §5 step 2 / §6 -->

# ⚠ OPEN OBLIGATION — sealed-1,319 measurement for the R4 goal-residual serving flip

**Status: REQUIRED, NOT YET DONE.** Blocks the claim that the GSM8K substrate is
still `wrong=0` on held-out.

## What changed and why this note exists

ADR-0207 §5 step 2 landed the first composition lift on serving: **cv-0005 / train_sample
0037** (R4 goal-residual) now solves, moving the serving metric **6/44/0 → 7/43/0**
(`wrong=0` preserved on every surface this lane *can* run). The new production
(`generate/derivation/goal_residual.py`) is wired to serving via
`resolve_promotable_goal_residual` at `generate/math_candidate_graph.py` (mirroring the
`product_bridge` pattern).

**The sealed holdout (1,319 cases, `evals/gsm8k_math/holdouts/v1/cases.jsonl.age`) was NOT
re-measured.** It is age-encrypted and not CI-reproducible, so the agent that built this
could not run it. Per ADR-0207 §6, **the sealed number is the real bar** — a serving gain
that does not hold on the sealed set is overfitting and does not count.

## The obligation

The operator (key-holder) or a CI job with decryption access **must**:

1. Decrypt + run the sealed 1,319 through the current serving path
   (`generate.math_candidate_graph.parse_and_solve`) at the merge SHA.
2. Confirm sealed **`wrong == 0`** still holds (prior recorded: `0/0/1319`).
3. Record the verdict in `docs/claims_ledger.md` (row A / ADR-0119.7) and resolve this file.

## If sealed `wrong > 0`

`goal_residual` fired-and-committed a wrong reading on a held-out case. **Revert is trivial
and isolated:** remove the `resolve_promotable_goal_residual` block from
`math_candidate_graph.py` (the serving bridge) — the production and its tests can stay; only
the serving promotion is rolled back. Then tighten the production's gate before re-flipping.

## Evidence the agent *could* gather (strong, not sufficient)

- Fires on **2 / 455** visible GSM8K-style cases, **both correct, zero wrong**.
- Self-verify gate (grounding ∧ unit ∧ completeness) + extreme narrowness (goal-intent
  lexeme + residual question + same-referent licensed progress).
- Gain-goal divergence firewall (`test_reads_goal_not_possession`) proves it reads the
  **goal**, not a possession (the coincidental-correctness trap).

None of that is the sealed verdict. **This note stays OPEN until step 2 above is done.**
