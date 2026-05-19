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

## Post-Cold-Path Wiring + Lane Priming (`2aae25f` + `9367209`)

Two follow-up commits closed the measurement gap:

- `9367209` — added optional `priming_prompts` to lane case schema, exposed
  `primed_multi_sentence_rate` so warm-path effects are measured without
  inflating cold-start numbers.
- `2aae25f` — engaged the discourse planner on the cold pack/teaching path,
  not only the warm post-walk path.  Identical helper now serves both.

Lane expanded from 15 → 21 cases (6 primed variants added).  A/B:

```json
{
  "flag_off": {
    "cases": 21,
    "multi_sentence_rate": 0.1429,
    "primed_multi_sentence_rate": 0.0,
    "primed_cases": 6,
    "connective_present_rate": 0.0769,
    "grounded_rate": 0.4762
  },
  "flag_on": {
    "cases": 21,
    "multi_sentence_rate": 0.5238,
    "primed_multi_sentence_rate": 0.5,
    "primed_cases": 6,
    "connective_present_rate": 0.2308,
    "grounded_rate": 0.4762
  }
}
```

Cold-start lift: `multi +38pp`, `connective +15pp`, `primed_multi +50pp`.
The remaining unlifted cases are upstream `IntentTag.UNKNOWN` failures, not
planner gaps — three sample classifications confirm:

```text
Explain truth.                       -> IntentTag.UNKNOWN, ResponseMode.EXPLAIN
Write a short paragraph about truth. -> IntentTag.UNKNOWN, ResponseMode.PARAGRAPH
Tell me about truth.                 -> IntentTag.NARRATIVE, ResponseMode.EXPLAIN
```

## Post-Helper-Dedup + Expository-DEFINITION Classifier (`f03d7d0` + this)

- `f03d7d0` — collapsed the two duplicated discourse-planner hooks
  (cold-start branch + warm post-walk branch) into a single helper
  `ChatRuntime._maybe_apply_discourse_planner(text, source_tag) -> str | None`.
  No behavior change — same lane numbers as `2aae25f`.
- This commit — extended `generate/intent.py:_RULES` with three new
  expository rules so `Explain X` / `Write a paragraph about X` /
  `Paragraph about X` route to `IntentTag.DEFINITION`, while keeping
  `Tell me about X` and `Describe X` on `IntentTag.NARRATIVE` and
  `ResponseMode` fully orthogonal.

Re-measured A/B on the same 21 cases:

```json
{
  "flag_off": {
    "cases": 21,
    "multi_sentence_rate": 0.1429,
    "primed_multi_sentence_rate": 0.0,
    "primed_cases": 6,
    "connective_present_rate": 0.5385,
    "grounded_rate": 0.8571
  },
  "flag_on": {
    "cases": 21,
    "multi_sentence_rate": 0.9048,
    "primed_multi_sentence_rate": 1.0,
    "primed_cases": 6,
    "connective_present_rate": 0.8462,
    "grounded_rate": 0.8571
  }
}
```

Combined lift over the original baseline:

| metric                    | pre-wiring | refined | post-cold | post-classifier | Δ total |
|---------------------------|-----------:|--------:|----------:|----------------:|--------:|
| multi_sentence_rate       | 0.5333†    | 0.20    | 0.5238    | 0.9048          | +70pp   |
| primed_multi_sentence_rate| n/a        | n/a     | 0.5000    | 1.0000          | +50pp   |
| connective_present_rate   | 0.10       | 0.10    | 0.2308    | 0.8462          | +74pp   |
| grounded_rate             | 0.4667     | 0.4667  | 0.4762    | 0.8571          | +39pp   |

† Inflated by structural tails — pre-refinement number is not comparable.

Interpretation: every metric is now driven by load-bearing capability rather
than punctuation artifacts.  Cognition eval byte-identical throughout
(`100/100/91.7/100` public, `100/100/83.3/100` holdout).  Conversational
thread coherence unchanged (3 unwanted placeholders flag-off and flag-on).
The remaining 9.5% of `multi_sentence_rate` and 14% of `connective_present`
miss flag-on lives in two cases that classify to UNKNOWN by other routes
(`compose` and `walkthrough` category prompts) — those are the next upstream
targets, not planner gaps.
