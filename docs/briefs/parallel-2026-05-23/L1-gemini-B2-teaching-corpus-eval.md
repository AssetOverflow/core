# L1 brief — Gemini — ADR-0131.2 Benchmark 2 (teaching-corpus math eval)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-2-teaching-eval -b feat/adr-0131-2-teaching-corpus-eval origin/main
cd ../core-adr-0131-2-teaching-eval
```

**Scope.** Ship the second of three benchmarks for the composite math-expert promotion gate from ADR-0131. This benchmark measures whether the *teaching/replay loop itself* can carry math content end-to-end — propose → ratify → replay-equivalent on a small math teaching corpus. It is **not** a parser-shape benchmark and **not** a symbolic-equivalence benchmark (#167 already covers that).

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131-math-expert-rebench.md` — the composite-gate framing.
2. `evals/math_symbolic_equivalence/v1/` (the B1 lane on main, post-#167) — copy its runner/report/test shape exactly. Mirror, don't innovate.

**What to ship:**
- `teaching/math_corpora/math_teaching_v1.jsonl` — ~20–30 hand-curated math teaching chains over a single bounded domain (arithmetic identity / linear equation / algebraic rewrite — pick one and stay in it). Each chain is propose-shape, ratification-ready.
- `evals/math_teaching_corpus/v1/{runner.py,cases.jsonl,README.md}` — CLI runner with `report.json` writeback, exit 0/1 on gate pass/fail. Lane gate = replay-equivalence holds across every chain AND `wrong == 0`. Mirror the B1 README's section structure.
- `tests/test_adr_0131_2_teaching_corpus_lane.py` — 6–10 lane tests: dataset integrity, exit criterion, replay-byte-equality of report.json, no chain proposes outside the bounded domain.
- `docs/decisions/ADR-0131.2-teaching-corpus-eval.md` — short ADR; cite ADR-0131 parent and ADR-0064 (cross-pack teaching) as precedent.

**Hard constraints:**
- **Bounded domain only.** Pick one math micro-domain; no GSM8K-style word problems. Word problems are B3's job (binding graph), not yours.
- **Replay-equivalence is the gate, not %.** A 100% lane on 20 chains beats a 60% lane on 200. Curate hard.
- **No runtime path changes.** This is a new eval lane + new corpus + new ADR. Touch nothing in `core/`, `chat/`, `generate/`, `algebra/`.
- **Field invariant untouched.** Don't run anywhere near `versor_condition`.
- **Determinism.** `report.json` byte-equal across runs (lane test asserts this).

**Out of scope (do not touch):**
- B1 hardening (PR #169 — different agent's lane).
- Binding-graph implementation (L2 — different agent's lane).
- B1 sealed holdout (L3 — different agent's lane).
- Promotion-gate wiring (ADR-0131.4 — sequential, after all three benchmarks land).

**Target branch.** PR against `main`. Title: `feat(ADR-0131.2): teaching-corpus math eval — lane PASSED <N>/<N>`. Body must include lane result + scope-discipline section matching #167's framing.

**Exit criterion.** PR opens with CI green, lane runner exits 0, `wrong == 0`, `replay_equivalent_count == total_chains`, and the new ADR is included.

**Do not stack on another agent's branch.** Target main directly. If you need anything from L2 or L3, the answer is no — design around the gap.
