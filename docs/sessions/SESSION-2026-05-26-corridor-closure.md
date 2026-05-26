# Session 2026-05-26 — Corridor Closure: First Measurable Lift on GSM8K

**Status:** Complete ✓
**Closed:** 2026-05-26 (evening PST)
**Headline:** Closed the math architecture corridor end-to-end (Phase A → B → C → D + operator ratification) and produced the first non-zero `correct` count on the GSM8K train_sample baseline.  Shipped the Workbench UI shell + chat surface concurrently.

---

## TL;DR

**14 PRs merged + 1 issue filed in a single session.**  The math architecture went from `0/50/0` (zero correct, fifty refused, zero wrong) to **`3/47/0` — the first lift the engine has ever produced on GSM8K — with the `wrong = 0` invariant preserved by construction at every step.**  The Workbench went from "doctrine only" to "fully operational end-to-end" (read-only API + design substrate + frontend shell + live chat surface with trace drawer).

The day demonstrated that the **"decodes, not generates" thesis is actionable as a corridor**: operator-authored exemplars → engine-derived recognizers → operator ratification → measurable admissibility lift, with no algebra changes, no pack mutations, no hidden normalization.

---

## Merged PRs (in chronological order)

| # | Title | SHA |
|---|---|---|
| #288 | chore(contemplation): CI run 2026-05-26T103018Z | `ddb94d3` |
| #290 | fix(W-025): polish contemplation-quality eval lane follow-ups | `8829529` |
| #291 | docs(L11): ADR-0161 — HITL async queue (proposed) | `0909ef2` |
| #292 | feat(W-026): read-only workbench API (ADR-0160 Phase 1) | `8a24ebe` |
| #293 | docs(workbench): ADR-0162 — Workbench Design System v1 (proposed) | `8a24256` |
| #294 | docs(math): ADR-0163 — path to GSM8K mastery (proposed) | `8b3314f` |
| #295 | feat(workbench-ui): design system v1 scaffold (ADR-0162 Branch 1) | (squash) |
| #296 | feat(ADR-0161.1): core teaching queue list\|show + fix + R1..R5 | `ec5d6f5` |
| #297 | feat(ADR-0163.A): refusal taxonomy lane — shape categorization | `5b4dcb1` |
| #298 | feat(ADR-0163.B.1): exemplar corpora — three categories | `1bff568` |
| #299 | feat(W-027): Workbench frontend shell — five-region grid | `cdead69` |
| #301 | feat(ADR-0163.C): contemplation ingests exemplars + DerivedRecognizer proposals | `08c5e0e` |
| #302 | feat(ADR-0163.D): wire ratified RecognizerSpecs into math_candidate_graph | `e9b7eb0` |
| #303 | feat(W-028): chat surface + trace drawer (ADR-0160 Phase 3) | `a612038` |
| #304 | chore(ratify): accept three Phase C exemplar_corpus recognizers (round 1) | `062d53f` |

Plus **issue #300** — `ingest/gate.py` versor_condition margin bug, discovered during Tier 1 manual GSM8K iteration.

---

## What landed by fork

### Fork A — Math Architecture (ADR-0163 corridor)

The corridor closed end-to-end in a single session:

