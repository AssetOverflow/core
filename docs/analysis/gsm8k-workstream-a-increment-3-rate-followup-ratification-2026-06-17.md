# GSM8K Workstream A Increment 3 — rate followup (post-#797) ratification

**Date:** 2026-06-17  
**Workstream:** A  
**Increment:** 3 — post-#797 rate frontier evidence loop closure (narrow)  
**Status:** Ratified for implementation (BEFORE code changes)  
**Scope lock:** Bounded to making the rate "recognized_no_injection" bucket produce actionable evidence by resolving the explicit remaining connector blocker left open in #797. One smallest change only.

## 1. Which exact refusal bucket is being attacked?

From frontier report run on the (stale but authoritative post-#797) committed proxy `evals/gsm8k_math/train_sample/v1/report.json`:

- Overall: 6 correct / 44 refused / 0 wrong (passed=false)
- recognized_no_injection: 32
- recognized_no_injection_by_category (rate relevant): rate_with_currency: 3

The three rate_with_currency cases still emitting the "recognizer matched but produced no injection" (category=rate_with_currency) are exactly the ones referencing the surfaces left partially unhandled after Inc2:
- 'Tina makes $18.00 an hour.' (category=rate_with_currency)
- 'Alexa has a lemonade stand where she sells lemonade for $2 for one cup.' (category=rate_with_currency)
- 'Erica lives near a lake where most locals sell fish as their main source of income, earning $20 per kg of fish.' (category=rate_with_currency)

Post-#797, the matcher fires for all three and "an"/"per" surfaces now reach the injector and emit a CandidateOperation (verified by live debug on current main). The "for one cup" explicitly sets `rate_anchor_token: None` (see matcher comment and spec unresolved_notes: "Non-canonical 'for one X' framing").

The injector returns () for the "one" case (and any elimination downstream for the others surfaces as the same top-level refusal reason because the statement-level inject did not contribute an admitted choice).

This is the narrow remaining rate-family blocker visible in the rate bucket of the frontier analyzer.

## 2. Which cases are expected to lift?

- On the train_sample proxy: expected 0 net lift in correct count (the Alexa "for one cup" case uses inverse semantics — target cups from known revenue, not forward apply_rate on a held cup count; Tina/Erica denom qty statements use verbs/shapes that do not yet emit the required Initial for "hour"/"kg" unit). The change makes injection succeed for the "one" framing; the case will surface a downstream refusal reason ("no branch produced a solvable graph", "no admissible...", or "requires ... state") instead of the "no injection" one.
- The rate_with_currency slice of recognized_no_injection is expected to drop from 3 (at least the connector case will no longer refuse at the injector boundary).
- No change to non-rate buckets. Wrong remains 0.

The primary deliverable is **actionable evidence**: after the change the frontier report will show the rate category either empty or reclassified to the true next blocker (denom state reachability), closing the post-#797 measurement loop without claiming a correct-count jump.

## 3. Which confusers must still refuse?

All existing confusers from the Inc2 ratification and test suite:
- No denom state for the actor (e.g. isolated rate sentence).
- Wrong actor (rate stated for A, quantity held by B).
- Multiple rates in one sentence.
- Time-unit without conversion (days vs hours).
- Any surface that would produce ambiguous or ungrounded Rate / actor / verb.

The change adds "one" only in the exact "for <one> <unit>" rate framing already present in the ratified rate_with_currency exemplars; no broadening of actor binding, no pronoun support, no new verbs outside the rate anchor list.

## 4. What is the wrong=0 guard?

- All paths still go through the existing five-layer net (matcher narrowness, source grounding in anchors, injector returns () on any construction failure, roundtrip_admissible + constraint propagation elimination, candidate-graph multi-branch disagreement + completeness).
- New surfaces exercise the same `CandidateOperation` + `roundtrip_admissible` + `KIND_TO_VERBS["apply_rate"]` checks.
- "one" treated as a surface alias only for the already-ratified "for one X" exemplar in the rate proposal; added to RATE_ANCHORS and injector allow-list with no other semantic change.
- No sealed path touched (train_sample runner + serving use sealed=False).
- Pre/post change: run the frontier script + `parse_and_solve` on the three rate surfaces + full proxy cases; assert wrong==0 on all.
- The `tests/test_math_candidate_graph_rate_injection.py` and `test_gsm8k_frontier_report.py` continue to pass (the existing test already tolerates non-"no injection" refusals for the Alexa stmt).
- If after change any train_sample case flips from refused to wrong, revert.

## 5. Does this touch serving, sealed lanes, report.json, or solver semantics?

- No changes to sealed injector lane (`_SEALED_INJECTORS` remains empty for this).
- No write of updated report.json in this increment (proxy remains at 6/44/0 unless a later runner run is separately committed; the ratification does not require rebaseline).
- No solver changes (`_apply_rate` unchanged; still requires denom state).
- No graph construction or cartesian changes.
- Touches only: the rate anchor token allow-list (matcher + roundtrip set + injector guard) + comments. This is the minimal patch to retire the explicit "narrow for Inc 2" deferral.
- The frontier report script, ratification, and roadmap update are docs/evidence only.

## 6. What is explicitly out of scope?

- Denominator-state production (seeding Initials for "hour", "kg", "cup" from "works N hours", "trawled 80 kg", etc.). That is future work once the connector surface is closed and the frontier reclassifies the bucket.
- Any change that would allow apply_rate without prior denom state.
- "for one cup" solving (would require inverse/division op or goal-residual style for price-per).
- Expansion to other temporal_aggregation, currency_amount, or non-rate categories.
- Comparative injection / Gate A1.
- Any movement of sealed SHAs, practice lane, or CLAIMS.
- Broad verb or subject binding relaxations.
- Re-running the train_sample runner and committing a new report.json as part of this PR (measurement-only refresh is out; the script run on the committed report is the evidence).

## Implementation Notes (for the PR)

- Smallest diff: 3 locations (RATE_ANCHORS, matcher "one" case, injector allow-list) + doc updates.
- Update comments that say "narrow for Inc 2" or "deferred".
- Run `uv run python scripts/gsm8k_frontier_report.py evals/gsm8k_math/train_sample/v1/report.json` before/after for the artifact.
- `core test --suite gsm8k` or equivalent lane (pytest on the rate graph test + frontier test) + full `core test --suite full -q` before merge when practical.
- Preserve `passed=false` on the proxy.

This Inc3 closes the rate follow-up loop narrowly so that Ladder A has a clean evidence boundary before any comparative work.
