# Workbench UI — Wave Scoping Brief

**Status:** Scoping (no code in this brief; names the wave shape and the
prerequisite ADRs/decisions before any implementation moves)
**Date:** 2026-05-27
**Author:** Shay
**Parent doctrine:** [ADR-0160](../decisions/ADR-0160-core-workbench-v1.md), [ADR-0162](../decisions/ADR-0162-workbench-design-system.md)
**Related:** ADR-0161 (proposal-review trust boundary), ADR-0167 (teaching-corridor), ADR-0168 / 0168.1 (FrameClaim handler), ADR-0169 / 0169.1 (CompositionClaim doctrine), ADR-0172 (math contemplation corridor)

---

## Goal

Stand up the workbench frontend so the math teaching corridor is
operable by a single operator at human-realistic throughput. The
current bottleneck is **not** capability — Tier 1 + Tier 1.5 shipped
FrameClaim and (pending) CompositionClaim handlers — it is **operator
ergonomics**. Every audit refusal we cannot ratify quickly is a
learning event the engine never gets.

This brief does not commit code. It names:

1. what doctrine has already settled,
2. what the current operator pain points are,
3. what needs a fresh decision (ADR or scoping note) before any
   implementation,
4. the proposed wave shape (sequence + dependency DAG),
5. the guardrails the wave must not violate,
6. the acceptance criteria for the wave overall.

---

## What doctrine has already settled

The frontend has substantial pre-existing doctrine. The scoping brief
must **respect**, not relitigate, the following.

### ADR-0160 — Workbench v1

- **Frontend stack pinned:** React + Vite + TypeScript, TanStack Query,
  Zustand/Jotai, Tailwind + shadcn primitives, Monaco where structured
  JSON inspection is necessary.
- **No Electron.** **No heavy design system.** **No plugin marketplace.**
- **Local-first, deterministic backend.** Backend already exists at
  `workbench/` (stdlib HTTP server, routes for chat/proposals/
  math-proposals/ratify/evals/replay/trace).
- **Trust boundary v1 = read-only by default.** Accepting proposals,
  rejecting proposals as durable state, and pack/corpus mutation were
  explicitly forbidden in v1.

### ADR-0162 — Design System

- **Token namespace, typography, color semantics** all bound to
  ratified enums (`EpistemicState`, `NormativeClearance`, `ReviewState`,
  grounding source). No invented color states.
- **Keyboard contract.** Workbench is keyboard-first.
- **Layout shell** committed.
- **Component map v1 must-ship** (15 components):
  `WorkbenchShell`, `TopBar`, `LeftNav`, `StatusFooter`,
  `CommandPalette`, `ChatTurnList`, `ChatTurnCard`,
  `ResponseEvidenceStrip`, `TraceDrawer`, four state badges,
  `ReplayTheater`, `ReplayComparisonPanel`, `ReplayDiffViewer`,
  `ProposalQueue`, `ProposalCard`, `ProposalDetailPanel`,
  `RatificationCommandPanel`, `EvalCenter`, `EvalLaneList`,
  `EvalFailureViewer`, `StableJsonViewer`, `StableJsonDiffViewer`,
  `ArtifactLink`.
- **No-go list:** no chat-clone bubbles, no "AI thinking" affordances,
  no glassmorphism, no purple-neon-cyberpunk, no graph-builder canvas,
  no dashboard splash metrics, no color-only state encoding.
- **Implementation plan — Branch 1** (pre-W-027) names a single PR
  scope: `workbench-ui/` directory at repo root with pinned deps and
  the tokens CSS. No app routes yet.

These two ADRs already constitute the design phase. The wave is
**implementation**, not re-design.

---

## Current state — backend ready, frontend zero

- `workbench/api.py` exposes the routes ADR-0160 anticipates:
  `/health`, `/runtime/status`, `/artifacts`, `/proposals`,
  `/math-proposals`, `/math-proposals/{id}/ratify`, `/evals`,
  `/evals/run`, `/chat/turn`, `/trace/...`, `/replay/...`.
- `workbench/server.py` is a stdlib `ThreadingHTTPServer`. No remote
  network dependency for cognition.
- `workbench/schemas.py` defines `ProposalSummary`, `ProposalDetail`,
  `MathProposalSummary`, `MathProposalDetail`, `MathRatifyResult`,
  `EvalLaneSummary`, `EvalRunResult`, `ReplayComparison`,
  `ReplayDivergence` — the JSON contract the UI will consume.
- `MathProposalDetail` already carries `suggested_ratify_cli` and
  `handler_name`, which means the **dispatch corridor is already
  end-to-end on the server side**.

What does **not** exist yet:

