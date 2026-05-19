# Multi-Sentence Response Eval Lane — Contract

**Lane:** `multi_sentence_response`
**Version:** v1
**Created:** 2026-05-19
**Status:** Red on creation — measurement substrate for compositional surface.

## What this lane measures

Whether `ChatRuntime` can emit a response that is more than a single
sentence when the prompt structurally calls for elaboration
("Explain X", "Tell me about X", "Describe X", "Walk me through X").

Currently every pack-grounded surface is a single sentence emitted
by `_frame_gloss`.  NARRATIVE and EXAMPLE intents already compose
multi-clause output via teaching chains, so they are tested here too
as the *only* multi-sentence-capable code path.

## Per-case predicates

| Predicate | Definition |
|---|---|
| `sentence_count_>=_2`   | the substantive surface contains at least 2 terminated sentences (`.`, `?`, `!`) |
| `each_sentence_>=_4_tokens` | every sentence has ≥ 4 alphabetic tokens (no fragments) |
| `connective_present`    | the surface contains at least one connective (`and`, `because`, `therefore`, `which`, `since`, `also`, `furthermore`, `however`, `consequently`) — only enforced when `expects_connective=true` |
| `not_just_provenance_tag` | sentence_count counts BEFORE trailing provenance / trust-boundary tails (`pack-grounded (…).`, `No session evidence yet.`) are treated as real sentences |
| `grounded`              | `grounding_source` ∈ {pack, teaching} |
| `subject_named`         | the prompt's subject lemma appears in the surface |

## Scoring rubric

```text
multi_sentence_rate     = cases_with_>=2_sentences / total_cases
non_fragment_rate       = cases_where_every_sentence_>=4_tokens / total_cases
connective_present_rate = cases_with_connective / cases_expecting_connective
```

## Doctrine constraints

- The trailing provenance / trust-boundary tail is structural, not a real
  sentence — predicate logic strips it before counting.
- Dotted semantic-domain atoms (`cognition.truth`, `logos.core`) are not
  sentence boundaries by themselves.  A terminal mark counts as a boundary
  only when it is followed by a new uppercase/digit sentence opener or the
  end of the substantive surface.
- No LLM judge.  Pure structural counting.
- Red-on-creation expected: only NARRATIVE / EXAMPLE / cross-pack /
  composed_surface code paths can possibly satisfy `sentence_count_>=_2`
  today.
