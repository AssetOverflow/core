# GSM8K Workstream A Gate A1 — multiplicative comparative injection ratification

**Date:** 2026-06-17
**Workstream:** A (GSM8K typed-operation ladder)
**Gate:** A1 — first comparative injection slice
**Status:** Ratified for implementation (BEFORE any code changes)
**Scope lock:** Multiplicative entity comparison with explicit same-sentence reference only. One narrow recognizer-injector bridge mirroring Inc2 rate discipline.

**Prerequisites (met on main @ 17f474a8):**
- PR #801: Inc3 evidence closure (rate `recognized_no_injection` = 0 on live runner; pinned `report.json` historical).
- PR #802: practice-lane monotonic contract (`wrong=0` hard; `correct>=6`, `refused<=44`).

**Implementation branch (future):** `feat/gsm8k-workstream-a-gate-a1-comparative-multiplicative-injection`

---

## 1. What exact Gate A1 slice is selected?

**compare_multiplicative entity comparison with explicit same-sentence reference.**

The deliverable is a **recognizer-anchor injector** for the **proposed future serving** category `ShapeCategory.COMPARATIVE_WITH_UNIT` (taxonomy label today; not yet a ratified `_MATCHERS` / `_INJECTORS` entry) that emits grounded `CandidateOperation(kind="compare_multiplicative", operand=Comparison(...))` when a ratified matcher fires and all slots are source-grounded. The existing candidate-graph parser path (ADR-0131.G.2) remains unchanged; this slice closes the **recognizer matched but produced no injection** frontier for comparative surfaces that the parser does not already admit.

**Confirmed code fact:** `compare_multiplicative` is a closed `Operation` kind with solver (`_apply_compare_multiplicative`), verifier, roundtrip anchors, and G.2 parser builders already landed. **Confirmed code fact:** `_INJECTORS` today registers only `DISCRETE_COUNT_STATEMENT`, `MULTIPLICATIVE_AGGREGATION`, and `RATE_WITH_CURRENCY`. `COMPARATIVE_WITH_UNIT` is a **taxonomy-only** shape label (`evals/refusal_taxonomy/shape_categories.py`); it is **not** a live serving recognizer category — no matcher or injector on the serving path (`recognizer_match.py:_MATCHERS`, `recognizer_anchor_inject.py:_INJECTORS`). Gate A1 **proposes** promoting it to a ratified serving category.

This is **first subfamily only** — not full Gate A1 comparative family (additive deferred).

---

## 2. Why multiplicative comparative before additive comparative?

| Reason | Evidence |
|--------|----------|
| **Substrate already complete** | `Comparison(factor, direction∈{times,fraction}, reference_actor)` + `_apply_compare_multiplicative` + `_build_compare_multiplicative` + G.2 axis lane (`evals/math_capability_axes/G2_comparatives/v1/`) |
| **Lower ambiguity** | Additive surfaces overlap numeric arithmetic (`2 more than 5 miles` — train-sample 0016); G.2 explicitly excludes numeric-reference additive. Multiplicative closed template requires `as many <unit> as <Reference>`. |
| **Clearer closed templates** | `twice/thrice/<N> times as many <unit> as <REF>` are pinned in G.2 and completeness-guard positives |
| **Active misroute today** | DCS injector refuses `<N> times` mis-injection (`recognizer_anchor_inject.py:314–323`) but comparative-bearing stmts still hit `discrete_count_statement` no-injection (e.g. pinned cases 0015, 0036, 0023) |
| **Confuser infrastructure** | H2 referent confusers (0022–0024) and §9 no-reference guard already target multiplicative family |
| **Inc2/Inc3 precedent** | One typed primitive per increment; additive is second wave after multiplicative confusers green |

**HYPOTHESIS:** Additive `compare_additive` recognizer injection may reuse the same seam in Gate A2; not in Gate A1 scope.

---

## 3. Exact accepted surface family (v1)

### In scope (closed set — must match G.2 parser discipline)

