# ADR-0189a — First metric move: 3/47/0 → 4/46/0 (case 0024, comprehension-composed)

**Status:** Accepted (implemented). Builds on
[ADR-0189](./ADR-0189-comparative-verb-unit-widening.md) (comparative reading).
Serving-path capability, landed because **wrong=0 is proven across every lane**.

> **One line.** The official GSM8K `train_sample` metric moves for the first time
> this arc: **3/47/0 → 4/46/0**. Case 0024 now solves by *composing three general
> comprehension capabilities* — day-of-week count enumeration (`Sidney =
> 20+36+40+50 = 146`), comparative reading (`Brooke = 3 × Sidney`, ADR-0189), and
> an activity question (`How many … did Brooke do?`) — feeding the unchanged
> ADR-0123 solver. No new arithmetic, no per-case hack, wrong=0 held everywhere.

---

## 1. What moved and why it's legitimate

`train_sample`: **3/47/0 → 4/46/0**. New correct: **0024** (answer 438).
Correct set is now `{0014, 0018, 0024, 0042}`.

This is the "serving if wrong=0 proven" path (operator-approved): a *complete*,
wrong=0-proven capability lands directly in serving and the committed
`report.json` + `CLAIMS.md` are re-baselined to the new metric. It is **not** a
sealed gain — it solves a real case through comprehension, with the wrong=0
firewall intact.

## 2. The three composed capabilities (each general, each wrong=0-safe)

0024: *"Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday,
and 50 on Thursday. Brooke does three times as many jumping jacks as Sidney. How
many jumping jacks did Brooke do?"*

1. **Day-of-week count enumeration** (`_day_enumeration_candidates`): `"<Actor>
   does N1 <noun> on <Day1>, N2 on <Day2>, …"` → one summed `CandidateInitial`
   (`Sidney = 146 jumping jacks`). Closed to the seven day names so the
   `<count> on <Day>` list cannot be confused with other comma lists. The derived
   sum is not literal in source, so provenance anchors on the first count token
   (which grounds) — the exact pattern `_embedded_quantifier_candidates` already
   uses for `N × M`.
2. **Comparative reading** (ADR-0189): `Brooke = 3 × Sidney` via the existing
   `compare_multiplicative` solver. Required the ADR-0189 verb-widening (`does`)
   and multi-word unit (`jumping jacks`).
3. **Activity question** (`_Q_DID_RE`): `"How many <unit> did <Entity> <verb>?"`
   → `Unknown(entity, unit)`, with a 1–2-word unit slot.

Plus the `CandidateInitial` anchor whitelist gains `do`/`does`/`did`
(production-possession: "does N jumping jacks" = holds a count of N), admitted
only via the closed day-enumeration shape.

## 3. wrong=0 evidence (the load-bearing gate)

- **All 8 capability-axis lanes: wrong=0** — G1 (20/0), G2_comparatives (29/29),
  G3_numerics (20/0), G4 (32/32), G5 (20/20), S1 (20/20), S3 (24/24), S4 (20/20).
- **train_sample 4/46/0, wrong=0**; the wrong bucket is empty.
- **Serving-frozen gate green**: `verify_lane_shas.py` exit 0 (no pinned lane —
  reviewer_registry / math_teaching_corpus / … — changed), `generate_claims.py
  --check` OK after re-baseline.
- **872 tests pass.** New tests are failing-under-violation, incl. wrong=0 guards:
  a non-day comma list must NOT be summed (`test_non_day_comma_list_does_not_enumerate`);
  polarity-inverting comparative verbs stay refused (ADR-0189).
- Re-baselined `report.json` + `train_sample_coverage_report.json` (the latter
  also clears pre-existing refusal-reason drift). The only remaining pre-existing
  failures (`G3_numerics::test_committed_report_matches_fresh_run`, a telemetry
  round-trip test) are unrelated and fail on pristine `origin/main`.

## 4. Why this obeys the standing principles

- **Decode, don't guess.** 0024 is solved by *reading* its structure (an
  enumeration is a sum; "three times as many" is a multiplicative comparison) and
  composing the existing solver — not by storing an answer or adding arithmetic.
- **General, not overfit.** Each piece is a recurring construction (day-of-week
  enumeration, comparative, activity question), not a 0024-specific regex; the
  day-enum is closed to day names and guarded against non-day lists.
- **Eliminate-first, then solve.** The microscope mapped all 47 refusals, proved
  no single-capability win exists, and identified 0024 as the cleanest *composing*
  target; the flip required exactly the three pieces the dissection predicted.
- **wrong=0 > coverage.** Landed only after wrong=0 was proven on every lane; the
  round-trip firewall and the solver are unchanged.
- **No contradiction** with in-use ADRs: extends the ADR-0131 extractors and the
  ADR-0189 comparative reading; feeds the ADR-0123 solver unchanged.

## 5. The path this opens

0024 proves the composition approach end-to-end. The same three components recur
across the remaining 46; the next flips come from the companion capabilities the
dissection mapped (multi-value/non-day aggregation, division questions, percentage,
currency-rate via ADR-0187/0188), each landed the same way: general, wrong=0-proven,
re-baselined in serving.
