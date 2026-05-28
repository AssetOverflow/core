# Comprehension Reader Audit

**Brief:** POST-RAT1-PARALLEL-BRIEFS.md §"Brief C"
**Date:** 2026-05-27
**Operator:** Sonnet (investigation phase)
**Branch:** `docs/comprehension-reader-audit`

---

## Summary finding

The comprehension reader (ADR-0164 Phase 1 + 2) is **not an inert component** — it is
actively exercised by tests and correctly wired into `parse_and_solve`. However it
contributes **zero eval admissions** today because:

1. **Phase 2 (whole-problem reader) refuses on every train-sample problem** due to
   fraction/percentage tokens, unresolved pronouns, or multi-quantity structures that
   are explicitly out-of-scope per Phase 2.1.
2. **Phase 1 (question-sentence hybrid) admits a `CandidateUnknown` but the statement
   side never completes** — the question reader's admission can only produce a result
   when the statement sentences also yield `per_sentence_choices`; for the 47 refused
   cases, statements already fail at the regex level, so the question reader's partial
   success is unreachable.

The reader is a **math substrate, not a cognition track**. It is not used anywhere
in the cognition eval lane. It is the designed long-term replacement for the regex
front-end (ADR-0164 §Decision) but is not yet at the coverage threshold where it
produces observable eval lift.

---

## Q1 — Call trace: where does `_try_comprehension_reader` actually run?

**Single caller.** `generate/math_candidate_graph.py::parse_and_solve` (line 568).
No other production code calls it.

The call tree within `parse_and_solve` has two paths:

```
parse_and_solve(text, config)
│
├── config.comprehension_reader_questions == True   [flag-gated]
│   │
│   ├── ADR-0164 Phase 2 — whole-problem reader
│   │     _try_comprehension_reader(text)          [line 569]
│   │       → begin_sentence / apply_word / end_sentence / finalize
│   │       → CandidateGraphResult on success
│   │       → None on any RefusalError (falls through to regex path)
│   │
│   └── (Phase 2 fell through) continue to regex statement loop
│         → ADR-0164 Phase 1 — question-sentence hybrid
│               _try_reader_for_question(question_sentence, ...)  [line 821]
│                 → build_problem_state_from_candidates
│                 → invoke_reader_for_question
│                 → list[CandidateUnknown] | None
│               → on reader admission: use reader's CandidateUnknown
│               → on refusal: regex question parser (Pattern A/B/C)
│
└── config is None or flag False  →  regex-only path (unchanged)
```

The flag `comprehension_reader_questions` is:
- Declared in `core/config.py:288` (default `False`)
- Set to `True` only in `evals/gsm8k_math/train_sample/v1/runner.py:92`
  when `--use-reader` is passed.
- Not set anywhere in the live `chat/runtime.py` path or any cognition eval runner.

**The reader is never active in production chat turns.** It is activated only by
an explicit CLI flag in the train-sample eval runner.

---

## Q2 — Does the reader admit anything on the cognition lane?

**No.** `comprehension_reader_questions` is not set in any cognition eval runner.
The reader is purely a math-domain component. Cognition evals (`core eval cognition`,
`core test --suite cognition`) do not call `parse_and_solve` and have no concept of
`comprehension_reader_questions`.

There is no reader-on-cognition usage to measure.

---

## Q3 — Is all-or-nothing the bottleneck, or is the reader itself refusing on simple shapes?

**Both, at different phases.**

### Phase 2 (whole-problem reader, `_try_comprehension_reader`)

The all-or-nothing policy is architecturally correct but the reader itself refuses
early on nearly every train-sample problem. Confirmed refusal sites in `lifecycle.py`:

| Token type | Handling | Covers cases |
|---|---|---|
| `fraction_token` / `percentage_token` | Explicit refusal at line 344–356: "out-of-scope (embedded-quantifier aggregate; deferred to Phase 2.1)" | 0004, 0005, 0010, 0041, etc. |
| `unknown_word` | Any word absent from the lexicon (many proper nouns, verbs not yet in lexicon) | Majority of 47 refused |
| `pronoun_resolution` failure | `entity_pronoun` without a resolvable prior entity | 0012, 0015, etc. |
| `multi_quantity_composition` | No composition frame in Phase 2 scope | 0006, 0013, 0025, etc. |

