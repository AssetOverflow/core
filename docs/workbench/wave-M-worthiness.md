# Wave M — CORE Workbench: Mastery & Worthiness

Date: 2026-06-13
Status: approved plan (Shay, 2026-06-13). Predecessor: Wave R complete
(#702–#723; 11 routes real, Replay Moment, trace integrity, DAG/Demo/wrong=0).
Execution: committed brief packs in `docs/handoff/`, parallel-safe DAGs,
dispatched between Fable 5 and GPT5.5 — the same production line that
shipped R2 + R3.

## Thesis

Two asks, one lens.

1. **Mastery** — take the shipped surface from very good to best-in-class.
2. **Worthiness** — add what's *missing* so the workbench is undeniably
   worthy of the deterministic cognitive engine beneath it.

The lens: **Anthropic and xAI as target users who would *want* to use it.**
They build the opaque transformer this engine defines itself *against*. What
impresses them is not prettier charts — it is a UI that makes
**determinism, refusal-discipline, and geometric coherence inspectable and
felt.** Standard: ADR-0160's three pillars — audit-native (not analytics
theater), calm default / infinite depth, replay before persuasion.

## Diagnosis — the two blind spots

The workbench today is excellent at **evidence browsing**: every route
projects an evidence manifold, the Evidence Chain Rail threads provenance,
the Replay Moment makes hash-equality felt. But it is blind to the two most
*distinctive* parts of the organism:

1. **It shows the teaching/ratification loop and is blind to the
   calibrated-learning / serving-discipline loop.** You can ratify a
   proposal, but you cannot *see* the gold-tether arena, the reliability
   gate, the Wilson floor vs the θ ceiling, or the moment "the engine earns
   the right to guess." That discipline — *the engine refuses rather than
   guesses wrong* — is the single most impressive idea in the project, and
   it is invisible.
2. **It shows outputs and evidence but not cognition itself.** The
   `CognitiveTurnPipeline` stages, the contemplation *process*, the CL(4,1)
   field substrate, `versor_condition`, identity continuity — none are
   legible. For an audience that lives inside opaque models, *legible
   deterministic cognition* is the wow.

Everything below closes those two gaps on top of a mastery polish.

## Non-negotiable disciplines (bind every phase)

- **Backend-reader-first, no theater.** Every new surface reads *real*
  engine data through a new read-only reader; no dashboard over invented or
  recomputed numbers. The calibration and field readers do not exist yet —
  that gating work is Python, not React.
- **Never re-implement engine math in the workbench.** The calibration
  reader *imports and uses* `core.reliability_gate` (`conservative_floor`,
  `license_for`, `Ceilings`, `Action`); the field reader uses the engine's
  real `versor_condition`/`cga_inner`. The workbench computes nothing the
  engine owns.
- **Read-only doctrine holds.** No new mutation endpoints; execution stays
  the existing allowlisted set (`/evals/run`, ratify, `/demos/{id}/run`). A
  calibration view never *changes* a license.
- **Determinism in the UI too.** No force-directed / nondeterministic
  layout, no decorative motion-as-cognition. Golden-file layout tests for
  every new visualizer (like the DAG). The honesty *is* the impressiveness.
- **Doctrine gates extend to every new surface**: schema mirrored, enums
  covered, route conformant, readers SHA-pinned where they assert a metric.

## Phases (priority-ordered)

### Phase A — Mastery polish of the shipped surface (scope: M; parallel)
No new concepts; make the 11 routes undeniable.
- Design-system full expression: semantic token roles, elevation, **density
  modes actually wired** (the deferred Settings density pref), `tabular-nums`
  on all numerics, `[text-wrap:balance]` on all statements, motion-discipline
  audit (only state-transition affordances).
- Cross-route consistency sweep: every list = `VirtualizedList` +
  `useListNavigation` + `SearchInput` + selection tokens; every detail =
  `Panel` + `TabBar`; calm-honest prose audit on every state.
- **DAG viewer: finish its consumers.** It shipped wired only to proposal
  chains; wire the **PCCP proof-promotion 8 scenarios** and **entailment
  traces** (the other two the brief named). A primitive with one consumer is
  half-built.
- Command/keyboard completeness: a palette verb for every route action;
  registry-driven help stays the exhaustive contract.
- Accessibility pass: focus-visible audit, SR labels on every evidence
  badge, reduced-motion honored.

### Phase B — Calibrated-Learning / Serving-Discipline surfaces (scope: L) ← the heart
The "worthy of the model" core. Backend-reader-first (none exist; data lives
in `core/reliability_gate/` + the committed `evals/gsm8k_math/*/report.json`).
Detailed brief pack: `docs/handoff/wave-M-phaseB-calibration-briefs-2026-06-13.md`.
- **B1 (Python):** read-only readers/endpoints over the real ledger —
  `GET /calibration/classes` (per-class `ClassTally` counts + the Wilson
  `conservative_floor` reliability + PROPOSE/SERVE `license_for` verdicts via
  the real `core.reliability_gate`), `GET /serving/metrics` (the committed
  `train_sample/v1/report.json` numbers — read the artifact, never re-run an
  unsafe lane). Schema mirrors + snapshots + drift gate.
