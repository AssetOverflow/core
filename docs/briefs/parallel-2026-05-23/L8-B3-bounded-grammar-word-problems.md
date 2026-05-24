# L8 brief — (agent assignment TBD by lead) — ADR-0131.3 Benchmark 3: bounded-grammar word problems

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-3-bounded-grammar -b feat/adr-0131-3-bounded-grammar origin/main
cd ../core-adr-0131-3-bounded-grammar
```

**Scope.** Third and final benchmark of the composite math-expert promotion gate from ADR-0131. B3 demonstrates the architecture's ability to handle **word problems** — but only those expressible in a **bounded grammar**, the deterministic subset the system can recognize. Outside the bounded grammar: refuse, never guess. Inside: solve through the full typed pipeline (parser → `MathProblemGraph` → binding graph → solver → verifier), with `wrong == 0`.

This is the benchmark that closes the GSM8K-arc lesson. Instead of paraphrase-chasing a benchmark designed to reward flexibility, B3 measures the architecture-aligned claim: *within a bounded grammar, deterministic end-to-end correctness*. The grammar's boundedness is the contract; coverage is a separate, honest, measurable property — not a promise.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131-math-expert-rebench.md` — the composite-gate framing; B1 and B2 are siblings.
2. `docs/decisions/ADR-0115-math-problem-parser-and-graph.md` + `ADR-0116-deterministic-solver.md` + `ADR-0117-solution-trace-verifier.md` — the existing pipeline B3 exercises. Read what they already do; do not reinvent.

**What to ship:**
- `evals/math_bounded_grammar/v1/grammar.md` — the **bounded grammar specification**. A small, explicit set of sentence templates the parser recognizes. Examples (illustrative, not exhaustive — pick a coherent set and pin it):
  - `<Entity> has <Number> <Unit>.`
  - `<Entity1> gives <Number> <Unit> to <Entity2>.`
  - `<Entity1> has <Number> times as many <Unit> as <Entity2>.`
  - `How many <Unit> does <Entity> have?`
  - `Each <Unit> costs <Number> <UnitB>. <Entity> buys <Number> <Unit>. How much does <Entity> spend?`
  Each template documented with its `MathProblemGraph` mapping. The grammar must be **closed** — every sentence either matches a template or is refused.
- `evals/math_bounded_grammar/v1/cases.jsonl` — ~40–60 hand-curated word problems split across **three classes** (mirror the B2 v1.B shape):
  - `expected="solved_correct"` (~30 cases): grammar-conformant problems with a single correct numeric answer. Span the full set of templates and operation kinds (`add`, `subtract`, `transfer`, `multiply`, `divide`, `apply_rate`, `compare_additive`, `compare_multiplicative`).
  - `expected="solved_wrong"` (~5 cases): grammar-conformant problems whose expected answer is **deliberately wrong** — exercises that the verifier catches solver errors, not just parser errors. (Use these sparingly; their purpose is to assert `wrong == 0` is load-bearing, not trivially satisfied.)
  - `expected="refused"` (~10–15 cases): problems outside the bounded grammar that must refuse cleanly through the parser's typed-refusal contract. Categories: paraphrase outside the templates, unit not in `en_units_v1`, ambiguous entity reference, multi-step problems beyond the grammar's depth, etc.
- `evals/math_bounded_grammar/v1/runner.py` — CLI runner. For each case: invoke the pipeline end-to-end (parser → `MathProblemGraph` → `bind_math_problem_graph` → admissibility → solver → verifier). Compare verifier output against `expected`. Emit `report.json` (deterministic, byte-equal across runs).
- `evals/math_bounded_grammar/v1/README.md` — methodology, scope, dataset categorization, exit criterion, link to the grammar spec.
- `tests/test_adr_0131_3_bounded_grammar_lane.py` — 10–15 lane tests:
  - Dataset integrity (case_ids unique, every case_id matches one of the documented categories).
  - **Grammar closure**: every `solved_correct` and `solved_wrong` case parses; every `refused` case raises the typed refusal — assert at the parser level, not just at end-of-pipeline.
  - Exit criterion (`wrong == 0` across all three classes; `correct_rate ≥ 0.95`).
  - Replay byte-equality of `report.json` across runs.
  - **Class diversity**: at least one case of each `expected` class (same load-bearing-gate logic as B2 v1.B).
  - Operation-kind coverage: each of the 8 `VALID_OPERATION_KINDS` exercised by at least one `solved_correct` case.
- `docs/decisions/ADR-0131.3-bounded-grammar.md` — the ADR. Cite ADR-0131 parent, ADR-0115/-0116/-0117 (pipeline), ADR-0132 through ADR-0135 (binding graph) as foundation. Document the bounded grammar as a **scope statement, not a coverage claim** — pin language like "the architecture solves problems in this grammar; problems outside it refuse." Defer wider grammar expansion to v1.B / future ADRs.

**Hard constraints:**
- **Closed grammar.** Every recognized sentence matches exactly one template. Ambiguity → refuse. No paraphrase tolerance; the grammar is the contract.
- **No new parser logic if avoidable.** If `generate/math_parser.py` already accepts the bounded grammar, route through it. If it doesn't, **prefer extending it** (in this PR) over building a parallel parser — but extensions must stay within the templates documented in `grammar.md`.
- **End-to-end pipeline.** The runner must invoke the **real solver + real verifier** for `solved_correct` and `solved_wrong` cases. No shortcuts; no mock solver. If the existing solver doesn't handle a template, drop that template from v1 and document it as deferred — do not stub.
- **Refusal-first.** Out-of-grammar cases refuse at the **parser** layer or, if the parser admits but downstream refuses, at the **binding-graph admissibility** layer (Phase 3, ADR-0134). Either is acceptable as long as the refusal is typed and deterministic. Never silently coerce.
- **Determinism.** `report.json` byte-equal across runs. Two consecutive runs produce identical hashes.
- **Field invariant untouched.** No changes to `algebra/`, `chat/`, `core/`. The pipeline runs in its existing shape.
- **Honest framing.** The PR body and README must make clear that B3's lane gate measures *correctness within the bounded grammar*, not coverage of natural-language math. The composite gate (B1+B2+B3) is the structural claim, not a free-form NL claim.

**Out of scope (do not touch):**
- L7 binding-graph Phase 4 (Opus#2's lane) — depend on Phase 1+2+3 (already on main) only. If Phase 4 lands before this PR opens, rebase and adopt the refined `BoundUnknown` signature; do not block on it.
- Promotion-gate wiring (ADR-0131.4 — sequential, after all three benchmarks land).
- GSM8K parser work, GSM8K dataset, GSM8K removal amendment (ADR-0131.5 — separate, docs-only follow-up).
- B1.B and B1.S follow-ups.
- B2 v1.B enrichment (L6 lane).

**Target branch.** PR against `main`. Title: `feat(ADR-0131.3): bounded-grammar word-problem benchmark — lane PASSED N/N`. Body must include: counts by `expected` class, operation-kind coverage table, the grammar's template list (or link to grammar.md), and an honest acknowledgement of the scope statement (bounded, not free-form).

**Exit criterion.** PR opens with CI green, lane runner exits 0 with `wrong == 0` across all three classes, `correct_rate ≥ 0.95`, every operation kind exercised, byte-equal report across runs, ADR-0131.3 included.

**Do not stack on another agent's branch.** Target main directly.
