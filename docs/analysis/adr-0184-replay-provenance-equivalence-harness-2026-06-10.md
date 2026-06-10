# ADR-0184 S4b — the replay/provenance equivalence harness

**Date:** 2026-06-10
**Status:** implemented (this PR). This is the brief-S4 / ADR-S4b boundary from
[adr-0184-s3-s5-candidate-source-boundary-2026-06-10.md](adr-0184-s3-s5-candidate-source-boundary-2026-06-10.md)
— the precondition for any future semantic-primary path.
**Authority unchanged:** `verify.py` / `pool.py` remain the sole commit authority;
this PR adds proof machinery only.

## 1. Diagnosis (required before coding)

**What did the #684/#685 937-problem differential actually compare?**
A local, uncommitted script ran four surfaces (`accumulation_candidates`,
`compose_accumulation`, `pooled_candidates`, `resolve_pooled`) over every unique
problem under `evals/gsm8k_math/**/cases.jsonl` (937 after text de-dup) in **two git
checkouts** — pre-change `main` vs the PR branch — and byte-compared canonical JSON
dumps. Non-vacuous because the reference was a *different code tree*.

**Is that comparison still non-vacuous after #685?** **No.** `accumulation_candidates`
is now a thin wrapper delegating to `semantic_state_candidates`; there is no
independent legacy implementation left in-tree. Any in-repo old-vs-new run is a
self-comparison and proves nothing. Reconstructing a "reference adapter" from the
compatibility wrappers fails the same way (same code path), so that option from the
brief is rejected.

**The smallest durable non-vacuous reference** is a **pinned canonical trace
artifact**: `evals/gsm8k_math/equivalence/v1/expected_traces.jsonl` (one canonical
JSON line per problem, sorted by problem SHA) plus `v1/manifest.json` (corpus SHA,
problem count, pin commit, provenance). Its authority comes from a documented
provenance chain, not from being self-generated:

```text
pre-S2 legacy behavior
  ==(PR #684 cross-tree differential, 937/0)== S2 ledger behavior
  ==(PR #685 cross-tree differential, 937/0)== S4 boundary behavior  <- pinned HERE
```

The independent-oracle property was *consumed at pin time* by those two cross-tree
proofs; from now on the artifact is frozen evidence (the same trust model as the
`verify_lane_shas.py` pins). Comparing live traces against it detects drift
non-vacuously. Updating it requires the explicit, diff-reviewable
`scripts/verify_semantic_equivalence.py --update` — never silent.

**Pytest or script?** Both. The pytest
(`tests/test_adr_0184_s4b_replay_equivalence.py`) is the always-on gate; the script
(`scripts/verify_semantic_equivalence.py`, mirroring `verify_lane_shas.py`) is the
human-runnable check/regenerate lane with per-dimension reporting.

**Committed artifacts:** the JSONL (~600 KB) + manifest. Full traces, not bare
hashes, so an intentional re-pin produces a *reviewable diff* naming exactly which
problems and dimensions moved.

**Determinism and cost:** every surface is deterministic (no RNG, no time); traces
are canonical JSON (sorted keys, fixed separators), problems sorted by SHA-256 of
exact text. Full-corpus generation measured at **~2 s**, the whole test file ~6 s —
cheap enough to run the full 937 on every invocation; no subset/sampling tier is
needed (none would be acceptable as proof anyway).

**CI now vs manual:** the dedicated test runs under `core test --suite full` and any
direct pytest; the existing smoke gate does not pick up new dedicated files, which is
correct — this is a derivation-lane gate, not a smoke property. Recommended (not done
here, to keep the PR narrow): run `python scripts/verify_semantic_equivalence.py` in
the same CI job that runs `scripts/verify_lane_shas.py`.

**What this unlocks:** ADR-S3 (semantic target wrapper) and ADR-S5 (transfer — the
first semantic-primary world) can now land with a standing drift net under them: any
unintended change to candidate values, order, duplicate multiplicity,
refusal/exemption classes, or commit decisions across the whole corpus fails loudly,
and any intended change must arrive as a reviewed artifact diff.

## 2. What the harness proves (the eight obligations)

| # | Obligation | Mechanism |
|---|---|---|
| 1 | Candidate output equivalence | live `semantic`/`pooled`/`compose`/`resolution` trace fields == pinned artifact, all 937 problems |
| 2 | Order equivalence | trace lists are order-preserving; canonical encoding makes reorder a detected diff (perturbation-tested) |
| 3 | Duplicate multiplicity | duplicates serialize as repeated entries; a dropped duplicate is a detected diff (perturbation-tested) |
| 4 | Refusal/fail-closed equivalence | refusals are pinned as `null` resolutions; a refusal→commit flip is a trace diff; empty-pool commits flagged by the authority checker |
| 5 | Exempt-only semantics | per-candidate `classifications` pinned; flips detected by both the snapshot net and the authority net |
| 6 | Pool/verify authority preservation | `authority_violations()` re-derives the commit law from trace content: commit ⇒ a `complete` reading exists ∧ no classified disagreement ∧ non-empty pool. One-directional by design — refusal is always lawful (wrong=0 hazards live only on the commit side) |
| 7 | No direct semantic-ledger commit path | #685's structural AST scan (still in force, auto-covers the new `state/provenance.py`) + the authority net detects a bypass *from the trace itself* (perturbation-tested) |
| 8 | No drift across the #684/#685 corpus | the full 937-problem live-vs-pinned comparison, in-tree, repeatable |

Provenance (the S4b "replay faithfulness" half):
`generate/derivation/state/provenance.py::replay_is_faithful` states the replay
bridge's law as a checkable structural property — every step corresponds 1:1, in
order, to a ledger transition (gain→add, loss→subtract; cue/value/source-token
verbatim; anchor-unit inheritance; no comparative steps; one key; SET start). The
harness asserts it for **every (world, candidate) pair in the corpus**, and the
boundary's candidates must be exactly the in-order replay of its worlds. Twelve
single-mutation tests prove the checker itself is non-vacuous.

## 3. How to run

```bash
# the gate (full corpus, ~6 s)
python -m pytest tests/test_adr_0184_s4b_replay_equivalence.py -q

# human-readable check / machine-readable report
python scripts/verify_semantic_equivalence.py
python scripts/verify_semantic_equivalence.py --json

# intentional, reviewed re-pin ONLY (the artifact diff is the audit trail)
python scripts/verify_semantic_equivalence.py --update
```

A failure means derivation-lane behavior moved relative to the pinned reference.
If unintentional: fix the regression. If intentional: re-pin with `--update` in the
same PR and let reviewers read the artifact diff. Never re-pin to silence a failure
you cannot explain.

## 4. Known caveats

- The pinned artifact freezes behavior *including current refusals*; capability work
  (ADR-S3/S5+) is **expected** to re-pin, consciously, with the trace diff as
  evidence. That is the harness working as designed, not friction to route around.
- The authority checker validates necessary commit conditions derivable from trace
  content; it is not a re-implementation of `resolve_pooled` (e.g. the prior-state
  question guard appears only as a pinned `null` resolution). The #685 structural
  scan plus the snapshot net carry the rest.
- The corpus definition is "every `cases.jsonl` under `evals/gsm8k_math/**`,
  de-duplicated by exact text" (937 today, count pinned in a test). Corpus additions
  change the count and SHA → loud, requiring a conscious re-pin.