- **B2 — Calibration / Gold-Tether route:** per class, a
  coverage-vs-Wilson-floor bar, the θ ceiling, and a plain-language "earned
  PROPOSE / SERVE / neither" verdict. Failures-first. Where you *see* "the
  engine earns the right to guess."
- **B3 — wrong=0 as a felt global presence:** an always-present invariant
  element (N correct / N refused / **0 wrong**, the zero load-bearing),
  elevating the per-run Evals ledger to the project's thesis made constant.
- **B4 — the leeway story:** wire the calibration verdict into the Proposals
  / Replay rails so a reviewer sees *why* a turn was granted latitude (which
  class license, which θ, the `[approximate]` disclosure) — connecting the
  HITL ratification you already have to the calibration that grants it.

### Phase C — Make cognition legible (scope: L) ← the wow for Anthropic/xAI
- **C1 — Cognitive Pipeline visualizer:** for a selected turn, render the
  real `CognitiveTurnPipeline` stages (intent → PropositionGraph →
  ArticulationTarget → realizer → walk telemetry → trace hash) as a
  deterministic staged view (reuse the DAG primitive). *The* "real,
  replayable path, not animated fake cognition" surface. Reader-first over
  existing trace/walk telemetry.
- **C2 — Contemplation as a process, not just outputs:** the contemplation
  *loop* (attempt → gold-tether → ClassTally → propose), connecting
  Demos/Proposals/Calibration into one story.
- **C3 — Field substrate (honest, read-only, hard):** `GET /field/state`
  over real `FieldState` + `versor_condition` for a turn, rendered as
  **inspectable exact numbers and invariant status** — `versor_condition <
  1e-6` as a live "field is valid" assertion, `cga_inner` coherence as exact
  values. **NOT** a decorative 3D blob; no force-directed/nondeterministic
  motion. The honesty is the impressiveness: "this is the geometry, it's
  exact, it can't fake coherence."
- **C4 — Identity continuity (L10/L11):** surface the engine-identity hash,
  lineage chain, reboot-verification status — "the same continuous life
  across restart," the deepest telos, currently invisible.

### Phase D — The "they'd want to use it" layer (scope: M)
- **Guided Determinism Tour** — elevate Demo Theater into a first-run
  narrative: pick a demo, watch the proposer get disciplined, see
  hash-to-hash replay, see a wrong answer *refused*. "What this proves / what
  this does not prove" honesty cards on every scenario.
- **Provider-agnostic framing** — the pitch for Anthropic *and* xAI: "bring
  your own model's claim; watch the deterministic engine decide, refuse, and
  replay it." The Tool-Authority / Hybrid-Verification demos already embody
  this; make it the tour's spine.
- **Shareable evidence bundles** — deterministic export of a turn + its
  trace + replay + calibration verdict as a single citable artifact.
  Reproducibility *as a deliverable*.

### Phase E — Robustness pillars (scope: S; continuous)
- Extend doctrine gates to every new surface; SHA-pin the calibration/field
  readers where they assert a metric.
- Performance budget (resolve the Vite chunk-size warning via route
  code-split), error-boundary discipline, golden-file regime for the
  pipeline/field visualizers.

## What's missing in the design (the second ask, distilled)

| Missing surface | Why it matters for worthiness | Reader exists? |
|---|---|---|
| Calibration / gold-tether arena | Makes wrong=0 *earned*, not asserted — the most distinctive idea, invisible | **No** — build first |
| Serving-vs-learning regime frame | Names the two-regime architecture; without it the UI reads as a chatbot | No |
| wrong=0 as a felt global presence | The thesis itself; today only per-eval-run | Partial (ledger) |
| Cognitive pipeline visualizer | "Real replayable cognition" vs animated fake — the core wow | Trace exists; needs staging reader |
| Contemplation-as-process | The learning flywheel, today only its outputs | Partial |
| Field substrate / versor_condition | The geometry that *can't fake coherence* — honest, exact | **No** — build first |
| Identity continuity (L10/L11) | "One continuous life" — the deepest telos | No |
| Serving metrics reachable | The actual capability numbers (gsm8k) aren't viewable | No |

## Risks

- **Theater is risk #1** — mitigated by backend-reader-first + never
  re-implementing engine math. The gating work (B1, C1, C3 readers) is
  Python and parallel-safe.
- **The field surface must stay honest** — read-only over real
  `versor_condition`/`cga_inner`, no decorative geometry, no motion theater.
- **Scope is large** — several PR trains. Sequences as readers → routes →
  cross-wiring → tour. Phase A runs in parallel as polish.
- No timelines — phases/priorities/scope-sizes; sequencing is the dependency
  DAG, not a clock.

