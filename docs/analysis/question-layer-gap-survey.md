<!-- FILE: docs/analysis/question-layer-gap-survey.md -->

# Question-Layer Gap Survey

Status: Proposed analysis draft. No serving behavior is changed.

Source of truth for the metric is `docs/claims_ledger.md` and
`evals/gsm8k_math/train_sample/v1/report.json`: the current real
`train_sample` result is 6 correct / 44 refused / 0 wrong. This survey assigns
each of the 44 refused case ids to exactly one current failure group. It does
not claim that any group would pass if widened; it names the layer that refuses
today and estimates whether the missing capability is single-step or
composition-bound.

The requested Task A file, `docs/analysis/comprehension-primitive-inventory.md`,
was not present in this worktree. I used the embedded older handoff only as
orientation and grounded the grouping below in the report plus the live parser /
recognizer code.

## Code Map

Current refusal topology:

- `generate/math_candidate_graph.py` first extracts statement choices, then
  consults the ratified recognizer registry when a numeric statement has no
  parser candidate. If recognition succeeds but injection yields no typed
  solver primitive, it now refuses explicitly instead of dropping the statement.
- `generate/recognizer_anchor_inject.py` is still a category dispatch surface.
  Only `discrete_count_statement` and a narrow `multiplicative_aggregation`
  entry can emit today; other categories return empty and therefore become
  explicit refusals.
- `generate/math_candidate_parser.py` admits a closed question grammar:
  total-across `How many ... do they have ...`, existential aggregate
  `How many ... are there ...`, entity possession, activity `did`, and three
  ADR-0163.D.4 patterns. If these emit no `CandidateUnknown`, the graph refuses
  before branch enumeration.
- ADR-0174 explicitly deprecates the per-category injector dispatch table as
  the long-term runtime admission path. Injector widening should therefore be
  treated as stopgap or hypothesis-emitter work, not the primary strategic
  direction.

## Assignment Table

Tractability scoring is case-level and arity-aware:

- High: one closed primitive or one local parser frame is plausibly missing.
- Medium: one local frame/schema is clear, but downstream composition is still
  likely needed.
- Low: the current refusal is an early stop in a 2-4 capability derivation.