| Template | Factor source | `direction` |
|----------|---------------|-------------|
| `<Actor> <verb> twice as many <unit> as <Reference>` | anchor `twice` → 2.0 | `times` |
| `<Actor> <verb> thrice as many <unit> as <Reference>` | anchor `thrice` → 3.0 | `times` |
| `<Actor> <verb> <N> times as many <unit> as <Reference>` | digit/word N via `_resolve_value` | `times` |
| `<Actor> <verb> half as many <unit> as <Reference>` | anchor `half` → 0.5 | `fraction` |
| `<Actor> <verb> a quarter as many <unit> as <Reference>` | anchor `quarter` → 0.25 | `fraction` |
| `<Actor> <verb> a third as many <unit> as <Reference>` | anchor `third` → 1/3 | `fraction` |

**Polarity-inverting verbs excluded** (G.2a): `lose`, `give`, `spend`, etc. — injector returns `()`.

**Statement-only:** question surfaces are not injection targets in v1 (injection applies to classified **statements** in the candidate-graph loop).

### Explicitly deferred in v1

| Surface | Deferral reason |
|---------|-----------------|
| `double` / `triple` / `quadruple as many` | In `COMPARE_MULTIPLICATIVE_ANCHORS` but **not** in `_ANCHOR_TO_FACTOR` or parser regexes; G2 refuses `double as many` |
| `one-third` (hyphenated) | G2 `G2-refuse-006` — refuse |
| `twice as much time` / `as much` (non-count unit) | Template mismatch (`as many` required); case 0015 |
| `N times greater than` / `N times more than` | Ambiguous additive vs multiplicative; G2 `G2-refuse-005` |
| Unit ellipsis (`twice as many as Tom` — no unit token) | G.2 deferred; no e2e admission |
| Nested (`N more than M times REF`) | Parser emits two flat candidates; composition not Gate A1 |
| Cross-sentence / pronoun reference | ADR-0138 draft only; no proven safe binding |

**Half/fraction verdict:** `half`, `quarter`, `third` (with optional article `a`) are **in scope for ratification** — parser `_ANCHOR_TO_FACTOR` and G.2 tests already admit them; **serving-path injection** for these surfaces must be proven in PR-3 tests. `double` and hyphenated `one-third` remain **explicitly deferred**.

---

## 4. Matcher category and parsed anchors

### Proposed future serving recognizer category

**Confirmed:** `ShapeCategory.COMPARATIVE_WITH_UNIT` exists as a **taxonomy / measurement** label only. It is **not** a current serving recognizer category — absent from `_MATCHERS` and `_INJECTORS`.

**Ratified approach (implementation PR):** add `_match_comparative_with_unit` + register in `_MATCHERS`; add `inject_comparative_multiplicative` + register in `_INJECTORS`; add ratified recognizer spec + exemplars in `teaching/admissibility_exemplars/` and `docs/recognizer-registry.md` (separate proposal artifact per ADR-0161, not in implementation unless already ratified). PR-3 must prove serving injection for `half` / `quarter` / `third` with tests even though parser factor substrate already supports them.

**HYPOTHESIS:** Some comparative stmts may continue to match `discrete_count_statement` first; Gate A1 evidence should measure **reclassification** when the comparative matcher fires. Widening DCS to emit comparative ops is **out of scope** (metric-inert per question-layer survey).

### Required `parsed_anchors` fields (per match)

| Anchor key | Semantics | Grounding rule |
|------------|-----------|----------------|
| `actor_token` | Subject entity surface | Same-sentence ProperName or ratified narrow subject extract (mirror rate actor binding) |
| `reference_actor_token` | Entity after `as` | Must match `_COMPARE_REF` shapes used by G.2 (`the X`, ProperName, `the number/amount of <noun>`) |
| `unit_token` | Counted unit phrase | Literal multi-word unit substring; `_canonicalize_unit` |
| `factor_token` | Comparator anchor or numeric | `twice`/`thrice`/`half`/`<N>`/`quarter`/`third` — literal from sentence |
| `comparator_phrase` | Full comparative anchor span | e.g. `three times as many` — for audit |
| `matched_verb` | Anchor verb for roundtrip | Must ∈ `COMPARE_MULTIPLICATIVE_ANCHORS` |
| `source_span` | Full statement sentence | Byte-identical to input statement |

