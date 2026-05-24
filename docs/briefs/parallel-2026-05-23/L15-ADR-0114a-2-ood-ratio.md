# L15 brief — ADR-0114a.2 — OOD surface variation ratio (Obligation #2 for B3)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0114a-2-ood-ratio -b feat/adr-0114a-2-ood-ratio origin/main
cd ../core-adr-0114a-2-ood-ratio
```

**Scope.** Wire **ADR-0114a Obligation #2** (OOD surface variation ratio) for the math composite gate's B3 lane. Continues your obligation-auditor work after L14 (#5 perturbation).

ADR-0114a #2 reads (via ADR-0120's table):

> `ood_score.py`'s **OOD/public ratio for the domain's lanes ≥ 0.95**.

The OOD lane is a separate case set whose surface forms vary along **non-semantic axes** the public split didn't exercise (different entity-name distributions, different unit-noun distributions, different sentence-ordering patterns) while staying strictly **within B3's bounded grammar** (the grammar IS the contract; outside the grammar is refusal-territory, which is obligation #8's domain, not #2's).

The obligation's spirit: a pattern-matcher overfits to surface distributions of the training/public set and falls off when surface varies; a deterministic reasoner stays approximately flat. The 0.95 ratio means OOD accuracy must be at least 95% of public accuracy.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0118a-ood-surface-generator.md` — methodological blueprint. Mirror the OOD generation taxonomy where it transfers; B3's bounded grammar narrows the design space (no paraphrase variance — that's adversarial, not OOD).
2. `core/capability/pack_provenance.py` (PR #189 / merged ADR-0114a.10) + `core/capability/depth_curve.py` (PR #190 / pending ADR-0114a.6) — the auditor pattern this PR mirrors. Same module-shape, same CLI-shape, same `validate_lane`/`evaluate_*` signature, same `obligation_N_*` verdict fields.

**What to ship:**

- **`evals/obligation_2_ood_ratio/v1/cases.jsonl`** — OOD case set, **≥30 cases**, strictly in-grammar (B3's grammar contract from ADR-0131.3 `grammar.md`). Each case is the **surface-varied sibling** of an existing B3 public case:
  - **Entity-name pool**: rotate `Sam → {Maya, Liam, Noah, Diana, Felix, ...}` from a closed substitution pool documented in the ADR. Same letter-case discipline as B3 (capitalized proper nouns).
  - **Unit-noun pool**: rotate `apples → {oranges, berries, marbles, pencils, books, candies, stamps, ...}` — all from `en_units_v1` (verify each is pack-recognized; if not, defer the unit).
  - **Operation-order variance**: where B3 puts initial first, OOD puts the question first or interleaves (within grammar). Example: B3 `Sam has 5 apples. Sam buys 3. How many apples?` ↔ OOD `Maya buys 7 oranges after she has 4 oranges. How many oranges does Maya have?` (when grammar admits both forms).
  - Each case carries `shape_category` matching one of B3's documented shapes + a new `public_sibling_case_id` field pointing to its B3 counterpart for audit traceability.

- **`evals/obligation_2_ood_ratio/v1/runner.py`** — runs the OOD set through the candidate-graph pipeline; emits `report.json` mirroring B3's runner shape.

- **`core/capability/ood_ratio.py`** — auditor. Reads B3's public `report.json` (cases_correct / cases_total) AND the OOD `report.json`. Computes `ood_ratio = ood_accuracy / public_accuracy`. Emits `OodRatioReport` with `obligation_2_ratio_satisfied` flag (gate: ratio ≥ 0.95). Same module-shape as pack_provenance.py / depth_curve.py.

- **CLI** `core capability ood-ratio`. Writes `evals/obligation_2_ood_ratio/<lane_id>.json`. Exit 0 iff ratio ≥ 0.95 AND OOD `wrong == 0` AND public-baseline-accuracy > 0.

- **Tests** `tests/test_adr_0114a_2_ood_ratio.py` (~15):
  - Dataset integrity: ≥30 cases; every case has `public_sibling_case_id` resolving to a real B3 case; every case in-grammar (parser admits).
  - Entity-name substitution: every OOD case has a *different* entity name than its public sibling.
  - Unit-noun substitution: every OOD case has a *different* unit (when the public sibling's unit appears in the substitution pool).
  - Auditor: ratio computed correctly; gate at 0.95 pinned (changing requires new ADR); `wrong == 0` is a separate gate (catches OOD cases where parser misroutes to a wrong answer).
  - Refusal on missing public report or missing OOD cases.
  - Determinism: report byte-equal across runs.
  - Snapshot test: current main satisfies obligation #2 on the OOD set you ship.

- **ADR** `docs/decisions/ADR-0114a.2-ood-ratio-auditor.md`. Cite parent ADR-0114a, ADR-0118a (methodology), PR #189 + PR #190 (auditor pattern), ADR-0131.3 (B3 grammar contract). Pin the entity-name and unit-noun substitution pools.

**Hard constraints:**

- **Strictly in-grammar.** Every OOD case must be parseable by B3's bounded grammar. Out-of-grammar cases are adversarial-territory (obligation #8), not OOD-territory. If a case refuses, it's a dataset bug — fix the case or drop it; don't relax the OOD framing.
- **Pack-aligned substitutions.** Every unit noun consults `en_units_v1` — never invent surface units. Entity names follow B3's existing capitalized-proper-noun convention.
- **No semantic perturbations.** OOD ≠ perturbation. Don't change values, don't swap operations, don't break invariants. Surface only (entity / unit / surface-order).
- **Gate at 0.95 pinned.** Changing the threshold requires a new ADR.
- **`wrong == 0` on the OOD set** (separate gate from the ratio; both must hold).
- **Determinism**: same OOD cases produce byte-equal report.
- **No solver / parser / pack changes.** This is pure evaluation substrate.
- **No new modules under `algebra/`, `chat/`, `core/cognition/`.** New module lives under `core/capability/`.

**Out of scope:**
- B1 (symbolic equivalence) + B2 (teaching corpus) OOD equivalents — separate sub-ADRs (mirror PR #189's structure).
- Cross-grammar fuzzing (paraphrases beyond the grammar) — that's adversarial obligation #8 (main agent is on this in parallel).
- ADR-0114a obligations #5 (perturbation, your L14), #6 (depth curve, PR #190), #8 (adversarial, main agent). Don't bundle.
- Composite-gate or promotion-gate wiring.

**Target branch.** PR against `main`. Title: `feat(ADR-0114a.2): OOD-ratio auditor — Obligation #2 wired for B3, ratio=<X.XX>`. Body: case count, family breakdown (entity / unit / order variance), public accuracy + OOD accuracy + computed ratio, link to ADR, plus an honest scope-limit if the substitution pool is smaller than ideal (deferred items go to a follow-up).

**Exit criterion.** CI green; OOD runner exits 0 with `wrong == 0`; auditor exits 0 with `ratio ≥ 0.95`; B3 public lane unchanged; obligations #10 + #6 + #5 still pass (no cross-PR breakage); ADR-0114a.2 included.

**Only run tests that exercise files you change plus the B3 public lane, the OOD lane, and the obligation-#10 / #5 / #6 auditors.** Do not run the full suite — that's the lead's job at integration.

**Do not stack on another agent's branch.** Target main directly. Note: PR #190 (obligation #6) and the main agent's #8 PR will land in parallel — no merge order needed unless `core/cli.py` conflicts arise, in which case the same "keep both sibling commands" resolution from PR #189 applies.
