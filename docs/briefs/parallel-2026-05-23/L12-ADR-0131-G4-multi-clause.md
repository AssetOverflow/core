# L12 brief — ADR-0131.G.4 — Capability axis: multi-clause composition (conjunctions, distributive subjects, embedded quantifier phrases)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g4-multi-clause -b feat/adr-0131-g4-multi-clause origin/main
cd ../core-adr-0131-g4-multi-clause
```

**Scope.** Capability-axis iteration: extend the **candidate parser + binding graph** to handle within-sentence composition that the per-statement parser currently refuses on. Baseline clusters: `Aaron and his brother Carson each saved up $40` (conjoined subject + distributive `each`), `Francine has five full boxes of crayons and 5 loose crayons` (conjoined object NPs sharing a verb), `Ella has 4 bags with 20 apples in each bag and six bags with 25 apples in each bag` (embedded quantifier `with N <unit> in each <bag>` + conjunction).

Target shapes (closed set):

- **Conjoined subjects with `each`:** `<A> and <B> each <verb> <N> <unit>.` → emits **two** `InitialPossession` candidates (one per actor), same `(N, unit)`.
- **Conjoined object NPs sharing a verb:** `<Entity> has <N1> <unit1> and <N2> <unit2>.` → emits **two** `InitialPossession` candidates for the same entity.
- **Embedded quantifier phrases:** `<Entity> has <N> <container> with <M> <unit> in each <container>.` → emits a derived `InitialPossession` with `value = N*M, unit = <unit>` **only if** the round-trip filter admits the product. The multiplication is a candidate, not a guarantee; the binding graph picks admissible compositions.
- **Conjoined embedded quantifiers:** `<Entity> has <N1> <container> with <M1> <unit> in each and <N2> <container> with <M2> <unit> in each.` → emits two derived candidates and a sum candidate.

This is the **highest-risk axis** of the four — multi-clause composition is where confabulation risk is highest. Refusal-first stays paramount; admission gains must be small and load-bearing, not maximum-rate-chasing.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.G-gsm8k-coverage-probe.md` — iteration discipline. The "smell test" (admission moves on GSM8K but new axis cases don't all pass → reject) bites hardest here.
2. `generate/math_candidate_graph.py` — the candidate-graph topology. New candidates must compose through the same graph; nothing in the binding/admissibility layer changes.

**What to ship:**
- **Parser extension** in `generate/math_candidate_parser.py`: three new extractors (`_conj_subject_each_candidates`, `_conj_object_candidates`, `_embedded_quantifier_candidates`) emitting multiple candidates per match. Source-span provenance covers the full sentence for each candidate.
- **Optional graph-side note** in `generate/math_candidate_graph.py` (read-only audit; only edit if a composed candidate is unreachable through existing edges — if so, the edge addition is a one-line widening, *not* a new admissibility rule). Decision to edit or not is documented in the ADR.
- **Curated coverage cases** at `evals/math_capability_axes/G4_multi_clause/v1/cases.jsonl` (~30 cases): ≥6 per shape + ≥6 refusal probes for shapes that look multi-clause but are **not** in the closed set (e.g. cross-sentence coreference `Aaron has 5. He gives 2 to Bob.`, ambiguous `each` scope, three-way conjunctions). Refusal probes are load-bearing — they pin the scope boundary the architecture refuses to cross.
- **Runner + report** at `evals/math_capability_axes/G4_multi_clause/v1/`.
- **Tests** at `tests/test_adr_0131_G4_multi_clause.py` (~15): per-shape at-least-one passing, refusal probes refuse typed, **`wrong == 0` (especially load-bearing here)**, replay byte-equality, **GSM8K probe re-run with admission strictly increases OR multi-clause refusals strictly decrease** (declare in ADR, gate on it), B3 + G.1/G.2/G.3 lanes unchanged.
- **ADR** `docs/decisions/ADR-0131.G.4-multi-clause.md`. Cite ADR-0131.G parent and ADR-0126 (candidate graph). Pin the closed shape set; document the `each`-scope policy (always distributive, never collective — refuse collective readings); document why cross-sentence coreference stays deferred.
- **Refresh** `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json`.

**Hard constraints:**
- **`wrong == 0`** is non-negotiable. Multi-candidate emission means the round-trip filter does more work — if any composed candidate slips a wrong answer, **remove the shape**, do not weaken the filter.
- **Closed shape set.** Every recognized multi-clause structure matches exactly one of the listed extractors. No paraphrase tolerance.
- **No cross-sentence state.** This axis is strictly within-sentence. Pronoun/coreference across sentences stays refused.
- **Distributive `each` only.** Collective readings (`Aaron and Carson saved $40 together`) must refuse — explicit adversarial probe required.
- **No solver changes.** If a multi-clause case parses but does not solve, file as follow-up ADR. Do not stub.
- **No new modules under `algebra/`, `chat/`, `core/`.**
- **Determinism.** Multi-candidate ordering pinned; report byte-equal across runs.

**Out of scope:** verb classes (L9/G.1), comparatives (L10/G.2), numeric literals (L11/G.3), cross-sentence coreference, ellipsis (`Aaron has 5, Carson 3`), three-way+ conjunctions, collective readings.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.G.4): multi-clause composition — admission N/50 (Δ+N)`. Body: per-shape case counts, refusal-set documentation, admission or refusal-family delta, explicit acknowledgement that this is the highest-risk axis and the `wrong == 0` evidence to back it.

**Exit criterion.** CI green; multi-clause runner exits 0 with `wrong == 0`; chosen GSM8K-probe gate satisfied; B3 + L9/G.1 + L10/G.2 + L11/G.3 lanes unchanged; refreshed coverage report committed.

**Do not stack on another agent's branch.** Target main directly.
