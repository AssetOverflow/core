# C2 — Wire `run_lane` to `_score_one_candidate_graph`

**Classification**: Unfinished migration (audit finding C2)  
**Risk**: Medium — must verify baseline comparison files still reproduce  
**Scope**: `evals/gsm8k_math/runner.py` only

---

## Problem

`run_lane` (line 449) calls `_score_one`, the legacy regex path
(`generate/math_parser.py` → `MathProblemGraph` → `solve`). Only the
per-lane override in `train_sample/v1/runner.py:33` uses
`_score_one_candidate_graph`. Any caller that goes through `run_lane` —
including the `public/`, `dev/`, and `holdout` lanes — is evaluated on the
legacy parser, not the candidate-graph architecture we've been measuring.

**Impact**: lift numbers on `train_sample/v1` are not comparable to what
`run_lane` would report on the other slices. The three-slice concern from the
audit is real.

---

## What `_score_one_candidate_graph` does differently

`_score_one_candidate_graph` (line 241) calls `parse_and_solve` from
`generate/math_candidate_graph`, which layers:

1. Whole-problem comprehension reader (ADR-0164 Phase 2, flag-gated)
2. Per-statement recognizer candidate graph (ME-1..ME-5 matchers)
3. Question-sentence hybrid reader (ADR-0164 Phase 1)
4. Injector dispatch (ADR-0170 + recognizer_anchor_inject.py)
5. Cartesian-product branch enumeration + admissibility gate
6. Existing solver + verifier (same as `_score_one`)

`_score_one` calls the regex parser directly, skipping steps 1–5.

---

## Migration plan

### Step 1 — Baseline snapshot (before changing `run_lane`)

```bash
# Capture current run_lane output on all slices that have unsealed cases
uv run python -m evals.gsm8k_math.runner --lane public  > /tmp/pre_public.json
uv run python -m evals.gsm8k_math.runner --lane dev     > /tmp/pre_dev.json
# Do NOT touch holdout; it is sealed.
```

### Step 2 — Wire `run_lane`

In `evals/gsm8k_math/runner.py` line 449, replace:

```python
outcomes = [_score_one(c) for c in cases]
```

with:

```python
outcomes = [_score_one_candidate_graph(c) for c in cases]
```

Add a `--legacy-parser` CLI flag that restores `_score_one` for the
comparison baseline file. The flag is only needed to reproduce
`baselines/frontier.json` and `baselines/comparison_v1.json`, both of which
were captured under the legacy path.

```python
# In run_lane signature:
def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: Any = None,
    legacy_parser: bool = False,
) -> LaneReport:
    score_fn = _score_one if legacy_parser else _score_one_candidate_graph
    outcomes = [score_fn(c) for c in cases]
```

### Step 3 — Verify wrong == 0 on public/dev

```bash
uv run python -m evals.gsm8k_math.runner --lane public  > /tmp/post_public.json
uv run python -m evals.gsm8k_math.runner --lane dev     > /tmp/post_dev.json
# Assert wrong == 0 in both outputs
```

### Step 4 — Update baselines if counts differ

If `correct` counts differ (expected — the new path refuses differently),
update `baselines/frontier.json` and `baselines/comparison_v1.json` by
re-running with `--legacy-parser` so the files still reflect legacy baseline
numbers:

```bash
uv run python -m evals.gsm8k_math.runner --lane public --legacy-parser \
    > evals/gsm8k_math/baselines/frontier.json
```

### Step 5 — Run smoke + packs suites

```bash
uv run core test --suite smoke -q
uv run core test --suite packs -q
```

---

## Invariant gates

- `wrong == 0` must hold on public + dev after the migration.
- `_score_one_candidate_graph` already enforces this by construction (same
  verifier as `_score_one`, additive reader, refusal-preferring injector).
- The baseline snapshots captured in Step 1 give you a before/after diff to
  explain any count change in a PR description.

---

## Relation to other findings

- **C4** (compositions compile): C4 should land first or simultaneously so
  that `run_lane` immediately benefits from the registry being non-empty.
- **C5** (reader zero-delta): confirmed that the reader is inert until
  statement-level injector gaps close. C2 does not depend on C5.
