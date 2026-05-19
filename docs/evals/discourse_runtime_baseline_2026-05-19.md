# Discourse Runtime Baseline — 2026-05-19

This note records the runtime evidence around the discourse-planner landing.
It preserves the pre-wiring baseline and the post-refinement predicate result
so future deltas are interpreted against the right measurement contract.

## Pre-Wiring Baseline

Measured before the five-step discourse planner sequence landed:

```json
{
  "conversational_thread_coherence_public_v1": {
    "cases": 6,
    "is_grounded_rate": 0.9333,
    "length_adequate_rate": 1.0,
    "no_placeholder_rate": 1.0,
    "no_topic_drift_rate": 0.8333,
    "not_walk_fragment_rate": 1.0,
    "topic_anchor_rate": 0.5,
    "total_turns": 45
  },
  "discourse_paragraph_public_v2": {
    "accuracy": 1.0,
    "mean_sentence_count": 14.333,
    "mean_subject_coverage": 1.0,
    "passed": 6,
    "per_sentence_grammar_pass_rate": 1.0,
    "replay_determinism_rate": 1.0,
    "total": 6
  },
  "multi_sentence_response_public_v1": {
    "cases": 15,
    "connective_present_rate": 0.1,
    "grounded_rate": 0.4667,
    "multi_sentence_rate": 0.5333,
    "non_fragment_rate": 1.0,
    "subject_named_rate": 0.5333
  }
}
```

The direct realizer path was already paragraph-capable:
`discourse_paragraph` passed at 100% with deterministic replay and
per-sentence grammar intact. The live runtime gap was upstream of
realization.

## Predicate Refinement

The original `multi_sentence_response` sentence splitter over-counted
structural punctuation:

- dotted semantic-domain atoms such as `cognition.truth`
- lowercase domain continuations such as `logos.core. truth grounds ...`
- the fixed trust-boundary tail `No session evidence yet.`

The refined predicate counts only substantive sentences:

- strip trailing provenance / trust-boundary tails before counting
- do not split on dotted semantic-domain atoms
- split a terminal mark only when followed by an uppercase/digit sentence
  opener or the end of the substantive surface

Measured on `30948a1` after the discourse planner sequence landed and with
the refined predicate:

```json
{
  "flag_off": {
    "cases": 15,
    "connective_present_rate": 0.1,
    "grounded_rate": 0.4667,
    "multi_sentence_rate": 0.2,
    "non_fragment_rate": 1.0,
    "subject_named_rate": 0.5333
  },
  "flag_on": {
    "cases": 15,
    "connective_present_rate": 0.1,
    "grounded_rate": 0.4667,
    "multi_sentence_rate": 0.2,
    "non_fragment_rate": 1.0,
    "subject_named_rate": 0.5333
  }
}
```

Interpretation: the earlier `0.5333` multi-sentence rate was inflated by
structural tails and domain punctuation. The flag-on planner work improved
form quality on surfaces where it engaged, but this one-shot lane still does
not isolate that hook. The next measurement should either prime the warm path
before scoring or move planner engagement into the cold pack/teaching-grounded
path and then compare flag-off versus flag-on again.