| Group | Count | Case ids | Current failing layer | Tractability | Representative report reason excerpts | Interpretation |
|---|---:|---|---|---|---|---|
| DCS high-arity composition wall | 18 | 0002, 0015, 0016, 0020, 0029, 0031, 0032, 0033, 0034, 0036, 0037, 0038, 0039, 0040, 0041, 0044, 0047, 0049 | Matcher -> injector -> composition | Low | `candidate_graph: recognizer matched but produced no injection for statement: 'She splits it up into 25-foot sections.' (category=discrete_count_statement)`; `candidate_graph: recognizer matched but produced no injection for statement: 'Malcolm is trying to find the fastest walk to school and is currently comparing two routes.' (category=discrete_count_statement)` | The recognizer often fires on a count-like token, but the actual derivation needs division, rest-state, route comparison, percent/rate, chained comparisons, target residuals, or per-entity attributes. Widening the discrete-count injector alone is metric-inert and risks incomplete readings. |
| Missing inverse/residual/comparative question frames | 5 | 0007, 0008, 0009, 0025, 0035 | Question parser / admissibility | Low | `candidate_graph: no admissible candidate for question: 'How many more boxes do they need if Francine has a total of 85 crayons?'`; `candidate_graph: no admissible candidate for question: 'How many more apples would Martha need to give away to be left with only 4 of them?'` | These are not just new surface phrasings for `Unknown(entity, unit)`. They ask for a missing operand, inverse relation, target residual, or conditional total. The question layer must bind the requested slot to a derivation, not merely extract a unit. |
| Rate, currency-rate, and tariff statements | 4 | 0001, 0011, 0017, 0022 | Recognizer -> injector/schema | Medium | `candidate_graph: recognizer matched but produced no injection for statement: 'Tina makes $18.00 an hour.' (category=rate_with_currency)`; `candidate_graph: recognizer matched but produced no injection for statement: 'He’s charging $50.00 per day or $500.00 for 14 days.' (category=temporal_aggregation)` | The local schema gap is visible: `rate_with_currency` and `temporal_aggregation` need typed rate/tariff hypotheses. Case-level admission still needs overtime, profit, historical+today aggregation, or piecewise tariff composition. |
| Non-quantitative relation category used as an early stop | 4 | 0012, 0023, 0027, 0046 | Matcher -> injector | Low | `candidate_graph: recognizer matched but produced no injection for statement: 'He put all of them in his aquarium but his fish ate half of them.' (category=descriptive_setup_no_quantity)`; `candidate_graph: recognizer matched but produced no injection for statement: 'Half of the students are girls, the other half are boys.' (category=descriptive_setup_no_quantity)` | The category name is accurate for the injector: it cannot emit a concrete primitive from the matched surface. The cases need fraction-of-prior, combined-total binding, partition, and percentage-of-subgroup reasoning. |
| Multiplicative aggregate beyond the narrow emitted shapes | 3 | 0006, 0013, 0045 | Recognizer -> injector / composition registry | Medium | `candidate_graph: recognizer matched but produced no injection for statement: 'Mandy started reading books with only 8 pages when she was 6 years old.' (category=multiplicative_aggregation)`; `candidate_graph: recognizer matched but produced no injection for statement: 'Each survey has 10 questions.' (category=multiplicative_aggregation)` | There is already a narrow product injector, but these rows need time/age chains, month segmentation, doubled rates, or survey-count composition. Single product emission may help local state, but full cases still depend on multi-step composition. |
| Financial currency amount / percent mutation statements | 3 | 0019, 0028, 0043 | Recognizer -> injector / mutation schema | Low | `candidate_graph: recognizer matched but produced no injection for statement: 'After the first appointment, John paid $100 for pet insurance that covers 80% of the subsequent visits.' (category=currency_amount)`; `candidate_graph: recognizer matched but produced no injection for statement: 'Her mother gave her an additional $4, and her father twice as much as her mother.' (category=currency_amount)` | The surface contains currency, but the required reading is coverage after first event, percent daily operating cost, revenue target, or comparative gift amount. A `CandidateInitial` currency emission would be an incomplete graph. |
| Fractional relational statements with no parser candidate | 3 | 0004, 0005, 0010 | Statement parser / admissibility | Low | `candidate_graph: no admissible candidate for statement: 'Half of the kids are going to soccer camp, and 1/4 of the kids going to soccer camp are going to soccer camp in the morning.'`; `candidate_graph: no admissible candidate for statement: 'Marion has 1/4 more than what Yun currently has, plus 7.'` | The parser has fraction literals and comparative operations, but these surfaces are relational fractions over prior or unknown quantities. They require held equations or derivation nodes, not a flat possession/operation candidate. |
| Duration and recurrence statement frames | 3 | 0030, 0048, 0050 | Statement parser / temporal composition | Medium | `candidate_graph: no admissible candidate for statement: 'It is a 2-hour drive each way.'`; `candidate_graph: no admissible candidate for statement: 'Mark does a gig every other day for 2 weeks.'` | These expose bounded duration-multiplier or temporal-frequency frames. Each frame is local and deterministic, but the cases still need composition across trip stages, weekly deltas to target, or per-event song duration totals. |
| Relational conjoined-subject each initial | 1 | 0026 | Statement parser / entity binding | Medium | `candidate_graph: no admissible candidate for statement: 'Aaron and his brother Carson each saved up $40 to go to dinner.'` | The parser has an `each` extractor for two named subjects, but this sentence uses a possessive relational subject (`his brother Carson`) and a purpose tail. The local parse is probably narrower than the concept; the full case remains multi-step because bill fraction and shared scoop count follow. |

Total assigned: 18 + 5 + 4 + 4 + 3 + 3 + 3 + 3 + 1 = 44.

## Backlog Interpretation