- **Phase A** (PR #297) — `evals/refusal_taxonomy/` lane.  Categorized the 50-case GSM8K train_sample refusal histogram into 9 disjoint shape categories + UNCATEGORIZED.  72% categorized (target was 50%).  Top three by count: `descriptive_setup_no_quantity` (17), `temporal_aggregation` (4), `rate_with_currency` (3).  Doctrine encoded as runtime guards (no LLM imports test, ≥3 evidence-cite rule per category).
- **Phase B** (PR #298) — `teaching/admissibility_exemplars/` carrying 60 hand-authored exemplars across three categories (20 each).  Each exemplar binds a statement to an `expected_graph` payload following a per-category schema.  Seven `author_note` entries surfaced schema gaps for downstream review.
- **Phase C** (PR #301) — `teaching/recognizer_synthesis.py` distils each Phase B corpus into a `RecognizerSpec`.  Synthesis is deterministic, narrower-not-broader, rules-only (no LLM / no embeddings).  Phase C also extended `teaching/replay.py` with `run_admissibility_replay_gate` that runs cognition + G1..G5+S1 + GSM8K train_sample and auto-rejects any candidate that would lift wrong > 0 even by one.  Three pending proposals landed in the proposal log.
- **Phase D** (PR #302) — `generate/recognizer_registry.py` (pure projection over the proposal log; only `state="accepted"` + `kind="exemplar_corpus"` entries enter) + `generate/recognizer_match.py` (per-category rules-only matchers that honor the Phase C narrowness rule) + a **single-edit guard** at `generate/math_candidate_graph.py:455-470`.  Skip-only by construction — recognized statements contribute zero math state, so the Cartesian product is byte-identical to "this statement was never there," preserving `wrong = 0` at the wiring layer.
- **Phase D ratification** (PR #304) — operator accepted all three pending proposals via `core teaching review --accept`.  The ratified registry returned `len = 3`.

### First measured lift — GSM8K train_sample (50 cases, post-ratification)

```
correct: 3   (up from 0 — first non-zero correct count ever)
refused: 47  (down from 50)
wrong:   0   (unchanged — the invariant holds)

exit_criterion: { correct_min: 10, wrong_max: 0, passed: false }
```

The three lifted cases:

| case_id | answer | question excerpt |
|---|---|---|
| `gsm8k-train-sample-v1-0014` | 240 | Bob can shuck 10 oysters in 5 minutes.  How many oysters can he shuck in 2 hours? |
| `gsm8k-train-sample-v1-0018` | 16  | Xavier plays football.  During 15 minutes Xavier can score 2 goals on average.  How many goals on average... |
| `gsm8k-train-sample-v1-0042` | 30  | Ella has 4 bags with 20 apples in each bag and six bags with 25 apples in each bag.  If Ella sells 200 apples, how many apples does she have left? |

**Capability-axis floor preserved**: G1..G5 + S1 all report `wrong = 0` post-ratification, byte-identical to the pre-Phase-D baseline.

**Unexpected positive observation**: none of the three lifts are "pure descriptive_setup_no_quantity" cases.  They all involve temporal or aggregation framings where the previously-refusing statement gets skipped and the *question* + *remaining statements* carry enough math for the existing solver to produce the right answer.  This suggests Phase D's skip-only wiring is doing more useful work than the projection suggested, and that a **Phase B round 2** (more shape categories from the uncategorized 14) may be a more direct path to clearing Round 1 exit (`correct ≥ 10`) than the originally-planned Phase D.2 (parsed_anchors solver plumbing).

### Fork B — Workbench UI (ADR-0160 + ADR-0162 + W-026..W-028)

The Workbench is fully operational end-to-end:

```bash
uv run core workbench api          # http://127.0.0.1:8765
cd workbench-ui && pnpm dev        # http://127.0.0.1:5173
```

What ships:

- **W-026 (PR #292)** — read-only HTTP API (`workbench/api.py` + `workbench/readers.py` + `workbench/schemas.py` + `workbench/server.py`).  Seven GET endpoints + one whitelisted POST (`/evals/run` for the `contemplation_quality` lane only).  Path-traversal protection, MAX_ARTIFACT_BYTES guard, single-operator concurrency lock on eval runs, request logging gated by `CORE_WORKBENCH_QUIET` env var.
- **ADR-0162 (PR #293)** — design system doctrine: semantic tokens, dark-only theme, motion rules ("reveals structure, not cognition"), `StableJsonViewer` six invariants, empty/error/loading state contracts, keyboard-first contract, five-region shell, v1 component map, explicit no-go list.
- **Branch 1 (PR #295)** — `workbench-ui/` scaffold with self-hosted Inter + JetBrains Mono, generated `tokens.ts` mirror from `tokens.css`, `StableJsonViewer` with all six invariants tested, enum-bound badge primitives (`EpistemicStateBadge`, `NormativeClearanceBadge`, `ReviewStateBadge`, `GroundingSourceBadge`), and a `/preview` route as the design baseline.  Build-time enum-coverage test parses `core/epistemic_state.py` + `teaching/proposals.py` via Python AST and asserts 1:1 badge coverage; adding an enum value on the Python side without updating the badge fails the test loud.
- **W-027 (PR #299)** — five-region grid shell (TopBar / LeftNav / MainSurface / RightInspector / StatusFooter), ten empty routes each with copy-CLI affordances, live `StatusFooter` consuming `useRuntimeStatus()` (color + label encoding of `mutation_mode`, click-to-copy `git_revision`, amber-on-warning `checkpoint_revision` with ADR-0157/0158 inline note), `CommandPalette` upgrade with three real commands + fuzzy search, `ApiErrorBoundary` for `WorkbenchApiError`, schema-drift sentinel via `scripts/dump-api-schemas.py`.
- **W-028 (PR #303)** — the first route with real content.  `/chat` route with `PromptComposer` (⌘/Ctrl+Enter submit, Esc clear, 4096-char cap), `ResponseCard`, `EvidenceStrip` (5 enum-bound badges visible at a glance — grounding source, epistemic state, normative clearance, refusal indicator, mutation/checkpoint), `TraceDrawer` with three layers (structured panels, `StableJsonViewer`, raw payload behind `<details>` with downloadable .json).  Server-side `POST /chat/turn` with module-level `threading.Lock`, 64 KiB body cap, returns full `ChatTurnResult` carrying surface/walk_surface/articulation_surface distinctly per `docs/runtime_contracts.md`.

### Fork C — HITL Queue (ADR-0161 + L10b followups)

- **ADR-0161 (PR #291)** — HITL async queue scope ratified.  Five sub-questions answered with the narrowest commitment compatible with existing ADR-0057 / 0151 / 0152 / 0155 machinery: queue is a derived view over the proposal log + contemplation runs, no new persistence file, three operator surfaces (PR / workflow_dispatch / CLI), pending cap 256, no wall-clock expiry, only repo owner ratifies.
- **Step 1 (PR #296)** — `core teaching hitl-queue list|show` read-only projection (renamed from `core teaching queue list|show` after I caught a namespace collision with the existing Phase 1.2 gap-promotion command).  `derive_queue()` is a pure function over the proposal log; `find_queue_item()` supports exact + prefix matching; CLI returns formatted human view or JSON.

---

## Things discovered along the way

### Tier 1 manual iteration falsified an assumption

Earlier in the session I described manual teaching-chain iteration as a path to lift GSM8K cases.  Empirical probing showed otherwise: `core teaching propose` writes to the cognition corpus, but the **math admission path is independent** — `generate/math_candidate_graph.py` refuses on its own admission surface, never consulting the teaching corpus.  Teaching chains don't lift math cases; only candidate_graph admissibility expansion does (which is ADR-0163's whole point).  The manual iteration was the right exercise even though the path it suggested was wrong: it falsified the assumption fast and refocused the session on the corridor.

### `ingest/gate.py` versor_condition margin bug (issue #300)

During Tier 1 probing of `Tom has 5 apples. He gives 2 to Sarah. How many does Tom have?`, the engine raised a `RuntimeError: Injection produced non-versor field: condition=2.12e-06` from `ingest/gate.py:346`.  Bisected the trigger: requires (a) a declarative statement with a quantity, (b) a transfer phrase with `to <recipient>`, and (c) a "How many" question.  Both observed condition values (`1.02e-06`, `2.12e-06`) cluster within 3× of the 1e-6 threshold — `normalize_to_versor()` is *almost* closing and missing by a small margin on this token mix.  Per CLAUDE.md, the threshold doesn't move; the construction boundary does.  Filed as a separate bug, not in scope for the corridor work.

### Phase D's skip-only wiring did more than projected

The Phase D PR projected 3 cases lifting under skip-only — primarily through `descriptive_setup_no_quantity` admissions where the remaining math is solvable by existing G1..G5+S1 admission.  Empirically all three lifts were in cases involving rate/temporal framings: the recognizer skipped the previously-refusing statement, the question and remaining statements together carried enough math for the solver to produce the correct answer.  This is a forward note for the math fork's next-move planning — Phase D.2 (parsed_anchors solver plumbing) may not be the highest-leverage next step.

### Code review discipline transferred across agents

Every PR opened today got a mastery-level review.  The review pattern that emerged:

1. Verify locally (run tests, build, smoke check)
2. List 5–10 items at mastery level (the pattern to keep for subsequent branches)
3. List 0–5 non-blocking forward notes (the pattern to track but not block on)
4. Verdict (approve / blocker / forward-action)
5. Cross-references checked

This pattern caught real regressions (Gemini's gap-queue namespace collision in #296) and real architectural framings (Codex's "skip-only by construction" naming in #302).  When the agent addressed feedback in a follow-up commit, the same pattern verified the fix.  The pattern is now durable; future sessions can use the same shape.

---

## Operator-side actions taken

| When | Action |
|---|---|
| Mid-session | Removed the `required_pull_request_reviews` policy on `main` (kept the `verify pinned lane SHAs` status check).  Authorized in-session by the operator.  All later merges flowed through this looser gate. |
| Late session | Ran `core teaching propose-from-exemplars` against each of the three Phase B corpora (via Opus 4.7's first commit on PR #302) to land the three pending proposals in the live log. |
| Late session | Operator ratified all three Phase C recognizers via `core teaching review --accept`.  PR #304 captured the resulting log transitions. |
| Late session | Filed issue #300 — `ingest/gate.py` versor_condition margin bug. |

---

## What's NOT done (deferred to future sessions)

- **Phase E** as briefed — the GSM8K train_sample re-baseline harness (versioned baselines under `evals/gsm8k_math/train_sample/v1/baselines/`, workflow_dispatch + nightly schedule, `LiftReport` schema, append-only history).  Brief ready to paste; not yet dispatched.
- **Phase D.2 / parsed_anchors solver plumbing** — would convert `rate_with_currency` and `temporal_aggregation` recognitions into solver state.  Scope-uncertain after the empirical observation that skip-only already produces some rate/temporal lifts; worth measuring more carefully before scoping.
- **Phase B round 2** — three more shape categories from the Phase A uncategorized tail (14 statements).  Likely candidates: comparative_with_unit, fractional_rate_of_change, indefinite_quantity, nested_question_target.  Operator picks.
- **W-029 proposal queue UI** — make the HITL queue visible in the Workbench (the three Phase D proposals are in the live log; W-029 surfaces them in the UI).
- **W-030 eval center UI** — failures-first layout per the vision doc.
- **W-031 replay theater UI** — original vs replay side-by-side, trace_hash comparison.
- **ADR-0161 Steps 2–5** — backpressure (pending-count cap + queue_full reports), submission invariants (duplicate, dependent_on_pending), workflow_dispatch extension to reject/withdraw, embed queue summary in contemplation PR body.
- **Issue #300** — `ingest/gate.py` versor_condition margin fix.

---

## Architectural state at session close

The **substrate is complete enough that the next round can run end-to-end automatically**:

```
Phase B round 2  →  3 new exemplar corpora authored
        ↓
Phase C  →  contemplation runner ingests; emits 3 new RecognizerSpec proposals
        ↓
        (replay gate auto-rejects anything that would lift wrong > 0)
        ↓
Phase D  →  proposals appear in the HITL queue; operator inspects + ratifies
        ↓
        (skip-only wiring + ratified registry both already on main)
        ↓
        next GSM8K eval shows next round of lift, wrong=0 invariant intact
```

That loop, once you decide to run it, is the math architecture working as designed.  Today we proved the loop closes.  Future rounds widen.

---

## Cross-references

- [ADR-0163 — Path to GSM8K mastery](../decisions/ADR-0163-gsm8k-path-to-mastery.md)
- [ADR-0162 — Workbench Design System v1](../decisions/ADR-0162-workbench-design-system.md)
- [ADR-0161 — HITL async queue](../decisions/ADR-0161-hitl-async-queue.md)
- [ADR-0160 — CORE Workbench v1](../decisions/ADR-0160-core-workbench-v1.md)
- [Master plan post-substrate-audit](../master-plan-post-substrate-audit.md) — superseded by this session for the math + workbench forks
- [docs/PROGRESS.md](../PROGRESS.md) — capability-roadmap tracker; this session adds the math-corridor closure entry

### Memory cross-references

- `thesis-decoding-not-generating` — the load-bearing thesis that this session demonstrated as actionable
- `feedback-address-critiques-dont-waive` — applied consistently across mastery-level reviews
- `feedback-cleanup-as-you-find` — stale worktrees and merged branches cleaned at session close
- `feedback-adr-cross-reference-discipline` — every new ADR cross-references existing substrate
- `feedback-no-timelines` — phases sequenced by prerequisite, not date
