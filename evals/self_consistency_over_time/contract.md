# Self-Consistency Over Time Eval Lane — Contract

**Lane:** `self_consistency_over_time`
**Version:** v1
**Created:** 2026-05-19
**Status:** Red on creation — measurement substrate for thread-level
truthfulness.

## What this lane measures

Whether `ChatRuntime` produces the same answer to a factual prompt
at turn 1, turn N, and turn 2N — with arbitrary unrelated turns
interleaved.  This is the strongest test of identity-truthfulness
under accumulated state.

Distinct from `warmed_session_consistency` (which only replays the
*same* prompt back-to-back, where vault state has barely diverged).
Here we measure stability across **drift**.

## Per-case predicates

| Predicate | Definition |
|---|---|
| `byte_identical`         | every probe response is byte-for-byte identical |
| `key_terms_stable`       | the prompt's `expected_key_terms` all appear in every probe response |
| `grounding_source_stable`| every probe response has the same `grounding_source` |
| `no_walk_fragment`       | no probe response degrades to a < 4-token surface |

## Scoring rubric

```text
byte_identical_rate    = cases_byte_identical / total_cases
terms_stable_rate      = cases_terms_stable / total_cases
grounding_stable_rate  = cases_grounding_stable / total_cases
no_drift_to_fragment   = cases_no_fragment / total_cases
```

## Doctrine constraints

- Byte-identical is the gold standard but the lane also tracks the
  weaker `key_terms_stable` predicate so we can distinguish *exact*
  determinism from *semantic* stability.
- No LLM judge.
- Red-on-creation is acceptable for `byte_identical` — the warm path
  may inject thread anaphora prefixes that legitimately change bytes;
  the `key_terms_stable` predicate is the load-bearing one.
