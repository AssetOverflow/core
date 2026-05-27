# Wave-Next — Recognizer Injectors + Lexical Closure + CompositionClaim Scoping

**Date:** 2026-05-27
**Goal:** Lift GSM8K `correct` from 3 → 10+ (ADR-0163 Round-1 gate)
via the recognizer-injector path identified in the post-eval analysis.
**Risk profile:** Low. Each brief is a focused single-category injector
with explicit `wrong=0` pinning. Composition / Frame work is deferred
to subsequent waves with their own ADRs.

---

## Operator pool (as of 2026-05-27)

- **Sonnet 4.6** — workhorse for mechanical injector work; can run 3+ parallel agents
- **Opus 4.6/4.7** — deepest reasoning; reserved for briefs with real design calls
- **Gemini** — long-context surveys only (per `feedback-parallel-dispatch-pattern`)
- **GitHub Copilot** — held in reserve; less proven for this workflow
- **Codex** — OFFLINE (rate limits, several days)

---

## Dispatch timeline

### Gate 1 — cascade complete

**Wait for #362 → #363 → #364 → #365 → #366 to all merge.** That puts on `main`:
- partition-test behavioral invariant (#362) — unblocks future ADR-0167 PRs
- domain-aware contemplation routing (#363) — partitions cognition vs math
- ADR-0168 FrameClaim scoping (#364) — names the next major sub-type ADR
- ADR-0168.1 adapter bridge (#365) — resolves the ADR-0057 evidence floor tension
- DCS injector spec (#366) — the methodology document A1–A4 reference

Verify the cascade with `git fetch origin main && git log origin/main --oneline -6`.

### Gate 2 — dispatch the parallel injector wave

**Single message → 4 parallel Agent calls:**

| Order | Brief | Operator | Branch |
|---|---|---|---|
| 1 | A1 currency_amount injector | Sonnet | `feat/injector-currency-amount` |
| 2 | A3 multiplicative_aggregation injector | Sonnet | `feat/injector-multiplicative-aggregation` |
| 3 | A4 temporal_aggregation injector | Sonnet | `feat/injector-temporal-aggregation` |
| 4 | A2 rate_with_currency injector | Opus | `feat/injector-rate-with-currency` |

All 4 touch `generate/recognizer_anchor_inject.py`. First to push opens
clean; the other 3 need a union-merge rebase. Each rebase is trivial
(adding a function + a dispatch-table line).

**In parallel with that wave**, the orchestrator (me) handles **B1**
inline — too small to dispatch.

### Gate 3 — sequential after the injector wave settles

| Brief | Operator | Branch |
|---|---|---|
| D1 ADR-0169 CompositionClaim scoping | Opus | `docs/adr-0169-compositionclaim-scoping` |

D1 is docs-only, no code conflicts. Can technically run in parallel
with the injector wave; sequencing it after lets Opus give A2 full
attention first.

### Gate 4 — optional background research

| Brief | Operator | Branch |
|---|---|---|
| GPT-5.5 dispatch Task 3 (recognizer registry audit) | Gemini | `docs/gemini-recognizer-registry-audit` |

Pure long-context survey of all 7 ratified recognizers. No code, no
risk. Informs future injector PRs. Run if you want background research
while the injector wave executes; skip if you don't want the noise.

---

## Shared constraints (every brief inherits these)

- Open a dedicated `git worktree add` (parallel-agent worktree rule)
- Branch off **current `main`** after Gate 1 confirms the cascade is in
- `wrong == 0` non-negotiable — verify against case `gsm8k-train-sample-v1-0050`
  in every test suite
- ADR-0166 — no new canonical eval lanes; reuse `gsm8k_math/train_sample/v1`
- No teaching-store / pack mutation as a side effect of injector work
- `uv venv` / `uv pip install` / `uv run` — never `--break-system-packages`
- Stage explicit files; never `git add -A`; NEVER commit `engine_state/`
- Each PR runs the full regression suite (see Validation block per brief)
- CLAUDE.md §"Documentation Discipline" — pure markdown, no standalone HTML
- CLAUDE.md §"Schema-Defined Proof Obligations" — every new injector
  must come with a test that can meaningfully fail under the wrong=0
  violations the injector is written to catch

---

## A1 — `currency_amount` injector

**Recommended operator:** Sonnet 4.6
**Branch:** `feat/injector-currency-amount`
**Expected lift:** 2–4 cases (4 currently refused as `currency_amount`)
**Blocked by:** Gate 1 (cascade complete)

### Context to read first

- `generate/recognizer_anchor_inject.py:79` — `inject_discrete_count_statement`
  (the existing template; do not reuse logic, just shape)
- `generate/recognizer_match.py` — the `currency_amount` match logic
- `engine_state/recognizers.jsonl` (read-only) — the ratified
  `currency_amount` canonical pattern
- `docs/handoff/discrete_count_statement-injector-spec.md` (post-#366)
  — the methodology for "narrow first, broaden later"
- `evals/gsm8k_math/train_sample/v1/report.json` — filter for
  `category=currency_amount`; these are the 4 cases you target
- `evals/gsm8k_math/train_sample/v1/cases.jsonl` — the original problem
  text for each

### Setup

```bash
git worktree add /tmp/wt-a1 -b feat/injector-currency-amount origin/main
cd /tmp/wt-a1
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Deliverables

1. **`generate/recognizer_anchor_inject.py`** — new
   `inject_currency_amount(match) -> tuple[CandidateInitial | CandidateOperation, ...]`
   function. Add entry to the dispatch table at the bottom of the file.
   Must:
   - extract `currency` + `amount` + `entity` from `match.parsed_anchors`
   - emit ONE `CandidateInitial` per match in the narrow canonical form
     `<ProperNoun> has|earns|charges $<amount>`
   - return `()` (preserve refusal) for any shape outside that narrow
     form — broadening is a follow-up PR
   - never emit a `CandidateOperation` (those are FrameClaim territory)
2. **`tests/test_injector_currency_amount.py`** (new) — 8+ tests:
   - happy path: narrow canonical form admits a complete graph
   - sub-shape rejection: 2+ variant shapes the injector deliberately
     skips (must return `()`, not raise)
   - hazard pin: case `gsm8k-train-sample-v1-0050` remains refused at
     `sentence_index=0`
   - determinism: same `RecognizerMatch` → byte-identical injector output
   - wrong=0 invariant: any admitted graph passes
     `assert_graph_complete` and the existing solver's verifier
3. **Eval delta artifact** — append a new section to
   `evals/gsm8k_math/train_sample/v1/audit_brief_11.md` documenting:
   - which N cases moved from `currency_amount` refusal to admission
   - which cases remained refused on a different bottleneck class
   - confirmation that `wrong` count remains 0

### Hard constraints

- The narrow form is non-negotiable. **Do not** match comparatives,
  rate compositions, or multi-currency arithmetic in this PR
- Reject any shape where the entity is anonymous (`The store earns ...`
  vs `Sam earns ...`)
- Manifest checksums unchanged (no pack file edits)
- Reader path remains the priority — flag-on reader still runs before
  recognizer; this injector only fires on reader refusal

### Verification

```bash
uv run pytest tests/test_injector_currency_amount.py -q
uv run pytest tests/test_brief_11b_audit_artifact.py tests/test_brief_11b_step2_lexicon.py tests/test_recognizer_skip_wrong_zero.py -q
uv run pytest tests/ -k "teaching or contemplation or candidate or correction or store or review" -q
PYTHONPATH=. uv run python evals/gsm8k_math/train_sample/v1/runner.py
```

Capture the before/after `report.json` counts in the PR body.

### PR body must include

- Before/after refusal taxonomy for the `currency_amount` row
- Case-by-case verdict for the 4 currently-refused cases (admitted /
  refused-on-different-class)
- Explicit case 0050 hazard verification line
- `wrong=0` invariant statement

### Report back

- PR URL
- Lift count (cases moved from refused → admitted)
- Hazard pin evidence
- Any sub-shapes you noticed that need follow-up injector PRs

---

## A2 — `rate_with_currency` injector

**Recommended operator:** Opus 4.6/4.7
**Branch:** `feat/injector-rate-with-currency`
**Expected lift:** 1–3 cases (3 currently refused)
**Blocked by:** Gate 1

### Why Opus instead of Sonnet

This brief has a real schema decision: does the existing
`Quantity` type in `generate/math_problem_graph.py` structurally model
a per-unit rate? If yes, the injector emits a `Rate`-shaped
`CandidateInitial` analogous to A1. If no, the injector must
**explicitly refuse** rather than invent a new type — flag for
follow-up. That decision needs judgment, not pattern-matching.

### Setup, context, deliverables, hard constraints

Identical structure to A1, but for `rate_with_currency`. Canonical
narrow form: `<ProperNoun> earns|charges|pays $<amount> per <unit>` or
`<ProperNoun> earns|charges|pays $<amount> for <unit>`.

Specific differences from A1:

- Check `generate/math_problem_graph.py` for the `Quantity` type
  structure; if it doesn't model rates, the injector returns `()`
  and the PR body writes an explicit follow-up note
- If `Quantity` does model rates (e.g. via a composite unit or a
  separate `Rate` type), use that — DO NOT invent a new type
- Hazard pin: case 0050 still refused

### Report back must include

- The schema decision (does `Quantity` model rates?) and your evidence
- If "no," the follow-up note for whoever ships the `Rate` schema
  extension
- Lift count (will be 0 if schema decision is "no" — that's still a
  successful PR; documenting the gap is the deliverable)

---

## A3 — `multiplicative_aggregation` injector

**Recommended operator:** Sonnet 4.6
**Branch:** `feat/injector-multiplicative-aggregation`
**Expected lift:** 2–4 cases (5 currently refused)
**Blocked by:** Gate 1

### Why this needs care

This is the **first injector that emits `CandidateOperation`** (not
just `CandidateInitial`). Multiplicative operations widen the case
0050 hazard surface — if the operand isn't the right unit, the
solver computes a wrong product.

### Canonical narrow form

`<ProperNoun> has <count> <noun> in each <container>` or
`<count> <noun> per <container>`. The injector emits a
`CandidateOperation` of kind `multiply` when the count, noun, and
container all extract cleanly from `parsed_anchors`.

### Extra hazard pinning (beyond A1's spec)

Reject any shape where:
- the container isn't a `count_unit_noun`
- the multiplier isn't a determinate integer or word-form integer
- the result unit doesn't match the original count unit

The `tests/test_injector_multiplicative_aggregation.py` must include
a parameterized test confirming each of those rejection paths
returns `()` rather than admitting a wrong-product graph.

### Otherwise identical to A1's structure

Same deliverables, hard constraints, verification, PR body, report-back.

---

## A4 — `temporal_aggregation` injector

**Recommended operator:** Sonnet 4.6
**Branch:** `feat/injector-temporal-aggregation`
**Expected lift:** 1–2 cases (2 currently refused)
**Blocked by:** Gate 1

### Why this is the structural sanity check

Smallest injector in the wave. If a focused PR can lift the 2 cases,
the recognizer-injector pattern is operational and the larger sub-shape
work (especially DCS sub-shapes) can follow with confidence.

### Canonical narrow form

`<count> <time_unit> per <time_unit>` (e.g. `5 hours per day`,
`3 days per week`). Emits a `Rate`-shaped or multiplicative-shaped
candidate depending on context.

### Coordinate with A3

Both A3 and A4 may produce multiplicative-kind operations. If the
`Quantity`/`Operation` schema doesn't distinguish them cleanly,
flag in the PR body for shared follow-up.

### Otherwise identical to A1's structure

---

## B1 — Lexical-entry closure: remaining 3 cases

**Recommended operator:** Orchestrator (me) — too small to dispatch
**Branch:** `feat/lexicon-closure-wave-3`
**Expected lift:** 1–3 cases
**Blocked by:** Gate 1 (cascade complete)

Three `lexicon_entry` refusals remain after #348:
- case 0001: `+` (arithmetic literal — DO NOT add as drain_token)
- case 0040: `sees` (perception verb — drain_token candidate)
- case 0049: `path` (noun — drain_token candidate)

This is small (12 lines of edits, 3 test additions) and I'll handle
it in-line while the injector wave runs. Decision-making for `+`
documented in PR body (it's a structural issue, not a lexical gap).

---

## D1 — ADR-0169 CompositionClaim scoping

**Recommended operator:** Opus 4.6/4.7
**Branch:** `docs/adr-0169-compositionclaim-scoping`
**Output:** `docs/decisions/ADR-0169-compositionclaim-ratification.md`
**Blocked by:** ADR-0168 (#364) merged — Gate 1
**Sequencing:** Run after A2 lands (Opus needs full attention on A2 first)

### Deliverable shape

A scoping ADR analogous to ADR-0168 (#364), answering the same six
open questions for `CompositionClaim`:

1. Sub-types of CompositionClaim needed?
2. SAFE_CATEGORIES allowlist applicable?
3. Concrete answer to how the ratification prevents the case 0050
   hazard (multi-quantity is exactly the hazard surface — a wrong
   composition rule could admit `5 apples + 3 oranges = 8 things`)
4. Evidence signature normalisation needed
5. Graph completeness gating
6. Ablation test that proves the handler doesn't admit a partial
   composition

Plus ADR-0166 three-question test, plus compatibility audit against
ADR-0056/0057/0114a/0164/0165/0166/0167/0168, plus implementation
wave outline.

### Hard constraints

- Docs-only; no code, no test, no eval, no pack change
- Must explicitly address: "is CompositionClaim safer or riskier than
  FrameClaim?" — argue from data, not intuition
- If "riskier," propose deferring CompositionClaim until FrameClaim
  ships a clean second-sub-type precedent

---

## (Optional) Background research — Gemini recognizer registry audit

**Recommended operator:** Gemini
**Branch:** `docs/gemini-recognizer-registry-audit`
**Output:** `docs/handoff/ratified-recognizer-registry-audit.md`
**Blocked by:** Nothing — pure read-only survey

This is GPT-5.5 dispatch Task 3 from the prior session that wasn't
picked up. Pure long-context audit of all 7 ratified recognizers in
`engine_state/recognizers.jsonl`. Output is a table-driven survey
naming: match-logic precision, injector presence/absence, GSM8K
refusal count, lift potential, hazard class.

Informs future injector PRs. Independent of A1–A4. Skip if you don't
want background research running in parallel.

---

## What this wave does NOT do

- It does not implement `discrete_count_statement` sub-shapes (21
  largest bucket). That's Wave C, informed by #366's spec post-merge.
- It does not implement FrameClaim (Wave E, requires ADR-0168 merged
  AND its own W1-W3 sub-wave).
- It does not add new eval lanes (ADR-0166 still gates).
- It does not touch workbench wiring (ADR-0167 §Q4, deferred).
- It does not propose any non-deterministic / non-decoding mechanism.

## Expected aggregate lift

If A1–A4 all ship cleanly: **6–13 cases lifted** out of the 14
across those four categories. Plus B1: **1–3 cases**.

That puts `correct` at **10–19**, clearing ADR-0163 Round-1
(`correct ≥ 10`) and potentially nudging Round-2 (`correct ≥ 25`).

A2's lift may be 0 if the `Quantity` schema doesn't model rates —
in that case the PR's value is documenting the gap, and the lift
shifts to A3 + A4.

---

## Dispatch protocol summary

```text
1. Wait for cascade #362→#366 (Gate 1)
2. Single message with 4 Agent calls:
   - subagent_type=general-purpose, model=sonnet → A1
   - subagent_type=general-purpose, model=sonnet → A3
   - subagent_type=general-purpose, model=sonnet → A4
   - subagent_type=general-purpose, model=opus → A2
3. Orchestrator handles B1 inline
4. After A2 lands: subagent_type=planner, model=opus → D1
5. (Optional) subagent_type=general-purpose, model=sonnet (or Gemini) → Task 3 audit
```

Each operator gets pointed at this file's section header for their
brief. Shared constraints at the top apply to everyone.
