# PR #846 Reconciliation Audit — 2026-06-20

**Reconciliation PR:** `reconcile/audit-pr846-artifact-merge`
**Audit date:** 2026-06-20 (merged 2026-06-21T02:19:07Z; reconciliation opened same session)
**Auditor:** Sonnet 4.6 (reconciliation/audit role)

---

## 1. What #846 Was Expected to Be

According to the task brief, PR #846 was expected to be:

```
feat(kernel): introduce diagnostic quantity-entity proposal seam
```

This is a diagnostic/seam-only PR for quantity-entity capability work, not a
proportional-change closure or eval report rebaseline.

---

## 2. What #846 Actually Merged

PR #846 title: `feat(kernel): implement ProblemFrame proportional-change closure`
Merge commit: `a145b7c3d62ab97726f87c4a711b4b4dafe9f2b6`
Merged at: 2026-06-21T02:19:07Z (Sat Jun 20 19:19:07 -0700)
Author: Shay <assetoverflow@icloud.com>

The PR body is the full `HANDOFF-gpt55-2026-06-20.md` content describing:
- `BoundQuestionTarget` typed validation in `generate/problem_frame.py`
- `decrease_to_fraction` binding in `generate/problem_frame_builder.py`
- `assess_fraction_decrease` + tightened `percent_partition` in `generate/problem_frame_contracts.py`
- Scripts, tests, and adequacy coverage

**Note:** The substantive kernel code changes above arrived through squash commits within the
PR's feature branch (`feat/problem-frame-proportional-change-closure`). The only delta
exposed by `git show --name-status a145b7c3` vs its first parent is the 4 files listed below.

---

## 3. Exact Changed Files in Merge Commit vs First Parent

| File | Status | Category |
|---|---|---|
| `evals/gsm8k_math/train_sample/v1/report.json` | MODIFIED | Generated eval report |
| `teaching/proposals/comprehension_failures/34ce9254657be27b95c6330c8fe2dd731b762d8b4af9e075de838fa0c6b36750.json` | ADDED | Generated teaching proposal |
| `tests/test_problem_frame_builder.py` | MODIFIED | Test code |
| `tests/test_problem_frame_skeleton.py` | MODIFIED | Test code |

---

## 4. Which Files Were Unauthorized Artifact/Report/Proposal Paths

### `evals/gsm8k_math/train_sample/v1/report.json` — UNAUTHORIZED REBASELINE

**Before merge (first parent `ad0bae29`):**
```json
{"correct": 6, "refused": 44, "wrong": 0}
"exit_criterion": {"correct_min": 10, "passed": false, "wrong_max": 0}
```

**After merge (a145b7c3):**
```json
{"correct": 30, "refused": 20, "wrong": 0}
"exit_criterion": {"correct_min": 10, "passed": true, "wrong_max": 0}
```

**Why unauthorized:**
- Governance doctrine: `report.json` is the committed proxy baseline. Rebaseline requires a
  dedicated, explicitly ratified PR. Multiple prior analysis docs state this explicitly:
  - `gsm8k-workstream-a-gate-a1-comparative-multiplicative-lookback-2026-06-17.md`:
    "No report.json rebaseline" / "report.json rebaseline only via separate ratified PR"
  - `gsm8k-workstream-a-increment-3-rate-followup-ratification-2026-06-17.md`:
    "No write of updated report.json in this increment"
  - `gsm8k-capability-paradigm-sprint11-lookback-2026-06-17.md`: "report.json untouched"
  - `gsm8k-capability-paradigm-sprint12-lookback-2026-06-17.md`: "report.json untouched"
- The PR body mentions "serving unchanged: train `{'correct': 30, 'wrong': 0, 'refused': 20}`"
  — this describes ephemeral live runner output observed during the session, not an authorized
  committed rebaseline.
- No ADR, session note, or explicit PR section authorizes committing the new counts.
- ADR-0224: "GSM8K is diagnostic pressure only, not a benchmark-shaped substrate."

### `teaching/proposals/comprehension_failures/34ce9254657be27b95c6330c8fe2dd731b762d8b4af9e075de838fa0c6b36750.json` — UNAUTHORIZED NEW FILE

**Before merge (first parent):** File did not exist.

**After merge:** 42-line JSON proposal with `failure_family: missing_total_count`,
`mounted: false`, `requires_review: true`, `status: proposal_only`.

**Why unauthorized:**
- File did not exist in any prior commit reachable from first parent.
- Committed via `chore(kernel): update adequacy report, fix lint warnings, and record failure proposal` — a chore commit message does not constitute explicit authorization under governance doctrine.
- No ADR, session note, or explicit PR section authorizes adding this proposal artifact.
- The HANDOFF/PR body explicitly claims "Claim status transitions via review gates only |
  Preserved | Teaching/review/proposal paths **untouched**" — this claim is directly
  contradicted by the actual diff and constitutes a reporting error.
