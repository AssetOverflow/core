# PR-1: CLOSE Relational-Transitive Consolidation + Disciplined Capability-Slice Workflow

**Date:** 2026-06-16  
**Branch:** `feat/close-relational-transitive-consolidation`  
**Base SHA at reconcile:** `5c048f9782f66e7438e185e4d3bbeb476f679f0f` (origin/main)  
**Top commits:**  
- `fb7f469c` feat(determine): consolidate declared relational transitive derived facts  
- `346c35dd` test(determine): cover relational transitive CLOSE consolidation  
- (optional docs follow-up on same branch)

**Governing spec:** AssetOverflow/core "SuperGrok / Grok Build Instruction Set" (the full PR-1/PR-2/PR-3 sequence with red lines, STEP 0 reconcile, exact positives/negatives, wait conditions, and 9-section reporting obligation).

## What PR-1 delivered (substrate only)

Extended `generate.determine.consolidate.consolidate_once` (and its one-hop candidate collection) so idle CLOSE can now consolidate sound derived facts for the four *declared* strict-order relational predicates already supported by DETERMINE:

- `less_than`
- `greater_than`
- `before_event`
- `after_event`

**Rules strictly observed (same-predicate only, no mixing):**
- `p(a,b) + p(b,c) → p(a,c)` (direct 2-hop candidates per tick)
- Only when `p in TRANSITIVE_PREDICATES`
- No `parent_of` / `sibling_of` / `left_of` / `spouse_of` / `equal_to` etc.
- No inverse mixing, no symmetric "promotion" to transitive, no cross-predicate composition, no reflexive (`a == c`).
- Verification is **mandatory** before any `realize_derived` write (reuses the Phase-C `_relational_transitive` search + proof_chain ROBDD verifier; `Determined` with `rule="transitive"` required).
- Writes use `realize_derived(..., rule="transitive", premise_structure_keys=...)`.
- Deterministic global sort by `(predicate, subject, object)`.
- Bounded (per-predicate `_TRANSITIVE_EDGE_BUDGET` inside the reused verifier; safe no-write on over).
- All derived records are `epistemic_status="speculative"`, `derived=True`, carry replayable `Derivation` (premise keys + rule + "entailed" verdict). No COHERENT minted.

**Existing behaviour 100% preserved:** member/subset CLOSE, the `member ∘ member` fallacy bite, `_one_hop_candidates` shape for is-a, budget checks for is-a, etc.

## Evidence (all gates on clean tree post-reconcile)

- `tests/test_determination_consolidation.py`: 18/18 (baseline is-a + 6 new relational tests).
- `tests/test_determine_relational_inference.py` + `test_determine_relational_transitive.py`: 33/33 (verifier reuse unchanged).
- `tests/test_architectural_invariants.py`: 74/74 (INV-30 open-world determine True-only + INV-31 FrameVerdict firewall both green; no violations).
- Targeted positives: less_than / before_event 2-hop consolidation + direct recall + determine answers + record shape (derived/speculative/transitive/entailed/premise keys) + multi-hop climb to fixed point (tick 1: 2-hops; tick 2: 3-hop; further no-op).
- Negatives (wrong=0 bites): parent_of/sibling_of/left_of chains refused (no derivation, Undetermined); inverse mix (less_than + greater_than) does not leak; reflexive excluded; TRANSITIVE_PREDICATES set exactly the four declared.
- `wrong_total == 0` on all touched lanes.
- Diff from base contains **exactly two files**: `generate/determine/consolidate.py` + `tests/test_determination_consolidation.py`.
- Tree was forced clean at STEP 0 (uncommitted hygiene from prior full-suite triage explicitly discarded via `git restore .` + `git clean -fd` + branch delete/re-create from origin/main). No mixing.

## The 3-PR Sequence (do not collapse)

1. **PR-1 (this)**: Cognitive *substrate* — CLOSE now climbs over the declared relational transitive facts (Phase C + D integration). Changes the lived loop's deductive power.
2. **PR-2** (only after PR-1 green/merged or explicit stack approval): Proposal/discovery bridge — derived CLOSE facts become review-gated proposal candidates (default-off flag, read-only miner, deduped, SPECULATIVE only, no auto-ratify, no corpus mutation).
3. **PR-3** (only after PR-2): Yardstick / capability-index lane — measures the autonomous climb (direct_answerable_before / after_tick_1 / after_fixed_point, facts_consolidated_per_tick, proposal_candidates when flag enabled, wrong_total, replay signature, fixture SHAs). Updates capability index *only* on clean results.

Wait conditions between each preserve auditability and make failures attributable. "Do not collapse all three PRs."

## Starting Work — Branch / Worktree Discipline (solid, repeatable, clean)

Always start from **clean current main** (prevents hygiene bleed and prior local partial work from contaminating the capability slice):

```bash
git fetch origin main
git status
git switch main
git pull --ff-only origin main
git log --oneline --decorate -20

# Inspect whether a local feat/ name already carries the extension or unrelated cleanup
git branch --all --sort=-committerdate | head -40
git log --all --oneline --decorate -- generate/determine/consolidate.py tests/test_determination_consolidation.py | head -40
git diff origin/main...HEAD -- generate/determine/consolidate.py tests/test_determination_consolidation.py

# Greps for the new symbols (TRANSITIVE_PREDICATES usage, consolidate_once, realize_derived in the right places)
grep -R "TRANSITIVE_PREDICATES" -n generate tests evals docs | head -80
# ... (consolidate_once, realize_derived, etc.)

# Force a pristine starting point for this slice
git branch -D feat/close-relational-transitive-consolidation || true
git switch -c feat/close-relational-transitive-consolidation origin/main
git status   # must be clean, on the new branch, at origin/main tip
```

