# Brief 11B-step-2 — Verb Classification for `pre_frame_filler_sentence`

This document is the deliverable for Brief 11B-step-2. It enumerates the 8
GSM8K train-sample cases the Phase 2 reader refuses with
`missing_operator = pre_frame_filler_sentence` and classifies the
unrecognized statement-opening verb in each case as either (a) a
frame-opener that should be added to the operational lexicon, or (b) a true
context filler.

It also documents — with explicit evidence — why **this PR ships no runtime
or pack change**, per Brief 11B-step-2 §Hard constraints:

> "If you can't find a safe fix that lifts cases without violating wrong=0,
> the right answer is to publish the verb-classification analysis as
> documentation + leave runtime unchanged. Don't ship a risky fix."

## Per-case enumeration

The 8 cases (reproduced by the canonical audit lane in
`audit_brief_11.json`):

| case_id                          | failing sentence (sentence_index)                                                      |
|----------------------------------|----------------------------------------------------------------------------------------|
| `gsm8k-train-sample-v1-0002`     | `(1)` "She splits it up into 25-foot sections."                                        |
| `gsm8k-train-sample-v1-0016`     | `(0)` "On Rudolph's car trip across town, he traveled 2 more than 5 miles and …"      |
| `gsm8k-train-sample-v1-0025`     | `(0)` "Lilibeth and her friends go strawberry picking."                                |
| `gsm8k-train-sample-v1-0028`     | `(0)` "Tom opens an amusement park."                                                   |
| `gsm8k-train-sample-v1-0030`     | `(0)` "Jake decides to go to the beach for a fun day."                                 |
| `gsm8k-train-sample-v1-0035`     | `(1)` "She decided to split them among her friends."                                   |
| `gsm8k-train-sample-v1-0036`     | `(0)` "Monica way studying for an exam."                                               |
| `gsm8k-train-sample-v1-0050`     | `(0)` "Mark does a gig every other day for 2 weeks."                                   |

## Current lexicon classification

The pre-frame failure is **not** because these verbs are unknown — almost
all of them are already in the `en_core_math_v1` lexicon, classified as
`drain_token`. The refusal mechanism is more subtle: when no
frame-opening verb fires before the sentence terminator, `_apply_preframe`
treats `statement_terminator` as an unhandled category at pre-frame
position and refuses with `unexpected_category`. The audit layer
(`generate/comprehension/audit.py`) labels this `pre_frame_filler_sentence`.

| verb / surface       | current category in pack             | proposed reclassification |
|----------------------|--------------------------------------|---------------------------|
| `splits`, `split`    | `drain_token` (lemma `split`)        | **keep as `drain_token`** — see §0002 below |
| `traveled`, `travel` | `drain_token` (lemma `travel`)       | **defer** — needs compound-numeric (`2 more than 5`) before any frame |
| `go`, `goes`         | `drain_token`                        | **keep as `drain_token`** — true filler |
| `picking`            | `drain_token` (lemma `picking`)      | **keep as `drain_token`** in this context; cf. `pick` is `capacity_verb` |
| `opens`, `open`      | `drain_token`                        | **keep as `drain_token`** — true scenario filler |
| `decides`, `decided` | `drain_token` (lemma `decided`)      | **keep as `drain_token`** — modal/control, not math |
| `studying`           | `drain_token`                        | **keep as `drain_token`** — gerund used as nominal |
| `does`               | `modal_aux`                          | **keep as `modal_aux`** — see §0050 below |
| `plays`, `play`      | `capacity_verb` (frame-opener)       | already correct; not the failing token here |

The `does`-as-`modal_aux` and `plays`-as-`capacity_verb` classifications
are both correct in the pack today. The actual blocker on each case is the
**rest of the sentence**, not a missing verb category.

## Per-case classification with evidence

### `0002` — "She splits it up into 25-foot sections."

