# ADR-0190 Fraction Reading — execution-ready build spec

**Status:** greenlit, ready to execute (scoped 2026-05-30, build next session)
**Worktree:** `/Users/kaizenpro/Projects/core-fraction-reading`
**Branch:** `feat/adr-0190-fraction-reading` (off `0770648`, #488 — serving 4/46/0)
**Goal:** first fraction flip, serving `4/46/0 → 5/45/0`, wrong=0 preserved.
**Direction chosen:** unify-on-serving-injection; comprehension composition into the
existing ADR-0123 solver (the #488 method), NOT the sealed-lane/bridge route.

---

## Target: case 0046 (gold 15)

> A school has 100 students. Half of the students are girls, the other half are
> boys. 20% of the girls have dogs at home and 10% of the boys have dogs at home.
> How many students own dogs?

Read: `students=100 → girls=½·100=50, boys=½·100=50 → dog-girls=0.20·50=10,
dog-boys=0.10·50=5 → total=10+5=15`.

**Already works:** `extract_initial_candidates("A school has 100 students.")` →
`InitialPossession(school, 100, students)`. ✓

**Single-unit fallback if subset-unit modeling proves thorny:** case **0005**
(gold 21, `decrease to 3/4 of 84 → 63; decrease by = 84−63 = 21`) — single entity
(temperature), single unit (degrees), but conditional-wrapped initial + a
difference ("decrease by") question.

---

## ⚠ BUILD-DISCOVERED REVISION (2026-05-30, started the build)

The "routes cleanly through `compare_multiplicative`" assumption **holds for the
arithmetic but NOT for any real fraction case.** Verified empirically:

- `compare_multiplicative` **does** handle fractional factors:
  `"Alice has 3/4 times as many apples as Bob"` (Bob=80) → **60** ✓;
  `"half as many"` → **40** ✓. So the arithmetic mechanism exists.
- **But it only works for the distinct-actor, same-unit, no-overwrite,
  entity-reference shape** — and **none of the 5 train_sample fraction cases
  match it:**
  - **0046 / 0004 / 0041 — PARTITION** (the unit *changes*: `students → girls`).
    `compare_multiplicative` does `state[(actor,unit)] = state[(ref,unit)]×factor`
    with the SAME unit; it cannot produce a new-unit subset.
  - **0005 — TEMPORAL self-overwrite** (`temperature → ¾·temperature`, same
    entity+unit). The solver **refuses overwrite** (`math_solver.py` "would
    overwrite existing state").
  - **0010 — multi-step** (accumulation `20−12` + additive-fraction `1/4 more`).
- Value resolution gotchas: `_resolve_value('half')` → **2** (NOT 0.5 — use
  `_ANCHOR_TO_FACTOR['half']=(0.5,'fraction')`); slash-fractions work
  (`3/4`→0.75); `'20%'` and `'a third'`/`'two thirds'` → None (need a map).
- Reference binding: the solver matches the reference by **entity only**, so a
  `"the students"` reference does NOT bind to the `(school, students)` state.

**Revised real work = a new PARTITION operation**, not a `compare_multiplicative`
reuse: `base[unit A, V] + "<frac> of <base> are <subset>" → subset[unit B,
frac·V]`, where the base binds by **unit** (refuse if ambiguous), plus a
chained-partition path (`20% of the girls`) and an **aggregate-without-overcount**
question (sum only the leaf subsets `10+5=15`, not the `school/girls/boys`
intermediates). This is a `math_problem_graph` + `math_solver` + extractor +
round-trip build — a real architectural piece, NOT the clean reuse scoped below.
The clean-reuse sections below remain valid ONLY for a (currently non-existent in
train_sample) distinct-actor same-unit fraction surface.

---

## The pieces (each general; each lands wrong=0-proven)

### Piece 1 — fraction-of extractor (foundational; all 5 fraction cases need it)
`<frac> of [the] <base> <verb> <result>` → `compare_multiplicative` op:
`actor=result, factor=frac, reference=base, direction="fraction"`.

- Route through **existing** `_build_compare_multiplicative` (`math_candidate_parser.py:1121`)
  and the **existing** `_apply_compare_multiplicative` solver (`math_solver.py:422`).
  `direction="fraction"` is already a valid `Comparison.direction`
  (`VALID_COMPARISON_DIRECTIONS`).
- **Word-fractions pass the round-trip filter UNCHANGED:** for "Half of the students
  are girls", `matched_verb="half"` ∈ `KIND_TO_VERBS["compare_multiplicative"]`
  = `{half, quarter, third, twice, thrice, double, triple, times}`;
  `matched_value_token == matched_verb` (anchor-as-value form, the round-trip
  filter's lines ~458-461 already allow it); empty `matched_unit_token` is allowed
  for a `Comparison` operand.
- New extractor `_fraction_of_candidates(sentence)` in `math_candidate_parser.py`,
  wired alongside `_compare_multiplicative_candidates` (~line 1181, called from the
  comparative block ~907-913).
- **wrong=0 guards:** factor token + reference token must ground in the surface;
  refuse when the base entity is ambiguous; `reference != actor` (already enforced
  at `_build_compare_multiplicative:1134`).

### Piece 2 — round-trip extension for `N%` / `N/M` factors (THE wrong=0-sensitive piece)
Every real fraction case mixes in a percentage or slash-fraction (0046 has `20%`/`10%`;
0005 has `3/4`; 0004 has `1/4`). These have **no word-anchor** in
`KIND_TO_VERBS["compare_multiplicative"]`, so they fail the filter today.

- Admit a numeric/percentage factor for `compare_multiplicative`: `matched_value_token`
  = the literal `"20%"` / `"3/4"` (grounds on the surface `%` / `/` token);
  resolve factor `0.20` / `0.75`. File: `generate/math_roundtrip.py` (`roundtrip_admissible`
  ~430, `KIND_TO_VERBS`) + the factor-resolution path.
- **Failing-under-violation test REQUIRED** (this is the load-bearing wrong=0 obligation):
  a spurious/non-fraction `%` (e.g. "20% off" with no base, or a bare percentage with
  no `of <base>`) must NOT admit. Confirm an existing-shape test fails if the guard is
  removed.

### Piece 3 — count-aggregate question + subset-unit modeling
`"How many students own dogs?"` → `Unknown(entity=None, unit=...)`; the solver
aggregates by **exact unit equality** (`math_solver.py:498`,
`sum(v for (_,unit),v in state.items() if unit==unknown.unit)`).

- **Decision to make first:** what unit do the derived subsets carry so `10+5=15`
  aggregates? `students ⊃ girls/boys ⊃ dog-owners`. Likely model all derived
  dog-owner quantities in unit `students` (or a shared `dogs`/`students-with-dogs`
  unit) so the aggregate sums them. This subset-unit choice IS the wrong=0 crux of
  0046 — pin it with a test before wiring.
- Question extractor: extend `extract_question_candidates` (`math_candidate_parser.py:797`)
  for `"How many <unit> <verb> <noun>?"` aggregate shape, or reuse `_Q_TOTAL_RE`-style
  aggregate. `Unknown.unit` must be non-empty.

---

## wrong=0 proof (the #488 cadence — all required before PR)
- All 8 capability-axis lanes wrong=0 (G1, G2_comparatives, G3, G4, G5, S1, S3, S4).
- `train_sample` `4/46/0 → 5/45/0` (0046 added to correct set; wrong bucket empty).
- `scripts/verify_lane_shas.py` exit 0; `scripts/generate_claims.py --check` OK after
  re-baseline.
- Re-baseline `evals/gsm8k_math/train_sample/v1/report.json` +
  `train_sample_coverage_report.json` + `CLAIMS.md`.
- New tests failing-under-violation: word-fraction admits + percentage admits +
  the Piece-2 spurious-`%` refusal + the Piece-3 subset-unit aggregate.

## Write ADR-0190
`docs/decisions/ADR-0190-fraction-reading.md` — fraction-of via `compare_multiplicative`;
why it's not a regex grammar template; the percentage round-trip extension + its
wrong=0 guard; the subset-unit aggregate decision; reuse of ADR-0123 solver.

## Parked from this session (recoverable, NOT for this build)
`_repeated_volume_candidates` (the 0021 distinct-unit triple-product extractor) is in
`git stash` on branch `feat/adr-0190-discrete-count-injection` (worktree
`core-discrete-count-injection`) — unrelated to fractions; leave it.
