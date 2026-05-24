# L10 brief — ADR-0131.G.2 — Capability axis: comparatives (additive + multiplicative)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g2-comparatives -b feat/adr-0131-g2-comparatives origin/main
cd ../core-adr-0131-g2-comparatives
```

**Scope.** Capability-axis iteration: land **candidate emitters** for `compare_additive` and `compare_multiplicative`. The round-trip verb tables (`COMPARE_ADDITIVE_ANCHORS`, `COMPARE_MULTIPLICATIVE_ANCHORS`) and the `Comparison` operation shape (`generate/math_problem_graph.py:128`) already exist — what's missing is the candidate-parser side. The comment at `generate/math_candidate_parser.py:30` explicitly flags this as a deferred phase.

Comparatives are an **operation kind** the binding graph already admits; the architectural extension is purely on the parse side. Target shapes (closed set):

- Additive: `<EntityA> has N more <unit> than <EntityB>`, `<EntityA> has N fewer <unit> than <EntityB>`, `<EntityA> has N additional <unit>`.
- Multiplicative: `<EntityA> has twice as many <unit> as <EntityB>`, `<EntityA> has N times as many <unit> as <EntityB>`, `<EntityA> has half as many <unit> as <EntityB>`.
- Nested compositional (load-bearing — appears in baseline refusal `Jen has 10 more ducks than four times…`): `<EntityA> has N more <unit> than M times <EntityB>'s <unit>`. Treat as a *composed* `compare_additive(EntityA, compare_multiplicative(EntityB, M))` structure.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.G-gsm8k-coverage-probe.md` — iteration discipline (single axis, own coverage cases, GSM8K admission strictly increases or a refused-reason family is deliberately reduced, `admitted_wrong == 0`).
2. `generate/math_problem_graph.py` (Comparison) + `generate/math_roundtrip.py` (anchor tables) — the contract the new emitter must satisfy. Do **not** redefine direction vocab; emit into the existing four `direction ∈ {more,fewer,times,fraction}` slots.

**What to ship:**
- **Parser extension** in `generate/math_candidate_parser.py`: new `_compare_additive_candidates` / `_compare_multiplicative_candidates` extractors emitting `CandidateOperation` records whose `op.kind` is `compare_additive` / `compare_multiplicative`. Regex specificity order documented; nested composition produces **two** candidates and the round-trip layer / binding graph (Phase 3, ADR-0134) picks the admissible composition.
- **Curated coverage cases** at `evals/math_capability_axes/G2_comparatives/v1/cases.jsonl` (~25 cases): ≥4 per direction (`more`, `fewer`, `times`, `fraction`) + ≥3 nested-composition cases + ≥4 refusal cases for **paraphrases outside the closed set** (e.g. "as many … as", "compared to", "in comparison with"). The refusal cases pin the scope boundary.
- **Runner + report** at `evals/math_capability_axes/G2_comparatives/v1/`.
- **Tests** at `tests/test_adr_0131_G2_comparatives.py` (~12): per-direction at-least-one passing, nested-composition at-least-one passing, refusal cases all refuse with typed parser error, `wrong == 0`, replay byte-equality, **GSM8K probe re-run** with `admission_rate` strictly increases OR `refused_reasons_top` for comparative-shape clauses strictly decreases (whichever is honest — pick one in the ADR and gate on it).
- **ADR** `docs/decisions/ADR-0131.G.2-comparatives.md`. Document closed-set anchor alternation; explicitly call out which paraphrases are deferred and why (they are not in the round-trip table either — admitting them would breach `wrong == 0`).
- **Refresh** `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json`.

**Hard constraints:**
- **Direction vocab is closed** to the four `Comparison.direction` literals. No new literals.
- **`wrong == 0`** on the new axis and the probe. Nested-composition admissibility is the round-trip layer's job — do not bypass it.
- **No solver / binding-graph changes.** If a comparative parses but does not solve, that's a downstream gap → file it as a follow-up ADR, do **not** stub the solver.
- **Specificity order documented.** Multiplicative anchors that overlap with additive (`twice` vs `two more`) must have deterministic precedence pinned in the ADR.
- **No new modules under `algebra/`, `chat/`, `core/`.**
- **Determinism.** Report byte-equal across runs.

**Out of scope:** verb classes for initial state (L9/G.1), rate verbs (L11/G.3), multi-clause distributive subjects (L12/G.4), implicit-comparison shapes ("the same number of … as").

**Target branch.** PR against `main`. Title: `feat(ADR-0131.G.2): comparative operations (additive + multiplicative) — admission N/50 (Δ+N)`. Body: per-direction case counts, refusal-set documentation, admission delta or refused-reason-family delta, link to ADR.

**Exit criterion.** CI green; comparatives runner exits 0 with `wrong == 0`; chosen GSM8K-probe gate (admission ↑ OR comparative-clause refusals ↓) satisfied; B3 + L9/G.1 axis lanes unchanged; refreshed coverage report committed.

**Do not stack on another agent's branch.** Target main directly.