- **Verb token**: `splits`.
- **Action semantics**: partition (`1000 feet` → `1000/25` sections).
- **Why not a frame-opener today**: the sentence's `25-foot` is a
  hyphenated compound numeric+unit ("25-foot"), not yet supported by the
  reader's primitive scanner. Even if `splits` were promoted to
  `depletion_verb`, the `operation_frame` would refuse on the compound
  literal before reaching the terminator.
- **Decision**: leave `splits` as `drain_token`. The honest blocker is
  `compound_numeric_literal`, already tracked in the Brief 11B taxonomy.

### `0016` — "…he traveled 2 more than 5 miles…"

- **Verb token**: `traveled`.
- **Action semantics**: distance covered (could be `capacity_verb`).
- **Why not a frame-opener today**: the sentence's `2 more than 5` is a
  comparative-numeric compound ("2 more than 5 miles"), not in the
  reader's primitive set. Promoting `traveled` to `capacity_verb` opens
  an `operation_frame` that would then refuse on the compound numeric —
  i.e. the refusal moves from pre-frame to in-frame but the case still
  refuses.
- **Decision**: leave `traveled` as `drain_token`. The honest blocker is
  `multi_quantity_composition`, already tracked.

### `0025` — "Lilibeth and her friends go strawberry picking."

- **Verb tokens**: `go`, `picking`.
- **Action semantics**: pure scenario setup. The sentence carries **no
  quantity**.