Every slot used in `CandidateOperation` must map to a literal substring (`matched_*_token` fields).

---

## 5. Required typed primitive

**Confirmed code fact** — emit existing type unchanged:

```text
CandidateOperation(
  actor=<grounded actor>,
  op=Operation(
    actor=<same>,
    kind="compare_multiplicative",
    operand=Comparison(
      reference_actor=<grounded ref>,
      delta=None,
      factor=<positive float>,
      direction="times" | "fraction",
    ),
  ),
  matched_actor_token=...,
  matched_unit_token=...,
  matched_value_token=...,  # factor surface
  matched_verb=...,         # ∈ COMPARE_MULTIPLICATIVE_ANCHORS
  source_span=<sentence>,
)
```

Construction should **reuse** `_build_compare_multiplicative` logic from `math_candidate_parser.py` or duplicate its invariants exactly — no new `Operation` kind.

**Stop rule:** If implementation discovers no safe emission path to this type without a new kind or solver change, **stop and re-ratify** before coding.

---

## 6. Actor / reference grounding rules

1. **Actor** = explicit same-sentence subject (ProperName head or ratified narrow extract identical to rate injector v1). No pronoun (`he`/`she`/`they`). No nearest-entity guess.
2. **Reference** = explicit token(s) after `as` in the comparative template. Must satisfy G.2 `_COMPARE_REF` shapes. Numeric-only reference (`2 more than 5`) → refuse (not entity comparison).
3. **Self-reference** (`actor == reference_actor`) → refuse (`Comparison` validation).
4. **No cross-sentence binding** unless a future ADR-0138 delta ratification proves replayable `QuantityReference` safety — **deferred**.
5. **Multiple comparative anchors in one sentence** → injector returns `()`.
6. **Missing reference tail** (`N times` without `as many … as <REF>`) → injector returns `()`; must not emit `CandidateInitial(value=N, unit="times")`.
7. **Question surfaces** — not injected in v1.

---

## 7. wrong=0 guard (five-layer net + comparative-specific)

Inherited from Inc2/Inc3:

1. Matcher narrowness (closed template + ratified exemplars).
2. Source grounding — every `matched_*` token literal in sentence.
3. Injector returns `()` on any construction / roundtrip failure.
4. `roundtrip_admissible` + `CandidateOperation` post-init + `KIND_TO_VERBS["compare_multiplicative"]`.
5. Candidate-graph multi-branch disagreement + completeness guard + solver refusal.

**Comparative-specific:**

| Hazard | Guard |
|--------|-------|
| No-ref `<N> times` | Injector `()` + §9 completeness guard (`test_candidate_graph_completeness_guard.py`) |
| Wrong referent (H2) | Downstream graph/solver refuses if question targets wrong actor; confusers 0022–0024 |
| Missing reference state | `_apply_compare_multiplicative` → `SolveError` if ref quantity absent |
| Unit mismatch / multi-unit ref | Solver refuses ambiguous reference units |
| Unsupported factor (`double`, `one-third`) | Injector `()` |
| Numeric inequality masquerading as compare | Template requires entity `_COMPARE_REF`; refuse `2 more than 5` shapes |
| Direct answer / LLM | Forbidden (Inc2 precedent) |

**If any confuser admits a wrong graph, revert before merge.**

---

## 8. Confuser matrix (must refuse unless noted)

