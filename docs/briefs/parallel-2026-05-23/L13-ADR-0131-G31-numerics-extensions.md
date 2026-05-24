# L13 brief — ADR-0131.G.3.1 — Numerics extensions (fractions + multi-currency + multi-token cardinals + word-num-adjective)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g31-numerics-ext -b feat/adr-0131-g31-numerics-ext origin/main
cd ../core-adr-0131-g31-numerics-ext
```

**Scope.** Follow-up to ADR-0131.G.3 (PR #183) extending literal recognition to the four shapes explicitly deferred in that ADR's "Out of scope, explicitly deferred to G.3.1+" section. The parent ADR's canonical-unit architectural decisions (cent for money via `en_units_v1`, pack-driven not regex-spam, refusal-first) stay absolute — this iteration extends scope inside those constraints, not around them.

**Closed-set scope (this iteration only):**

1. **Fractions end-to-end.** `_resolve_value` in `generate/math_candidate_parser.py` already handles `N/M` token-level (returns float via `Fraction(N,M)`). Land axis cases that exercise fractions through the full pipeline — likely requires widening `_INITIAL_HAS_RE`'s `(?:of|in|for|with) <NP>` substance-qualifier handling so `Bob has 3/4 of a cup.` parses cleanly (the fraction is the value; `of a cup` carries the unit). Closed-set: digit/digit literal with `M > 0`.
2. **Multi-currency.** Extend `_money_unit_normalization` (math_candidate_parser.py) and `_unit_grounds` (math_roundtrip.py, the `"$" in source_span` check) to recognize `¢ € £ ¥ ₱`. Each gets its own canonical unit per `en_units_v1`. **Verify `en_units_v1.lexicon.jsonl` actually contains `euro / pound / yen / peso` before wiring; if any is missing, defer that currency to G.3.2 rather than hardcoding a unit name the pack doesn't recognize.**
3. **Space-separated multi-word cardinals.** `one hundred`, `two thousand five hundred`. `parse_compound_cardinal` in `language_packs/numerics_loader.py` already supports these; the parser's `_VALUE` regex doesn't yet match space-separated sequences because they'd span the unit slot boundary. Either (a) add a separate extractor that pre-passes value-slot whitespace runs through `parse_compound_cardinal`, or (b) widen `_VALUE` to greedily match cardinal-word sequences. **Pick one approach, document the choice in the ADR.**
4. **Word-number-adjective compositions.** `five full boxes` per ADR-0127 substance-qualifier precedent. Adjective inserted between cardinal and unit head noun; treat as part of the unit phrase, not a separate value-slot widening.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.G.3-numerics.md` — the parent; what's already done, what's deferred, the canonical-unit decision you must respect.
2. `docs/decisions/ADR-0127-units-pack-and-units-aware-parser.md` — substance-qualifier precedent for axis 4.

**What to ship:**
- **Parser extensions** in `generate/math_candidate_parser.py` (+ `generate/math_roundtrip.py` for new grounding cases).
- **New axis lane** at `evals/math_capability_axes/G3_numerics/v1.1/` — additive sibling to v1. **Do not modify v1** (`evals/math_capability_axes/G3_numerics/v1/`); it's frozen as the audit-trail artifact for #183. v1.1 carries fresh `cases.jsonl`, `runner.py`, `report.json`.
- **Curated cases:** ≥4 per axis + ≥4 refusal probes pinning what's still out of scope (percentages `50%`, scientific notation `1e3`, locale separators `1,000`, three-decimal money `$1.234`).
- **Tests:** `tests/test_adr_0131_G31_numerics_extensions.py` — per-axis at-least-one passing, refusal probes refuse typed, `wrong == 0`, replay byte-equality, parent v1 lane still passes (no regression).
- **ADR:** `docs/decisions/ADR-0131.G.3.1-numerics-extensions.md` — cite #183 parent + ADR-0127 substance-qualifier precedent. Document the axis-3 approach choice (extractor vs `_VALUE` widening).
- **Refresh** `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json` — fractions or compound cardinals may now unlock some GSM8K cases.

**Hard constraints:**
- **`wrong == 0`** on the v1.1 axis lane AND the GSM8K probe.
- **Pack-driven, not regex-spam.** Every recognized literal traces to `en_numerics_v1` or `en_units_v1`. No inline alternations for things the pack should own.
- **`en_units_v1.canonical_unit` precedence stays absolute** (cent for money, etc.) — same architectural decision G.3 set. New currencies normalize to their pack-pinned canonical unit; do not invent surface units.
- **Closed set per axis.** Refusal probes prove the boundary. If a paraphrase isn't in the closed set, it must refuse, not coerce.
- **Determinism:** `v1.1/report.json` byte-equal across runs.
- **No solver / binding-graph changes.** If a fraction parses but doesn't solve through, file a follow-up ADR; don't stub the solver.
- **Don't modify v1.** It's the audit-trail artifact for #183 and stays frozen.
- **Field invariant untouched.** No changes to `algebra/`, `chat/`, `core/`.

**Out of scope (do not touch):**
- Percentages, scientific notation, locale separators, three-decimal money (these become refusal-probe cases — closed-set boundary).
- ADR-0131.4 promotion-gate wiring (main agent's parallel work).
- Anything in `algebra/`, `chat/`, `core/`.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.G.3.1): numerics extensions (fractions + multi-currency + multi-token cardinals + word-num-adjective) — axis lane N/N`. Body: per-axis case counts, currencies actually wired (vs. deferred to G.3.2 because missing from pack), axis-3 approach choice + rationale, link to ADR, GSM8K probe delta if any (admission may or may not move depending on which cases the extensions unlock).

**Exit criterion.** CI green; v1.1 axis runner exits 0 with `wrong == 0`; v1 lane unchanged; GSM8K probe `admitted_wrong == 0` preserved.

**Only run tests that exercise files you change plus the axis lane + GSM8K probe + the parent v1 lane.** Do not run the full suite — that's the lead's job at integration.

**Do not stack on another agent's branch.** Target main directly.
