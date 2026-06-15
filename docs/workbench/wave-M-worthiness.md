# Wave M — CORE Workbench: Mastery & Worthiness

> **Historical record — superseded.** This is the planning doc for its wave and
> records that wave, not current state. Wave M is complete (Phase B/C/D + B4
> leeway producer all merged). For the live surface see [`README.md`](./README.md)
> (Current Status), [`UI-UX-GUIDE.md`](./UI-UX-GUIDE.md), and the route registry
> `workbench-ui/src/app/routes.ts` (16 routes).

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
   field substrate, `versor_condition`, identity continuity. C1 (pipeline),
   C2-a (contemplation), C3-a (field substrate), and a first C4 run-level
   identity projection now exist. For an audience that lives inside opaque
   models, *legible deterministic cognition* is the wow.

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
  **Implementation note (2026-06-13):** Demo Theater now renders backend-owned
  `DemoEvidenceDag` projections for all proof-carrying promotion scenarios and
  deductive-entailment traces. The shared DAG primitive now has proposal,
  cognitive-pipeline, PCCP, and entailment consumers.
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
  replayable path, not animated fake cognition" surface.
  **Persistence-first constraint (verified 2026-06-13):** this is NOT
  reader-first over existing telemetry — the journal does not persist the
  stage internals. `CognitiveTurnResult` carries ~25 fields (field_state,
  proposition, proposition_graph, intent, admissibility_trace,
  operator_invocation, dropped_compound_clauses, versor_condition, …) but
  `TurnJournalEntry` persists only ~12 surface fields, and `_run_chat_turn`
  discards the rest; there is no `/trace/{id}/pipeline` endpoint and the data
  was never written. So **C1-a's real first deliverable is a persistence
  change, not an API route**: persist a *curated* `CognitivePipelineRecord`
  at turn-write time, then the endpoint is a trivial read-only projection.
  Two hard constraints: (1) persist the cheap structured stage records +
  `versor_condition` as a scalar (and at most a field *digest*) — **never the
  raw `field_state_before/after` multivectors**, which would resurrect the
  deferred per-turn O(n²) persistence cost and contradict the L10
  discard-on-exit design; (2) it touches the runtime surface contract
  (`CognitiveTurnResult → ChatTurnResult → TurnJournalEntry` is two narrowing
  hops), so the PR updates `docs/runtime_contracts.md` + a **non-vacuous
  fail-closed test** that a silently-dropped stage fails loudly (CLAUDE.md
  Schema-Defined Proof Obligations), and pre-widening turns show
  `missing_evidence`, not green. The replay-reconstruction fallback (Option B)
  recomputes rather than reads recorded state — fallback only, never primary.
  **C1-a implementation note (2026-06-13):** new `/chat/turn` journal rows now
  carry `CognitivePipelineRecord` with input → intent → PropositionGraph →
  ArticulationTarget → realizer → walk telemetry → trace hash stages; `/trace`
  renders it as a deterministic DAG and renders pre-widening rows as
  `missing_evidence`. Full C1 still needs richer readers/inspection beyond
  this first persisted substrate.
  **C1-b/C1-c implementation note (2026-06-13):** `/trace/{turn_id}/pipeline`
  is now the canonical read-only projection over the persisted record, and the
  Trace route renders a deterministic stage rail + DAG + selected-stage detail
  inspector. This completes the first usable pipeline visualizer over recorded
  stage evidence; later C1 expansion should add new engine-owned stage facts
  only by widening `CognitivePipelineRecord`, not by replay recomputation or UI
  inference.
