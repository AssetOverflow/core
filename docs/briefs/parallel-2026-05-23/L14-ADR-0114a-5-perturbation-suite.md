# L14 brief — ADR-0114a.5 — Reasoning-isolation perturbation suite (Obligation #5 for B3)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0114a-5-perturbation -b feat/adr-0114a-5-perturbation origin/main
cd ../core-adr-0114a-5-perturbation
```

**Scope.** Wire **ADR-0114a Obligation #5** (reasoning-isolation perturbation suite) for the math composite gate's B3 lane (bounded grammar). Plays to your recent parser-layer expertise (G.2 / G.4 / G.3.1) — perturbation is parser-input-modification work.

ADR-0114a #5 reads:

> `perturbation_score.py`'s **invariance-preserving rate == 1.0** AND **invariance-breaking predictable-change rate == 1.0**.

Two classes of perturbation, each must hold absolutely (per ADR-0120 §"Threshold rationale" — ε=0 here, not 0.05; reasoning isolation is binary).

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0125-reasoning-isolation-perturbation-suite.md` — methodological blueprint. Mirror the perturbation taxonomy where it transfers cleanly.
2. `evals/gsm8k_parser_dev/perturbation_score.py` — existing GSM8K-context perturbation scorer. Read the architecture; **do not** import from it (different domain assumptions — B3's bounded grammar is its own contract). Use it as a pattern source.

**What to ship:**

- **`core/capability/perturbation_b3.py`** — perturbation generator + scorer for B3.
  - **Invariance-preserving perturbations** (each must NOT change the answer):
    - **Entity rename**: `Sam → Alex`, `Bob → Carol` (drawn from a closed substitution pool documented in the ADR). Multi-occurrence consistent within a problem.
    - **Commutative reorder**: `"Sam has 5 apples. Sam has 3 oranges."` ↔ `"Sam has 3 oranges. Sam has 5 apples."` (single-entity multi-unit initial-state only; respect distributive `each` boundaries from G.4).
    - **Unit-noun synonym substitution** (closed set, pack-aligned): `apples ↔ oranges`, `dollars ↔ cents` only when the question's unit is also substituted consistently.
  - **Invariance-breaking perturbations** (each MUST change the answer by a *predictable* delta):
    - **Value replacement**: `5 → 7` in a single sentence; predicted delta = +2.
    - **Op-verb flip**: `buys` ↔ `loses`; predicted delta sign-flips the corresponding op's contribution.
  - For each case in B3's expected-correct subset, generate ≥3 invariance-preserving variants and ≥3 invariance-breaking variants. Run the pipeline on each. Tally rates.
  - Module exposes `validate_perturbation_suite(lane_id="B3_bounded_grammar", cases_path=...) -> PerturbationReport`. Same shape as the pack-provenance auditor's `validate_lane` (PR #189) — mirror that pattern for consistency.

- **CLI** `core capability perturbation` (parallel to `core capability pack-provenance`). Writes `evals/obligation_5_perturbation/<lane_id>.json`. Exit 0 iff both rates == 1.0.

- **Tests** `tests/test_adr_0114a_5_perturbation.py` (~15):
  - Each perturbation generator function is pure (same input → same output set).
  - Invariance-preserving variants of a known case all produce the same expected_answer.
  - Invariance-breaking variants produce the predicted delta.
  - Determinism: report byte-equal across runs.
  - Snapshot test: current main B3 satisfies obligation #5 (or document precisely which case-perturbation pair fails — refuse to pass spuriously).
  - Empty-lane refusal: missing cases file → typed refusal.

- **ADR** `docs/decisions/ADR-0114a.5-perturbation-suite.md`. Cite ADR-0114a parent, ADR-0125 (methodology), PR #189 (auditor pattern), ADR-0131.3 (B3 substrate). Document the closed perturbation taxonomy. Pin the entity-substitution pool + unit-synonym mapping.

- **Refresh** the obligation-#10 audit report (`evals/obligation_10_pack_provenance/B3_bounded_grammar.json`) if your perturbation generator affects parser internals (it shouldn't — perturbation operates on the *input string*, not the parser — but worth re-running the auditor to confirm).

**Hard constraints:**

- **`wrong == 0` preserved on the B3 axis lane.** Perturbation testing is auxiliary; never relax the load-bearing invariant.
- **Closed perturbation set.** Every perturbation rule documented in the ADR + asserted in tests. No paraphrase-style fuzz that wanders into G.1/G.2/G.3/G.4 axis territory; this is *reasoning isolation*, not grammar coverage.
- **Pack-aligned synonyms.** Unit substitution consults `en_arithmetic_v1` / `en_units_v1` — never invent surface units. (Same rule the G.<n> work established.)
- **Both rates must equal 1.0** for obligation #5 to pass. Anything less is a refusal — file the failing perturbation as a follow-up scope-reduction, do NOT weaken the threshold.
- **Determinism**: same seed (if you use one) and same cases produce byte-equal report.
- **No solver / binding-graph changes.** If a perturbation reveals a solver bug, file as a follow-up ADR; don't patch the solver from inside this PR.
- **No new modules under `algebra/`, `chat/`, `core/cognition/`.** New module lives under `core/capability/`.

**Out of scope:**
- B1 (symbolic equivalence) + B2 (teaching corpus) equivalents — separate sub-ADRs (mirror PR #189's "B3 only, others deferred" structure).
- Cross-sentence semantic perturbations (pronoun rewrites, paraphrasing) — those are coverage axes, not reasoning isolation.
- ADR-0114a obligations #2 (OOD), #6 (depth curve — main agent is on this in parallel), #8 (adversarial). Don't bundle.
- Composite-gate wiring (ADR-0131.4 already shipped + sufficient for the benchmark portion; obligation auditors stay orthogonal).

**Target branch.** PR against `main`. Title: `feat(ADR-0114a.5): reasoning-isolation perturbation suite — Obligation #5 wired for B3, PASSING <N>/<N>`. Body: per-perturbation-class counts, invariance-preserving rate, invariance-breaking predictable-change rate, link to ADR.

**Exit criterion.** CI green; perturbation runner exits 0 with both rates == 1.0; B3 axis lane unchanged; obligation #10 still passes; ADR-0114a.5 included.

**Only run tests that exercise files you change plus the B3 lane, the perturbation suite, and the obligation #10 auditor.** Do not run the full suite — that's the lead's job at integration.

**Do not stack on another agent's branch.** Target main directly. Note: PR #189 (obligation #10) and the main agent's parallel PR (obligation #6) are independent — no merge order needed.
