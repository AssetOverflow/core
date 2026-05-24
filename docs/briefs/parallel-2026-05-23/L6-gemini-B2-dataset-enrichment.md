# L6 brief — Gemini — ADR-0131.2.B B2 dataset enrichment (load-bearing curation)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-2b-enrichment -b feat/adr-0131-2b-b2-enrichment origin/main
cd ../core-adr-0131-2b-enrichment
```

**Scope.** Strengthen the B2 teaching-corpus math eval (shipped in #172, ADR-0131.2) so its lane gate is *load-bearing*, not trivially satisfied. The v1 dataset you shipped passes the gate as specified — but every chain has `expected="replay_equivalent"` and every chain cites the same cognition-pack evidence ref (`cause_truth_grounds_knowledge`). That makes `wrong == 0` mechanically true regardless of engine behavior. v1.B closes that gap.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.2-teaching-corpus-eval.md` (your prior ADR; the v1 contract you're extending — not breaking).
2. `evals/math_symbolic_equivalence/v1/cases.jsonl` + `generated_cases.py` (post-#169 if it has merged, otherwise post-#167) — pattern reference for **positive + negative + refused** case mixing in a single lane file. Mirror that shape.

**What to ship:**
- `teaching/math_corpora/math_teaching_v1.jsonl` (modify): replace the placeholder evidence ref `cause_truth_grounds_knowledge` with **honest grounding refs**. Each chain must cite at least one ref from a **math-relevant** source — either:
  - a chain id internal to this same corpus that the new chain builds on, OR
  - a lemma id from `en_mathematics_logic_v1` / `en_arithmetic_v1` / `en_units_v1` packs that the chain references.
  Do not invent refs that don't exist. Mass placeholder reuse is the v1 sin — fix it.
- `evals/math_teaching_corpus/v1/cases.jsonl` (modify + extend): keep the 30 positive `expected="replay_equivalent"` cases (renumbered if needed), and **add ~10 negative cases** of two flavors:
  - `expected="not_equivalent"` — chains whose propose-shape produces a candidate that the existing teaching loop will *correctly reject* (e.g., subject lemma not in the math pack; redundant chain already in corpus; missing required evidence; cycle in chain graph). The point is to exercise the refusal/rejection paths so `wrong == 0` becomes a real assertion.
  - `expected="refused"` — chains whose propose call raises `ProposalError` deterministically (e.g., malformed `proposed_chain`, empty subject). Mirrors the symbolic-equivalence refusal-first contract.
- `evals/math_teaching_corpus/v1/runner.py` (light modify): nothing structural — the existing `_score_one` already handles `rejected`/`pending`/`ProposalError` arms; the new cases just exercise the previously-untaken branches.
- `evals/math_teaching_corpus/v1/README.md` (modify): document the v1.B mix (positive + negative + refused), update gate language to "wrong == 0 across all three case classes".
- `tests/test_adr_0131_2_teaching_corpus_lane.py` (modify): add a test that asserts the dataset contains **at least one case of each expected class** (`replay_equivalent`, `not_equivalent`, `refused`). This is what makes the gate non-trivial — without diversity, the assertion is empty.
- `docs/decisions/ADR-0131.2.B-teaching-corpus-enrichment.md` (new): short follow-up ADR; cite ADR-0131.2 parent; explicitly call out that v1's gate was trivially satisfied and v1.B is the load-bearing version. Be honest in the framing.

**Hard constraints:**
- **Stay in the single bounded math micro-domain you chose for v1** (`en_mathematics_logic_v1`). Do not widen the domain — the bounded-domain rule from the original L1 brief still holds.
- **No real corpus mutation.** The runner's `tempfile.TemporaryDirectory()` isolation must continue to hold. Verify nothing you change leaks into live `teaching/proposals.jsonl` or the cognition corpus.
- **Refusal-first.** Refused cases must produce `ProposalError` from the live `propose_from_candidate`, not synthetic exceptions in the runner. If you cannot deterministically trigger a refusal in `propose_from_candidate`, drop that case category and document why; do **not** fake it.
- **Determinism.** `report.json` byte-equal across runs (existing invariant; new cases must not introduce nondeterminism).
- **No runtime path changes.** Same constraint as v1.
- **Honest evidence.** Every evidence ref you cite must resolve to a real corpus chain or pack lemma. Lane test should fail-loud if any ref is dangling.

**Out of scope (do not touch):**
- B1.B (#169) — separate lane, may or may not have merged when you start.
- Binding-graph PRs (#171, #174, ongoing L5) — different domain.
- Sealed holdout for B1 (#173) — already merged; mirror its honesty in your enrichment, but don't change it.
- Promotion-gate wiring (ADR-0131.4) — sequential.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.2.B): B2 teaching-corpus enrichment — load-bearing gate`. Body must include: counts by `expected` class, dangling-ref check result, and an honest acknowledgement that v1's gate was trivially satisfied and v1.B fixes that.

**Exit criterion.** PR opens with CI green, lane runner exits 0 with the new mix, `wrong == 0` across **all three case classes** (not just replay_equivalent), and ADR-0131.2.B included. Existing lane tests still pass; new diversity test passes.

**Do not stack on another agent's branch.** Target main directly.
