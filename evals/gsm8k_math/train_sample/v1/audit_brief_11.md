# Brief 11B — Reader Closure Audit (GSM8K train-sample v1)

This document is the human-readable companion to
`audit_brief_11.json`. Last updated by **Brief 11B-step-2 lexicon closure**:
12 new `drain_token` lemmas + 1 alias added to `en_core_math_v1`.

## Per-case counts

| Outcome    | Count |
|------------|------:|
| admitted   | 0     |
| refused    | 50    |
| **wrong**  | **0** |

`wrong == 0` is preserved by construction: the additions are all
`drain_token` (non-frame-opening). The hazard canary case
`gsm8k-train-sample-v1-0050` remains refused at sentence_index 0 — pinned by
`tests/test_brief_11b_step2_lexicon.py::test_hazard_case_0050_remains_refused_pre_frame`.

## Refusal taxonomy

| refusal_reason         | count | Δ vs 11B-step-1 |
|------------------------|------:|----------------:|
| incomplete_operation   | 20    | +2              |
| unexpected_category    | 17    | +3              |
| unknown_word           | 5     | **−6**          |
| unattached_quantity    | 4     | +1              |
| unresolved_pronoun     | 3     | 0               |
| no_question_target     | 1     | 0               |

The 6-case drop in `unknown_word` is the load-bearing lift. Increases in
other rows reflect *previously-hidden* downstream bottlenecks becoming
visible (Brief 11 §Gate 1: "refusal taxonomy may shrink while correct
stays flat — real new work becoming visible, not regression").

## Missing-operator taxonomy (load-bearing)

This is the work backlog that any subsequent reader-closure PR must address.
Every previously-`None` operator has now been labelled.

| missing_operator              | count | category          |
|-------------------------------|------:|-------------------|
| quantity_extraction           | 9     | incomplete_operation |
| lexicon_entry                 | 9     | unknown_word      |
| multi_quantity_composition    | 8     | incomplete_operation |
| **pre_frame_filler_sentence** | **8** | **unexpected_category (new label)** |
| pronoun_resolution            | 3     | unresolved_pronoun |
| fraction_percentage_literal   | 3     | unexpected_category |
| unit_binding                  | 3     | unattached_quantity |
| **descriptive_frame_question**| **2** | **unexpected_category (new label)** |
| compound_numeric_literal      | 1     | unknown_word      |
| compound_time_literal         | 1     | unknown_word      |
| multi_subject_sentence        | 1     | unexpected_category |
| question_target_slot          | 1     | no_question_target |
| **question_frame_slot**       | **1** | **incomplete_operation (new label)** |

## New labels introduced in this PR

### `pre_frame_filler_sentence` (8 cases)

A sentence whose verb the reader does not recognise as a frame-opener, so the
sentence reaches its terminator while still at pre-frame state with a subject
entity pinned but no quantity and no transactional verb. Examples:

- `gsm8k-train-sample-v1-0028`: *"Tom opens an amusement park."*
- `gsm8k-train-sample-v1-0035`: *"... go strawberry picking."*
- `gsm8k-train-sample-v1-0050`: *"Mark does a gig every other day for 2 weeks."*

### `pre_frame_filler_sentence` — design tension (open for operator review)

A naive fix (drain `statement_terminator` at pre-frame and route through
`_end_descriptive_frame`) **lifts 2 cases from refused → admitted** but creates
a real `wrong > 0` hazard on case `gsm8k-train-sample-v1-0050`:

```
Mark does a gig every other day for 2 weeks.  For each gig, he plays 3 songs.
2 of the songs are 5 minutes long and the last song is twice that long.
How many minutes did he play?
```

With pre-frame drain enabled, the reader admits a partial graph
`Operation(mark, add, 3, songs)` with unknown unit `minute` and would project to
a wrong answer (~3 vs expected 280). The looser variant of the fix is therefore
**rejected** by this PR per Brief 11 §"Failure modes to avoid §1 — Correct-count
greed."

A stricter variant (gate the drain on `pending_entity_ref is None and not
sentence_state.quantities`) fires on 0 of the 11 candidate cases — all of them
have a subject entity pinned before the terminator — so it is purely additive
overhead without lift.

The honest closure path requires either:

1. **Verb-vocabulary expansion** — promote currently-unknown statement verbs
   (`opens`, `does`, `goes`, `plays`, `splits`, `picking`) to recognised
   categories that open the correct statement frame; or
2. **Sentence-level intent classification before frame dispatch** — distinguish
   *context-setting* from *math-content* statements deterministically before
   committing to (or refusing) a frame.

Both are real capability work, not a one-line drain rule. Brief 11B-step-2
(future PR) is the right home.

### `descriptive_frame_question` (2 cases)

A `?` terminator reached while the sentence has fallen into `descriptive_frame`
without a `question_open` token — the question target slot was missed.
Distinct refusal mechanism from the `no_question_target` finalize check.

### `question_frame_slot` (1 case)

A `question_frame` opened (correct intent) but did not receive a required slot
such as `unit_class`. Separated from generic `incomplete_operation` so the
operator can attack question-slot recovery independently of statement-frame
slot recovery.

## Highest-leverage backlog (Brief 11B-step-2 candidates)

Ranked by `count × proximity-to-existing-mechanism`:

1. `lexicon_entry` (9) — vocabulary gap; lowest-risk extension since adding a
   lemma to the cognition pack cannot create wrong admissions without also
   passing the graph completeness check.
2. `multi_quantity_composition` (8) — requires the reader to emit two
   `PartialInitialPossession` or `PartialOperation` entries from a single
   compound-noun statement ("5 full boxes and 5 loose crayons"). Real frame
   work.
3. `pre_frame_filler_sentence` (8) — see design tension above.
4. `quantity_extraction` (9) — usually co-occurs with `compound_*` literals or
   indefinite quantifiers ("some", "a few"); needs a deliberate
   indefinite-quantity policy before any admission.

## Reproducibility

```bash
uv run python -c "
import json
from generate.comprehension.audit import audit_problem
from generate.comprehension.state import ReaderRefusal
with open('evals/gsm8k_math/train_sample/v1/cases.jsonl') as f:
    for line in f:
        c = json.loads(line)
        r, rows = audit_problem(c['question'], case_id=c['case_id'])
        print(c['case_id'], type(r).__name__,
              rows[0].missing_operator if rows else '-')
"
```

The artifact `audit_brief_11.json` is pinned by `tests/test_brief_11b_audit_artifact.py`.
