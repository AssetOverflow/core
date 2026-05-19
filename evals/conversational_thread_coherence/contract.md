# Conversational Thread Coherence Eval Lane — Contract

**Lane:** `conversational_thread_coherence`
**Version:** v1
**Created:** 2026-05-19
**Status:** Red on creation — measurement substrate for long-span fluency.

## What this lane measures

Whether `ChatRuntime` maintains coherent grounding and topic continuity
across an 8–12 turn thread that includes topic shifts, follow-up
questions, and re-introductions of earlier subjects.

The asymmetric pair to `warmed_session_consistency`: that lane pins
*replay* stability of identical prompts; this lane pins *evolving*
conversation across structurally-different turns.

## Per-turn predicates

| Predicate | Definition |
|---|---|
| `no_placeholder`        | surface contains none of: `...`, `<pending>`, `<prior>`, `<empty>` |
| `is_grounded`           | `grounding_source` ∈ {pack, teaching, vault, oov, partial} (not `none`) on turns whose prompt is expected to ground |
| `not_walk_fragment`     | surface has ≥ 4 alphabetic tokens AND ≥ 1 finite verb form |
| `length_adequate`       | `len(surface.strip()) ≥ 20` |

## Per-case predicates

| Predicate | Definition |
|---|---|
| `topic_anchor_present`  | When a follow-up prompt does not name the prior topic explicitly (e.g. "What about that?"), the response surface mentions the prior topic's subject lemma OR explicitly discloses |
| `no_topic_drift_to_none` | After any `pack`/`teaching` turn, no subsequent turn on the SAME prompt-subject drops to `none` (would indicate state corruption) |

## Scoring rubric

```text
per_turn_grounded_rate     = grounded_turns / total_turns
per_turn_not_fragment_rate = non_fragment_turns / total_turns
case_topic_anchor_rate     = cases_passing_anchor / cases_with_anaphora
case_no_drift_rate         = cases_passing_no_drift / replay_cases
```

## Doctrine constraints

- No LLM judge.  All predicates are deterministic, lexical / structural.
- No paraphrase equivalence by embedding.  Lexical overlap only.
- Red-on-creation is acceptable and expected — this lane is a target,
  not a regression gate (yet).