**Rationale:** If the local feat branch had mixed full-suite hygiene (opt-outs, clears, demo forces, etc.) or a partial Phase D attempt, we delete and re-create from origin/main. This "splits" the work exactly as required. The reconcile also confirms main is still member/subset-only for the consolidation module (the relational extension is implemented fresh here).

**Worktrees for isolation (recommended during wait periods):**

While PR-1 is under review / CI, you may safely prepare the next slice without touching the review branch:

```bash
git worktree add -b feat/close-derived-proposal-bridge ../core-pr2 origin/main
cd ../core-pr2
# ... do PR-2 reconnaissance / test scaffolding only (do not commit on the review branch)
```

Worktrees live under the parent dir (or `.claude/worktrees/` per agent conventions) and are cheap, isolated checkouts. They inherit the same clean-main discipline. Prune with `git worktree prune` when done.

Never push the PR branch until the logical slice commits + 9-section report are ready. Use `-u` on first push.

## Finishing & PR Discipline

- **Logical slices in commit history** (per the exact shape for this sequence):
  1. `test(determine): cover relational transitive CLOSE consolidation`
  2. `feat(determine): consolidate declared relational transitive derived facts`
  3. `docs(determine): ...` (optional but required when the change is a design/capability extension — see below)

- Conventional commits. Before opening the PR: analyze full history (`git log base...HEAD`), run `git diff base...HEAD`, draft comprehensive summary + test plan + the 9-section report.

- **Mandatory 9-section report format** (exact, at the end of each PR in the sequence, back to the requester):

  1. Branch / base SHA
  2. What changed
  3. What did not change
  4. Tests run
  5. Results
  6. Any remaining reds
  7. Whether those reds are blocking or unrelated
  8. PR link
  9. Next recommended step

- Do not claim full-suite green, wrong=0, or "autonomous learning" (the latter is only after reviewed mutation; this work is session/SPECULATIVE/proposal-only until PR-2/3 + human review).

## Documentation Obligation (design / capability changes)

When a design or capability change is implemented (even "just" substrate), the following must be updated in the same PR (or as an immediate follow-up docs slice on the branch):

- **Canonical runtime contract**: `docs/runtime_contracts.md` (the Idle consolidation / Step D — CLOSE section must name the new behaviour while re-stating every existing contract: SPECULATIVE honesty, wrong=0 by proof-gating + verifier, replayable provenance, session-only / no parallel path, no COHERENT, no normalization outside sanctioned boundaries).
- **Dated analysis / lookback note** under `docs/analysis/` (this file). Captures scope, evidence, the governing sequence plan, branch discipline, red lines, and non-goals. Follows the style of other step/phase lookbacks and design notes in the tree.
- **High-level entry points** (root `README.md`, `docs/capability_roadmap.md`, `docs/PROGRESS.md`, etc.): minimal accurate cross-reference or one-sentence pointer so a reader of the high-level material knows the lived loop now also consolidates declared strict-order relations via CLOSE. Do not bury the contract details in the overview README.
- Any ADR/brief/handoff that would otherwise become stale on the cognitive loop description.

This note + the runtime_contracts.md extension + the small README pointer satisfy the obligation for PR-1.

## Documentation Updates Delivered in This Step

- Extended the "Idle consolidation (Step D — CLOSE)" section in `docs/runtime_contracts.md` (one clear paragraph + contract bullets re-affirming the invariants now apply to the relational transitive case as well).
- This analysis note (the reusable "solid organized, clean plan" for branch/worktree start, PR slicing, wait conditions, 9-section reporting, and the documentation-update rule).
- Tiny, accurate pointer added to root `README.md` near the learning-loop / teaching-corpus description (cross-ref to the contracts for the new CLOSE behaviour).

All updates are minimal, load-bearing, and follow the project's Markdown + analysis-note conventions. No broad churn.

## Red Lines (still green after this PR-1)

- `wrong_total` remains 0 wherever a lane reports correctness.
- `determine()` remains open-world True-only (INV-30). Absence is never False.
- No FrameVerdict serving / default wiring / INV-31 relaxation (PR #787 left untouched).
- Derived facts: SESSION / SPECULATIVE / as-told only. No reviewed/ratified teaching mutation, no corpus mutation, no COHERENT minted by this path.
- Every derived fact carries replayable provenance (premise structure keys from verified grounds) and is proof-gated by the existing sound verifier.
- If unsure about soundness: refuse/skip. Coverage gaps acceptable; silent wrongness is not.
- No stochastic / similarity / ANN / LLM / template fallback.
- Changes small and reviewable; hygiene not mixed into the capability PR.

## Next Recommended Step

**STOP after this PR-1.**

- Produce / post the exact 9-section report (this note feeds it).
- Push the branch (`git push -u origin feat/close-relational-transitive-consolidation`).
- Open the PR with the required title and body (include the what/why/only-TRANSITIVE/verifier path/wrong=0/invariants/non-goals + link to this note and the contracts update).
- **Wait** for PR-1 to pass targeted tests + (documented-unrelated) fast lane + review + merge (or explicit approval to stack).
- Only then: reconcile to clean `origin/main` again and create `feat/close-derived-proposal-bridge` for PR-2.

The lived loop is now materially stronger for declared relational transitive facts, with every invariant and boundary preserved. The flywheel (comprehend → realize → determine → CLOSE consolidate → (future) propose → reviewed learning → measured climb) has its next substrate piece in place.

---

*This document is the permanent, diffable record of both the technical extension and the process discipline used to deliver it cleanly.*