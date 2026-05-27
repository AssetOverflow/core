# ADR-0164 — Incremental Comprehension Reader (replaces regex sentence-template parsing)

**Status:** Proposed
**Date:** 2026-05-26
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Parent:** [ADR-0163 — Path to GSM8K mastery](./ADR-0163-gsm8k-path-to-mastery.md)
**Companions:** [ADR-0165 — Regex Scope Rule](./ADR-0165-regex-scope-rule.md), [ADR-0132/0133/0134/0135 — Binding graph](./), [ADR-0150/0152/0155/0161 — Contemplation / HITL corridor](./), [ADR-0114a — Anti-overfitting proof obligations](./ADR-0114a-anti-overfitting-proof-obligations.md)
**Supersedes in part:**
- [ADR-0163](./ADR-0163-gsm8k-path-to-mastery.md) §Phase B–E *prescription* (the regex-based `DerivedRecognizer` production path). Its diagnosis and its HITL corridor are preserved.
- [ADR-0136 — Statement Layer Corridor](./ADR-0136-statement-layer-corridor.md) and the [ADR-0136.S.1–S.4](./) sub-family (regex sentence-template additions). Their empirical refusal taxonomies are preserved as input evidence; the regex prescription is replaced.

---

## Context — why the front-end was the bottleneck, and why the prescribed fix doesn't fix it

ADR-0163 correctly identified that the GSM8K capability gap sits *before* the
binding graph and solver, in `generate/math_candidate_parser.py` and
`generate/math_candidate_graph.py`. The downstream substrate
(`MathProblemGraph`, the binding-graph admissibility check, the solver, the
verifier, the realizer) is mastered in isolation and passes every controlled
capability axis at 100% with `wrong = 0`. GSM8K refuses at near-100% because
its statements span surface shapes the front-end has never been taught.

That diagnosis is preserved verbatim by this ADR.

The *prescription* of ADR-0163 — broaden the recognizer set via the
contemplation → proposal → review corridor, where each accepted recognizer is
a typed regex matcher in `generate/recognizer_match.py` — does not fix the
underlying problem. It institutionalizes it.

A regex template is, by construction, an enumeration of one surface shape.
Each accepted recognizer covers exactly the cases its pattern matches and
refuses on every novel phrasing of the same underlying mathematical
structure. The post-D.2 baseline measured this directly:

```text
GSM8K train_sample/v1:  correct=3  refused=47  wrong=0
  exit_criterion: { correct_min: 10, wrong_max: 0, passed: false }
```

The refusal split is diagnostic:

- **34/47** are `no admissible candidate for question:` — the statements
  parsed, but the question surface form did not match any of the ~6 question
  regexes in `math_candidate_parser.py` (Pattern A/B/C, capacity, earnings,
  conditional-op).
- **9/47** are `no admissible candidate for statement:` — a statement hit a
  recognizer gap (fractions, rate-with-currency, periodic temporal).
- **4/47** are `no branch produced a solvable graph` — statements + question
  admitted but the solver couldn't close.

The question grammar is the dominant bottleneck. The current question
patterns try to enumerate ~6 frames of "what an English math-problem question
looks like." English doesn't have a closed grammar for math-problem
questions, so the enumeration is unbounded and the refusal rate climbs with
linguistic diversity. Adding a seventh, eighth, twentieth pattern is not a
limit-decreasing operation; the refusal-rate ceiling is set by the regex
template approach itself.

---

## Diagnosis — regex sentence-templates overfit by design

A regex template at the **sentence-structure** level claims that a class of
meanings (e.g. "ask for a residual quantity") has a closed orthographic form
(e.g. `How\s+much\s+(money|...)\s+(will|did)\s+...\s+(make|earn|...)`). This
claim is false for natural language. Three consequences follow:

1. **Refusal is brittle.** "How much will it cost him?" and "how much did he
   pay in total?" and "how much money will she be left with after the
   purchase?" all ask the solver for the same kind of output — the value of
   one terminal-state quantity — but no template covers all three, and each
   missing template is a refusal.

2. **The fix path is unbounded.** Each refused phrasing produces a new
   recognizer. Each new recognizer adds vocabulary and structural assumptions.
   The set has no closure: there is no point at which "all GSM8K question
   shapes have been covered" because the set of question shapes is not finite.

3. **The model loses comprehension.** A template either matches or it
   doesn't. It has no partial understanding. There is no state in which the
   engine has "read three words and narrowed the interpretation" — the
   pattern matches the whole sentence or refuses. That is the opposite of
   how comprehension works.

