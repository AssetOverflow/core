# L16 brief — ADR-0131.G.5 — Capability axis: aggregate answer composition

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g5-aggregate -b feat/adr-0131-g5-aggregate origin/main
cd ../core-adr-0131-g5-aggregate
```

**Scope.** Close the aggregate-answer composition loop opened by G.4's
multi-entity candidate emission. The parser already emits
`Unknown(entity=None, unit=<unit>)` for questions containing
`in total` or `altogether` (lines 688–735 of
`generate/math_candidate_parser.py`). The solver already sums terminal
state across all entities when `entity is None` (lines 525–532 of
`generate/math_solver.py`). The gap is two-fold:

1. **Vocabulary gap**: `"combined"` and `"together"` are not in `_Q_TOTAL_RE`'s
   tail alternation — "How many apples do they have combined?" is refused at
   the question layer even though the two-entity sum would be correct.
2. **No pinned lane**: there are no curated axis cases proving the
   two-entity and three-entity aggregate paths work end-to-end through
   `parse_and_solve`. The capability exists but is untested as a named lane.

**Pre-flight check (run before coding):**

```python
from generate.math_candidate_graph import parse_and_solve
r = parse_and_solve(
    "Sam has 5 apples. Tom has 3 apples. How many apples do they have altogether?"
)
assert r.answer == 8.0 and r.refusal_reason is None  # already passes
r2 = parse_and_solve(
    "Sam has 5 apples. Tom has 3 apples. How many apples do they have combined?"
)
assert r2.refusal_reason is not None  # currently fails — this is the gap
```

**Reference docs (read these, only these):**

1. `docs/decisions/ADR-0131.G-gsm8k-coverage-probe.md` — iteration
   discipline; axis cases are independent of GSM8K; `admitted_wrong == 0`
   is non-negotiable.
2. `generate/math_candidate_parser.py` lines 685–750 — `_Q_TOTAL_RE` and
   `_Q_ENTITY_RE`; the change is a one-line alternation extension in
   `_Q_TOTAL_RE`'s tail group.

**What to ship:**

- **Parser fix** in `generate/math_candidate_parser.py`: extend
  `_Q_TOTAL_RE`'s tail alternation from
  `(?:in\s+total|altogether|left|now)` to include `combined` and
  `together` as aggregate cues. Map both to the same `entity=None`
  semantics. Update the docstring's closed-cue list.

- **Curated axis lane** at
  `evals/math_capability_axes/G5_aggregate/v1/cases.jsonl` — **≥20
  cases** exercised end-to-end through `parse_and_solve` (not just the
  parser):

  | Shape | Count | Cue coverage |
  |---|---|---|
  | 2-entity sum, no operations | ≥4 | `altogether`, `in total`, `combined`, `together` (≥1 each) |
  | 3-entity sum, no operations | ≥4 | all four cues |
  | 2-entity sum with one add/subtract op | ≥4 | mixed cues |
  | Single-entity total cue (degenerate aggregate) | ≥4 | regression guard |
  | Refusal: aggregate cue with mismatched units | ≥4 | wrong==0 probe |

  Each case carries `expected_answer` (numeric). The runner verifies
  `r.answer == expected_answer` (exact float equality is fine — these are
  integer initial states). Refusal cases verify `r.answer is None`.

- **Runner + report** at `evals/math_capability_axes/G5_aggregate/v1/`.
  Same shape as G2 runner: deterministic `report.json`, `wrong==0` gate,
  byte-equal across runs.

- **Tests** at `tests/test_adr_0131_G5_aggregate.py` (**≥15**):
  - `"combined"` and `"together"` cues parse to `entity=None` (unit
    confirmed via `extract_question_candidates`).
  - All four cue words are in the closed-set docstring list.
  - 2-entity axis cases produce the correct sum.
  - 3-entity axis cases produce the correct sum.
  - Single-entity degenerate case still works.
  - Mismatched-unit cases refuse (no wrong answer emitted).
  - `wrong == 0` on the full axis lane.
  - Runner report is byte-equal across two back-to-back runs.
  - B3 lane unchanged (import and run one B3 test as a regression guard).
  - **GSM8K probe safety rail**: `admitted_wrong == 0` preserved on the
    legacy probe (`train_sample_coverage_report.json`). No admission
    movement is expected (all 50 sample cases still refuse at statement
    parsing); gate on `admitted_wrong == 0`, not on admission rate.

- **ADR** `docs/decisions/ADR-0131.G.5-aggregate-answer-composition.md`.
  Cite ADR-0131.G parent. Document the closed aggregate-cue vocabulary
  (`in total`, `altogether`, `combined`, `together`). State explicitly
  that the solver path (`entity is None` → sum) was pre-existing — this
  ADR extends the cue vocabulary and pins the lane, not the solver. Call
  out what's deferred: implicit aggregation without a cue word ("How many
  do Sam and Tom have?" with no aggregate cue — that requires coreference
  and is out of scope), rate-based aggregation ("how many dollars did they
  earn in total?" where the unit is derived from a rate operation).

**Hard constraints:**

- **`wrong == 0`** on every axis case and the GSM8K safety rail. The
  solver sum is exact (integer initial states); any wrong answer means the
  candidate graph selected a mismatched graph — fix the graph selection,
  do not touch the solver.
- **Closed cue vocabulary.** Exactly four cues: `in total`, `altogether`,
  `combined`, `together`. No synonym expansion, no paraphrase tolerance.
  Document the deferred forms.
- **No solver changes.** The `entity is None` sum is already correct.
  This ADR is parser-vocabulary + lane pinning only.
- **No new modules under `algebra/`, `chat/`, `core/`.** Parser change is
  a one-line regex extension. New files live under `evals/` and `tests/`.
- **Determinism.** `report.json` byte-equal across runs.

**Out of scope:**
- Implicit aggregation without a cue word (coreference).
- Rate-unit aggregation ("total earnings" from rate operations).
- GSM8K admission movement (statement parsing is the current bottleneck
  for every sample case; question-layer work cannot lift that).
- Any changes to `math_solver.py`, `math_problem_graph.py`, or the
  binding-graph layer.

**Target branch.** PR against `main`. Title:
`feat(ADR-0131.G.5): aggregate answer composition — combined/together cues wired, axis lane N/N, wrong==0`.
Body: cue vocabulary, per-shape case counts, pre/post pre-flight check
output, link to ADR. Honest note that no GSM8K admission movement is
expected (statement parsing is the probe bottleneck).

**Exit criterion.** CI green; axis runner exits 0 with `wrong == 0`;
B3 lane unchanged; GSM8K `admitted_wrong == 0` preserved; ADR committed.

**Only run tests that exercise files you change plus the G5 axis lane,
the B3 lane, and the GSM8K safety rail.** Do not run the full suite —
that is the lead's job at integration.

**Do not stack on another agent's branch.** Target main directly.
