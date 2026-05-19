# Cold-Start Grounding Eval Lane — Contract

**Lane:** `cold_start_grounding`
**Version:** v1
**Created:** 2026-05-19

## What this lane measures

Cold-start routing of conversational prompts to the correct grounding
source.  Each case is fed through a **fresh** `ChatRuntime()` (no
vault accumulation, no prior turn) and the runtime's
`ChatResponse.grounding_source` is compared against the case's
`expected_grounding_source`.

This is a *routing* probe, not a fluency probe.  It does not score
sentence quality, morphology, or surface diversity.  It scores:

> *"For a realistic conversational prompt about a pack-resident lemma,
> does the runtime correctly route to a pack/teaching surface — and
> for a genuinely OOV lemma or an honest knowledge gap, does it route
> to OOV/none?"*

Two architectural invariants are pinned by this lane:

1. Pack-resident DEFINITION subjects always route to `pack`.
2. CAUSE / VERIFICATION subjects without an active teaching chain
   stay `none` (deliberate non-fallback — preserves the
   discovery-candidate signal the teaching pipeline uses).

## Scoring rubric

Each case produces three binary signals:

| Signal | Definition |
|---|---|
| `intent_match`     | `actual_intent.tag.value == expected_intent` |
| `grounding_match`  | `actual_grounding_source == expected_grounding_source` |
| `subject_match`    | `actual_intent.subject == expected_subject` (optional; only checked when case carries `expected_subject`) |

Lane-level metrics:

| Metric | Definition | v1 pass threshold |
|---|---|---|
| `grounding_accuracy` | Fraction of cases with correct grounding source | >= 0.95 |
| `intent_accuracy`    | Fraction of cases with correct intent tag       | >= 0.95 |
| `subject_accuracy`   | Fraction of cases with correct extracted subject (subset that asserts subject) | >= 0.90 |

## Pass criteria

All three thresholds satisfied on the public v1 split.

## Cold-start invariant

The runner constructs a **new** `ChatRuntime()` for every case.  This
is deliberate: the lane measures cold-start routing, not multi-turn
accumulation behaviour.  Re-using a runtime across cases would
contaminate vault content from earlier prompts (this is exactly the
bug observed during the 2026-05-19 probe — when the same runtime
processed multiple prompts the vault grounding source overrode the
pack source on later turns, producing garbled surfaces).

## Why this lane exists

The 2026-05-19 cumulative live probe surfaced that ~52% of realistic
conversational DEFINITION prompts on pack-resident lemmas were
returning `grounding_source="none"`.  The bottleneck was intent
classification + subject extraction, not lexicon coverage.  Five
specific patterns (`Define X`, `What does X mean?`, `What is to V?`,
`How does X work?`, `What causes X?`) had no rule or routed to an
intent the runtime dispatcher couldn't handle.

This lane commits that probe set as a durable, replayable artifact so
the lift is reproducible and any future regression in intent routing
fails the lane immediately.

## Case schema

```jsonl
{
  "id": "definition_doubt_001",
  "prompt": "What is doubt?",
  "category": "definition_meta_pack",
  "expected_intent": "definition",
  "expected_grounding_source": "pack",
  "expected_subject": "doubt"
}
```

`expected_grounding_source` is one of: `pack`, `teaching`, `oov`,
`none`, `vault`, `partial`.

`expected_subject` is optional; when present it pins the
extracted-subject invariant.

`category` is freeform and used to group cases in reports.
