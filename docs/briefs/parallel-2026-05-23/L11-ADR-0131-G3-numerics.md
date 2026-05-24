# L11 brief — ADR-0131.G.3 — Capability axis: numeric literals (money, fractions, compound numbers)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g3-numerics -b feat/adr-0131-g3-numerics origin/main
cd ../core-adr-0131-g3-numerics
```

**Scope.** Capability-axis iteration: extend the parser's `<value>` slot to recognize numeric literal shapes that the baseline refuses on, by **consuming the existing `en_numerics_v1` pack** (ADR-0128) — *not* by hard-coding new regexes inline. The baseline `refused_reasons_top` shows clauses like `Tina makes $18.00 an hour`, `Aaron and his brother Carson each saved up $40`, `In one hour, Addison mountain's temperature will decrease to 3/4 of its temp…`, `Mandy started reading books with only 8 pages` (compound), `Allison … uploads 10 one-hour videos` (hyphenated compound), `Francine has five full boxes of crayons and 5 loose crayons` (word-number + adjective + bag-quantifier).

Target literal classes (closed set, drawn from `en_numerics_v1`):

- **Money:** `$N`, `$N.NN`, `N dollars`, `N cents`. Currency symbol → unit lift via `en_units_v1`.
- **Fractions:** `N/M`, `N/M of <X>`, plus word forms already in `en_numerics_v1` (`one-half`, `three-quarters`).
- **Word-number compositions:** `five full boxes` — number + adjective + unit. Adjective is part of the unit phrase (`full boxes` ≢ `boxes`) per ADR-0127 substance-qualifier precedent.
- **Hyphenated compound numerics:** `one-hour`, `10 one-hour` — adjectival numeric modifying a head noun.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.G-gsm8k-coverage-probe.md` — iteration discipline.
2. `docs/decisions/ADR-0127-units-pack-and-units-aware-parser.md` + `docs/decisions/ADR-0128-numerics-pack.md` — the packs that already exist; the work is **consuming them at the parser layer**, not extending them.

**What to ship:**
- **Parser extension** in `generate/math_candidate_parser.py`: widen the value-slot matcher to consult `en_numerics_v1.lexicon` (money + fraction + compound forms) before falling back to the existing integer/word-number regex. Currency-symbol → unit promotion routes through the `en_units_v1` resolver. The pack lookup is **deterministic, ordered, and cached** at parser-construction time; no I/O on hot path.
- **Curated coverage cases** at `evals/math_capability_axes/G3_numerics/v1/cases.jsonl` (~25): ≥5 per literal class + ≥5 refusal probes (e.g. `$N.NNNN` with too many decimals, fractions like `N/0`, ambiguous hyphenations like `one-hour-old`). Refusal probes pin the scope.
- **Runner + report** at `evals/math_capability_axes/G3_numerics/v1/`.
- **Tests** at `tests/test_adr_0131_G3_numerics.py` (~12): per-literal-class at-least-one passing, refusal probes all refuse typed, `wrong == 0`, replay byte-equality, **GSM8K probe re-run with admission strictly increases OR money/fraction-shape refusals strictly decrease** (declare in ADR, gate on it).
- **ADR** `docs/decisions/ADR-0131.G.3-numerics.md`. Cite ADR-0127/0128 packs; document the closed literal classes; pin currency-symbol → unit mapping; list every deferred shape.
- **Refresh** `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json`.

**Hard constraints:**
- **Pack-driven, not regex-spam.** Every recognized literal must trace to an entry in `en_numerics_v1` (or to the existing integer/word-number regex). No silent inline alternations.
- **`wrong == 0`** on the new axis and the probe. If a fraction `N/0` slips through and the solver divides — that's a parser bug, fix the parser, do not weaken the verifier.
- **Currency → unit composition** is deterministic. `$18.00` parses as `value=18.00, unit=USD` (or whatever `en_units_v1` canonical id is) — pin the exact unit id in the ADR and assert in tests.
- **Scope is literals only.** "Each saved up $40" is in scope for the literal `$40`; the distributive-subject "each" is **out of scope** and routes to L12/G.4. The case may still refuse on the distributive — that's correct, and it should refuse with a **non-literal** reason (the literal layer succeeded).
- **No new modules under `algebra/`, `chat/`, `core/`.** No changes to packs themselves (consumption, not extension).
- **Determinism.** Pack lookup ordered; report byte-equal across runs.

**Out of scope:** verb classes (L9/G.1), comparatives (L10/G.2), multi-clause / distributive subjects (L12/G.4), percentages (`30%`), scientific notation, locale-specific separators.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.G.3): numeric literals (money + fractions + compounds) — admission N/50 (Δ+N)`. Body: per-literal-class case counts, currency-symbol unit-id mapping, admission or refusal-family delta, link to ADR.

**Exit criterion.** CI green; numerics runner exits 0 with `wrong == 0`; chosen GSM8K-probe gate satisfied; B3 + L9/G.1 + L10/G.2 lanes unchanged; refreshed coverage report committed.

**Do not stack on another agent's branch.** Target main directly.
