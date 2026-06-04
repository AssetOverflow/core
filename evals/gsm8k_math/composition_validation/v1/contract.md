# GSM8K Composition Validation v1

This corpus is a Phase 5b measurement instrument, not a serving lane and not an
emission implementation. It pins a small set of real and guard-seeded GSM8K
composition shapes so each future slice is measured against two coupled facts:
coverage may rise only while `wrong == 0` remains true.

## Scope

- 22 cases total (4 baseline controls, 7 permanent hard-negatives, 11 future
  positives).
- Positive cases use `target_verdict = solve` and a non-baseline `gate`; they
  refuse today and should flip only when that gate's capability slice lands.
- Hard-negative cases use `target_verdict = refuse` and `gate = permanent`; they
  must continue refusing because the input is incomplete or outside the current
  decidable regime.
- Baseline controls use `gate = baseline`; they already solve and must keep
  solving to the exact gold answer.

## Schema

Each JSONL row has these fields:

- `case_id`: stable corpus-local id.
- `source`: exact source pointer (`gsm8k_train_sample:*`, `guard:*`, or
  `analysis:*`).
- `question`: prompt passed to `generate.math_candidate_graph.parse_and_solve`.
- `gold`: numeric gold answer, or `null` for permanent hard-negatives where no
  complete reading exists.
- `target_verdict`: `solve` or `refuse`.
- `composition`: coarse composition family.
- `gate`: `baseline`, `permanent`, or a future capability gate such as `5b-R1`.
- `baseline_verdict`: tree-verified current verdict at corpus creation.
- `baseline_answer`: current answer when `baseline_verdict = solve`, otherwise
  `null`.
- `baseline_branches_enumerated`: current `CandidateGraphResult` branch count.
- `note`: short reason the case is included.

## Invariants

1. Wrong-zero firewall: every case must either refuse or answer exactly `gold`;
   a non-gold admission is a failure.
2. Null-gold hard-negatives: when `gold` is `null`, any admission is a failure.
3. Baseline controls: every `gate = baseline` row must solve to `gold` at every
   step.
4. Permanent refusals: every `gate = permanent` row must refuse until a future
   reviewed ADR explicitly changes its decidable regime.
5. Progress metric: count rows where `target_verdict = solve` and the current
   answer equals `gold`; this starts at the baseline controls and may increase
   only when invariants 1-4 still pass. The solved-positive count is monotone
   non-decreasing across Phase 5b slices.
6. Dataset-sourced golds: every `gsm8k_train_sample:*` row's `gold` equals that
   case's `answer_numeric` in `evals/gsm8k_math/train_sample/v1/cases.jsonl`,
   verbatim. Golds are never hand-computed — a wrong gold is a `wrong=0` hazard
   in the instrument itself. (`guard:*` / `analysis:*` rows are seeded probes,
   not dataset cases, and carry their stated gold.)
7. Baseline fields are diagnostic, not asserted targets:
   `baseline_verdict` / `baseline_answer` / `baseline_branches_enumerated`
   record the tree state at creation for drift detection on non-positive rows.
   They are not a pass/fail target for positive rows — a 5b flip updates them in
   lockstep with the snapshot assertion.

## Baseline

At creation on `origin/main` lineage after PR #534 plus the docs-only runway
correction, and extended with the second R4/R5 positives (cv-0021/cv-0022), the
intended baseline is:

- 4 solve
- 18 refuse
- 0 wrong

The corpus deliberately includes both future positives and permanent
hard-negatives. A future Phase 5b slice should update only the measured current
result, not the row's baseline fields.
