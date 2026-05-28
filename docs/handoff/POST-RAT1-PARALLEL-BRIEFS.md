# Post-RAT-1 Parallel Briefs (B, C, D, E)

**Date:** 2026-05-27
**Author:** Shay
**Context:** Following the architecture audit (RAT-1 / PR #406), five components are structurally underbuilt. **A (the 4 missing injectors) is in flight as its own PR by Opus**. The remaining four are parallel-safe and each can be dispatched to its own operator.

Each brief below is self-contained, copy-paste-runnable.

---

## Brief B — Make math contemplation produce **ratifiable** claims

**Operator profile:** Opus (load-bearing — the claim shape is what an operator ratifies; getting it wrong is operator-burden risk)
**Branch:** `feat/contemplation-ratifiable-claims`
**Base:** `origin/main`
**Estimated effort:** medium

### Why

Currently `core eval math-contemplation` produces proposals whose `proposed_change_payload` is:
```json
{"evidence_count": 8, "group_key": {...}, "modal_sub_type": "composition"}
```

This is evidence aggregation, not a ratifiable claim. The operator has to **design the claim from scratch** (pick a `surface_pattern`, pick a `composition_category`, pick a `polarity`) before calling `apply_composition_claim()`. The "operator just reviews" framing is misleading.

### Outcome

Make `teaching/math_contemplation.py::decompose_audit` (and the dispatcher in `teaching/math_contemplation_proposal.py`) emit proposals where `proposed_change_payload` carries:

```json
{
  "surface_pattern": "bound(count) × bound(unit_cost)",
  "composition_category": "multiplicative_composition",
  "polarity": "affirms",
  "evidence_count": 8,
  "group_key": {...},
  "modal_sub_type": "composition"
}
```

— directly ratifiable by `apply_composition_claim()` with no operator-side design step.

For `proposed_change_kind == "composition_reclassification"`, dispatch by `missing_operator`:
- `quantity_extraction` → `multiplicative_composition` + `bound(count) × bound(unit_cost)` (currency-per-unit shape)
- `multi_quantity_composition` → `additive_composition` + `bound(qty_a) + bound(qty_b)` (default; operator may edit)

For `frame_reclassification`, `matcher_extension`, `injector_sub_shape` — keep current payload (those are still upstream of ratifiable claims).

### Reads required FIRST

- `teaching/math_contemplation.py::decompose_audit`
- `teaching/math_contemplation_proposal.py` (proposal schema)
- `teaching/math_composition_proposal.py::SAFE_COMPOSITION_CATEGORIES`
- `teaching/math_composition_ratification.py::apply_composition_claim` signature

### Hard requirements

- Backward-compatible JSONL: existing tests that read evidence_count + group_key + modal_sub_type must still pass
- Only `composition_reclassification` proposals get the enriched payload in v1 (frame/matcher/injector deferred)
- `polarity` is always `"affirms"` (the audit row signals a real refusal — the operator can override to `"falsifies"` if needed)
- `surface_pattern` must be in the operator's expected vocabulary (mirror the three SAFE patterns)
- An end-to-end test that runs `core eval math-contemplation` then immediately feeds the first composition proposal into `apply_composition_claim()` without any field synthesis

### Tests

- `tests/test_contemplation_ratifiable_payload.py`:
  - 5+ test cases: each refusal pair yields a payload whose fields satisfy `apply_composition_claim`'s preconditions
  - Round-trip: proposal payload → ratification → no exception
  - Schema regression: existing fields still present
- `tests/test_adr_0172_w2_decomposer.py` — update existing assertions

### Truth test

After this PR + a fresh `core eval math-contemplation`, the operator workflow becomes:
```
core eval math-contemplation
core teaching review <composition-proposal-id> --accept --review-date YYYY-MM-DD
```
**without manually constructing a `MathReaderRefusalEvidence` or picking a category.**

---

## Brief C — Comprehension reader audit + decision

**Operator profile:** Sonnet (investigation + documentation; minor wiring if needed)
**Branch:** `docs/comprehension-reader-audit`
**Base:** `origin/main`
**Estimated effort:** small (investigation) — could escalate to medium if "operationalize" is chosen

### Why

The comprehension reader (`generate/comprehension/lifecycle.py` — `begin_sentence`, `apply_word`, `end_sentence`, `finalize`, `ProblemReadingState`, `EntityRef`, Phase 1/2 of ADR-0164) is substantial code that **admits zero cases in the math eval**.

Direct measurement:
```
core eval gsm8k_math --split public --use-reader → 150/150 wrong=0 (same as without)
train_sample --use-reader → 3/47/0 (same as without)
```

The reader exists but contributes nothing observable. Two possible truths:
1. **It's load-bearing for something we don't measure** (cognition lane? semantic recall? answer rendering?)
2. **It's a parallel R&D track that needs honest naming** as not-yet-operational on math

### Outcome (investigation phase)

Produce `docs/handoff/COMPREHENSION-READER-AUDIT.md` answering:

1. Where in the live code path does `_try_comprehension_reader` actually run? Trace every caller.
2. When `comprehension_reader_questions=True`, what specifically does the reader admit on the cognition eval lane (not just math)?
3. Is the all-or-nothing discipline (one refusing sentence kills the whole reader path) the bottleneck on math? Or is the reader itself refusing on simple shapes?
4. Are there ADR-0164 Phase 1/2 promises that aren't being honored?
5. List 3 options:
   - **Operationalize**: change all-or-nothing → per-sentence so reader can contribute partial admissions
   - **Relabel**: honest doc update naming reader as "cognition track, not math substrate" (if true)
   - **Retire**: if the reader path duplicates capability that the regex/recognizer paths already provide

### Hard requirements

- No code changes in the investigation phase — pure read + doc
- Audit must distinguish reader-on-math vs reader-on-cognition usage
- Recommendation must be falsifiable (provide a measurable test for each option)
- If "operationalize" is chosen, ship as separate PR after operator approval

### Tests

- None in audit phase. Implementation phase (if approved): operationalize path requires its own test plan.

### Truth test

After this brief: the project has a deliberate answer to "what does the comprehension reader do today, and what should it do?" Right now nobody knows. That's the bug being closed.

---

## Brief D — `core teaching coverage` CLI

**Operator profile:** Sonnet (tight-scope CLI; mechanical aggregation)
**Branch:** `feat/teaching-coverage-cli`
**Base:** `origin/main`
**Estimated effort:** small

### Why

There's no automated way to answer "given the current ratified state, what % of train_sample admits / refuses / wrong-counts by ShapeCategory?" We only see deltas by running the eval manually and eyeballing report.json. Flying blind on operator dispatch decisions.

### Outcome

New CLI: `core teaching coverage [--lane gsm8k_math] [--split train_sample] [--use-reader] [--json]`

Behavior:
1. Run the lane's runner if its report.json is stale (or always, if `--run`)
2. Read the per-case verdict + refusal reasons
3. Bin by:
   - `correct / refused / wrong`
   - Within refused: by `(refusal_mode, ShapeCategory)` — using the same categorization the position paper §4 table uses
4. Emit a clean histogram with deltas vs the **last committed** report.json

Example output:
```
Lane: gsm8k_math/train_sample/v1 (use_reader=true)
Counts: correct=3 refused=47 wrong=0  (Δ from prior: 0 / 0 / 0)

Refusal taxonomy:
  21  recognizer_empty_injection(discrete_count_statement)
  10  no_admissible_candidate
   5  recognizer_empty_injection(multiplicative_aggregation)
   4  recognizer_empty_injection(currency_amount)
   3  recognizer_empty_injection(rate_with_currency)
   2  recognizer_empty_injection(temporal_aggregation)
   2  recognizer_empty_injection(descriptive_setup_no_quantity)

Wrong=0: ✓
Case 0050 hazard pin: refused ✓
```

### Reads required FIRST

- `evals/gsm8k_math/train_sample/v1/runner.py`
- `evals/gsm8k_math/train_sample/v1/report.json` schema
- `core/cli.py` existing teaching subcommands
- `evals/refusal_taxonomy/shape_categories.py`

### Hard requirements

- Read-only (no eval lane mutation)
- Delta comparison against the most recent **committed** report.json (uses `git show HEAD:evals/.../report.json` — if absent, no delta)
- `--json` for CI integration
- `--lane` defaults to `gsm8k_math`; `--split` defaults to `train_sample`
- Refusal taxonomy is regex-pulled from `report.json[per_case][].reason` — no hardcoded category list
- Exit code 0 on success regardless of counts (it's a report, not a gate)

### Tests

- `tests/test_teaching_coverage_cli.py`:
  - Fixture report.json with known counts → expected histogram
  - Delta path: stage old + new report → expected delta
  - `--json` schema
  - Empty/malformed report.json → clear error

### Truth test

After dispatch: every operator can run `core teaching coverage` after any ratification to see exactly which refusal modes their work moved (or didn't).

---

## Brief E — Lexical ratification auto-compile

**Operator profile:** Codex (tiny mechanical; mirror RAT-1's pattern)
**Branch:** `feat/lexical-ratification-auto-compile`
**Base:** `origin/main`
**Estimated effort:** tiny

### Why

RAT-1 (PR #406) added `compile_pack()` auto-call at the end of `apply_frame_claim` + `apply_composition_claim` so source-file writes immediately reach the runtime. **`apply_lexical_claim` was deliberately skipped** because the existing `language_packs/compiler.py` already compiles `lexicon.jsonl`. But the lexicon compiler runs at pack-build time, not after a runtime ratification.

So today: `core teaching` ratifies a LexicalClaim → writes `lexicon/{category}.jsonl` → the **next runtime turn doesn't see it** because nothing triggers re-compile + manifest update.

### Outcome

Extend `teaching/math_lexical_ratification.py::apply_lexical_claim` to call `compile_pack()` at the end of a successful ratification — same pattern RAT-1 used for frame + composition.

Plus: ensure `compile_pack()` regenerates the lexicon compiled artifact `lexicon.jsonl` AND updates `manifest.checksum`. Currently RAT-1's `compile_pack` only handles frames + compositions; this brief extends it.

### Reads required FIRST

- `teaching/math_lexical_ratification.py::apply_lexical_claim`
- `language_packs/compile_pack.py` (the RAT-1 helper)
- `language_packs/compiler.py::_load_pack_cached` (existing lexicon compile)
- `generate/comprehension/lexicon.py::load_lexicon` (the runtime consumer)

### Hard requirements

- `wrong == 0` preserved (no test moves wrong)
- The existing lexicon checksum SCHEME stays the same — just regenerated more frequently
- Mirror RAT-1's `tests/test_math_{frame,composition}_ratification.py` update — `test_lexicon_checksum_preserved_by_lexical_ratification` (manifest may change; lexicon checksum re-derives from compiled bytes)
- Idempotent: running ratification twice doesn't bump checksum unless source bytes changed
- Existing `core teaching compile-pack` command should pick up lexical changes too — extend the receipt to include `lexicon_checksum` + `lexicon_bytes_written`

### Tests

- `tests/test_lexical_ratification_auto_compile.py`:
  - Ratify a LexicalClaim → compile fires → lexicon registry reload sees the new entry
  - Idempotent: second ratify with same evidence → no compile mutation
  - Lexicon-checksum-preserved-across-ratify (with new bytes)

### Truth test

After this PR: a LexicalClaim ratification reaches the runtime within one turn, matching the frame + composition discipline RAT-1 established.

---

## Dispatch DAG

```
RAT-1 (PR #406) — base for all four briefs
       │
       ├──── A (Opus, in-flight) — 4 missing injectors
       │
       ├──── B (Opus) — contemplation ratifiable claims
       │
       ├──── C (Sonnet) — comprehension reader audit
       │
       ├──── D (Sonnet) — coverage CLI
       │
       └──── E (Codex) — lexical auto-compile (tiny)
```

All four briefs are parallel-safe — no shared file conflicts. Each touches different modules.

## Anti-regression invariants (all four)

- `wrong == 0` on `core eval gsm8k_math --split public` preserved (150/150)
- Case 0050 hazard pin holds
- `engine_state/*` never committed
- ADR-0166 — no new eval lanes

## Memory pointers

- [[milestone-me1-me5-matcher-extensions-complete]] — the wave that exposed the gaps
- [[project-ratification-consumption-gap-2026-05-27]] — the original finding
- [[feedback-ratify-vs-consume-loop-closure]] — the general pattern

---

## Copy-paste dispatch (per brief)

```text
# Brief B
Read docs/handoff/POST-RAT1-PARALLEL-BRIEFS.md §"Brief B".
git fetch origin main && git worktree add /tmp/wt-brief-b origin/main && cd /tmp/wt-brief-b && git checkout -b feat/contemplation-ratifiable-claims

# Brief C
Read docs/handoff/POST-RAT1-PARALLEL-BRIEFS.md §"Brief C".
git fetch origin main && git worktree add /tmp/wt-brief-c origin/main && cd /tmp/wt-brief-c && git checkout -b docs/comprehension-reader-audit

# Brief D
Read docs/handoff/POST-RAT1-PARALLEL-BRIEFS.md §"Brief D".
git fetch origin main && git worktree add /tmp/wt-brief-d origin/main && cd /tmp/wt-brief-d && git checkout -b feat/teaching-coverage-cli

# Brief E
Read docs/handoff/POST-RAT1-PARALLEL-BRIEFS.md §"Brief E".
git fetch origin main && git worktree add /tmp/wt-brief-e origin/main && cd /tmp/wt-brief-e && git checkout -b feat/lexical-ratification-auto-compile
```