## Consolidated re-sequencing (amended 2026-06-13, after Phase B heart landed)

Phase B's heart is **done** — B1 (#724 readers), B2 (#725 Calibration route),
B3 (#726 wrong=0 frame) make the serving-discipline loop visible. A design
review of that work + an information-architecture decision now fold into a
single **Phase A (Structure & Polish) that runs BEFORE we resume Phase C** —
because two of them are structural prerequisites the Cognition cluster (C)
should land *into*, not extend a flat list past.

The governing insight: **the command-palette drift bug and the
grouped-navigation idea are the same fix.** Navigation must derive from one
registry that also encodes structure; build that once.

### Standing IA constraint (binds everything below)

**One workbench, one address space, one Chain Rail.** Grouping is a wayfinding
skin, never an architectural fork. A calibration class and the trace it
relates to stay co-addressable. We do **not** split into separate workbenches
— the single evidence model is the thesis. "Levels" are expressed as *depth
within a surface* (calm default / infinite depth), not as top-level
categories.

### Phase A — Structure & Polish (NEXT; runs before resuming C)

- **A1 — Navigation registry (one source of truth) + grouped nav + palette
  fix.** Today `LeftNav.NAV_ITEMS` and `CommandPalette.NAV_COMMANDS`/`NAV_PATHS`
  are two hardcoded lists that have **already drifted** — Demos (#723) and
  Calibration (#725) are in the nav but unreachable via `⌘K`, and the `⌘1–0`
  map is stale. Replace both with one `routes` registry `{ id, label, path,
  section, shortcut? }`; LeftNav renders it **grouped by section**;
  CommandPalette derives its nav commands and the `⌘` map from it (drift
  becomes structurally impossible — the same registry-driven move that made
  KeyboardHelp honest). Sections follow the organism's loop:
  **Converse · Cognition (core-logos) · Evidence · Determinism · Discipline ·
  Substrate · Settings.** Current routes group as: Chat→Converse;
  Trace/Runs/Audit/Vault→Evidence; Replay/Demos→Determinism;
  Evals/Calibration/Proposals→Discipline; Packs→Substrate; Settings→Settings.
  The **Cognition** group is created now (empty or near-empty) so Phase C's
  surfaces slot into a home rather than a flat tail.
- **A2 — Calibration earned-state (the centerpiece must show its thesis).**
  On committed data the Calibration route shows three classes all "not yet
  licensed" with empty bars — it never shows a class crossing θ, because the
  reader reads `practice/v1/report.json` `per_class`, whose committed copy is
  a sub-`N_MIN` baseline, while the *earned* state (`additive` committed=100,
  measured 0.86, **PROPOSE-licensed**) lives in the separately-committed
  `ratification_queue.json` — and the two artifacts disagree (correct:3 vs 95,
  different commits). **Primary fix:** regenerate the committed practice
  artifacts from one coherent run via the sealed practice runner so
  `report.json` per_class and the queue agree and the reader (unchanged) shows
  the earned class — deterministic regen, reviewed, no metric weakening.
  **Fallback** if regen is out of scope: the reader honestly surfaces *both*
  artifacts with provenance (the per_class ledger AND an "earned licenses"
  panel from the queue), each labeled by source. Either way the disagreement
  is resolved and the route shows its moment.
- **A3 — Doctrine station ("how this UI can't lie").** Elevate the
  "contracts/checks" instinct into a *surface*, not a folder: a read-only
  station that lists the doctrine gates (hexScan, schemaDrift across both
  snapshots, enumCoverage, route conformance, golden-file layout) and the
  load-bearing invariants (`wrong=0`, `versor_condition < 1e-6`), each with
  *what it proves* and a pointer to its executable check. Every other AI UI
  asks for trust; this one shows the proofs. Larger scope than A1/A2 — may
  trail into/after C, but it is the single most novel "worthy of the model"
  surface and belongs in the Cognition/meta neighborhood.
- Remaining Phase-A polish (density pref wiring, DAG's other two consumers,
  accessibility pass, tabular-nums/balance sweep) continues as before,
  parallel-safe.

Brief pack: `docs/handoff/wave-M-phaseA-briefs-2026-06-13.md`.

### Parked / deferred

- **B4 (per-turn leeway attribution)** is **blocked**: a served turn carries
  no calibration-class/license/θ. It needs an **engine-side** change to stamp
  ReachLevel/class/θ onto served results (its own ADR) — then B4 is a trivial
  display. Do not re-derive in the workbench (theater).
- **Calibration EvidenceSubject kind** (the route uses local selection today)
  — a conscious deferral, not an accident; revisit if a calibration class
  needs to thread the Chain Rail.

### Order

**A (A1 → A2 in parallel; A3 trails) → resume C (Cognition / core-logos
cluster) → D (tour) → E (continuous).** A1+A2 land before C so the Cognition
surfaces arrive into a grouped structure that already shows discipline
honestly.
