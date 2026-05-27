# SESSION 2026-05-26 — Comprehension Reader Decision

**Participants:** Shay, Claude (Sonnet 4.6 → Opus 4.7 for ADR drafting)
**Outputs:**
[ADR-0164 — Incremental Comprehension Reader](./ADR-0164-incremental-comprehension-reader.md),
[ADR-0165 — Regex Scope Rule](./ADR-0165-regex-scope-rule.md).
**Affected:** [ADR-0163](./ADR-0163-gsm8k-path-to-mastery.md) (prescription
partially superseded), [ADR-0136 + sub-family](./ADR-0136-statement-layer-corridor.md)
(regex prescription superseded; vocabulary preserved as lexicon seed).
**Anchor:** [[thesis-decoding-not-generating]]

---

## What triggered the session

PR cleanup turn that started as "merge the open PRs" became an architectural
session when the operator asked why the post-D.2 GSM8K train_sample baseline
remained at `correct=3 refused=47 wrong=0`.

Three open PRs were on the board at session start:

- **#316** — `fix(INV-02): allowlist test_issue_300_versor_margin.py` — all
  checks green, mergeable. Merged first.
- **#315** — `feat(ADR-0163.D.2): parsed_anchors → MathProblemGraph state
  — discrete_count_statement injection v1` — smoke failing because the
  INV-02 allowlist fix wasn't in its base. Rebased onto new main after
  #316, smoke turned green, merged.
- **#314** — `docs(plan): CORE general advancement path` — rebased onto
  new main, all checks green, merged.

Board cleared. Then the substantive question.

## The diagnostic dive

The operator asked: "Why aren't we getting more of these answers right?"

Running the train_sample runner directly produced
`correct=3 refused=47 wrong=0` with `exit_criterion: correct_min=10, passed=false`.
Refusal-reason aggregation showed the bottleneck precisely:

- **34 / 47** refusals were `no admissible candidate for question: '<text>'`
  — statements parsed successfully, but the question surface form did not
  match any of the ~6 question regexes in
  `generate/math_candidate_parser.py` (Pattern A / B / C, capacity,
  earnings, conditional-op).
- **9 / 47** refusals were `no admissible candidate for statement: '<text>'`
  — statement-side regex gaps (5 of them fraction operands).
- **4 / 47** refusals were `no branch produced a solvable graph` —
  statements + question admitted but the solver couldn't close.

The 3 admitted cases shared a tight structural signature: rate × time
patterns plus one distributive multiply + subtract. The exact patterns the
regex front-end was originally written to handle.

The v4 refusal taxonomy
(`evals/gsm8k_math/train_sample/v1/refusal_taxonomy_v4.json`) reinforced
the picture: 23 distinct primary-barrier categories across 47 cases, with
no single category larger than 5 cases. The long tail of distinct shapes
is the long tail of English question surface forms.

## The operator's diagnosis (load-bearing)

The operator said, plainly:

> "Obviously the whole regex stuff is overfitting by design… lol. I was
> literally wondering about that when it was being built… just thought
> you knew what you were doing."

And:

> "Regex wasn't meant to be there. And I said, if we are going to allow
> regex in, then we teach the model how to use regex itself as a 'mental
> tool' of sorts. but not use it to overfit templates to what we want.
> That's only ever going to end up being a bottleneck risk. Makes no
> sense. If there truly were a said, rule-based system for sentence
> structure then that would be different, and we could use all the
> 'known' templates."

This is the architectural pivot. Three points compress into it:

1. **Sentence-template regex is overfitting by definition.** A regex
   sentence-template is an enumeration of memorized surface shapes
   pretending to be a grammar rule. English does not have a closed
   grammar for math-problem questions. Adding more templates does not
   approach a limit; the refusal-rate ceiling is set by the *method*,
   not by template count.

2. **Regex has a legitimate role at the lexeme level.** Currency
   literals, fractions, percentages, numeric expressions, closed-set
   unit-noun lists — these have genuinely closed orthographic rules.
   Regex is the honest tool for recognizing them. The boundary is:
   regex describes "what one piece of orthographic material looks like,"
   never "how words combine to mean X."

3. **The model should be able to acquire regex tools through review,
   not have them hard-coded.** The operator had already designed the
   teaching/contemplation/HITL corridor (ADR-0150 / 0152 / 0155 / 0161)
   for exactly this purpose. The corridor is general: it can ratify new
   vocabulary, new categories, and new lexeme primitives through the
   same review pathway. Regex tools become *data* the engine
   accumulates through reviewed teaching, not code the operator writes.

The operator's framing of point 3 was the moment the corridor's purpose
generalized in scope: it teaches *recognition capability*, not just
*recognized content*. That is the structural difference between a fixed
toolkit and an intelligence that can grow its own tools.

## The architectural shape of the answer

The downstream substrate is correct and stays:

```
... → MathProblemGraph → BoundUnknown (ADR-0135) → Admissibility
       (ADR-0132/0133)    via question_target.py     (ADR-0134)
                                                     → Solver (ADR-0116)
                                                     → Verifier (ADR-0117)
                                                     → Realizer (ADR-0118)