The audited partition is the stable artifact. A single `count x tractability`
sort is misleading here because count ranges from 1 to 18 while tractability is
coarse; it would place the known composition wall at the top as if it were an
incremental injector work order. In this survey, count is impact evidence, not
the sort key for near-term changes.

### Composition-Bound Work

These groups should feed the ADR-0174 held-hypothesis / derivation-composer
scope, not category-specific injector widening. They need multi-clause state,
referent binding, ratio/fraction relations, target-slot questions, or
event-scope composition before any answer can be safe.

| Group | Count | How to use the count |
|---|---:|---|
| DCS high-arity composition wall | 18 | Main evidence that discrete-count recognition is surfacing a composition wall, not an injector backlog. |
| Missing inverse/residual/comparative question frames | 5 | Question-layer evidence that unknowns must bind to derivation slots, not just noun units. |
| Rate, currency-rate, and tariff statements | 4 | Rate/tariff hypotheses are useful only if downstream overtime, profit, history, or piecewise composition can refuse partial readings. |
| Non-quantitative relation category used as an early stop | 4 | Evidence for relation/partition composition and for avoiding hard-stop loss of later structure. |
| Multiplicative aggregate beyond the narrow emitted shapes | 3 | Product-like anchors need day/month, age-chain, or survey-count composition before admission. |
| Financial currency amount / percent mutation statements | 3 | Currency is not enough; these need percent coverage, operating-cost, or spend/residual mutation. |
| Fractional relational statements with no parser candidate | 3 | Needs relational fraction/equation hypotheses, not flat possession candidates. |
| Duration and recurrence statement frames | 3 | Duration-multiplier and recurrence frames are local signals whose answers require temporal composition. |

### Bounded Near-Term Fixes

These are smaller, lower-blast-radius probes that may be useful as executable
follow-ups or regression tests. They should still preserve refusal-first
admission and should not be represented as the main path to the metric.

| Candidate fix | Case ids | Why bounded |
|---|---|---|
| Relational conjoined-subject `each` binding | 0026 | One row exposes a local entity-binding gap around `Aaron and his brother Carson each ...`; useful as a narrow parser/binding probe even though the full problem remains multi-step. |
| Descriptive/no-quantity early-stop handling | 0012, 0023, 0027, 0046 | The bounded mechanism is to avoid losing later structure when a descriptive relation cannot emit state; the cases behind it still require composition, so this is not a direct answer path. |
| Single-slot question-frame probes | subset of 0007, 0008, 0035 | A few question surfaces can become narrow probes for residual or divisor target-slot binding. They must be held as unknown slots and refused unless the derivation is complete. |

## Layer Notes

The high-count `discrete_count_statement` bucket should not be read as "add more
discrete-count injectors." The report is saying the matcher saw something
count-shaped before the engine had a safe composed reading. In the live code,
recognized-but-uninjected statements refuse explicitly because dropping them
would permit incomplete graphs. ADR-0174 points in the same direction:
injectors should become hypothesis emitters inside a held-hypothesis reader,
where branch disagreement, constraint propagation, and completeness can reject
partial readings.

The five question refusals are genuinely question-layer refusals in the narrow
code sense: `extract_question_candidates` emits no `CandidateUnknown`. But all
five ask for an inverse or residual target. A wider regex that only extracts
the noun would not identify the unknown slot and would still be unsafe under
`wrong = 0`.

## Open Questions for the Claude Lane

- Confirm whether `docs/analysis/comprehension-primitive-inventory.md` was meant
  to be landed in this worktree or only supplied out-of-band; this draft could
  be amended to cite its exact primitive table once present.
- Run an instrumented read of the 44 refused cases to distinguish "injector
  returned empty because no parsed anchors existed" from "anchors existed but
  constraint propagation eliminated them."
- For the five question refusals, collect the intended `Unknown` slot shape
  without using gold answers: missing operand, residual-to-target, inverse
  divisor, or aggregate total.
- Decide whether the next executable lane should prototype rate/tariff
  hypotheses or question-target slots first; both are safer as held hypotheses
  than as direct category admissions.
