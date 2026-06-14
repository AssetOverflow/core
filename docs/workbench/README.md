# CORE Workbench v1

CORE Workbench is the first dedicated operator/auditor UI for CORE.

It is intentionally designed as:

- a cognition observatory,
- replay debugger,
- proposal review workstation,
- deterministic eval console,
- and audit surface.

It is NOT intended to be a generic chatbot shell.

---

# Document Index

## Doctrine

- `../decisions/ADR-0160-core-workbench-v1.md`

Defines:

- product doctrine
- trust boundaries
- architecture direction
- module scope
- acceptance criteria

---

## UX Blueprint

- `core-workbench-v1-blueprint.md`

Defines:

- visual philosophy
- interaction model
- module behavior
- navigation
- replay/proposal/eval UX

---

## Implementation Plan

- `implementation-plan.md`

Defines:

- W-026 through W-031
- phase sequencing
- backend/frontend constraints
- release criteria

---

## API Contract

- `api-contract-v1.md`

Defines:

- read-only endpoint surface
- request/response envelopes
- mutation boundaries
- runtime/trace/proposal/eval/replay routes

---

## Data Shapes

- `data-shapes-v1.md`

Defines:

- typed UI-facing shapes
- proposal structures
- replay structures
- artifact references
- trust badges

---

## Proposal Artifact Substrate

- `proposal-artifact-substrate-v1.md`

Defines:

- the universal proposal artifact envelope
- subject-specific proposal adapters
- proposal-only vs ratification-enabled capability levels
- safety, validation, affected-artifact, and checksum-impact report shapes
- the migration path for math, cognition, CORE-Logos, packs, and future modalities

---

## Wave M Consolidation / B3.5

- `wave-m-consolidation-b3.5.md`

Defines:

- the route-registry unification plan
- calibration as a first-class evidence subject
- the B4 leeway-feasibility gate
- the UI/UX guide requirement
- the Phase A residue ledger before further complexity

Supporting B3.5 deliverables:

- `UI-UX-GUIDE.md` — operator/evaluator route map, evidence grammar, route
  proofs, boundaries, and absences.
- `b4-leeway-feasibility-gate.md` — B4 source-tuple audit and B4a nullable
  read model (gate CLEARED 2026-06-13; the producer now exists).
- `b4-leeway-producer-scope-2026-06-13.md` — the engine-side leeway producer
  scope: the serving-path seam, the `LicenseDecision`→`LeewayEvidence` mapping,
  and the two honest layers (STRICT / earned-`APPROXIMATE`).
- `phase-a-residue-ledger.md` — implemented/deferred/blocked residue.

---

## Mastery & Worthiness Waves (1 / R / M)

The plans that took the surface from read-only spine to "worthy of the
deterministic engine":

- `wave-1-evidence-spine.md` — the evidence-address model (URL = subject),
  Evidence Chain Rail, and RightInspector.
- `wave-R-mastery-revamp.md` — the 11 real routes, the Replay Moment, trace
  integrity, and the DAG/Demo/wrong=0 surfaces.
- `wave-M-worthiness.md` — the governing plan for the worthiness arc:
  Phase B (calibrated-learning / serving discipline), Phase C (cognition
  legibility), Phase D (guided tour + shareable evidence bundles), Phase E
  (robustness). Per-deliverable implementation notes live inline.

---

## Design System

- `design-system.md` — semantic token roles, density, primitives, and the
  motion / calm-honesty discipline.

---

## CORE-Logos Studio

- `core-logos-studio-plan.md`

Defines:

- the `/logos` Studio route concept
- pack identity, lexicon, glosses, morphology, alignment, holonomy, safety, and patch-forge tabs
- CORE-Logos evidence subjects
- read-only readers and proposal-only draft endpoint direction
- the handler-family admission sequence for future ratification

---

## UI Component Map

- `ui-component-map.md`

Defines:

- page layout
- navigation structure
- shared components
- trace drawer structure
- proposal/eval/replay modules

---

## Acceptance Gates

- `acceptance-gates.md`