```

The binding-graph layer already operates on typed structure rather than
surface words. It infers `question_form` (count / total / rate /
difference / ratio / identity) from the operations touching the unknown.
That's the correct level. It just doesn't get fed enough graphs because
the front-end refuses too often.

The front-end is replaced. The new shape:

```
Text
  → Lexical Primitives        (regex, lexeme-scope only — ADR-0165)
  → Lexicon Lookup            (word → semantic category, ADR-0164)
  → Incremental Reader        (word-by-word state accumulation)
  → MathProblemGraph          (same downstream type as before)
  → [unchanged downstream]
```

The reader is a deterministic shift-reduce parser **over semantic
categories**, not over surface tokens. The category set is closed
(~20 items), the composition rules are bounded (30–50). Adding a verb
adds a lexicon lookup, not a new code path. The vocabulary already
collected in `math_candidate_parser.py` (`_MASS_NOUNS`,
`_PATTERN_A_VERBS`, `_PATTERN_B_VERBS`, `_PATTERN_C_VERBS`, name lists,
add/subtract/transfer verb sets) ports wholesale as the lexicon seed —
the vocabulary work is salvaged; only the regex template wrappers are
removed.

## Why this preserves wrong = 0

The reader can be more permissive about *which sentences it
comprehends* without being more permissive about *what comprehension
produces*. The output type is identical to what the regex parser
produces today, so the existing admissibility gate (unit proofs,
multi-branch disagreement refusal, replay-equivalence) stays in force.
A malformed comprehension produces a graph that admissibility rejects.
wrong = 0 is preserved by construction.

## The corridor generalizes

The teaching → contemplation → review corridor (ADR-0150 / 0152 / 0155 /
0161) already exists for vocabulary. Under ADR-0164 it expands in scope
to also ratify:

- **Lexicon entries** (word → category mappings)
- **Composition rules** (rare — bounded set, ADR-tracked)
- **Lexeme primitives** (new regex tools the engine can wield)

Three orthogonal kinds of evidence, three orthogonal review predicates,
one shared corridor. The engine becomes able to acquire new recognition
capability through reviewed experience instead of through operator
edits to parser code.

The operator's reaction at the moment this clicked into place:

> "That's the absolute fundamental key to intelligence. Truly. That's
> what I had been hoping we could figure out."

## Deprecation discipline

ADR-0163's *diagnosis* (the front-end is the bottleneck) is reaffirmed.
ADR-0163's *prescription* (Phases B–E producing regex-based
`DerivedRecognizer` records in `generate/recognizer_match.py`) is
superseded — what flows through the corridor changes, the corridor
itself does not.

ADR-0136 and its S-family (S.1 / S.2 / S.3 / S.4 / post-rescan
variants): regex sentence-template prescription superseded. Empirical
refusal taxonomies preserved. Closed-set vocabulary tables preserved as
lexicon seed.

All ratified work survives in some form. The regex *wrappers* go;
everything else carries forward.

## Phasing committed in ADR-0164

1. **Phase 1 — Question reader.** Build the reader for question
   sentences only. Coexist with existing regex; reader runs first, regex
   is fallback. Target: `correct ≥ 10` on train_sample/v1, satisfying
   ADR-0163 Round-1 exit. Reader covers ≥20/34 currently-refused
   question cases.
2. **Phase 2 — Statement reader.** Extend to statements. Target:
   `correct ≥ 25`.
3. **Phase 3 — Regex layer removal.** `math_candidate_parser.py` no
   longer contains sentence-level regex patterns. Target: `correct ≥ 35`.
4. **Phase 4 — Scale.** Per ADR-0163 §Phase F: public, holdout, full
   GSM8K.

## What the session did not decide

- Specific category set and composition-rule closure beyond a sketch.
  These will be sub-ADRs once Phase 1 measurement reveals real
  collisions.
- Cross-sentence reading state (pronoun resolution across the problem
  body). Scoped in Phase 1 design.
- The lexicon pack's exact frontmatter and merging policy with
  existing packs (`en_core_cognition_v1`, `en_core_relations_v1`).
- Whether the existing `recognizer_registry` / `recognizer_match`
  modules become the new primitive registry or are replaced with
  fresh modules under `generate/comprehension/`.

## Closing observation

The hard part of the session was not the new architecture — it was
recognizing that ADR-0163's prescription, which had landed only days
earlier and was actively being extended (PRs #305, #306, #307, #308,
#309, #310, #315), was wrong in its mechanism even though right in its
diagnosis. The mechanism was *institutionalizing* the regex template
approach by routing it through the corridor.

The operator had been holding the right intuition the whole time:
"sentences come in all shapes and forms." That intuition is now an
ADR, an invariant boundary, and an architectural transition plan with
acceptance gates.