ADR-0163's pathway (recognizer-via-contemplation) addresses *who writes the
regex* (the contemplation loop, not the operator). It does not address
*whether regex sentence-templates are the right representation at all.* They
are not.

---

## Decision — incremental comprehension reader

Replace the regex sentence-template front-end with an **incremental
compositional reader** that processes one token at a time, maintains an
immutable partial-comprehension state, and produces the same downstream
types (`CandidateInitial`, `Operation`, `MathProblemGraph`,
`BoundUnknown`-input fields) the regex parser produces today.

The downstream substrate is unchanged. The binding graph, admissibility
check, solver, verifier, realizer, and round-trip filter all stay in place
and continue to enforce the `wrong = 0` invariant.

### Three components

**1. Operational lexicon (data, not code).**

Each word in the comprehension vocabulary maps to a *semantic category* and
an *update rule*. The category carries the generalization; adding a word is
adding a lookup, never a rule.

Example category set (closed, ADR-tracked, extended only by ratification):

| Category | Examples | Role in reader state |
|---|---|---|
| `question_open` | how, what | open question frame |
| `question_continuous_qty` | much, long, far, old | continuous-quantity question |
| `question_discrete_qty` | many | discrete-count question |
| `question_comparative` | more, less, longer, fewer | mark question as `difference` |
| `residual_modifier` | left, remaining, after | terminal-state residual |
| `aggregate_modifier` | total, in all, altogether, combined | sum across entities |
| `accumulation_verb` | earn, make, gain, accumulate, save | additive op |
| `depletion_verb` | spend, pay, lose, give | subtractive op |
| `transfer_verb` | give, send, pass | transfer op |
| `distributive_modifier` | each, per | bind rate or multiply |
| `currency_unit_noun` | money, dollars, profit, income, savings, cost | unit class: currency |
| `count_unit_noun` | apples, books, kids, chickens, … | unit class: countable |
| `time_unit_noun` | hour, day, week, minute, year | unit class: time |
| `entity_pronoun` | she, he, they, it | binds resolved entity |
| `proper_noun_entity` | Tina, Marion, Jen, … | binds entity directly |

The lexicon lives under `language_packs/data/en_core_math_v1/` parallel to
`en_core_cognition_v1` and `en_core_relations_v1`, with the same loader
discipline, the same manifest-checksum rule (CLAUDE.md §Semantic Pack
Discipline), and the same review pathway (ADR-0150/0152/0155/0161). New
lexicon entries enter through reviewed teaching, never via operator edits.

The vocabulary already collected in `math_candidate_parser.py` —
`_MASS_NOUNS`, `_PATTERN_A_VERBS`, `_PATTERN_B_VERBS`, `_PATTERN_C_VERBS`,
`_CAPACITY_VERB_PATTERN`, `_EARNINGS_VERB_PATTERN`, `ADD_VERBS`,
`SUBTRACT_VERBS`, `TRANSFER_VERBS`, `_FEMALE_NAMES`, `_MALE_NAMES` — is
**ported wholesale** as the seed corpus of the new lexicon. That ratified
vocabulary is good work; only its container (regex character classes inside
sentence templates) is wrong.

**2. Partial-comprehension state (immutable).**

```text
ComprehensionState:
  entities:        tuple[EntityRef, ...]      # who's been mentioned
  quantities:      tuple[QuantityRef, ...]    # numbers with units, attached or floating
  operations:      tuple[PartialOp, ...]      # verb-induced operations, possibly incomplete
  question_target: QuestionTargetSlot | None  # what's being asked, possibly partial
  expectation:     ExpectationFrame | None    # what category would close the current frame
```

`expectation` is the load-bearing field for recontextualization. After
reading "How much money will she", the state's expectation is "an
accumulation verb, a depletion verb, a residual modifier, or a
state-continuation verb." Each closes the question frame differently. The
expectation is what tells the reader how to interpret an ambiguous next
word.

State is frozen-dataclass immutable. Canonical-bytes serialization
(sorted-key, fixed-precision) keeps `trace_hash` deterministic per CLAUDE.md
§Runtime Surface Contract.

**3. Deterministic reader (state machine over categories).**

```text
apply_word(state, word) -> state | Refusal
```

For each token:
1. **Lexical primitive scan** (ADR-0165): try to match orthographic
   primitives — currency literal, fraction literal, numeric literal,
   percentage literal, time-unit noun — in priority order. If one fires,
   the token becomes a typed lexeme with extracted value(s) and category.
2. **Lexicon lookup**: if no primitive fired, look up the surface form in
   the operational lexicon. If absent, refuse with
   `unknown_word: <token> (position N)`.
