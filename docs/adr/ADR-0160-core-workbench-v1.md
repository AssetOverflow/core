# ADR-0160 — CORE Workbench v1: operator/auditor UI before public chat

Status: proposed
Date: 2026-05-26

## Context

CORE now has the first complete contemplation/review corridor:

- ADR-0152 — learning-arc proof corridor
- ADR-0155 — CI contemplation reports
- ADR-0156 — atomic checkpoint writes
- ADR-0157 — revision-mismatch warning
- ADR-0158 — reboot-event audit trail
- ADR-0159 — contemplation-quality eval lane

The next surface should not be a generic chatbot clone.  CORE's distinction is
not merely that it can answer prompts; it is that its cognition can be inspected,
replayed, audited, reviewed, and ratified under explicit trust boundaries.

A UI that hides this machinery would erase the strongest architectural evidence.
A UI that exposes everything by default would become cognitive noise.

The correct first UI is therefore an operator/auditor workbench with a small
chat surface and deep progressive disclosure.

## Decision

Build **CORE Workbench v1** as the first UI/UX surface.

The v1 product is an admin/engineer/dev/auditor interface with five primary
modules:

1. **Chat Surface** — minimal prompt/response interface for live turns.
2. **Trace Drawer** — per-turn inspection of surfaces, trace hashes, grounding,
   replay indicators, proposal/candidate metadata, and telemetry.
3. **Proposal Review Queue** — pending proposals, contemplation provenance,
   replay evidence, downstream effect, and accept/reject readiness.
4. **Eval Center** — run/read deterministic eval lanes including cognition,
   learning-arc, and contemplation-quality.
5. **Replay Theater** — select an artifact or turn and compare deterministic
   replay evidence against the original.

The first implementation phase is planning + read-only observability.  Mutating
actions (proposal acceptance, corpus mutation, workflow dispatch) require a later
ADR and explicit operator confirmation gates.

## Product doctrine

### Calm default, infinite depth

The UI must be quiet by default.  The first screen should show a response and
small trust badges, not a wall of internal machinery.  Deep evidence is revealed
through drawers, split panes, and artifact inspectors.

### Audit-native, not analytics theater

The workbench is not a generic dashboard.  Every panel must answer one of these
questions:

- What happened?
- Why was it allowed?
- What evidence supports it?
- Can it be replayed?
- Did it mutate anything?
- Who/what has authority to ratify the next step?

If a panel cannot answer one of those questions, it does not belong in v1.

### Proposal before mutation

The workbench may visualize proposals and review readiness.  It must not add a
parallel learning path.  Proposal acceptance remains governed by teaching review
and existing ADR-0057/0151 doctrine.

### Replay before persuasion

The UI should never ask the operator to trust an impressive answer.  It should
show replay status, trace identity, provenance, and mutation boundaries first.

## Architecture choice

### Frontend

Adopt a thin React/Vite/TypeScript workbench:

- React + Vite + TypeScript
- TanStack Query for API state
- Zustand or Jotai for local UI state
- Tailwind + shadcn-style primitives for consistent low-noise UI
- Monaco only where structured JSON/editor inspection is necessary
- xterm-like console only where raw CLI/replay output genuinely helps

No Electron in v1.  No heavy design system.  No plugin marketplace.  No agent
workflow builder.

### Backend

Expose a narrow local API over the existing runtime surfaces:

- chat turn endpoint / stream endpoint
- trace/artifact read endpoints
- proposal-log read endpoint
- eval lane run/read endpoint
- replay artifact read/compare endpoint
- telemetry read endpoint

The backend must remain local-first and deterministic.  Any endpoint that can
mutate corpus, packs, proposals, engine_state, or workflows is out of scope for
v1 unless a later ADR explicitly admits it.

## Trust boundary

V1 is **read-only by default**.

Allowed:

- read telemetry JSONL
- read proposal logs
- read contemplation run artifacts
- read eval results
- run read-only eval lanes
- execute chat turns against existing runtime APIs
- display trace/replay metadata

Forbidden in v1:

- accepting proposals
- rejecting proposals as durable state
- mutating teaching corpus
- mutating packs
- writing engine_state except through normal runtime checkpoint path already
  governed by ADR-0146/0150
- workflow dispatch that commits to main
- hidden background jobs
- remote network dependencies for cognition

## Module contracts

### 1. Chat Surface

Purpose: live interaction with visible trust badges.

Required visible signals:

- grounding source
- replay/trace id when available
- refusal/review state when applicable
- mutation status: none / transient / proposal-only / ratified

### 2. Trace Drawer

Purpose: expose one turn's evidence stack.

Should display:

- final `surface`
- `articulation_surface` when present
- `walk_surface` as telemetry/evidence only
- trace hash / replay digest
- grounding source
- proposal/candidate references
- rejected/admissibility evidence when available

Must preserve the runtime surface contract: user surface and telemetry evidence
remain distinct.

### 3. Proposal Review Queue

Purpose: make proposal lifecycle legible.

V1 displays only:

- pending proposal id
- source.kind / source_id
- replay-equivalence evidence
- proposed chain
- candidate evidence
- review state
- downstream quality signal if present

V1 does not accept/reject.  It can show exact CLI command suggestions for local
operator review, but must not execute them.

### 4. Eval Center

Purpose: make deterministic quality lanes discoverable.

Required initial lanes:

- cognition
- learning-arc demo report view
- contemplation-quality

Eval Center must distinguish:

- lane execution
- stored result inspection
- failure details
- mutation boundary

### 5. Replay Theater

Purpose: demonstrate deterministic replay as an experience, not a footnote.

V1 should support:

- selecting a run/turn/report
- showing original artifact hash
- showing replay result hash
- comparing metrics and surfaces
- highlighting divergence, if any

## Non-goals

- public marketing site
- multi-tenant SaaS
- hosted cloud service
- auth system beyond local operator mode
- background daemon requirement
- arbitrary plugin execution
- agent marketplace
- broad chat polish before audit polish
- replacing CLI lanes

## Acceptance criteria

The first implementation PR after this planning ADR should include only the
minimal skeleton necessary to prove the workbench shape:

- local API skeleton or documented endpoint contract
- frontend shell with navigation
- static/mock-free read-only panels wired to real local files or real local API
  where practical
- no corpus/packs/proposals mutation path
- no hidden background jobs
- no remote dependencies
- README/runbook for local launch

A future implementation PR may add proposal mutation only after a separate ADR
ratifies the operator confirmation flow.

## Consequences

Positive:

- Gives CORE a surface that matches its actual strengths.
- Makes replay/audit/proposal boundaries visible.
- Creates an investor/engineer demo that is not reducible to chatbot fluency.
- Preserves existing ADR trust boundaries.

Negative:

- More work than a simple chat UI.
- Requires careful API design to avoid accidental mutation paths.
- Forces discipline in telemetry and artifact schemas.

## Follow-up work

- W-026: Workbench endpoint contract and local read-only API.
- W-027: Workbench frontend shell and navigation.
- W-028: Chat Surface + Trace Drawer read-only wiring.
- W-029: Proposal Review Queue read-only wiring.
- W-030: Eval Center + contemplation-quality display.
- W-031: Replay Theater artifact comparison.