| ID | Surface class | Example | Expected v1 |
|----|---------------|---------|-------------|
| C1 | Incomplete `N times` — no `as REF` | `Jerry has 3 times as many apples.` | **refuse** |
| C2 | Incomplete — `times more` | `Jerry has 3 times more apples.` | **refuse** |
| C3 | Incomplete — `the number of` without ref | `Jerry has 3 times the number of apples.` | **refuse** |
| C4 | Anchor only — `twice` no ref | `Jerry has twice as many apples.` | **refuse** |
| C5 | DCS trap | `Jerry has 3 times` → must not be `Initial(3,"times")` | **refuse** |
| C6 | Wrong referent (H2) | Comparative on Tom, question asks Alice | **refuse** |
| C7 | Pronoun reference | `He has twice as many as Bob` | **refuse** |
| C8 | Numeric inequality | `traveled 2 more than 5 miles` | **refuse** |
| C9 | Additive `more than` | `Alice has 3 more apples than Bob` | **refuse** (additive out of scope; parser may solve separately — injector must not emit multiplicative) |
| C10 | Ambiguous `N times more than` | `3 times more apples than Bob` | **refuse** |
| C11 | Unit mismatch | Comparative apples vs oranges in one clause | **refuse** |
| C12 | Multiple comparatives | Two factor anchors one sentence | **refuse** |
| C13 | Question surface | Comparative in question stmt | **refuse** (v1) |
| C14 | No grounded unit | `twice as many as Tom` (no unit) | **refuse** |
| C15 | Nested comparative | `10 more than four times the number of chickens` | **refuse** (composition deferred) |
| C16 | Unsupported fraction | `one-third as many as Bob` | **refuse** |
| C17 | Unsupported `double as many` | `double as many apples as Bob` | **refuse** |
| C18 | Polarity inverting verb | `Alice lost twice as many as Bob` | **refuse** |

### Positive controls (must still solve)

| Surface | Expected | Existing pin |
|---------|----------|--------------|
| `Tom 7, Jerry 3× Tom, together 28` | solve 28 | `test_n_times_as_many_with_reference_still_solves` |
| Sidney/Brooke 438 case | solve 438 | `test_sidney_brooke_still_solves` |
| G.2 axis multiplicative admits | wrong=0 | `test_adr_0131_G2_comparatives.py` |

---

## 9. Expected metric movement

**Live ephemeral runner (confirmed 2026-06-17, main @ 17f474a8):** 6 correct / 44 refused / 0 wrong; `recognized_no_injection` total 31; `rate_with_currency` no-injection = 0.

**Expected after Gate A1 implementation:**