- **C2 — Contemplation as a process, not just outputs:** the contemplation
  *loop* (attempt → gold-tether → ClassTally → propose), connecting
  Demos/Proposals/Calibration into one story.
  **C2-a implementation note (2026-06-13):** Workbench now exposes persisted
  `contemplation/runs/*.json` process reports through `/contemplation`: cold
  attempt, checkpoint enrichment, engine-authored proposal boundary,
  ratification boundary, and grounded-after scenes remain report-authored
  evidence. This is the first process trace; the fuller Calibration/Proposal
  integrated loop is still open.
  **C2-b implementation note (2026-06-13):** the run detail is no longer a flat
  JSON dump — each scene is now a typed loop stage. The reader
  (`_contemplation_scenes`) projects every scene onto a canonical
  `stage_role` (`cold_attempt`/`engine_enrichment`/`engine_proposal`/
  `operator_ratifies`/`grounded`/`other`) and pulls the loop's connective ids
  (`proposal_id`, `candidate_id`, `proposal_state`, `grounding_source`) out of
  the raw detail; the UI renders the arc "attempt → enrich → propose → ratify →
  grounded" with named stages, cold→grounded bookends, and the ids as evidence.
  **Honest wrinkle (surfaced, not faked):** the fixture proposals do NOT resolve
  in the live proposal log (source_kinds `exemplar_corpus`/`operator`, none
  `contemplation`), so the proposal id is shown as evidence but is intentionally
  NOT a clickable cross-route link — a dead link would be theater. Live
  Proposals/Calibration navigation is deferred until real contemplation
  proposals reach the log (reader-verified linking is the follow-up).
- **C3 — Field substrate (honest, read-only, hard):** real `FieldState` +
  `versor_condition` for a turn, rendered as **inspectable exact numbers and
  invariant status** — `versor_condition < 1e-6` as a live "field is valid"
  assertion, `cga_inner` as an exact transition value. **NOT** a decorative 3D
  blob; no force-directed/nondeterministic motion. The honesty is the
  impressiveness: "this is the geometry, it's exact, it can't fake coherence."
  **C3-a implementation note (2026-06-13):** BUILT persist-first. Per-turn
  `FieldEvidence` (exact `versor_condition`, `field_valid` vs the `1e-6`
  ceiling, a content-addressed `field_digest`, and `cga_inner(before, after)`)
  is computed in `workbench/field_evidence.py` from the engine result and
  persisted on the journal entry at `from_chat_turn` — the raw multivector
  never crosses the boundary, only scalars + digests. The read endpoint is a
  trace facet (`GET /trace/{turn_id}/field`, consistent with `/pipeline`) and
  the surface is the Trace route's **Field** tab. `field_valid` is
  consistency-checked against the ceiling at construction, so it can never claim
  validity while `versor_condition` breaches `1e-6` (the wrong=0 analogue).
  Honest `missing_evidence` for pre-widening journal rows. Deferred: cross-turn
  field-coherence trends and session-level field persistence.
- **C4 — Identity continuity (L10/L11):** surface the engine-identity hash,
  lineage chain, reboot-verification status — "the same continuous life
  across restart," the deepest telos.
  **C4-a implementation note (2026-06-13):** `RunDetail` now carries a typed
  `IdentityContinuity` projection from `engine_state/manifest.json` and the
  current ratified substrate identity. Runs renders an Identity tab with
  engine/current/parent digests, lineage relation, revision pair, verified vs
  break vs missing-evidence status, and no frontend manifest inference.

### Phase D — The "they'd want to use it" layer (scope: M)
- **Guided Determinism Tour** — elevate Demo Theater into a first-run
  narrative: pick a demo, watch the proposer get disciplined, see
  hash-to-hash replay, see a wrong answer *refused*. "What this proves / what
  this does not prove" honesty cards on every scenario.
- **Provider-agnostic framing** — the pitch for Anthropic *and* xAI: "bring
  your own model's claim; watch the deterministic engine decide, refuse, and
  replay it." The Tool-Authority / Hybrid-Verification demos already embody
  this; make it the tour's spine.
  **D1+D2 implementation note (2026-06-13):** BUILT as the first-class `/tour`
  route. `workbench/tour.py::determinism_tour()` is a curated, ordered narrative
  bound to the **real** demo registry: intro (the provider-agnostic thesis) →
  three demo steps (deductive entailment decides; epistemic truth-state refuses
  a wrong proposer; proof-carrying promotion ignores proposer authority) →
  payoff (replay-to-the-same-hash + the citable evidence bundle). **Honesty by
  construction:** each demo step's `what_this_proves` / `what_this_does_not_prove`
  cards are pulled from the real demo spec (never re-authored), and a step that
  references a missing demo **fails closed** (`KeyError`) rather than becoming a
  dead link — a test asserts both. The spine is the three substrate-capability
  demos that exist today (the named Tool-Authority/Hybrid demos are not in the
  registry); the thesis carries the bring-your-model framing. Read endpoint
  `GET /tour`; route registered in the registry (Determinism section, 14 routes).