- `workbench-ui/` directory (ADR-0162 Branch 1 deliverable — not landed).
- Any HTML/CSS/JS asset.
- Any client-side state management.
- Any keyboard binding implementation.

So the wave starts from zero on the client and from a complete
contract on the server.

---

## Operator pain points (evidence)

Sourced from the 2026-05-27 end-to-end demo and the CompositionClaim
brief pack:

1. **HITL burden is high.** Architecturally clean rejection of
   handler-mismatched proposals still costs the operator a full
   round-trip (read row → reason about category → reject → move on).
   At 47 audit rows × multiple proposal categories, this is the
   gating cost on the compounding loop.
2. **No keyboard corridor for ratification.** Operator currently
   constructs the suggested CLI by reading `MathProposalDetail.suggested_ratify_cli`
   from JSON output and pasting into a shell — a four-step
   context-switch per row.
3. **Evidence is text-block JSON.** `MathReaderRefusalEvidence` ships
   the audit-row context but reading it from raw JSON requires the
   operator to mentally render the source sentence, the bound slots,
   and the missing-operator pair.
4. **Reasoning traces are flat.** `MathProposalDetail.reasoning_trace_steps`
   carries the step-by-step decomposer hypothesis, but with no
   visualization the operator cannot quickly see where the chain
   would diverge from a correct admission.
5. **Replay equivalence is a string field.** `replay_equivalence_hash`
   is a meaningful invariant but currently surfaces as opaque hex —
   the operator has no eyes-on confirmation that a proposal genuinely
   replays.
6. **No "stuck queue" diagnosis.** The queue of pending proposals
   does not currently visualize *why* an item is pending (replay
   passed but operator hasn't reviewed? replay didn't run? evidence
   incomplete?). All three states render identically.

These are not capability problems. They are throughput problems with
a deterministic fix.

---

## What needs a fresh decision

Two doctrine updates are prerequisites. Both should land **before**
any frontend code so the wave doesn't burn cycles on a moving target.

### D1 — Trust-boundary ratchet (new ADR)

**Problem.** ADR-0160 v1 explicitly forbids "accepting proposals" in
the UI. That was correct when no ratification handlers existed
server-side. Tier 1.5 changed the world:

- `teaching/math_lexical_ratification.py::apply_lexical_claim` (W2-D, merged)
- `teaching/math_frame_ratification.py::apply_frame_claim` (PR #389, merged)
- `teaching/math_composition_ratification.py::apply_composition_claim` (PR-β, pending)

Each handler is replay-gated, hazard-pinned (case 0050), partition-
tested, idempotent, and append-only on a reviewed JSONL artifact.
The original ADR-0160 prohibition was a safety stance against
mutation paths that did not yet have proper gates. Those gates now
exist.

**Decision needed.** Either:

- **(a)** A new ADR (working title: **ADR-0173 — Workbench
  Ratification Trust Boundary**) that explicitly admits operator
  ratification through the workbench, scoped to the three existing
  handlers and gated by their existing replay/hazard/partition
  pins; or
- **(b)** A scoping note that re-affirms ADR-0160 v1 read-only and
  defers ratification UI to a v2.

Recommendation: **(a)**. Otherwise the wave reduces to "render
proposals you cannot act on," which does not retire the operator-
burden pain point at all.

Acceptance: ADR-0173 must enumerate exactly which handlers are
admitted, which are not, what mutation paths are still forbidden
(corpus, packs, engine_state outside checkpoint path, frame/lexical
registry edits outside the handler), and how the UI surfaces the
proposal-review trust boundary visually (e.g. RatificationCommandPanel
must distinguish "replay passed, you may ratify" from "replay didn't
run, ratify is disabled").

### D2 — Component-set ratification (sub-decision in D1 or its own scoping note)

ADR-0162's "v1 must-ship" component list pre-dates the ratification
handlers. Specifically, `RatificationCommandPanel` was named as
must-ship but its semantics were not pinned because no handler
existed. With handlers live, we need to fix:

- which proposal kinds the panel can drive (LexicalClaim, FrameClaim,
  CompositionClaim — and the deferred SUB_TYPE_FOR_OPERATOR entries
  remain disabled with a clear "no handler yet" affordance);
- whether the panel **executes** the suggested CLI in-process via the
  existing `apply_*_claim()` handlers, or merely **renders** the CLI
  for the operator to copy/run (the brief recommends in-process
  execution under D1's trust boundary, because copy/paste-to-shell
  is itself an operator-burden axis);
- the keyboard binding contract (e.g. `j/k` to navigate proposals,
  `r` to ratify the focused proposal, `x` to reject, `?` for help —
  must be pinned in D1 or a sibling note before implementation so
  every panel shares one mental model).

Recommendation: fold D2 into D1 as a single ADR.

---

## Proposed wave shape

Five waves, ordered. Each wave is **one PR or one tight stack**, not
a sprawling branch.

```text
W0 (docs):    Trust-boundary ratchet ADR + component-set update
                │
                ▼
W1 (UI base): workbench-ui/ scaffold per ADR-0162 Branch 1
              (Vite, TS, Tailwind, shadcn primitives, tokens CSS,
               shell, command palette, status footer — no routes yet)
                │
                ▼
W2 (read):    ProposalQueue + ProposalCard + ProposalDetailPanel
              (math + cognition proposals, read-only;
               StableJsonViewer for evidence/replay payloads;
               EpistemicState / ReviewState / TraceHash badges)
                │
                ▼
W3 (act):     RatificationCommandPanel + handler dispatch
              (keyboard corridor: j/k navigate, r ratify, x reject;
               in-process apply_*_claim() execution via API;
               replay-state visualization;
               post-ratify auto-advance to next pending)
                │
                ▼
W4 (verify):  TraceDrawer + ReplayTheater + ReplayComparisonPanel +
              ReplayDiffViewer + EvalCenter + EvalLaneList +
              EvalFailureViewer
              (the audit/replay surfaces that close the loop;
               StableJsonDiffViewer for replay divergences)
```

### Why this order

- **W0 is unblock-everything.** Code written against a stale trust
  boundary either gets thrown out (if doctrine tightens) or builds
  in a constraint that the rest of the wave can't honor (if doctrine
  loosens unevenly).
- **W1 is the substrate.** ADR-0162 already named it; ship it once,
  every later wave assumes it.
- **W2 is the *minimum* legible workbench.** If we ship W0-W2 only,
  the operator can already inspect every pending proposal at human
  speed — a real throughput improvement even without ratification UI.
- **W3 is the throughput multiplier.** The keyboard ratification
  corridor is the entire reason this wave exists. It must land
  before W4 because trace/replay surfaces are *audit* tools, not
  *throughput* tools — and we're throughput-bound, not audit-bound.
- **W4 closes the loop.** Once an operator has ratified a proposal,
  TraceDrawer + ReplayTheater + EvalCenter let them verify the
  effect immediately rather than dropping back to the CLI.

### What ships in each wave

| Wave | One-line description | Approximate PR count | Approximate test surface |
|---|---|---|---|
| W0 | Trust-boundary ratchet ADR + (sub-decision) component-set update | 1 docs PR | 0 (docs only) |
| W1 | `workbench-ui/` scaffold + tokens + shell + palette + status footer | 1 frontend PR | smoke (build green, tokens snapshot, shell renders) |
| W2 | ProposalQueue + ProposalCard + ProposalDetailPanel + StableJsonViewer + badges | 1 PR (math) + 1 PR (cognition) OR 1 bundled | component tests + 1 e2e against backend fixtures |
| W3 | RatificationCommandPanel + keyboard corridor + handler dispatch | 1 PR per handler **OR** 1 bundled PR (LexicalClaim + FrameClaim + CompositionClaim) | one e2e per handler ratifying a fixture proposal → checking the JSONL artifact change |
| W4 | TraceDrawer + ReplayTheater + ReplayDiff + EvalCenter | 2 PRs (replay surfaces + eval surfaces) | one e2e per surface |

This is the **shape**, not the exact PR boundaries — operators
running W2/W3/W4 should bundle per the project's existing
"batch-during-research" pattern when CI cycle time argues for it.

---

## Guardrails (must hold across every wave)

Each is non-negotiable. A PR that violates one is reworked, not
waived.

1. **CLAUDE.md docs discipline.** No standalone HTML artifacts as
   substrate (CSS regen ordering / SVG element ordering break
   determinism). The workbench is allowed to render HTML because it
   is a **read-only view of deterministic JSONL artifacts**, not a
   substitute for them.
2. **ADR-0162 no-go list.** Reread every PR. No chat-clone bubbles,
   no "AI thinking" theater, no glassmorphism, no dashboard splash
   pages, no graph-builder canvas, no auto-dismiss toast for audit
   events, no color-only state encoding.
3. **Determinism preserved.** Every UI state derived from a
   deterministic backend payload. No client-side randomness that
   affects rendered content. (Loading skeletons are fine; "shuffle
   proposal queue" is not.)
4. **Trust boundary respected.** W2 ships read-only. W3 ships
   ratification only for handlers admitted by D1's ADR. Pack /
   corpus / engine_state mutation paths remain forbidden through
   the UI.
5. **`wrong == 0` invariant unchanged.** No UI wave touches the
   server-side handlers' hazard pins. Every UI PR runs the affected
   server suites green (`core test --suite teaching -q`,
   `core test --suite runtime -q`).
6. **Case 0050 protected.** UI must not introduce a fast-path that
   bypasses the handler's pre-conditions. Ratifying through the UI
   must call the same `apply_*_claim()` function as the CLI,
   carrying the same evidence, raising the same exceptions.
7. **Keyboard-first.** No mouse-only interactions for any v1 must-
   ship component. (Mouse is supported; mouse-only is not.)
8. **Accessibility.** No icon-only buttons without accessible labels;
   no color-only state encoding (badges carry text + shape, not
   color alone). Pinned in ADR-0162 §"The no-go list" — restated
   here because it's the easiest guardrail to drift on.
9. **No remote network dependencies for cognition.** Workbench
   backend stays local-first. UI may fetch from
   `http://127.0.0.1:<port>` only. No CDN-loaded fonts/icons in v1;
   bundle locally.
10. **No engine_state writes** outside the existing checkpoint path
    (ADR-0146/0150).

---

## Anti-regression invariants

Inherited from the broader teaching corridor — listed so every wave
PR can self-check.

- `wrong == 0` on `core eval gsm8k_math` preserved.
- ADR-0166 — no new eval lanes introduced by UI work.
- ADR-0057 replay-equivalence — inherited unchanged.
- ADR-0167 partition — cognition and math proposal surfaces remain
  partitioned in the UI as on the server.
- Case 0050 hazard pin holds across every W3 ratification path.
- `engine_state/*` never committed.
- Pinned-lane SHAs should not require updates due to UI work; if
  one moves, the UI PR is doing something it shouldn't.

---

## Open questions (resolve in W0)

1. **In-process ratification vs out-of-process dispatch.** D1
   recommends in-process via the existing API, but if there's a
   reason to keep the UI strictly read-only and dispatch ratification
   through the CLI (e.g. an audit-trail concern), W0 must name it.
2. **Single-operator only vs multi-operator-aware.** The current
   handler architecture is single-operator (no proposal locking, no
   review-state contention). W0 should affirm or deny that v1
   stays single-operator.
3. **Telemetry path.** The backend `chat/telemetry.py` JSONL sink
   exists. W0 should pin whether the UI emits its own operator-
   action events (e.g. "operator-ratify",
   "operator-reject", "operator-defer") into the same sink, or
   into a separate workbench-events log.
4. **Font / icon bundling.** ADR-0162 pins typography but doesn't
   commit on whether to bundle Inter / a system stack. W0 should
   resolve so W1 doesn't introduce a runtime fetch.
5. **Build artifact location.** Does `workbench-ui/dist/` get
   committed, gitignored, or served from a CI step? W0 should
   commit. (Recommendation: gitignored; built locally; CI verifies
   the build is green but does not commit the artifact.)

---

## Acceptance criteria (whole wave)

The wave is "done" when:

- A new operator can run `core workbench serve` (existing CLI) and
  open the UI in a local browser.
- Pending audit refusals from `audit_brief_11.json` appear as a
  navigable queue.
- An operator can ratify a LexicalClaim, FrameClaim, **or**
  CompositionClaim proposal via keyboard in **under 10 seconds per
  row** for a row whose evidence they understand.
- The ratification produces the same JSONL artifact change as
  invoking the corresponding `apply_*_claim()` from the CLI —
  byte-equal where possible, semantic-equal otherwise.
- `core test --suite teaching -q`, `core test --suite runtime -q`,
  and `core eval gsm8k_math` remain green throughout.
- Case 0050 remains refused after end-to-end UI ratification of any
  pending proposal.
- The five operator pain points listed above are individually
  retired (each can be pointed at one shipped component).

---

## Memory pointers

- [[feedback-batch-during-research]] — bundling rule for the
  W2/W3/W4 PRs when CI cycle time argues for it
- [[feedback-no-self-dispatch-of-subagents]] — Shay dispatches
- [[feedback-production-line-pattern]] — wave brief pack pattern
- [[feedback-parallel-agent-worktrees]] — fresh worktree per brief
- [[feedback-wrong-zero-hazard-case-0050]] — W3 mandatory pin
- [[feedback-address-critiques-dont-waive]] — guardrail violations
  are reworked, not waived
- [[milestone-adr-0172-tier1-2026-05-27]] — context for why
  throughput, not capability, is the bottleneck
- [[adr-0167-audit-as-evidence-wave]] — parent corridor

---

## Next step

If approved, **W0 docs PR** is the immediate output: ADR-0173 (working
title: Workbench Ratification Trust Boundary) authored against the
five operator pain points above, the existing handlers as scope, and
the keyboard contract as pinned semantics. Once W0 lands, W1 (the
ADR-0162 Branch 1 scaffold) can dispatch.