3. **Expectation check**: if the token's category satisfies
   `state.expectation`, apply the update rule. If not — and the category
   is a legal frame opener at this position — close the current frame and
   open a new one. If neither — refuse with
   `unexpected_category: got <cat>, expected <frame>`.
4. Emit new state.

End-of-sentence: the state must satisfy a finalization predicate
(question_target is bound, operations have their operands, dangling
quantities have unit attachments). Otherwise refuse with `unfinished_frame`.

The reader is a deterministic shift-reduce parser **over semantic
categories**, not over tokens. The category set is ~20 items; the
composition rules total 30–50. Adding a verb does not change a rule. Adding
a category requires an ADR.

### Output

The reader emits one of:
- A `MathProblemGraph` (and the underlying `CandidateInitial` /
  `Operation` tuple) ready for the existing candidate-graph admissibility
  layer, or
- A typed `ReaderRefusal` carrying the token position, the failed
  expectation, and the closest legal next category. Refusals are the
  evidence the teaching loop chews on (Phase E below).

Downstream consumption is unchanged. The binding-graph adapter (ADR-0133),
the `BoundUnknown` resolver (ADR-0135), the admissibility check (ADR-0134),
the solver (ADR-0116), and the verifier (ADR-0117) all act on the reader's
output exactly as they act on the regex parser's output today. The
`wrong = 0` invariant is preserved by construction because the reader does
not *bypass* admissibility — it produces inputs to it.

---

## Constraints (non-negotiable)

1. **`wrong = 0` at every phase, every round, every split.** The reader can
   be more permissive about *which sentences it comprehends* without
   weakening *what comprehension produces*. The existing admissibility,
   unit-proof, and multi-branch-disagreement refusal stay in force.

2. **No hidden normalization, stochastic fallback, or "best guess."** The
   reader refuses cleanly on novel structure. No softmax over candidate
   parses, no nearest-template selection, no default category.

3. **No regex sentence-templates.** Per [ADR-0165](./ADR-0165-regex-scope-rule.md),
   regex is allowed only at the lexeme level (currency literal, fraction
   literal, etc.). Any regex that matches across word combination is a
   grammar template and forbidden.

4. **Lexicon and category set are closed and ADR-tracked.** New lexicon
   entries land through reviewed teaching (the existing ADR-0150/0152/0155/
   0161 corridor — preserved from ADR-0163). New categories or new
   composition rules require an ADR.

5. **Deterministic replay.** Identical input → byte-equal reader output. The
   `ComprehensionState` has canonical-bytes serialization. The reader emits
   a deterministic trace that feeds `trace_hash`.

---

## What's deprecated, what's preserved

### Deprecated by this ADR

- **ADR-0163 §Phase B–E prescription**: the production of regex-based
  `DerivedRecognizer` records that land in
  `generate/recognizer_match.py`. New recognizers in this form are blocked
  starting with the reader's first acceptance round. Existing recognizers
  remain dormant during the transition (see Coexistence below) and are
  removed once their categories are covered by the reader.
- **ADR-0136 — Statement Layer Corridor** and the sub-family
  [ADR-0136.S.1–S.4](./): regex sentence-template additions to
  `math_candidate_parser.py`. The empirical refusal taxonomies they
  produced are preserved as input evidence for lexicon and category work.
  The patterns themselves are scheduled for removal once the reader
  covers their cases.
- The `Pattern A` / `Pattern B` / `Pattern C` regex blocks introduced by
  ADR-0163.D.4 in `generate/math_candidate_parser.py` (`_Q_MASS_NOUN_RE`,
  `_Q_COMPARATIVE_RE`, `_Q_PRONOUN_VERB_RE`) — replaced by the reader's
  question-frame composition rules.

### Preserved in full

- **The binding graph** (ADR-0132/0133/0134/0135). The reader produces the
  same input types it consumes today.
- **The HITL corridor** (ADR-0150/0152/0155/0161). New lexicon entries and
  new categories ride the same contemplation → proposal → review pathway.
  ADR-0163's corridor architecture is correct; only what flows through it
  changes (lexicon entries instead of regex recognizers).
- **The capability-axis lanes** (G1–G5, S1). They continue to validate the
  downstream substrate and act as the regression net for any reader
  change.
- **`wrong = 0` doctrine** and the replay-equivalence gate.
- **All closed-set vocabulary** previously collected by the regex parser.
  It is the seed of the operational lexicon.

### Untouched but adjacent

- The `recognizer_registry` / `recognizer_match` modules become the lexicon
  loader and lexical-primitive registry rather than the regex pattern
  store. The interface signature changes but the corridor-driven
  *population* of these registries is preserved.