- **Decision**: leave `go` / `picking` as `drain_token`. Even if drained
  cleanly, the next sentence ("Lilibeth fills 6 baskets where each basket
  holds 50 strawberries") refuses on `lexicon_entry`, per the post-skip
  simulation below.

### `0028` — "Tom opens an amusement park."

- **Verb token**: `opens`.
- **Action semantics**: pure scenario setup. No quantity in the sentence.
- **Decision**: `drain_token`. Post-skip simulation shows the next
  refusal is `pronoun_resolution` ("It cost $100,000 …").

### `0030` — "Jake decides to go to the beach for a fun day."

- **Verb tokens**: `decides`, `go`.
- **Action semantics**: pure scenario setup. No quantity.
- **Decision**: `drain_token`. Post-skip simulation shows the next
  refusal is `pronoun_resolution` ("It is a 2-hour drive each way.").

### `0035` — "She decided to split them among her friends."

- **Verb tokens**: `decided`, `split`.
- **Action semantics**: declares intent; no quantity in this sentence.
- **Decision**: `drain_token`. Post-skip simulation shows the next
  refusal is `unit_binding`.

### `0036` — "Monica way studying for an exam."

- **Verb token**: `studying`. (`way` is a likely-typo of `was`; the
  corpus preserves it verbatim and we do not normalize.)
- **Action semantics**: scenario setup. No quantity.
- **Decision**: `drain_token`. Post-skip simulation shows
  `pronoun_resolution` next.

### `0050` — "Mark does a gig every other day for 2 weeks." (THE HAZARD)

- **Verb token**: `does` (currently `modal_aux`).
- **Action semantics**: aspectual filler — "performs a gig". The phrase
  `every other day for 2 weeks` is a frequency × duration construct that
  yields `14 / 2 = 7` gigs as an implicit count; the reader does not yet
  represent frequency-by-duration aggregation.
- **Quantity in this sentence**: `2` (with unit `weeks`).
- **Why a runtime drain is unsafe**: per Brief 11B §Design tension, the
  naive drain of `statement_terminator` at pre-frame, followed by
  `_end_descriptive_frame`, would let the second sentence ("For each
  gig, he plays 3 songs.") admit `Operation(mark, add, 3, songs)`,
  while the expected answer requires aggregating across
  (gigs × songs × minutes/song). Result: graph projects to ~3, expected
  280. **wrong > 0.**
- **Decision**: leave `does` as `modal_aux`. The honest blocker is a
  frequency-aggregation operator (`every other day for 2 weeks`), which
  is out-of-scope for Brief 11B-step-2.

## Post-skip simulation evidence (no admissions available)

For each of the 8 cases we re-ran `audit_problem` on the problem text
**with the failing sentence elided**. In every case the problem still
refuses — i.e. **no case can be lifted from refused → admitted** by
handling only the pre-frame filler:

| case_id   | next refusal_reason       | next missing_operator        |
|-----------|---------------------------|------------------------------|
| `…-0002`  | `unexpected_category`     | `fraction_percentage_literal`|
| `…-0016`  | `unresolved_pronoun`      | `pronoun_resolution`         |
| `…-0025`  | `unknown_word`            | `lexicon_entry`              |
| `…-0028`  | `unresolved_pronoun`      | `pronoun_resolution`         |
| `…-0030`  | `unresolved_pronoun`      | `pronoun_resolution`         |
| `…-0035`  | `unattached_quantity`     | `unit_binding`               |
| `…-0036`  | `unresolved_pronoun`      | `pronoun_resolution`         |
| `…-0050`  | `unresolved_pronoun`      | `pronoun_resolution`         |

Even a hypothetical "perfect" pre-frame closure produces **zero lifts**
in the GSM8K train-sample today.

## Decision: ship documentation, leave runtime + pack unchanged

Per Brief 11B-step-2 §Hard constraints — no safe fix lifts a case
without violating `wrong == 0`, and no fix lifts a case at all without
first delivering one of:

1. Compound-numeric / multi-quantity composition (Brief 11B-step-3
   candidate);
2. Pronoun resolution for `it` / `he` / `she` referencing the elided
   subject of a prior filler sentence;
3. Frequency × duration aggregation for case 0050.

Each is real capability work and is the right home for further Brief
11B work, not this PR.

## wrong=0 verification

This PR makes **no** change to:

- `generate/comprehension/lifecycle.py`
- `generate/comprehension/lexicon.py`
- `generate/comprehension/audit.py`
- `language_packs/data/en_core_math_v1/**`

Therefore the reader runtime and the audit artifact
(`audit_brief_11.json`) are bit-identical to PR #345 (Brief 11B), and
the load-bearing invariants from
`tests/test_brief_11b_audit_artifact.py` continue to hold:

- `summary.admitted == 0`
- `summary.refused == 50`
- `invariants.wrong_count == 0`

Case `gsm8k-train-sample-v1-0050` — the hazard — remains refused at
`pre_frame_filler_sentence`, with the partial graph
`Operation(mark, add, 3, songs)` **never reaching
`assert_graph_complete`**.

## Reproducibility

The pre-skip enumeration:

```bash
uv run python -c "
import json
from generate.comprehension.audit import audit_problem
with open('evals/gsm8k_math/train_sample/v1/cases.jsonl') as f:
    for line in f:
        c = json.loads(line)
        r, rows = audit_problem(c['question'], case_id=c['case_id'])
        if rows and rows[0].missing_operator == 'pre_frame_filler_sentence':
            print(c['case_id'])
"
```

The post-skip simulation:

```bash
uv run python -c "
import json, re
from generate.comprehension.audit import audit_problem
SPLIT = re.compile(r'(?<=[.!?])\s+')
TARGETS = {'gsm8k-train-sample-v1-' + n for n in
           ('0002','0016','0025','0028','0030','0035','0036','0050')}
with open('evals/gsm8k_math/train_sample/v1/cases.jsonl') as f:
    for line in f:
        c = json.loads(line)
        if c['case_id'] not in TARGETS: continue
        sents = [s for s in SPLIT.split(c['question'].strip()) if s.strip()]
        r, rows = audit_problem(c['question'], case_id=c['case_id'])
        si = rows[0].sentence_index
        remainder = ' '.join(sents[:si] + sents[si+1:])
        r2, rows2 = audit_problem(remainder, case_id=c['case_id'] + '-skip')
        print(c['case_id'], rows2[0].refusal_reason, rows2[0].missing_operator)
"
```

Both lanes are pinned by
`tests/test_brief_11b_step2_verb_classification.py`.