For the current 47 refused cases, the Phase 2 reader fails at or before the first
non-trivial token and returns `None`, deferring to the regex path. The all-or-nothing
rule is not the marginal bottleneck; **lexicon coverage is**. Even with per-sentence
relaxation, a sentence containing an unknown verb would refuse.

### Phase 1 (question-sentence hybrid, `_try_reader_for_question`)

Phase 1 is more targeted — it only reads the question sentence, informed by
`per_sentence_choices` already produced by the regex parser. Its bottleneck is the
**upstream statement failure**: if the regex parser can't build `per_sentence_choices`
for a statement sentence, `_try_reader_for_question` is called with an incomplete or
empty `flat` list, and `build_problem_state_from_candidates` has insufficient context
to produce meaningful question-slot resolution.

The Phase 1 reader does admit case 0027 (Malcolm/followers) per
`test_reader_coexistence.py::test_case_0027_malcolm_admits`. That's the only
confirmed admission on train_sample under flag ON. The 3 currently-correct cases
are unchanged between flag OFF and flag ON (coexistence test).

**Conclusion:** all-or-nothing is not causing the zero-lift result. The reader admits
the cases it can handle; it simply cannot yet handle most train-sample problems
because their lexicon coverage and structural scope (fractions, multi-quantity, complex
pronouns) exceed Phase 1/2 scope.

---

## Q4 — ADR-0164 Phase 1/2 promises vs current state

| Promise | Status |
|---|---|
| Phase 1: question reader with regex fallthrough | ✅ implemented and tested (52 tests across 3 test files) |
| Phase 1: wrong=0 preserved under flag ON | ✅ verified by `test_reader_coexistence.py::TestWrongZeroInvariant` |
| Phase 1: admit case 0027 (Malcolm/followers) | ✅ `test_case_0027_malcolm_admits` |
| Phase 2: whole-problem reader, all-or-nothing | ✅ implemented, `_try_comprehension_reader` |
| Phase 2: fraction/percentage scope declared | ✅ explicit refusal at `lifecycle.py:344`, labeled "deferred to Phase 2.1" |
| Phase 2: eval delta on train_sample | ✗ **zero new admissions** under flag ON |
| Phase 3 (per ADR-0164 §Phasing): remove regex question parser | Not started — reader must reach sufficient question coverage first |
| Lexicon: seed corpus ported from regex parser | ✅ math lexicon loaded at `generate/comprehension/lexicon.py::load_lexicon` |

The only broken promise is Phase 2's intended eval delta. The ADR did not specify a
minimum lift target for Phase 2 at initial ship — it specified "measure pickup rate
against `train_sample/v1` per round." The current pickup rate is 0 new cases on Phase
2 and 0 new cases on Phase 1 (case 0027 is already correct via regex). This is an
accurate measurement, not a latent bug.

**There are no ADR-0164 Phase 1/2 contract violations.** The reader is operating
within its declared scope. The scope is narrow.

---

## Q5 — Three options and measurable tests

### Option A: Operationalize (expand scope incrementally)

**What:** Expand Phase 2 scope to handle one new token class per iteration:
1. Common proper nouns not in the lexicon — add lexicon entries via the ratification
   corridor (ADR-0150/0152/0155/0161). No code change.
2. `multiplicative_aggregation` structures (e.g. "6 baskets × 50 strawberries") —
   add a `distributive_modifier` frame rule to Phase 2. ADR required.
3. Fraction/percentage embedded quantifiers — add Phase 2.1 handling. Separate ADR.

This is the intended path per ADR-0164 §Phasing.

**Measurable test:** After each lexicon expansion, run `uv run python -m
evals.gsm8k_math.train_sample.v1.runner --use-reader` and count new Phase 2
admissions. A single lexicon batch adding the 15 most common unknown verbs should
move the Phase 2 admission count from 0 to ≥ 2.