- **Shareable evidence bundles** — deterministic export of a turn + its
  trace + replay + calibration verdict as a single citable artifact.
  Reproducibility *as a deliverable*.
  **D3 implementation note (2026-06-13):** BUILT. `workbench/evidence_bundle.py`
  assembles a turn journal entry into a content-addressed `EvidenceBundle`
  composing the Phase-C evidence (pipeline + field) with the trace and the
  calibration leeway verdict. The `bundle_digest` content-addresses the
  **deterministic cognitive evidence only** — journal position + wall-clock
  (`turn_id`, `journal_digest`, `replay_reproducer`) are carried for provenance
  but excluded, so the same turn content reproduces the same digest (verified by
  test: identical content → identical digest; different journal position → same
  digest; any evidence change → different digest). Read endpoint
  `GET /trace/{turn_id}/bundle`; surfaced as the Trace **Bundle** tab (citable
  digest, "what this proves / does not prove" honesty note, reproducer command,
  deterministic JSON download). Read-only, no engine execution. The bundle
  carries the replay *reproducer* rather than a live-run replay so the artifact
  itself stays deterministic — verification is the consumer's step. Phase D
  remaining: guided determinism tour (D1) + provider-agnostic framing (D2).

### Phase E — Robustness pillars (scope: S; continuous)
- Extend doctrine gates to every new surface; SHA-pin the calibration/field
  readers where they assert a metric.
- Performance budget (resolve the Vite chunk-size warning via route
  code-split), error-boundary discipline, golden-file regime for the
  pipeline/field visualizers.
  **Route chunk-split implementation note (2026-06-13):** Workbench routes now
  load through React lazy route elements while preserving the registry contract.
  `pnpm build` emits route chunks and the entry bundle is below the 500 kB Vite
  warning threshold without raising the budget.

## What's missing in the design (the second ask, distilled)

| Missing surface | Why it matters for worthiness | Reader exists? |
|---|---|---|
| Calibration / gold-tether arena | Makes wrong=0 *earned*, not asserted — the most distinctive idea, invisible | **No** — build first |
| Serving-vs-learning regime frame | Names the two-regime architecture; without it the UI reads as a chatbot | No |
| wrong=0 as a felt global presence | The thesis itself; today only per-eval-run | Partial (ledger) |
| Cognitive pipeline visualizer | "Real replayable cognition" vs animated fake — the core wow | Trace exists; needs staging reader |
| Contemplation-as-process | The learning flywheel, today only its outputs | Partial — persisted process reports |
| Field substrate / versor_condition | The geometry that *can't fake coherence* — honest, exact | **No** — build first |
| Identity continuity (L10/L11) | "One continuous life" — the deepest telos | Partial — run-level manifest projection |
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


## Consolidation & re-sequencing — see B3.5

Phase B's heart is done (B1 #724 / B2 #725 / B3 #726). The consolidation that
must happen before Phase C — route-registry unification (kills the
command-palette drift), calibration becoming evidence-native, the B4
feasibility gate, the UI/UX guide, and the Phase-A residue ledger — is
governed by **`wave-m-consolidation-b3.5.md`** (deliverables B3.5-a … e). That
doc is authoritative for the consolidation slice; this plan's Phase A items
fold into B3.5-e (the residue ledger). The grouped-navigation idea and the
Calibration earned-state fix are folded into B3.5 (D1 `section` field; D2
acceptance). Related parallel tracks: `core-logos-studio-plan.md` (the
language/manifold Substrate surface) and `proposal-artifact-substrate-v1.md`
(the universal proposal envelope).

**Order:** B3.5 (consolidation) → resume Phase C (cognition legibility) →
D (tour) → E (continuous). B4 stays parked behind B3.5-c's feasibility gate.
