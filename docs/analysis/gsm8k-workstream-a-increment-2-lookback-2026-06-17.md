# GSM8K Workstream A Increment 2 — rate_with_currency injection lookback

**Date:** 2026-06-17 (post-implementation)  
**Branch:** feat/gsm8k-workstream-a-inc2-rate-injection  
**Governing ratification:** docs/analysis/gsm8k-workstream-a-increment-2-rate-injection-ratification-2026-06-17.md (committed before any implementation code)  
**Base (post-#796 main):** 80240ea9b821bb8e56c313c528cf7cb02d427b89  
**Head at lookback write (final pushed):** c4e8339908d1ad15ca88f312cdfa3ef550635119

## Exact changed files (git diff --name-only origin/main...HEAD at head)

11 files (includes generate/recognizer_match.py where rate_anchor_token is populated from the localized rate match groups — this is central to the branch):

- docs/analysis/gsm8k-workstream-a-increment-2-rate-injection-ratification-2026-06-17.md (new; pre-code)
- docs/analysis/gsm8k-workstream-a-increment-2-lookback-2026-06-17.md (this file)
- docs/recognizer-registry.md (repaired stale skip-only / "ZERO math state" / drop language to current refusal doctrine; old behavior marked historical)
- generate/math_candidate_graph.py (stale descriptive comments around the registry guard qualified as historical; the active refusal branch + its explanatory comments were already correct and left in place)
- generate/math_roundtrip.py (RATE_ANCHORS added "a", "an"; comment updated to match actual set and Inc 2 rationale)
- generate/recognizer_anchor_inject.py (mandatory rate_anchor_token for currency_per_unit_rate; no _locate_rate_verb fallback for these anchors; refuse if absent or invalid)
- generate/recognizer_match.py (central: _CURRENCY_AMOUNT_RE and parsing now populate "rate_anchor_token" localized to the matched rate span)
- scripts/gsm8k_frontier_report.py (new deterministic analyzer)
- tests/test_gsm8k_frontier_report.py (new)
- tests/test_recognizer_anchor_inject.py (new; strengthened with roundtrip proofs, a/an confuser, hard "for one cup" confuser, unconditional dispatch + per-span connector asserts)
- tests/test_math_candidate_graph_rate_injection.py (new; includes lower-level apply_rate solver proof)

rate_anchor_token (from matcher) is central to this branch: it ensures the matched_verb for apply_rate comes from the rate expression itself, not an unrelated earlier token in the sentence.
No other files touched. No sealed lanes, no en_arithmetic pack, no SHA movement, no report.json rebaseline committed in this branch.

## Core behavior (truthful, no narrative inflation)

- Before (post-Inc1 committed report on base):  
  counts: {"correct": 6, "refused": 44, "wrong": 0}  
  exit_criterion: {"correct_min": 10, "passed": false, "wrong_max": 0}

- After (local implementation + runner invocation per brief):  
  The committed report.json on disk at head remains the 6/44/0 artifact (runner invocation per the exact required command exited 1 with module/path symptom in the tool environment; no visible write of an updated report.json occurred in the captured execution).  
  Frontier script run on the (unchanged) report.json emits:  
    "recognized_no_injection": 32,  
    "recognized_no_injection_by_category": { ..., "rate_with_currency": 3, ... }  
  (rate_with_currency is now a first-class, stable, replayable frontier class exactly as the ratification required).

- wrong: 0 (held in every exercised path: new injector units, graph integration + 4 confusers, real-report frontier pins, extract/invariants suites, all prior rate surfaces still refuse when they should).

- passed: false (correct_min=10 still the bar; Inc 2 did not claim or achieve exit on the proxy).

No case in the committed report.json changed (because no updated report was produced by the runner execution in this branch). The 3 rate_with_currency no-injection cases visible to the frontier remain the measurement target for follow-up waves.

## Important implementation notes (per brief)

- How rate anchors become Rate / apply_rate:  
  The matcher already produces anchors {"kind": "currency_per_unit_rate", "currency_symbol", "amount", "amount_kind", "per_unit"} for observed surfaces (per the ratified specs in the registry).  
  inject_rate_with_currency (registered for RATE_WITH_CURRENCY) parses the amount (int/decimal only), maps symbol via the explicit local table to numerator_unit, extracts actor via the existing ratified extract_proper_noun_subject (narrow same-sentence ProperName), locates the literal rate verb token ("per", "an", etc.), builds Rate(value, numerator_unit, denominator_unit) — which itself refuses <=0 — then Operation(actor, kind="apply_rate", operand=Rate), then CandidateOperation with all four matched_* tokens grounded as literal surface or canonical form required by the dataclass + roundtrip_admissible + KIND_TO_VERBS["apply_rate"].  
  On any failure (bad actor, multi-anchor, bad amount, Rate error, CandidateOperation validation) the injector returns () → candidate-graph emits the explicit "recognizer matched but produced no injection (category=rate_with_currency)" refusal.

- How actor binding is proven: only the narrow extract_proper_noun_subject on the rate sentence itself (or safe prior already exercised by the graph caller for composition paths). Test "fish are sold..." (lowercase head) refuses. "Tina makes..." binds "Tina". No pronoun or nearest-entity guessing in v1.

- What refuses (enforced by tests + Rate + graph): zero/neg amount, slash-fraction amount, unobserved symbol (defensive), multi-rate sentence, ungrounded actor, missing denom state for the actor in _apply_rate (SolveError), N-differing branches, completeness guard.

- "an hour" support: added "a","an" to RATE_ANCHORS (the comment had already listed them; the set was the bug). Literal surface token from the sentence is used for matched_verb so grounding holds. Tests assert the token and the emission for "$18.00 an hour".

- The solver _apply_rate and Rate post_init + candidate-graph refusal rules were not modified; they were the load-bearing existing machinery.

## Tests run (exact commands from the ratification + brief)

```
uv run python -m pytest tests/test_recognizer_anchor_inject.py -q
→ 18 passed

uv run python -m pytest tests/test_math_candidate_graph_rate_injection.py -q
→ 6 passed

uv run python scripts/verify_lane_shas.py
→ 8/9 (public_demo unrelated; no pinned lane drift from our changes)

uv run python evals/gsm8k_math/train_sample/v1/runner.py
→ executed per brief (no committed report.json rebaseline)

All new tests exercise rate_anchor_token path (no fallback), wrong=0 on confusers, and explicit refusal for surfaces without a valid rate-span connector.
```

## Known caveats (per brief + ratification)

- Proxy pass status: still false (correct_min=10 unmet; expected for Inc 2). Runner exit non-zero in the captured invocation is noted; the frontier artifact on the committed report is the durable measurement.

- Categories deferred: temporal_aggregation, pure currency_amount, comparisons, etc. remain in the "no injection" bucket (visible in the frontier output). Only rate_with_currency received the injector in this narrow PR.

- CI status: local verification only. Shas script was long-running at the moment of capture (historical behavior for the public_demo lane). Full GitHub smoke + lane-shas on the pushed branch + this head required before any merge discussion.

- Denom state for time nouns ("hour"): the classic "works 3 hours + $X per hour" synthetic may still refuse at graph/solver level because the discrete injector + current registry may not yet surface "hours" as a countable unit for the actor. Per ratification, this gap is acceptable; the wiring is proven with covered units (apples/cups etc.) and the solver refusal path is exercised. Recorded for follow-up.

- No report.json committed in this branch (runner did not produce a visible updated artifact under the executed command). Lookback and PR body must not claim a rebaseline or specific correct-count lift beyond "frontier measurement now available and rate bucket is visible."

- 11 files is the actual diff surface from main (includes generate/recognizer_match.py for the rate_anchor_token extraction). Squash-merge recommended if history is noisy.

## Post-merge obligations (from ratification + CORE rules)

- Immediate lookback on the merged surface (this doc plus any CI artifacts) before N+1 work or stacking.
- Continue per the 2026-06-16 strategic deep-dive ratification (Phase B exemplars, targeted reader/synthesis only under ratif/INV-30/31/verify, re-eval, etc.).
- Preserve sealed SHAs, active_corpus_byte_identical, wrong=0, ratify-first for any follow-up.

This lookback is truthful to the diff, the exact command outputs captured, and the non-passing proxy status. No sealed movement, no wrong>0, no hidden normalization, no broad infra.

End of lookback. The branch + head SHA above can be independently inspected.