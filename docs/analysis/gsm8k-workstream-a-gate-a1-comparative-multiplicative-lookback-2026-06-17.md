# GSM8K Workstream A Gate A1 — multiplicative comparative injection lookback

**Date:** 2026-06-17 (post-implementation evidence closure)
**Branch:** `feat/gsm8k-workstream-a-gate-a1-comparative-multiplicative-injection`
**Head (implementation + patch):** `11abb9d572e26cb8feb57063827eda39f9279bd7`
**Base implementation commit:** `e578ec72`
**Governing ratification:** `docs/analysis/gsm8k-workstream-a-gate-a1-comparative-multiplicative-ratification-2026-06-17.md` (merged #803)
**Scope:** **First subfamily only** — multiplicative entity comparison with explicit same-sentence reference. Additive comparative (Gate A2) deferred.

## What shipped

Gate A1 closes the `COMPARATIVE_WITH_UNIT` recognizer-anchor injector frontier for the closed v1 template family:

- `twice/thrice/<N> times/half/a quarter/a third as many <unit> as <Reference>`
- Emits existing `CandidateOperation(kind="compare_multiplicative", operand=Comparison(...))`
- DCS yield guard routes comparative surfaces away from detection-only discrete-count fallback
- N-times factor narrowness: plain digit or single-word cardinal only (no money, slash-fraction, hyphenated, indefinite)

### Exact semantic path

1. **Matcher** (`generate/recognizer_match.py`): `_match_comparative_with_unit` + `_parse_comparative_v1_count_factor` on the N-times branch.
2. **Injector** (`generate/recognizer_anchor_inject.py`): `inject_comparative_multiplicative` reuses `_build_compare_multiplicative` + `roundtrip_admissible`.
3. **Registry** (`teaching/admissibility_exemplars/comparative_with_unit_v1.jsonl` + accepted proposal `bec14058…`).
4. **DCS yield** (`_match_discrete_count_statement`): returns `None` when `_is_comparative_multiplicative_v1_surface` holds.

No solver semantic changes. No `report.json` rebaseline. No sealed-lane movement.

## Changed files (implementation + patch)

| File | Role |
|------|------|
| `generate/recognizer_match.py` | Matcher + v1 count-factor narrowness + DCS yield |
| `generate/recognizer_anchor_inject.py` | Injector + `_INJECTORS` registration |
| `teaching/recognizer_synthesis.py` | `_synthesize_comparative_with_unit` |
| `teaching/exemplar_ingest.py` | Validator + supported category |
| `teaching/admissibility_exemplars/comparative_with_unit_v1.jsonl` | 12 exemplars |
| `teaching/proposals/proposals.jsonl` | Created + accepted recognizer proposal |
| `teaching/cognition_chains/cognition_chains_v1.jsonl` | Corpus append from accept |
| `tests/test_recognizer_comparative_inject.py` | Unit + confuser + graph tests |
| `tests/test_gsm8k_frontier_report.py` | Live `comparative_with_unit` no-injection = 0 |

## Tests run (patch)

```bash
git diff --check origin/main...HEAD
.venv/bin/python -m pytest tests/test_recognizer_comparative_inject.py -q
.venv/bin/python -m pytest tests/test_gsm8k_frontier_report.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_recognizer_wiring.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_completeness_guard.py -q
.venv/bin/python -m pytest tests/test_adr_0131_G2_comparatives.py -q
.venv/bin/python -m pytest tests/test_recognizer_anchor_inject.py -q
.venv/bin/python -m pytest tests/test_math_candidate_graph_rate_injection.py -q
.venv/bin/python -m core test --suite smoke -q
```

## Measurement truth (pinned vs live)

### Pinned committed artifact (unchanged)

`evals/gsm8k_math/train_sample/v1/report.json` remains the **Inc1-era / pre-Gate-A1** artifact:

- **6 correct / 44 refused / 0 wrong**
- No `comparative_with_unit` category in pinned no-injection bucket (category did not exist on serving path; comparative-bearing stmts appeared under `discrete_count_statement` no-injection)

**Not rebaselined** — intentional per ratification §9.

### Live ephemeral runner (current code)

`build_report(cases)` on Gate A1 head (ephemeral; no `report.json` write):

| Metric | Before Gate A1 (main @ ed2d04c9) | After Gate A1 |
|--------|----------------------------------|---------------|
| correct | 6 | 6 |
| refused | 44 | 44 |
| wrong | 0 | 0 |
| `comparative_with_unit` no-injection | N/A (not on serving path) | **0** |
| total `recognized_no_injection` | 31 | **31** |

Live `recognized_no_injection_by_category` (post-Gate A1):

- `discrete_count_statement: 19`
- `temporal_aggregation: 2`
- `multiplicative_aggregation: 3`
- `descriptive_setup_no_quantity: 4`
- `currency_amount: 3`

**Interpretation:** injector frontier for `comparative_with_unit` is closed (mirror Inc3 rate lesson). Aggregate proxy unchanged; refusal family reclassification expected over time as comparative-bearing stmts move off DCS misroutes.

## wrong=0

- Live ephemeral runner: `wrong: 0`
- Proposal replay at accept: `wrong_count_delta: 0`
- Confuser suite: money/slash-fraction/indefinite N-times factors refuse at matcher; any recognizer match must emit `inject_from_match() == ()`

## Explicit non-changes

- No `report.json` rebaseline
- No additive comparative (`compare_additive`) — Gate A2
- No `double` / `one-third` / hyphenated N-times factors
- No sealed-lane movement
- No solver `_apply_compare_multiplicative` semantic change
- No `determine()` / FrameVerdict / CLOSE interaction

## Known caveats

1. **Not full Gate A1 family** — multiplicative entity-comparison subfamily only; additive deferred to Gate A2.
2. **No guaranteed correct-count lift** — monotonic contract holds (`correct>=6`, `refused<=44`); primary deliverable is injector closure + reclassification visibility.
3. **DCS/parser path for bare `Jerry has 3 times`** — standalone no-reference surface may still interact with parser initials on some question shapes; Gate A1 injector refuses; completeness guard covers multi-clause confabulation class. Not claimed solved in this slice.
4. **Matcher regex vs factor narrowness** — `_COMPARE_MULT_NTIMES_RE` still uses broad `_VALUE` at template level; extraction refuses unsafe factors via `_parse_comparative_v1_count_factor`.
5. **Pinned frontier tests** — historical `report.json` fixture unchanged; live behavior tested ephemerally.

## Deferred work (Gate A1b / A2)

- `double`, `one-third`, `as much`, unit ellipsis
- Additive comparative injection
- Cross-sentence / pronoun reference (ADR-0138)
- Nested comparative composition
- Hyphenated N-times cardinals (e.g. `twenty-five times`) if ratified separately
- `report.json` rebaseline only via separate ratified PR

## Loop-closure criterion

Gate A1 implementation loop is **closed** when:

1. Ratification #803 merged (**done**)
2. Test doctrine #804 merged (**done**)
3. Matcher + injector + exemplars + accepted proposal on serving path (**done**)
4. `comparative_with_unit` live no-injection = 0 (**done**)
5. `wrong=0` on exercised lanes (**done**)
6. This lookback doc lands with patch (**this PR**)