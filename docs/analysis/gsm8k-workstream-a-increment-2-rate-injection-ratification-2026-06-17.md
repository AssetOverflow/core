# GSM8K Workstream A Increment 2 — rate_with_currency → apply_rate typed injection ratification

**Date:** 2026-06-17  
**Workstream:** A (first increment of reader/recognizer lift per strategic deep-dive ratif 2026-06-16)  
**Increment:** 2 — frontier measurement + stale doctrine repair + narrow rate injection  
**Status:** Ratified for implementation (before any code changes on this branch)  
**Scope lock:** This ratification governs only the three items in the attached Grok Build Brief. No broadening.

## 1. What failure class is being attacked?

From the post-Inc1 train-sample proxy report (committed on main post-#796):

- 6 correct / 44 refused / 0 wrong (passed=false; exit requires correct_min=10)
- Dominant refusal reason (visible in per_case):  
  `"candidate_graph: recognizer matched but produced no injection for statement: 'Tina makes $18.00 an hour.' (category=rate_with_currency)"`

(and similar for other rate_with_currency surfaces: Alexa lemonade $2 for one cup, Erica $20 per kg, etc.)

The recognizer (ratified exemplars + _match_rate_with_currency) fires and produces `parsed_anchors` with `kind="currency_per_unit_rate"`, `currency_symbol`, `amount`, `per_unit`. The candidate-graph now explicitly refuses on "recognizer matched but produced no injection" (the post-#359 / ADR-0167 correction that retired the old silent-drop/skip-only hazard).

The bottleneck has moved from "recognizer never saw the shape" (Inc1 target) to "recognizer saw it, injector emitted nothing, explicit refuse".

This is the next measurable frontier for typed comprehension → solver state.

## 2. Why rate_with_currency is the next seam (Mechanical Sympathy + Third Door)

- **Recognizer side already exists and is narrow** (`generate/recognizer_match.py:_match_rate_with_currency`, `_CURRENCY_AMOUNT_RE`). It already honors the ratified spec's `observed_currency_symbols` / `observed_per_units`. It already extracts amount token (int/decimal; fractions noted as 'word').
- **Typed solver primitives already exist and are exercised**:
  - `generate/math_problem_graph.py:Rate(value, numerator_unit, denominator_unit)` — post_init refuses <=0 and bad units. Example: `Rate(2.0, "dollars", "apple")`.
  - `Operation(actor=..., kind="apply_rate", operand=Rate(...))`.
  - `generate/math_solver.py:_apply_rate` — multiplies actor's existing denom-unit Quantity by the rate; produces numerator-unit result in state. Explicitly refuses (SolveError) if the actor does not already hold a denom-unit quantity. No guessing.
  - `CandidateOperation` + `roundtrip_admissible` + `KIND_TO_VERBS["apply_rate"]` already gate the matched_verb token.
- **Candidate-graph already has the refusal machinery** (0 admissible → refuse; 1 → emit; N differing → refuse; completeness guard that still requires source quantities to be consumed by the chosen graph).
- **Injector dispatch table already has the exact seam** (`generate/recognizer_anchor_inject.py:_INJECTORS`, the explicit "RATE_WITH_CURRENCY — deferred" comment, `InjectorEmission` widening from ADR-0170 already landed, `inject_from_match` already calls per-category and falls back to composition or ()).
- **No new solver, no new graph kinds, no new admission rules.** We are closing one narrow typed bridge on the existing path: anchor → grounded Rate → CandidateOperation(apply_rate) → existing Cartesian + solver + verifier.

This is Third Door: the deterministic, replayable, proof-carrying extension of the listen/comprehend path using the seams the architecture already provided. Not an LLM fallback, not a regex-to-answer shortcut, not broad new infra.

## 3. Why this uses existing typed graph/solver machinery (Semantic Rigor)

- All content slots in the emitted `CandidateOperation` / `Operation` / `Rate` will be source-grounded:
  - `matched_value_token` = literal amount substring from the statement.
  - `matched_unit_token` = canonical currency unit (or symbol-grounded form that roundtrip accepts).
  - `matched_actor_token` = ProperName surface extracted from the same sentence (or existing safe discourse prior).
  - `matched_verb` = literal "per"/"an"/"each"/... token from the surface (will require RATE_ANCHORS update for "a"/"an" with tests).
  - `source_span` = the full statement sentence.
- No arithmetic is performed in the injector or matcher for the rate value itself (amount is parsed from surface token only; the multiply happens inside the already-ratified `_apply_rate`).
- Actor binding is deliberately narrow (see hazards below). No pronoun guessing, no "nearest prior entity" unless an already-ratified, tested discourse path (ME-2 style prior_subject or lookback) proves it for this category.
- The Rate constructor itself is the invariant enforcer (value > 0). Injector returns `()` on any failure to construct a fully-grounded, admissible primitive.

## 4. What wrong=0 hazards exist and how they are mitigated

- **Ungrounded / wrong actor**: rate sentence "Tina makes $18 an hour" applied to Sam who has the hours.  
  **Mitigation**: narrow same-sentence ProperName extraction (or existing safe prior_subject path only). Different-actor confuser test required. Return `()` if actor not unambiguously extractable in v1 scope.
- **Multiple rates in one sentence**: ambiguity → could pick wrong rate.  
  **Mitigation**: explicit refuse in injector if >1 clean rate anchor (or let downstream multi-admissible rule refuse). Confuser test: "Tina makes $18 an hour and $20 per job".
- **Missing denominator state**: "Tina makes $18 an hour. How many dollars...?" (no hours quantity ever stated for Tina).  
  **Mitigation**: `_apply_rate` already refuses (SolveError → no admissible branch). Completeness guard still applies. Confuser test required.
- **Bad amount (zero, negative, NaN, slash fraction in v1)**: Rate post_init + explicit checks in injector refuse.
- **Unobserved currency or per_unit**: matcher already refuses before we ever see the anchor (spec narrowness).
- **matched_verb not in KIND_TO_VERBS["apply_rate"]**: "an hour" surfaces would cause post-init ValueError on CandidateOperation.  
  **Mitigation**: either (A) only admit literal "per|each|every" surfaces in v1, or (B) add "a","an" to RATE_ANCHORS with tight grounding tests proving the literal token from sentence passes roundtrip. Brief prefers B with tests because "$X an hour" is a major real proxy surface; we will do B only if the tests are added.
- **Incomplete graph hazard (the scar)**: prior serving bridges lifted train-sample correct but introduced wrong on sealed held-out.  
  **Mitigation**: this lands only in the injector path (serving _INJECTORS, not sealed). All new paths go through the same `roundtrip_admissible` + candidate-graph multi-branch disagreement + completeness + existing solver refusal. New unit + integration tests + frontier + full lane runs before any promotion discussion. No sealed SHA movement in this PR.
- **Cross-sentence actor without proof**: deferred. Only same-sentence or already-ratified discourse machinery.

If any of the above cannot be made to refuse loudly on the confusers, the injector returns `()` and the candidate-graph refuses with the "no injection" message.

## 5. What is explicitly out of scope for this increment (and this ratification)

- No comparisons (additive/multiplicative), no temporal_aggregation, no currency_amount alone, no descriptive_setup consumption beyond current.
- No partition/chunking, no affine equations, no "X more/less than" solver extensions.
- No broad actor resolution (pronouns, "the person", nearest prior unless proven safe path already exists and is tested for rates).
- No machine-admissible ambiguous exemplars added to teaching/admissibility_exemplars/.
- No direct-answer fast paths, no LLM, no postprocessor guesses.
- No changes to sealed injector lane for serving paths.
- No movement of sealed SHAs / active_corpus_byte_identical / lane SHAs (except natural addition of new focused tests under the existing verify script).
- No claim that the proxy "passes" (correct_min=10 remains the bar; we expect the runner may still exit non-zero and passed=false).
- No rebaseline of report.json unless the runner.py in this branch actually writes an updated one and we commit it — the lookback will record exactly whether it happened.
- No CLOSE / FrameVerdict / idle consolidation interaction.
- No grammar changes to question parsing unless they fall out of the minimal synthetic test; if the "how many dollars does Tina make?" question form is not yet supported by the question side, we record the gap in frontier + lookback and use a narrower unit/integration test at the injector + graph + solver level.

Follow-up waves will be separately ratified.

## 6. What tests / evals / commands will prove non-corruption

**Required exact commands (must be green or explicitly documented as expected non-passing proxy status):**

```
uv run python -m pytest tests/test_recognizer_anchor_inject.py -q
uv run python -m pytest tests/test_math_candidate_graph_rate_injection.py -q
uv run python -m pytest tests/test_adr_0179_extract.py -q
uv run python -m pytest tests/test_architectural_invariants.py -q -k "not worktree and not claude"
uv run python scripts/verify_lane_shas.py
uv run python evals/gsm8k_math/train_sample/v1/runner.py
```

**New artifacts (committed in branch):**
- `scripts/gsm8k_frontier_report.py` (deterministic bucketizer; must surface rate_with_currency as a top recognized_no_injection category on the input report).
- `tests/test_gsm8k_frontier_report.py`
- `tests/test_recognizer_anchor_inject.py` (≥8 focused cases: happy $2 per cup → CandidateOperation(Rate(2,"dollars","cup")); "an hour" handling per Option B or A; unknown actor refuse; multi-rate refuse; slash-fraction refuse; zero refuse; unobserved currency/per_unit refuse; value/unit tokens ground in source).
- `tests/test_math_candidate_graph_rate_injection.py` (synthetic "Tina works 3 hours. Tina makes $18.00 an hour. How many dollars does Tina make?" → 54, selected_graph not None, op kind=apply_rate; plus the 4 confusers listed in brief that must refuse or not mis-apply).
- Updates to `docs/recognizer-registry.md` and stale comments in `generate/math_candidate_graph.py` so that `grep -R "dropped from per_sentence_choices|contributes ZERO math state|skip-only"` (on the relevant files) finds only historical/rejected descriptions.
- Possibly light updates to `math_roundtrip.py` (RATE_ANCHORS + comment) if Option B chosen.
- Ratification (this doc) + post-impl lookback (`gsm8k-workstream-a-increment-2-lookback-2026-06-17.md`).
- The frontier report run on the (post-run) train_sample report.

**Non-corruption invariants the tests must exercise:**
- All new emission paths still pass the existing `_initial_admissible` / `roundtrip_admissible` + CandidateOperation post-init (verb in KIND_TO_VERBS).
- Rate construction only succeeds for positive grounded values.
- Solver still refuses (no wrong) when denom state absent.
- Candidate-graph still refuses on 0 or N-differing.
- No change to pre-existing discrete / multiplicative paths (byte-identical on their tests).
- Lane shas remain  the prior 8/9 pattern or better (public_demo unrelated); no unintended movement of sealed lanes.
- Invariants suite (worktree/claude excluded) stays green.
- Extract tests (ADR-0179) untouched and green (this increment does not touch the derivation/extract lexeme layer).

**Report expectations (truthful recording only):**
- Before: 6/44/0, passed=false.
- After runner (if it writes report.json in this branch): record exact new counts, which specific case_ids changed reason/verdict, whether wrong stayed 0, whether passed became true (unlikely in inc2).
- If the runner still exits non-zero because correct_min unmet, state that exactly. Do not claim "lane passes."

## Engineering pillars re-affirmed

- **Mechanical Sympathy**: smallest possible delta on the exact seam (one new injector function + registration + narrow actor extraction + RATE_ANCHORS tweak + docs + measurement tool). Uses the typed graph/solver that was already there for rates.
- **Semantic Rigor**: every token in the CandidateOperation is a literal substring or canonical form proven by roundtrip. "recognized + no injection" now has one meaning (refuse) and the docs will say what the code does. Report numbers will match committed artifacts.
- **Third Door**: we are extending the deterministic typed bridge (recognizer anchor → Rate/apply_rate Operation → existing solver path protected by existing refusal gates), not choosing between LLM or ad-hoc shortcut.

## Lookback obligation (enforced by this ratification)

After implementation a separate lookback doc will be written that records:
- exact `git diff --name-only origin/main...HEAD`
- exact outputs of the 6 required commands
- exact before/after report counts and per-case deltas (or "runner did not update report.json in this branch")
- any gaps (e.g. question parser for "how many dollars")
- confirmation that no sealed SHA moved, wrong stayed 0, and all new paths are refusal-preferring on the listed confusers.

If any test or invariant fails the criteria above, the implementation does not satisfy this ratification.

## Ratification sign-off

This document is the governing spec for the PR titled:
`feat(derivation): Workstream A inc 2 — frontier report + rate_with_currency apply_rate injection`

Implementation may proceed on the branch `feat/gsm8k-workstream-a-inc2-rate-injection` (forked from main post-#796 at 80240ea9).

All subsequent code, tests, docs, and the lookback must be auditable against the six questions and the non-goals listed here. 

---

**References (must be read before coding):**
- The attached Grok Build Brief (exact scope, commands, test cases, reporting format at end).
- Post-#796 train_sample report + Inc1 lookback/ratif.
- `generate/recognizer_anchor_inject.py` (current dispatch + patterns).
- `generate/recognizer_match.py` (rate matcher).
- `generate/math_problem_graph.py:Rate`, `generate/math_solver.py:_apply_rate`.
- `generate/math_candidate_graph.py` (current recognized + injector call site + refusal branch).
- `generate/math_roundtrip.py` (RATE_ANCHORS, KIND_TO_VERBS, CandidateOperation).
- Existing injector tests (`tests/test_adr_0163_d2_discrete_count_injection.py` etc.).
- `docs/recognizer-registry.md` (stale text to repair).
- CORE Claude.md / rules: ratify-first, lookback on 3+PR surface or phase, small load-bearing PRs, wrong=0 > correct count, no hidden normalization, explicit trust boundaries on user text / dynamic execution. 

End of ratification. Proceed to implementation only after this doc is committed on the branch.