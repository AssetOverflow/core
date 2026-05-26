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