---

## Phasing

### Phase 1 — Question reader (where 34/47 refusals live)

Build the reader for question sentences only. The output type is narrow:
just the fields `BoundUnknown` consumes (`entity`, `unit`, question_form).
Coexist with the existing regex question patterns: reader runs first; on
refusal, falls through to existing regex; on reader acceptance, regex is
not invoked. Measure pickup rate against `train_sample/v1` per round.

Acceptance for Phase 1:
- Reader covers ≥20/34 currently-refused question cases.
- Combined (reader + legacy) `correct ≥ 10` on the 50-case sample with
  `wrong = 0`. This satisfies the Round-1 exit criterion of ADR-0163.
- Reader has zero disagreement with regex on the 6 cases where both fire
  (3 correct + 3 secondary), per byte-equal `BoundUnknown` output.

### Phase 2 — Statement reader

Extend the reader to statement sentences. Coexist with existing regex
statement patterns the same way. Phase out the regex statement patterns
incrementally as reader coverage grows.

Acceptance for Phase 2:
- Reader covers ≥30/50 train_sample cases end-to-end (statements +
  question both via reader).
- `correct ≥ 25` (ADR-0163 Round-2 exit) with `wrong = 0`.

### Phase 3 — Regex layer removal

Once reader coverage ≥ regex coverage on a case-by-case basis, the regex
sentence-template layer is deleted. The lexical-primitive layer (regex
applied to single orthographic shapes per ADR-0165) survives — that is the
correct use of regex and is not what this ADR deprecates.

Acceptance for Phase 3:
- `correct ≥ 35` on train_sample, `wrong = 0` (ADR-0163 Round-3 exit).
- `math_candidate_parser.py` no longer contains sentence-level regex
  patterns. Closed-set vocabulary tables remain (now consumed by the
  lexicon loader rather than woven into regexes).

### Phase 4 — Scale

Per ADR-0163 §Phase F: public, holdout, full GSM8K. No changes to that
scope from this ADR; the reader simply replaces the front-end.

---

## Acceptance criteria for this ADR (Proposed → Accepted)

This ADR moves to **Accepted** when:

1. A `ComprehensionState` prototype exists in `generate/comprehension/`
   with frozen-dataclass shape, canonical-bytes serialization, and unit
   tests pinning determinism.
2. The seed lexicon pack `en_core_math_v1` is materialized from the
   existing closed-set vocabulary in `math_candidate_parser.py`, with the
   standard pack-test discipline.
3. Phase 1 acceptance is met on `train_sample/v1`.
4. Capability-axis lanes G1–G5, S1 remain at 100% `wrong = 0` (regression
   net unbroken).
5. `verify pinned lane SHAs` continues to pass.

---

## Open questions (resolve before Phase 1 PR)

1. **Lexical primitive set scope.** Inventory of which orthographic shapes
   get primitives vs. lexicon entries (currency literal, fraction literal,
   percentage literal, decimal literal, time-unit noun, dollar-amount,
   ordinal). Likely a sub-ADR (ADR-0164.1).
2. **Ambiguity resolution precedence.** When a token could open two
   frames, the precedence order. Likely a sub-ADR after Phase 1
   measurement reveals which collisions are real.
3. **Pronoun-entity resolution.** The reader needs entity resolution
   anyway; the regex parser's `_resolve_question_entity` heuristic is a
   reasonable starting point but should be reviewed against the
   compositional model.
4. **Cross-sentence state.** The current regex parser is per-sentence;
   GSM8K problems have cross-sentence references ("she" referring to
   "Tina" three sentences earlier). The reader will need a
   `ProblemReadingState` that persists across sentences. Scope this in
   Phase 1 design.

---

## Cross-references

- **Bottleneck evidence**: `evals/gsm8k_math/train_sample/v1/report.json`,
  `refusal_taxonomy_v4.json`.
- **Substrate that survives**: `generate/binding_graph/`,
  `generate/math_solver.py`, `generate/math_verifier.py`,
  `generate/math_realizer.py`, capability-axis lanes.
- **The corridor**: ADR-0150 (contemplation), ADR-0152 (learning-arc),
  ADR-0155 (CI contemplation runner), ADR-0161 (HITL queue).
- **The boundary rule**: ADR-0165.
- **The anti-overfitting doctrine**: ADR-0114a.
- **The thesis**: `[[thesis-decoding-not-generating]]` — the reader is a
  decoder. Each word narrows the space; the meaning is the accumulation,
  not the match.