| Metric | Expected |
|--------|----------|
| `wrong` | **0** (hard) |
| `correct` | **≥ 6** (monotonic per #802); **not guaranteed lift** |
| `refused` | **≤ 44** (monotonic) |
| `recognized_no_injection` | Likely **reclassification** — some DCS/descriptive misroutes move to `no_admissible_statement` or downstream graph refusal when comparative matcher injects |
| `comparative_with_unit` no-injection bucket | Target **0** on live runner (mirror Inc3 rate closure) |
| Pinned `report.json` | **Unchanged** unless separately ratified rebaseline PR |

**Do not claim** aggregate correct-count lift in PR body without per-case ephemeral evidence. Reclassification of refusal family is the primary deliverable (Inc3 lesson).

**Cases that must not be double-counted as injector lift:** 0024 (parser compare + product bridge), 0029 (R1/QuantityReference) — already correct via non–Gate-A1 paths.

---

## 10. Explicit non-goals

- No **additive** / **subtractive** comparative injection (`compare_additive`).
- No broad comparative family, partition/chunking, affine equation frame.
- No `graph_planner.py` changes.
- No `report.json` rebaseline in implementation PR.
- No sealed-lane movement (`_SEALED_INJECTORS` stays empty for serving).
- No corpus / pack / policy / identity mutation.
- No `determine()` / `FrameVerdict` / CLOSE / idle consolidation interaction (**INV-30 / INV-31** unchanged).
- No `answer=False` anywhere in scanned production code.
- No LLM / direct-answer fast paths.
- No solver semantic changes to `_apply_compare_multiplicative` beyond existing behavior.
- No cross-sentence pronoun/reference binding (ADR-0138).
- No nested comparative composition.
- No runtime implementation in **this ratification PR** (docs only).

---

## Implementation touch list (for PR-3)

| File | Change |
|------|--------|
| `generate/recognizer_match.py` | `_match_comparative_with_unit`, `_MATCHERS` registration |
| `generate/recognizer_anchor_inject.py` | `inject_comparative_multiplicative`, `_INJECTORS` registration; keep DCS `times` guard until injector proven |
| `docs/recognizer-registry.md` | Comparative spec (if exemplars ratified) |
| `teaching/admissibility_exemplars/` | `comparative_with_unit` exemplars (if not already present) |
| `tests/test_recognizer_comparative_inject.py` | **new** — 15 unit tests |
| `tests/test_math_candidate_graph_comparative_injection.py` | **new** — 8 graph tests |
| `tests/test_gsm8k_frontier_report.py` | pinned-historical vs live comparative bucket |
| `tests/test_candidate_graph_completeness_guard.py` | §9 regression (+3) |
| `tests/test_candidate_graph_recognizer_wiring.py` | synthetic registry + wrong=0 |
| `tests/test_adr_0131_G2_comparatives.py` | parser path unchanged + GSM8K probe |

**Read-only (no changes expected):** `math_problem_graph.py`, `math_solver.py`, `math_verifier.py`, `math_roundtrip.py` (unless new surface tokens require anchor set doc sync only).

---

## Validation obligations (PR-3, not this PR)

```bash
.venv/bin/python -m pytest tests/test_recognizer_comparative_inject.py -q
.venv/bin/python -m pytest tests/test_math_candidate_graph_comparative_injection.py -q
.venv/bin/python -m pytest tests/test_gsm8k_frontier_report.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_recognizer_wiring.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_completeness_guard.py -q
.venv/bin/python -m pytest tests/test_adr_0131_G2_comparatives.py tests/test_adr_0131_G2a_comparative_verb_widening.py -q
.venv/bin/python -m pytest tests/test_architectural_invariants.py -q -k "INV_30 or INV_31 or inv_30 or inv_31"
.venv/bin/python scripts/verify_lane_shas.py
# Ephemeral only — do not commit unless ratified:
# build_report(cases) → wrong==0; frontier analyze_report
```

---

## Open risks (honest)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Over-recognition on no-ref `N times` | **Critical** | §9 guard + injector `()` + 15 unit confusers |
| H2 wrong referent solve | **High** | Confusers 0022–0024; question-target alignment deferred — refuse until proven |
| DCS still wins match race | **Medium** | Measure per-case; may need matcher priority doc amendment |
| `comparative_with_unit` exemplars not ratified | **Medium** | Phase C proposal before serving promotion |
| Parser + injector double admission | **Medium** | Parser path runs first; injector only on empty choices |
| No guaranteed correct lift | **Low** (expected) | PR body must not claim lift without evidence |
| `double`/`as much` pressure to widen | **Low** | Explicit deferral; re-ratify Gate A1b |

---

## Arena reconciliation summary

| Agent | Key finding |
|-------|-------------|
| **Comparative substrate mapper** | `compare_multiplicative` full stack exists; Gate A1 gap = recognizer matcher/injector only; half/quarter/third supported |
| **Frontier evidence auditor** | Comparative surfaces dominate DCS/descriptive `recognized_no_injection` on pinned proxy; live total 31; rate bucket closed |
| **Over-recognition adversary** | 18 confuser classes; §9 + G2 + confusers v1 cover most; gaps: pronoun ref, unit ellipsis, DCS injector unit test |
| **Truth-boundary auditor** | INV-30/31 + Inc2/Inc3 forbid determine/FrameVerdict/CLOSE; composition §9 hazard blocks no-ref emission |
| **Test-plan auditor** | 15+8+4+3+3+3 tests across new files; Inc2 ladder mirror; completeness guard is merge blocker |

This ratification closes the docs-first gate. Implementation may proceed only after this document merges to `main`.