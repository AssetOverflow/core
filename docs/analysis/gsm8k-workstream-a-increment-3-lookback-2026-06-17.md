# GSM8K Workstream A Increment 3 — rate followup lookback

**Date:** 2026-06-17 (post-merge evidence closure)
**Branch (implementation):** feat/gsm8k-workstream-a-inc3-rate-followup (merged as PR #799)
**Head (merged on main):** 8a981e66c716f020b5558c584d39084fadee5011
**Governing ratification:** docs/analysis/gsm8k-workstream-a-increment-3-rate-followup-ratification-2026-06-17.md
**Evidence-closure PR branch:** docs/gsm8k-workstream-a-inc3-lookback (this lookback + test semantics; no runtime logic)

## What shipped (PR #799 merged)

Inc3 closed the post-#797 rate connector blocker: the `"one"` token in **for one &lt;unit&gt;** rate surfaces is now a valid `apply_rate` rate anchor.

### Exact semantic path

1. **Matcher** (`generate/recognizer_match.py`): when the currency-per-unit regex captures connector `q`, if `q in ("each", "every", "a", "one")` then `connector = q` and `rate_anchor_token` is set to that literal (e.g. `"one"` for *for one cup*).
2. **Roundtrip whitelist** (`generate/math_roundtrip.py`): `RATE_ANCHORS` includes `"one"` alongside `per`, `each`, `every`, `a`, `an`.
3. **Injector** (`generate/recognizer_anchor_inject.py`): `inject_rate_with_currency` accepts `rate_anchor_token in ("per", "each", "every", "a", "an", "one")`; on success emits `CandidateOperation(kind="apply_rate", operand=Rate(...))` with `matched_verb` grounded to the literal connector.

No other runtime modules changed solver semantics, sealed lanes, graph construction, or serving policy.

### Files in the merged implementation (#799)

- generate/math_roundtrip.py
- generate/recognizer_match.py
- generate/recognizer_anchor_inject.py
- tests/test_recognizer_anchor_inject.py
- tests/test_math_candidate_graph_rate_injection.py
- tests/test_gsm8k_frontier_report.py
- tests/test_candidate_graph_recognizer_wiring.py
- docs/analysis/gsm8k-workstream-a-increment-3-rate-followup-ratification-2026-06-17.md
- docs/analysis/core-problem-solving-capability-roadmap-v2-2026-06-17.md (partial update at merge time)

## Measurement truth (pinned vs live)

### Pinned committed artifact (historical / stale for rate bucket)

`evals/gsm8k_math/train_sample/v1/report.json` remains the **pre-Inc2/Inc3 runner output** committed at the Inc1 rebaseline:

- **6 correct / 44 refused / 0 wrong**
- `recognized_no_injection_by_category.rate_with_currency: 3` (Tina *an hour*, Alexa *for one cup*, Erica *per kg* still show injector-level no-injection strings)

This artifact is **intentionally not rebaselined** in Inc3 or this evidence-closure PR. Frontier script analysis on the pinned file still reports `rate_with_currency: 3` — that is expected and documents the historical measurement surface Inc2 targeted.

### Live ephemeral runner (current main code, not committed)

`build_report(cases)` on current main (ephemeral invocation; no `report.json` write):

| Metric | Value |
|--------|-------|
| correct | 6 |
| refused | 44 |
| wrong | 0 |
| `rate_with_currency` in `recognized_no_injection` | **0** |
| total `recognized_no_injection` | 31 (was 32 on pinned artifact) |
| live `recognized_no_injection_by_category` | `discrete_count_statement: 19`, `temporal_aggregation: 2`, `multiplicative_aggregation: 3`, `descriptive_setup_no_quantity: 4`, `currency_amount: 3` |

**Interpretation:** rate surfaces no longer refuse at the injector boundary. Refusal moved **downstream** (e.g. `no admissible candidate for statement`, `no branch produced a solvable graph`) because denom-state / composition blockers remain. This matches Inc3 ratification §2: actionable evidence, not correct-count lift.

`evals/gsm8k_math/train_sample/v1/refusal_rescan_v3.json` corroborates Tina/Alexa cases: `current_refusal_reason` is `no admissible candidate for statement`, not `produced no injection`.

## wrong=0

- Pinned artifact: `wrong: 0`
- Live ephemeral runner: `wrong: 0`
- Inc3 unit/graph tests exercise confusers; no wrong answers admitted on exercised paths.

## Explicit non-changes (Inc3 scope held)

- **No** `report.json` rebaseline committed
- **No** denominator-state production (hour/kg/cup Initial seeding)
- **No** comparative injection / Gate A1
- **No** sealed-lane movement (`_SEALED_INJECTORS` remains empty; train_sample uses `sealed=False`)
- **No** serving SHA / CLAIMS movement
- **No** `determine()` / FrameVerdict / CLOSE interaction
- **No** corpus/pack/policy/identity mutation
- **No** solver `_apply_rate` semantic change

## Known caveats

1. **Aggregate proxy unchanged:** still 6/44/0 and `passed=false` (`correct_min=10`). Inc3 did not claim net correct lift.
2. **Refusal-family reclassification:** rate cases may move from `recognized_no_injection` to `no_admissible_statement` or graph unsolvability — not to `correct`.
3. **Pinned frontier tests:** tests that read committed `report.json` encode the **historical** rate bucket (3× no-injection). Live-behavior tests use ephemeral `build_report` or synthetic fixtures (see `tests/test_gsm8k_frontier_report.py`).
4. **Erica / denom reachability:** third rate case may still refuse downstream for actor/denom reasons; connector fix does not solve inverse *for one cup* pricing semantics.
5. **Inc3 lookback was missing until this PR:** ratification landed with #799; lookback + roadmap status update closes the governance loop before Gate A1 ratification.

## Loop-closure criterion (for Gate A1 readiness)

The post-#797 rate follow-up loop is **closed** when all of the following hold:

1. PR #799 merged with `"one"` connector in matcher + roundtrip + injector (**done**).
2. Live ephemeral frontier shows `rate_with_currency` no-injection = **0** (**done** on current main).
3. `wrong_total == 0` on train_sample proxy (**done**).
4. This lookback + roadmap status committed; frontier tests distinguish pinned historical artifact from live post-Inc3 behavior (**this PR**).
5. No `report.json` rebaseline unless separately ratified (**held**).

Gate A1 comparative ratification may proceed after this evidence-closure PR merges.

## Tests (evidence-closure PR adds/clarifies)

Focused lane (from worktree):

```
.venv/bin/python -m pytest tests/test_gsm8k_frontier_report.py -q
.venv/bin/python -m pytest tests/test_recognizer_anchor_inject.py -q
.venv/bin/python -m pytest tests/test_math_candidate_graph_rate_injection.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_recognizer_wiring.py -q
```

See PR body for exact captured outputs at commit time.

## Post-merge obligations

- Ratify Gate A1 multiplicative comparative injection (docs-only) before any comparative code.
- Preserve wrong=0, sealed discipline, and ratify-first on all Workstream A follow-ons.
- Do not treat pinned `report.json` rate bucket as live-state without ephemeral runner corroboration.

This lookback is truthful to merged #799 behavior, the stale pinned artifact, and ephemeral live measurement. No benchmark theater; no hidden rebaseline.