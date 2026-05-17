# discourse_paragraph eval lane

## What it measures

Whether the deterministic realizer can produce **paragraph-scale**
output — multiple grammatical sentences joined by deterministic
discourse markers — from a multi-step ArticulationTarget.

This is the first lane that stresses output longer than a single
3-word SVO sentence.  It addresses the open scope item:
*"longer/more complex sentences and phrases for testing and proving
stuff"*.

## Inputs

Each case carries a `graph` (≥ 3 nodes), an ordered `steps` list
(`ASSERT` open, then `SEQUENCE` / `ELABORATE` / `CONTRAST`), and
acceptance constraints:

```json
{
  "id": "DP-PUB_001",
  "topic": "epistemic_chain",
  "graph": {"nodes": [{"node_id": "n1", "subject": "wisdom",
                       "predicate": "grounds", "obj": "knowledge"}, ...],
            "edges": []},
  "steps": [{"node_id": "n1", "move": "ASSERT"}, ...],
  "min_sentences": 4,
  "max_sentences": 6,
  "must_contain_subjects": ["wisdom", "knowledge", "evidence", "truth"],
  "discourse_markers": ["furthermore", "next"]
}
```

## Scoring rubric

Per case:

  - `paragraph_sentence_count` ≥ `min_sentences` (and ≤ `max_sentences`)
  - `subject_coverage_rate` ≥ 0.75
  - `discourse_marker_present` — at least one expected marker emitted
  - `replay_determinism` — running the case twice produces an
    identical surface string

Aggregate metrics:

  - `accuracy` — pass rate
  - `mean_sentence_count`
  - `mean_subject_coverage`
  - `replay_determinism_rate`

## Splits

| Split | n | content |
|---|---|---|
| public/v1 | 12 | epistemic / scientific / creation / logic / ethics / linguistic / math / narrative / biology / physics + 2 contrast cases |
| holdouts/v1 | 5 | musical / social / computational / psychological / economic |
| dev | 1 | epistemic_chain smoke |

## What this lane does NOT measure

- Round-trip through `ChatRuntime` (the realizer is exercised
  directly).  See gaps.md.
- Factual correctness of the asserted propositions.
