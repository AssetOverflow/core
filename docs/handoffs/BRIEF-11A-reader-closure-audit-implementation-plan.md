# Brief 11A — Reader Closure Audit Implementation Plan

**Status:** Implementation branch scaffold
**Date:** 2026-05-27
**Branch:** `feat/brief-11a-reader-closure-audit`
**Parent:** PR #336 / Issue #337

---

## Purpose

Brief 11A turns the current GSM8K reader corridor into a measurable diagnostic surface without relaxing the `wrong == 0` discipline.

The key hidden surface in current `main` is the recognized-but-not-injected statement path in `generate/math_candidate_graph.py`:

```python
# Recognized but no injection — skip the sentence, do
# not refuse.  Identical to the round-2 skip-only
# wiring; preserves wrong=0 because zero math state
# is contributed.
continue
```

That behavior is safe, but it hides the work queue. Brief 11A should expose it as audit data.

---

## Implementation target

Do not create a parallel runner.

Extend the existing train-sample runner:

```text
evals/gsm8k_math/train_sample/v1/runner.py
```

It already owns:

- `--use-reader`
- baseline-vs-reader delta generation
- `reader_phase1_delta.json`
- deterministic case iteration
- correct/refused/wrong counting

Brief 11A should add audit output to this harness, not fork the measurement path.

---

## Proposed changes

### 1. CandidateGraphResult audit field

Add an optional immutable diagnostic field:

```python
recognized_skipped_statements: tuple[str, ...] = ()
```

or, preferably, structured JSON strings if avoiding new dataclasses in the first pass:

```json
{
  "sentence_index": 1,
  "sentence": "...",
  "recognized_category": "...",
  "recognized_terms": [...],
  "skipped_frame": "recognizer_match_without_injection",
  "missing_operator": "inject_from_match_empty",
  "refusal_reason": "recognized_but_not_injected"
}
```

Keep this field empty on paths that do not consult the recognizer registry.

### 2. Capture skip-only recognizer matches

At the `recognizer_match is not None` / `injected == ()` path, append one audit event before `continue`.

The event must be deterministic:

- stable key ordering;
- no object reprs;
- sentence index from the loop, not nondeterministic enumeration;
- recognizer category/name normalized to a string;
- parsed anchors reduced to sorted primitive values only.

### 3. Propagate audit events through every return

Every `CandidateGraphResult` return after statement parsing must preserve the tuple.

Early short-circuit paths before statement parsing may return an empty tuple.

### 4. Runner report extension

Extend each per-case row:

```json
{
  "case_id": "...",
  "verdict": "refused|correct|wrong",
  "reason": "...",
  "reader_trace": [...],
  "recognized_skipped_statements": [...]
}
```

If `_score_one_candidate_graph` currently hides the raw `CandidateGraphResult`, add the smallest safe access path. Prefer enriching the existing score object only if it is already the canonical report boundary.

### 5. Audit summary file

When `--use-reader` is passed, write:

```text
evals/gsm8k_math/train_sample/v1/reader_closure_audit.json
```

Suggested schema:

```json
{
  "schema_version": 1,
  "brief": "11A",
  "sample_path": "evals/gsm8k_math/train_sample/v1/cases.jsonl",
  "counts": {
    "cases_with_recognized_skips": 0,
    "recognized_skipped_statements": 0
  },
  "rows": [
    {
      "case_id": "...",
      "sentence_index": 1,
      "sentence": "...",
      "recognized_terms": [],
      "skipped_frame": "recognizer_match_without_injection",
      "missing_operator": "inject_from_match_empty",
      "refusal_reason": "recognized_but_not_injected"
    }
  ]
}
```

### 6. Tests

Add tests that prove:

1. audit rows are emitted for a recognized-but-not-injected statement;
2. audit rows are deterministic across two runs;
3. audit rows do not change admission/refusal outcome;
4. `wrong == 0` remains the train-sample invariant for the reader-enabled path;
5. flag-off path has empty audit rows.

---

## Acceptance gate

Brief 11A is successful when the repo can answer:

> Which GSM8K train-sample statements did CORE recognize but fail to inject into a complete solver graph?

without weakening refusal discipline.

---

## Non-goals

- Do not fix the missing operators in 11A.
- Do not widen regex surfaces.
- Do not change scoring thresholds.
- Do not promote capability.
- Do not add new canonical eval lanes.

This PR is instrumentation and audit only.
