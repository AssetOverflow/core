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
  read model.
- `phase-a-residue-ledger.md` — implemented/deferred/blocked residue before
  Phase C.

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

# Current Status

The planning package is merged on `main` via `404e694`
(`docs(workbench): CORE Workbench v1 planning architecture (ADR-0160)`).

The prototype branch `feat/w026-workbench-readonly-api` is superseded and must
not be used as the implementation base.  It mixed W-026 with frontend and trace
work, added auth and web-framework dependencies before the local read-only
boundary was proven, and included placeholder replay/trace behavior that could
be mistaken for evidence.

The next accepted implementation starts clean from `main` with W-026 only:
dataclass schemas, repo-root-constrained readers, a standard-library local HTTP
API, and route/read-model tests.  W-027 and later phases build on that boundary
after it is accepted.

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

# Initial Work Queue

| Work Item | Goal |
|---|---|
| W-026 | Read-only API |
| W-027 | Frontend shell |
| W-028 | Chat + trace drawer |
| W-029 | Proposal queue |
| W-030 | Eval center |
| W-031 | Replay theater |

---

# Guiding Question

The correct operator reaction to the workbench should be:

> “Wait… I can actually inspect and replay the cognition.”

not:

> “Cool chatbot.”
