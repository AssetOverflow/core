# Parallel work plan — post-GB-3a (2026-05-29)

Dispatch-ready briefs for operators (Opus / Sonnet / Gemini) to run **in parallel
with** Claude's serial Gap-B line. Each brief touches a **disjoint file set** so
PRs cannot conflict. One sub-phase = one PR. Do **not** merge — Claude verifies
(lane-SHA + CLI) and merges.

> **The hard constraint (learned this session):** GB-3b → GB-4 → GB-5 all edit the
> **same** files (`compose.py`, `clauses.py`). They are **serial** — never dispatch
> two of them in parallel. The four ADR-0179 EX PRs each rewrote one file off main
> and cost a full reconciliation. Parallelism is only safe across the *disjoint*
> surfaces below.

The `wrong=0` rule, the sealed/serving boundary, and "no grammar templates"
(ADR-0165) from `docs/handoff/CHATGPT-REMOTE-BRIEF.md` §1/§2/§6 apply verbatim to
all three. Never touch `chat/**`, `generate/math_roundtrip.py`, `algebra/**`,
`field/**`, `vault/**`, CI files, or any currently-green test.

---

## Track A — CP-1 cue-precision ledger substrate (ADR-0177)  ·  Opus/Sonnet

**Files (only):** new package `generate/cue_precision/` (e.g. `ledger.py`) + new
`tests/test_adr_0177_cp1_ledger.py`. **Read:** `docs/decisions/ADR-0177-cue-precision-learning.md`
§"Sub-phases" CP-1, and `core/reliability_gate/ledger.py` (mirror its `ClassTally`
counts-only, refusals-excluded discipline).

**Scope:** the `(cue, op, unit_shape)` ledger + credit assignment **mechanism only**
— record per-pattern committed/correct counts from gold-checked practice chains.
**Do not wire it into the gate or any scorer** (that is CP-2). No reliability-based
resolution (CP-3). It is inert substrate with tests, exactly like
`core/reliability_gate/` shipped before its consumer.

**Acceptance:** deterministic; counts-only (no float thresholds invented);
refusals never counted as commitments; serving untouched; the package is imported
by nothing outside its own tests.

**Dispatch:** `Read docs/handoff/PARALLEL-WORK-PLAN-2026-05-29.md, do Track A (CP-1 ledger substrate) exactly as written. New generate/cue_precision/ package + its test only. Inert (no gate/scorer wiring). One PR. Do not merge.`

---

## Track B — scale the sealed practice case set (ADR-0163 §F)  ·  Sonnet/Codex

**Files (only):** `evals/gsm8k_math/practice/**` data/case files (and a loader if
one is needed) — **not** `train_sample/v1/cases.jsonl` (that is the pinned serving
lane; do not touch it). **Read:** `evals/gsm8k_math/README.md`,
`evals/gsm8k_math/practice/v1/runner.py`.

**Scope:** add more GSM8K practice cases (additive only) so the practice/learning
signal has volume — 50 is mechanism-demonstration, not enough for cue-precision to
learn. Pure data + scoring; the sealed lane gold-checks attempts, so more cases
can only add eliminations/correct, never a *served* wrong.

**Acceptance:** deterministic ordering; cases are well-formed (id/question/answer);
the serving `train_sample` lane and its pinned SHA are **untouched**; `build_search_report`
still runs. State the new case count in the PR body.

**Dispatch:** `Read docs/handoff/PARALLEL-WORK-PLAN-2026-05-29.md, do Track B (scale the practice case set) exactly as written. Only evals/gsm8k_math/practice/** ; never touch train_sample. Additive. One PR. Do not merge.`

---

## Track C — EX-3 redo: tight multi-word units (ADR-0179)  ·  Sonnet (or Gemini research)

**Files (only):** `generate/derivation/extract.py` + `tests/test_adr_0179_extract.py`.
**Read:** `docs/handoff/AUDIT-ADR-0179-EX-RECONCILE.md` §"Why EX-3 was deferred"
(the exact trap), and the `extract.py` module docstring.

**Scope:** a **tight** multi-word-unit rule that does **not** cross connectives and
does **not** regress GB-2. The deferred greedy version read `"6 apples and 4 apples"`
as unit `"apples and"` and broke `test_same_unit_list_sums`. The replacement must:
(a) keep `"12 jumping jacks"` → `"jumping jacks"` only where tight; (b) leave
`"6 apples and 4 apples"` as two `apples` quantities; (c) keep **every** test in
`test_adr_0178_gb1_clauses.py`, `test_adr_0178_gb2_compose.py`,
`test_adr_0178_gb3_referent_guard.py`, `test_adr_0179_extract.py` green. If no rule
satisfies all of (a)–(c) without a grammar template, **write a note and ship no
code** — a refusal is fine.

**Acceptance:** all listed test files stay green; lexeme-level only (ADR-0165);
serving untouched. *Safe to run alongside GB-3b: Gap-B edits `compose.py`/`clauses.py`,
not `extract.py`.*

**Dispatch:** `Read docs/handoff/PARALLEL-WORK-PLAN-2026-05-29.md, do Track C (tight multi-word units) exactly as written. Only extract.py + its test. Must not regress any GB-1/2/3 test. If impossible without a grammar template, write a note and ship no code. One PR. Do not merge.`

---

## What Claude keeps (serial, do NOT dispatch)

GB-3b (cross-clause chaining consuming GB-1, referent-safe) → GB-4 (held
hypotheses + eliminate) → GB-5 (DAG/0033-class). All on `compose.py`/`clauses.py`,
all `wrong=0`-critical. One at a time.
