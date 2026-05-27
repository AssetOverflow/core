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

## Post-W2 baseline (ADR-0167 LexicalClaim-first)

Measured by running the comprehension audit over the 50 cases on the W3-A
branch (`feat/adr-0167-w3a-e2e-determinism`, base = `origin/main` after W1-A,
W2-A, W2-B, W2-C, and W2-D merged).  No pack mutation occurred during the
measurement — counts reflect the same real `en_core_math_v1` pack the test
suite runs against.

| dimension | count |
| --- | --- |
| admitted | 0 |
| refused | 50 |

Refusal reasons:

| reason | count |
| --- | --- |
| incomplete_operation | 20 |
| unexpected_category | 17 |
| unknown_word | 5 |
| unattached_quantity | 4 |
| unresolved_pronoun | 3 |
| no_question_target | 1 |

Missing operators (first refusal per case):

| missing_operator | count |
| --- | --- |
| quantity_extraction | 11 |
| pre_frame_filler_sentence | 9 |
| multi_quantity_composition | 8 |
| fraction_percentage_literal | 4 |
| unit_binding | 4 |
| lexicon_entry | 3 |
| pronoun_resolution | 3 |
| descriptive_frame_question | 2 |
| multi_subject_sentence | 2 |
| compound_numeric_literal | 1 |
| compound_time_literal | 1 |
| question_frame_slot | 1 |
| question_target_slot | 1 |

Adapter, signature, ratification, and e2e tests all green; cognition
regression untouched.

Case 0050 hazard verification: refused at sentence_index 0 (verified by both
`tests/test_math_lexical_ratification.py::test_hazard_case_0050_remains_refused`
and `tests/test_math_evidence_e2e.py::test_lexical_ratification_advances_unknown_word_row`
step 8).

Regression net: any future PR that touches the math reader → evidence wire
must keep `tests/test_math_evidence_e2e.py` green.  It covers the full path
from `AuditRow` → `MathReaderRefusalEvidence` → `claim_signature` →
`apply_lexical_claim` → re-audit, plus a cross-process determinism check and
the cognition-domain partition guard from W2-C.

## Wave-Next A2 — `rate_with_currency` injector — schema-refusal delta

Branch: `feat/injector-rate-with-currency`.  Brief: Wave-Next A2 (see
`docs/handoff/WAVE-NEXT-INJECTORS.md`).

### Schema decision

**Does `Quantity` structurally model a per-unit rate? No — but a separate
`Rate` type (ADR-0122) does.**  The schema-refusal hinges not on the
absence of `Rate` but on its absence from the per-sentence injector
contract:

- `Quantity` is a scalar + single unit pair; it carries no
  numerator/denominator distinction (verified in
  `tests/test_injector_rate_with_currency.py::TestSchemaEvidence`).
- `Rate(value, numerator_unit, denominator_unit)` exists at
  `generate/math_problem_graph.py:78` and is the operand of
  `Operation(kind='apply_rate')`.
- The per-sentence dispatch contract is
  `SentenceChoice = Union[CandidateInitial, CandidateOperation]`
  (`generate/math_candidate_graph.py:152`).  There is no
  `CandidateRate` variant for the injector to deposit.
- A rate-declaration sentence alone ("Tina makes $18.00 an hour.")
  carries no denominator quantity, so it cannot be coerced into a
  complete `apply_rate` `CandidateOperation` either.

### What this PR delivers

- `generate/recognizer_anchor_inject.py` — new
  `inject_rate_with_currency(match, sentence) -> ()` function plus
  dispatch-table entry for `ShapeCategory.RATE_WITH_CURRENCY`.  The
  injector returns `()` for every input shape and documents the
  schema gap inline.
- `tests/test_injector_rate_with_currency.py` — 16 tests across six
  pin classes: schema evidence, schema refusal, dispatch wired, case
  0050 hazard pin, determinism, and wrong=0 invariant.

### Eval delta

| dimension | before A2 | after A2 |
|---|---:|---:|
| correct  | 3  | 3  |
| wrong    | 0  | 0  |
| refused  | 47 | 47 |

Lift count: **0** (expected — the schema decision is "Rate is not in
`SentenceChoice`," so v1 cannot emit state).  The PR's deliverable is
documenting the gap; the case-by-case picture is unchanged.

### Case 0050 hazard verification

Sentence 0 of case `gsm8k-train-sample-v1-0050` is
"Mark does a gig every other day for 2 weeks." — it carries no
currency symbol, so the `rate_with_currency` recognizer never matches
it.  Even if A2 v1 emitted state (it doesn't), this case is not
reachable through the A2 path.  Pinned by
`tests/test_injector_rate_with_currency.py::TestCase0050HazardPin`
(sentence-zero currency-absence check + end-to-end refusal check).

### Follow-up note — "rate-type schema needs extension"

For a future PR to lift any of the rate-shaped refusals via the
recognizer-injector path, the `SentenceChoice` union must be widened.
Concretely:

1. Add a `CandidateRate` dataclass to
   `generate/math_candidate_parser.py` (sibling of `CandidateInitial`
   and `CandidateOperation`) carrying a `Rate` operand keyed by
   actor, with source-span provenance fields analogous to the
   existing two `Candidate*` types.
2. Extend `SentenceChoice = Union[CandidateInitial,
   CandidateOperation]` to include `CandidateRate`.  Update
   `_slot_count`, `_collapse_per_sentence_ties`, `_initial_admissible`
   (or add a sibling `_rate_admissible`), and the per-sentence
   admission gate in
   `generate.math_candidate_graph.parse_and_solve`.
3. Teach `parse_and_solve` to compose an accepted `CandidateRate`
   with a downstream `apply_rate`/multiply-shaped question.  The
   existing `extract_earnings_candidates` short-circuit path is the
   closest precedent and should be unified with the new
   `CandidateRate` flow rather than left as a sibling.
4. Only after (1)–(3) ship can `inject_rate_with_currency` emit
   `CandidateRate` and start lifting rate-shaped refusals.  The
   matcher (`generate/recognizer_match.py:_match_rate_with_currency`)
   already extracts the necessary `(currency_symbol, amount,
   per_unit)` triple; an entity-extraction extension is the only
   additional matcher work required.

This sequencing keeps the wrong=0 doctrine intact: no widening of
admissible solver state until the schema extension is reviewed and
the round-trip filter is updated.