Defines:

- implementation gates
- red flags
- release conditions
- mutation restrictions

---

# Core Principles

## Replay before persuasion

The UI should make replay evidence more important than aesthetic persuasion.

## Calm by default

The interface should remain quiet and precise.

## Progressive disclosure

The system should become more transparent the deeper an operator inspects.

## Proposal is not ratification

The UI must preserve ADR-0057 review doctrine.

## Read-only first

The first workbench phases prioritize visibility and auditability before any
mutation capability.

---

# Current Status (2026-06-13)

The Workbench is shipped and well past the W-026…W-031 planning era. The
read-only local API + React UI are real; W-026 (read-only API) through W-031
(replay theater) all landed, followed by the Wave 1 evidence spine, the Wave R
mastery revamp (11 routes + the Replay Moment), and the Wave M worthiness arc.

**Wave M is complete** — Phase B (calibrated-learning surfaces), Phase C
(cognition legibility), Phase D (guided tour + evidence bundles), and the B4
leeway producer all merged. Phase E (robustness; continuous) and the parallel
tracks (CORE-Logos Studio, the universal proposal envelope) remain.

Doctrine is unchanged: read-only first, allowlisted execution only
(`/evals/run`, ratify, `/demos/{id}/run`), every surface a real backend reader
(no theater), determinism over persuasion.

## Shipped surfaces

14 registry-driven routes (`src/app/routes.ts`), grouped by section:

| Section | Routes |
|---|---|
| Converse | **Chat** |
| Cognition | **Trace** (Pipeline / Field / Bundle / Surfaces / Grounding / Verdicts tabs), **Contemplation** (staged learning loop) |
| Determinism | **Tour** (guided determinism narrative), **Replay** (hash-to-hash), **Demos** (Demo Theater) |
| Evidence | **Proposals** (+ HITL ratification), **Runs** (+ identity continuity), **Vault**, **Audit** |
| Discipline | **Evals** (wrong=0 ledger), **Calibration** (gold-tether arena, Wilson floor vs θ) |
| Substrate | **Packs** |
| Settings | **Settings** (landing / density / inspector prefs) |

Cross-cutting: Evidence Address (URL = subject, `?inspect=`), Evidence Chain
Rail, command palette + registry-driven keyboard help, per-turn pipeline /
field / leeway / bundle evidence, doctrine gates (hexScan, schemaDrift,
enumCoverage, route conformance, golden-file DAG layout).

---

# W-026 Local Runbook

Start the read-only local API:

```bash
core workbench api
```

Verify liveness:

```bash
curl http://127.0.0.1:8765/health
```

Inspect each W-026 endpoint family:

```bash
curl http://127.0.0.1:8765/runtime/status
curl http://127.0.0.1:8765/artifacts
curl http://127.0.0.1:8765/artifacts/evals/contemplation_quality/contract.md
curl http://127.0.0.1:8765/proposals
curl http://127.0.0.1:8765/evals
curl http://127.0.0.1:8765/evals/contemplation_quality
curl -X POST http://127.0.0.1:8765/evals/run \
  -H 'Content-Type: application/json' \
  -d '{"lane":"contemplation_quality","version":"v1","split":"public"}'
```

Bind to a different local port:

```bash
core workbench api --port 9000
```

Non-local binds require an explicit operator flag:

```bash
core workbench api --host 0.0.0.0 --allow-nonlocal-bind
```

---

# Initial Work Queue (delivered)

The original W-026…W-031 queue is complete; it is kept here as provenance.
Current work is tracked in the Wave M worthiness plan and the residue ledger.

| Work Item | Goal | Status |
|---|---|---|
| W-026 | Read-only API | done |
| W-027 | Frontend shell | done |
| W-028 | Chat + trace drawer | done |
| W-029 | Proposal queue | done |
| W-030 | Eval center | done |
| W-031 | Replay theater | done |

---

# Guiding Question

The correct operator reaction to the workbench should be:

> “Wait… I can actually inspect and replay the cognition.”

not:

> “Cool chatbot.”