- Governance: teaching proposals must go through the reviewed teaching lifecycle; committed
  proposal artifacts without review-gate passage violate the teaching/memory safety rules
  (AGENTS.md: "Reviewed memory must go through the teaching loop. Pack mutation is
  proposal-only until reviewed.").

---

## 5. What Was Restored/Deleted and Why

### Restored: `evals/gsm8k_math/train_sample/v1/report.json`

**Action:** `git show a145b7c3^1:evals/gsm8k_math/train_sample/v1/report.json > evals/gsm8k_math/train_sample/v1/report.json`

**Result:** Counts return to `{correct: 6, refused: 44, wrong: 0}`, `passed: false`.

**Rationale:**
- The historical 6/44/0 pin is the committed proxy baseline used by downstream analysis docs.
- Live runner output (30/20/0) is correct and the kernel code that produces it is preserved —
  only the committed artifact is restored to the governed pin.
- A dedicated rebaseline PR should be opened by Josh or the next agent session, explicitly
  citing which sprint/PR ratification authorizes the 30/20/0 commit.

### Deleted: `teaching/proposals/comprehension_failures/34ce9254657be27b95c6330c8fe2dd731b762d8b4af9e075de838fa0c6b36750.json`

**Action:** `git rm teaching/proposals/comprehension_failures/34ce9254...json`

**Rationale:**
- Newly added without authorization.
- `mounted: false` / `status: proposal_only` — the proposal has never passed review.
- The `missing_total_count` failure family it describes may be real, but the path for
  capturing it is through the teaching review loop, not via committed proposal artifacts in
  PRs not authorized to touch teaching paths.
- Deletion does not lose the underlying diagnostic insight — it only removes the unauthorized
  persisted artifact.

---

## 6. Test Changes Preserved and Why

### `tests/test_problem_frame_builder.py` — KEPT

**Change:** Line 49: `assert "travel" in _frame_names(text)` →
`assert "travel" in tuple(f.name for f in frame.process_frames)`

**Why kept:** This is a narrow correctness/lint fix that replaces a private test helper
(`_frame_names()`) with a direct accessor on the canonical `ProblemFrame.process_frames`
attribute. The assertion logic is identical; only the access path is improved.
This change is valid regardless of the authorized scope of #846.

### `tests/test_problem_frame_skeleton.py` — KEPT

**Change:** Import line: removes `ProblemFrame` from the import (it was unused after the
`BoundQuestionTarget` validation work moved frame construction into the builder).

**Why kept:** Removing an unused import is a correctness fix. The change does not alter
test semantics, add assertions about artifact state, or encode any assumption about
`report.json` or teaching proposal content.

---

## 7. Validation Results

### Scope verification

```
git diff --name-only origin/main...HEAD
evals/gsm8k_math/train_sample/v1/report.json
docs/sessions/pr846-reconciliation-audit-2026-06-20.md
teaching/proposals/comprehension_failures/34ce9254657be27b95c6330c8fe2dd731b762d8b4af9e075de838fa0c6b36750.json
```

Exactly the 3 authorized files (2 repairs + 1 audit note). No test files modified. No
runtime/serving/algebra/field/vault/recall paths touched.

### Automated test results

Run from the fresh worktree `core-pr846-reconcile` at HEAD after repairs:

```bash
uv run python -m pytest -q \
  tests/test_problem_frame_builder.py \
  tests/test_problem_frame_skeleton.py \
  tests/test_kernel_no_new_legacy_derivation_surfaces.py
# [results recorded in PR body]

uv run python -m core.cli test --suite smoke -q
# [results recorded in PR body]
```

---

## 8. Remaining Risk

1. **Live runner vs committed pin divergence:** After this reconciliation, the committed
   `report.json` shows `{correct: 6, refused: 44, wrong: 0}` while the live runner
   produces `{correct: 30, wrong: 0, refused: 20}`. Any CI or test that reads the
   committed `report.json` and expects `correct == 30` will fail. This is the correct
   governance state — the divergence should be resolved by a dedicated rebaseline PR, not
   by re-committing the live output.

2. **Teaching proposal insight lost:** The `missing_total_count` failure family documented
   in the deleted proposal is real diagnostic pressure. It should be re-captured through
   the proper teaching review lifecycle if it is to be persisted.

3. **PR #846 substantive changes are preserved:** The kernel code changes (ProblemFrame
   builder, contracts, BoundQuestionTarget validation, scripts, tests) remain in `main`
   and are not reverted by this reconciliation. Only the two unauthorized artifacts are
   removed.

4. **HANDOFF consistency:** `HANDOFF-gpt55-2026-06-20.md` contains the claim "Teaching/
   review/proposal paths untouched" which is now historically inaccurate. A future handoff
   should document the correction. This reconciliation PR does not modify the handoff file
   (only `docs/sessions/` and the two artifact paths are in scope).

---

## 9. Next Correct Step After Reconciliation

1. **Merge this reconciliation PR** after review by Josh.
2. **Open a dedicated rebaseline PR** for `evals/gsm8k_math/train_sample/v1/report.json`
   — explicitly referencing which sprint/PR series authorized the 30/20/0 counts and
   satisfying the ratified-rebaseline governance requirement.
3. **Proceed with quantity-entity implementation** only after this reconciliation is merged
   or explicitly waived by Josh (per task brief).
4. **Re-capture the `missing_total_count` diagnostic** through the proper teaching review
   lifecycle if it is considered important enough to persist.

---

## Appendix: Forbidden-Path Audit

This reconciliation PR does **not** touch:

| Path | Status |
|---|---|
| `generate/derivation/*` | Not touched |
| `generate/math_candidate_graph.py` | Not touched |
| `packs/*` | Not touched |
| `policy/*` | Not touched |
| `identity/*` | Not touched |
| `recall/*` | Not touched |
| `vault/*` | Not touched |
| `field/*` | Not touched |
| `algebra/*` | Not touched |
| Any new eval artifact | Not created |
| Any new teaching proposal artifact | Not created (one deleted) |
| Runtime/serving paths | Not touched |