**Ship as:** Series of small PRs, each adding lexicon entries or a single new frame
rule. Not this brief — this brief is investigation only.

### Option B: Relabel (honest documentation update)

**What:** Add a status section to ADR-0164 acknowledging the current measurement
(Phase 2: 0 new admissions on train_sample) and naming the scope gates that block
lift. Rename the reader's activation flag from the generic
`comprehension_reader_questions` to something that signals its scope:
e.g., `comprehension_reader_phase2_experimental`.

**Measurable test:** No code change → no measurable test required. The honest
claim after relabeling: "the reader is implemented and correct-by-construction;
it produces no eval delta because its lexicon and structural scope don't yet
cover any of the 47 refused cases."

**Ship as:** This PR (docs-only). Low risk, zero regression surface.

### Option C: Retire (remove dead code)

**What:** Remove `_try_comprehension_reader`, `_try_reader_for_question`, and
`lifecycle_runtime_adapter.py`; revert the `comprehension_reader_questions` flag;
remove the 52 tests.

**Why not:** The reader is **not dead code**. It is architecturally load-bearing:
- It is the designed replacement for the regex front-end (ADR-0164 §Decision).
- It has 52 tests, 3 test files, 1,872 lines in `lifecycle.py`, and a working
  Phase 1 admission on case 0027.
- Retiring it would require reverting ADR-0164 and ADR-0165 (regex scope rule),
  since those two ADRs are paired: 0165 forbids cross-word regex, and 0164 provides
  the replacement.

**Measurable test for disconfirmation:** If any of the 52 reader tests currently
fail or test no meaningful property (see CLAUDE.md §Schema-Defined Proof Obligations),
retirement would be justified for those specific tests. Inspection shows the tests
are substantive — Phase 2 tests (`test_reader_phase2.py`) exercise actual statement
frame parsing with real admission paths.

**Verdict: retire is wrong.**

---

## Recommendation

**Ship Option B (relabel) in this PR.** Add a `## Current Status` section to
`docs/decisions/ADR-0164-incremental-comprehension-reader.md` recording:

- Phase 1: implemented, tested, 0 net new admissions (case 0027 already correct
  via regex; wrong=0 verified)
- Phase 2: implemented, tested, 0 new admissions (fraction/multi-quantity scope
  gates block all 47 refused cases; explicit "Phase 2.1" label already in code)
- Next lift path: lexicon expansion via ratification corridor (no code change)
  followed by Phase 2.1 fraction scope (separate ADR)

**Option A (operationalize) follows naturally** as the next ADR wave whenever the
lexicon ratification corridor is the active dispatch target. It does not require a
structural change to the reader — just lexicon entries and optionally a Phase 2.1
fraction rule.

---

## Falsifiability of recommendation

The claim "lexicon expansion is the highest-leverage next step" is falsifiable:

1. Add the 10 most-common unknown verbs from the 47 refused cases to the math lexicon
   (via `apply_lexical_claim` or direct ratification).
2. Run `uv run python -m evals.gsm8k_math.train_sample.v1.runner --use-reader`.
3. If ≥ 1 new case admits: **claim confirmed**; lexicon-first is the path.
4. If 0 new admissions: **claim refuted**; the bottleneck is structural (frame rules),
   not vocabulary — escalate to Phase 2.1 ADR first.

---

## Files read during investigation

- `generate/math_candidate_graph.py` — call sites (lines 445–515, 564–571, 809–833)
- `generate/comprehension/lifecycle.py` — reader implementation (1,872 lines)
- `generate/comprehension/lifecycle_runtime_adapter.py` — Phase 1 bridge (402 lines)
- `generate/comprehension/state.py` — reader state types (828 lines)
- `core/config.py:288` — flag declaration
- `evals/gsm8k_math/train_sample/v1/runner.py` — sole production flag consumer
- `docs/decisions/ADR-0164-incremental-comprehension-reader.md` — doctrine
- `tests/test_reader_phase2.py` (19 tests), `test_reader_question_frame.py` (20 tests),
  `test_reader_coexistence.py` (13 tests)
