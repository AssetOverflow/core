# Brief W3 — Workbench Ratification Corridor (the throughput multiplier)

**Status:** Ready to dispatch once W0 (ADR-0173 acceptance) lands.
**Date:** 2026-05-29
**Author:** Shay
**Supersedes:** the W3 section of
`docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md` (lines 324–487), which
was written against a stale "frontend zero" state and a Zustand layout
this codebase never adopted. Read the *Reconciliation* section below
before treating the older brief as authoritative.
**Parent doctrine:** [ADR-0173](../decisions/ADR-0173-workbench-ratification-trust-boundary.md)
(trust boundary), [ADR-0160](../decisions/ADR-0160-core-workbench-v1.md)
(workbench v1), [ADR-0162](../decisions/ADR-0162-workbench-design-system.md)
(design system + keyboard contract)
**Operator profile:** Opus — load-bearing `wrong == 0` surface; must
mirror the case-0050 hazard-pin rigor of
`tests/test_math_composition_ratification.py`.

---

## Reconciliation — what actually shipped vs. what the old brief assumed

The earlier wave pack (`WORKBENCH-UI-WAVE-BRIEF-PACK.md`) was authored
2026-05-27 against the scoping brief's "backend ready, frontend zero"
framing. That framing was already wrong on arrival. Verified state of
`origin/main` as of 2026-05-29:

| Old brief's wave | Old assumption | Actual state on `main` |
|---|---|---|
| W1 scaffold | "not landed" | **Merged** — `workbench-ui/` (#295, #299), Vite/TS-strict/Tailwind, tokens, shell, LeftNav, TopBar, StatusFooter, CommandPalette |
| W2 read surfaces | "not landed" | **Merged** — `src/app/proposals/*` (#329), `ProposalsRoute`, `ProposalTable`, `ProposalDetailPanel` analog, `SuggestedCLIBox`, `StableJsonViewer`, state badges |
| W4 verify | "not landed" | **Merged** — replay (#328), eval center (#327), chat+trace (#303) |
| W3 ratify | the genuinely-new piece | **Not started** — this brief |

**Consequence:** W3 no longer depends on a "W2 merge." Its only hard
upstream dependencies are:

1. **W0 — ADR-0173 status flips `Proposed → Accepted`.** It amends
   ADR-0160's read-only stance; W3 must not land while it is still a
   proposal. (One-line PR; no code.)
2. **The backend advisory→in-process flip** (below) — currently
   `/ratify` *routes but does not apply*. This is the load-bearing
   change the old brief glossed.

All three handlers now exist on `main`
(`apply_lexical_claim`, `apply_frame_claim`,
`apply_composition_claim` — the last via PR #393), so there is no
"pending CC-2" caveat anymore.

---

## The load-bearing backend fact (read this twice)

`workbench/readers.py::ratify_math_proposal` **does not ratify
anything today.** Verified live:

```
POST /math-proposals/{id}/ratify
→ {"routing_status": "routed", "handler_name": "CompositionClaim",
   "suggested_cli": "from teaching.math_composition_ratification import ...",
   ...}   # no JSONL append; git status clean afterward
```

It validates the `proposed_change_kind`, picks a handler name, and
returns a *suggested CLI string with hard-coded placeholder arguments*
(`category='drain_token'`, `composition_category='multiplicative_composition'`).
It never constructs a `MathReaderRefusalEvidence`, never calls a
handler, never writes.

**W3's central backend task is to add a real apply path** that invokes
the handler in-process per ADR-0173 §Q1 — while keeping the advisory
dry-run path reachable for the `y` (copy-CLI) audit fallback.

### Why this is the wrong=0 hazard, not a plumbing change

The live `/math-proposals` payload carries `shape_category:
"uncategorized"` on real proposals. The handlers refuse to write
unless given a category in their safe allowlist
(`SAFE_CATEGORIES` / `SAFE_FRAME_CATEGORIES` /
`SAFE_COMPOSITION_CATEGORIES`) and a polarity in
`{"affirms", "falsifies"}`. The proposal record **does not contain a
ratifiable category** — it contains a *structural commonality* and an
*uncategorized* shape.

Therefore the category and polarity **must be supplied by the
operator at ratification time**, constrained to the per-handler safe
allowlist, and passed in the request body. The old brief hard-coded
`composition_category='multiplicative_composition'` in a CLI comment —
that is exactly the silent-wrong-category path that case 0050 exists to
catch. **Do not auto-derive the category. Make the operator choose it
from the allowlist; refuse if it is absent or off-allowlist.**

---

## Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w3 origin/main && \
  cd /tmp/wt-wb-ui-w3 && \
  git checkout -b feat/workbench-ui-w3-ratification-corridor
```

(Fresh worktree per [[feedback-parallel-agent-worktrees]]. Do not
share a working dir with other agents.)

## Reads required FIRST

- `docs/decisions/ADR-0173-workbench-ratification-trust-boundary.md`
  — entire ADR. The §"Keyboard contract", §"What the workbench MAY
  do / MUST NOT do", §"Ratification record extension", and
  §"Acceptance gates → W3" are verbatim requirements.
- `workbench/readers.py::ratify_math_proposal` — the advisory impl
  you are extending (not replacing — see §Q1 dry-run retention).
- `workbench/api.py` — the `POST /math-proposals/{id}/ratify` route
  and `_math_ratify`; `MathRatifyResult` in `workbench/schemas.py`.
- `teaching/math_lexical_ratification.py` — `apply_lexical_claim()`
  signature, `SAFE_CATEGORIES`, exception types
  (`WrongClaimSubType`, `WrongZeroViolationCandidate`,
  `AlreadyRatified`, `EvidenceTampered`).
- `teaching/math_frame_ratification.py` — `apply_frame_claim()`,
  `SAFE_FRAME_CATEGORIES`, `EvidenceLaundering`.
- `teaching/math_composition_ratification.py` —
  `apply_composition_claim()`, `SAFE_COMPOSITION_CATEGORIES`.
- `tests/test_math_composition_ratification.py::test_case_0050_hazard_pin`
  — the hazard-pin template W3 mirrors.
- `workbench-ui/src/app/proposals/` — actual component layout
  (`ProposalsRoute`, `ProposalTable`, `SuggestedCLIBox`, badges).
- `workbench-ui/src/api/queries.ts` — established `useMutation`
  pattern (`useEvalRun`, `useChatTurn`); this is how the ratify
  mutation is wired. **There is no Zustand in this repo** — auto
  advance is local React state + `queryClient.invalidateQueries`.
- `workbench-ui/src/api/client.ts` — existing POST support.

---

## Outcome

One backend apply path, one component, one keyboard surface, one e2e
per handler.

### Backend

1. **`workbench/readers.py` — add an apply path.**
   `ratify_math_proposal(proposal_id, *, category, polarity,
   reviewer, dry_run=False, jsonl_path=None)`:
   - `dry_run=True` (or category omitted) → existing advisory behavior
     unchanged (`routing_status="routed"` + `suggested_cli`). This is
     what the `y` copy-CLI affordance and audit fallback rely on.
   - `dry_run=False` with a category → reconstruct the
     `MathReaderRefusalEvidence` from the proposal record's evidence,
     then dispatch to the matching handler:
     - `LexicalClaim` → `apply_lexical_claim(claim=…, category=category, reviewer=reviewer)`
     - `FrameClaim` → `apply_frame_claim(claim=…, frame_category=category, polarity=polarity, reviewer=reviewer)`
     - `CompositionClaim` → `apply_composition_claim(claim=…, composition_category=category, polarity=polarity, reviewer=reviewer)`
   - Return a `MathRatifyResult` carrying the handler receipt fields
     (target JSONL path, evidence hash, `applied=True`) on success.
   - **Do not catch handler exceptions to smooth them.** Let
     `WrongClaimSubType` / `WrongCompositionCategory` /
     `EvidenceLaundering` / `AlreadyRatified` / `EvidenceTampered`
     propagate; the API layer translates them to structured 4xx with
     the message verbatim.
2. **`workbench/api.py` — accept a request body** on the existing
   route: `{ "category": str, "polarity": "affirms"|"falsifies",
   "dry_run": bool }`. `reviewer` is **server-derived** (OS username
   of the workbench process, same as Surface C — never operator-typed,
   per ADR-0173 §"Ratification record extension"). Reject a non-local
   `Origin`/`Host` (CORS stays closed). Map handler exceptions →
   `400`/`409` with `{"error": {"code", "message"}}` carrying the raw
   handler message.
3. **`ratifier_kind: "workbench"`** written into the JSONL artifact's
   provenance record. **Audit-forensic field only, never a permission
   gate** (ADR-0173). `proposal_id` and `to` remain the only
   replay-load-bearing fields.
4. **Operator-action telemetry** to the existing `chat/telemetry.py`
   sink (ADR-0173 §Q3) — `operator_ratify` / `operator_reject` /
   `operator_defer`. Outcome-only (no intent-to-ratify events),
   redact-by-default (no evidence/surface text):
   ```json
   {"event": "operator_ratify", "proposal_id": "...", "handler": "...",
    "outcome": "applied|rejected_precondition", "ratifier_kind": "workbench"}
   ```
   No parallel log file.

### Frontend

5. **`workbench-ui/src/app/proposals/RatificationCommandPanel.tsx`** —
   panel attached to the focused proposal in the detail view.
   - Renders only when the focused proposal is `pending` AND
     `replay_equivalent == true` AND `handler_name ∈ {LexicalClaim,
     FrameClaim, CompositionClaim}`. Otherwise renders disabled with a
     status-footer message naming the failing precondition (no silent
     failure — ADR-0173 §"Keyboard contract").
   - **Category selector** populated from the handler's safe allowlist
     (fetched/typed from the API; do not hard-code in TSX). **Polarity
     selector** (`affirms`/`falsifies`) for Frame/Composition;
     Lexical takes no polarity. `r` is disabled until a category is
     selected.
   - Shows: handler name, claim evidence-hash digest, target JSONL
     artifact path, and the four affordances
     (`ratify (r)` / `reject (x)` / `defer (d)` / `copy CLI (y)`).
6. **`useMathRatify` mutation in `src/api/queries.ts`** — follow the
   `useEvalRun`/`useChatTurn` `useMutation` pattern. On 2xx invalidate
   the proposals query and advance focus to the next
   `pending`+`replay_equivalent` row. On 4xx, surface
   `WorkbenchApiError.message` **verbatim** into the status footer.
7. **Auto-advance** via local React state + `queryClient
   .invalidateQueries`. No new global store.

---

## Keyboard wires (per ADR-0173, pinned — do not invent new bindings)

- `r` → ratify focused proposal. No-op + named status-footer message
  unless `pending` ∧ `replay_equivalent == true` ∧ admitted handler ∧
  a category is selected.
- `x` → reject with note (single-line input; `Enter` commits, `Esc`
  cancels). Emits `operator_reject`. (Reject is **not** durable
  proposal-state mutation in v1 — it is an operator annotation +
  telemetry event; the proposal remains in the log.)
- `d` → defer (proposal stays `pending`; `operator_defer` emits).
- `y` → copy `suggested_ratify_cli` to clipboard (audit fallback;
  uses the dry-run path).
- No `Cmd`/`Ctrl` chords (collides with browser shortcuts).

---

## Hard requirements (mirror ADR-0173 §"Acceptance gates → W3" verbatim)

- **Same Python entrypoint.** Every non-dry-run ratify executes the
  same `apply_*_claim()` the CLI would. Proven by a parametrized test
  (one per handler) that ratifies a fixture via the API and an
  equivalent fixture via the CLI, then asserts the JSONL artifact rows
  are **byte-equal except for `ratifier_kind`**.
- **Operator-supplied category, allowlist-gated.** A ratify request
  with no category, or a category outside the handler's `SAFE_*`
  allowlist, is refused (`400`) and writes nothing. Proven by test.
- **Case 0050 hazard pin holds end-to-end.** Ratify a synthetic claim
  under each safe category via the UI path, then run
  `core eval gsm8k_math` (via `/evals/run`) and assert case 0050 stays
  **refused**. This is the mandatory pin — mirror
  `test_math_composition_ratification.py::test_case_0050_hazard_pin`.
- **Exception surface verbatim.** `AlreadyRatified`,
  `WrongClaimSubType`, `WrongCompositionCategory`,
  `EvidenceLaundering`, `EvidenceTampered`, replay-regression — all
  surface raw into the status footer. No translation, no smoothing.
- **`r` is a no-op** on any proposal failing a precondition; the no-op
  names the failing precondition in the footer.
- **Partition.** A math ratify cannot mutate cognition artifacts and
  vice versa; a cross-domain attempt returns `400` with a
  partition-violation reason. Proven by test.
- **No auto-ratify.** Replay-passed proposals stay `pending` until an
  explicit `r`. Proven by polling a queue of replay-passed fixtures
  and asserting zero transitions until a keypress.
- **No batch / multi-select ratification.** One `r` = one proposal.
- **CORS stays closed.** Backend binds `127.0.0.1`; cross-origin
  refused. Proven by test.
- **Telemetry redact-by-default.** Events carry no evidence/surface
  text. Proven by emit→parse→assert-no-leak test.
- **`ratifier_kind` is not load-bearing for replay.** A test strips
  `ratifier_kind` from the record and confirms replay still passes.

---

## Tests (mirror `tests/test_math_composition_ratification.py` rigor)

- `tests/test_workbench_ratify_lexical.py` — UI ratify → JSONL
  byte-diff vs CLI ratify (except `ratifier_kind`)
- `tests/test_workbench_ratify_frame.py` — same shape, FrameClaim
- `tests/test_workbench_ratify_composition.py` — same shape, CompositionClaim
- `tests/test_workbench_ratify_category_allowlist.py` — missing /
  off-allowlist category refused, nothing written
- `tests/test_workbench_ratify_case_0050_hazard_pin.py` — **mandatory**
- `tests/test_workbench_ratify_partition.py` — math/cognition isolation
- `tests/test_workbench_ratify_no_auto.py` — auto-ratify forbidden
- `tests/test_workbench_ratify_exception_surface.py` — verbatim 4xx
- `tests/test_workbench_ratify_idempotent.py` — duplicate → `AlreadyRatified`
- `tests/test_workbench_operator_telemetry.py` — events emit; no leak
- `workbench-ui/src/app/proposals/RatificationCommandPanel.test.tsx` —
  visibility gating, category-required disable, keyboard, no-op paths
- `workbench-ui/e2e/ratification_corridor.spec.ts` — end-to-end for all
  three handlers (if Playwright is wired; otherwise a vitest+MSW
  integration test against the real API shape)

## Deliverables

- `workbench/readers.py` apply path; `workbench/api.py` body parsing +
  exception mapping + telemetry; `workbench/schemas.py` `MathRatifyResult`
  extension (`applied`, `target_path`, `evidence_hash`)
- `RatificationCommandPanel.tsx`; `useMathRatify` in `queries.ts`;
  category/polarity selectors typed from the safe allowlists
- All tests above, green
- `core test --suite teaching -q` green
- `core test --suite runtime -q` green
- `core eval gsm8k_math` green; **case 0050 remains refused**
- `cd workbench-ui && pnpm build && pnpm test` green

## Forbidden

- Auto-deriving the ratification category from `shape_category` or
  `proposed_change_kind` (operator must choose; off-allowlist refused)
- Admitting any handler outside {Lexical, Frame, Composition}
- Auto-ratify of any flavor; batch / multi-select ratification
- Bypassing handler preconditions in any code path
- Catching/smoothing handler exceptions before the API boundary
- Remote operator auth, login, token-bearer; relaxing CORS
- `Cmd`/`Ctrl` keyboard chords
- Writing `engine_state/*` outside the existing checkpoint path
- Treating `ratifier_kind` as a permission gate
- A parallel telemetry log file
- A new Zustand/Jotai global store (use TanStack Query + local state)

---

## Anti-regression invariants

- `wrong == 0` on `core eval gsm8k_math` preserved
- Case 0050 refused after end-to-end UI ratification of any handler
- ADR-0167 partition (math vs cognition) preserved in API and UI
- ADR-0161 §5 replay invariants unchanged (`proposal_id` + `to` only)
- No new eval lane (ADR-0166)
- `engine_state/*` never committed
- Pinned-lane SHAs unchanged by UI work

## Acceptance

W3 is done when an operator can, against a locally-running
`core workbench api`:

1. open the proposal queue, focus a `pending`+`replay_equivalent`
   math proposal;
2. choose a safe category (+ polarity for Frame/Composition);
3. press `r` and have it invoke the same `apply_*_claim()` the CLI
   would, producing a JSONL artifact append byte-equal to the CLI's
   except for `ratifier_kind`;
4. see the handler's exception verbatim when a precondition fails;
5. confirm case 0050 stays refused afterward — under each safe
   category, end-to-end.

Each of the five operator pain points in
`WORKBENCH-UI-WAVE-SCOPING.md` is retired by a named affordance here:
queue navigation (j/k), category-confirmed ratify (r), evidence digest
+ target path in the panel, replay-state gating of `r`, and the
no-silent-failure status footer.

## Memory pointers

- [[feedback-no-self-dispatch-of-subagents]] — Shay dispatches; this
  brief is written and stops. No Agent calls.
- [[feedback-production-line-pattern]] — brief-pack discipline
- [[feedback-parallel-agent-worktrees]] — fresh worktree per dispatch
- [[feedback-wrong-zero-hazard-case-0050]] — mandatory W3 pin
- [[feedback-address-critiques-dont-waive]] — guardrail violations are
  reworked, not waived
- [[adr-0175-calibrated-learning-architecture]] — keep ratification
  honest: move intelligence into the solver, not per-shape matchers
- [[milestone-adr-0172-tier1-2026-05-27]] — why throughput, not
  capability, is the bottleneck
