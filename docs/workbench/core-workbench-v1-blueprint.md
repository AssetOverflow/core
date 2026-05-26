# CORE Workbench v1 — Product + UX Blueprint

## Vision

CORE Workbench is not a chatbot shell.

It is:

- a cognition observatory,
- a replay theater,
- a proposal review station,
- a deterministic eval console,
- and a trust-boundary visualizer.

The system should feel:

- calm,
- precise,
- inspectable,
- authoritative,
- and progressively deep.

The design target is not “AI toy.”

The design target is:

> a cognition operating system for engineers and auditors.

---

# UX Principles

## 1. Calm by default

Most AI products overload the first screen.

CORE should not.

The first screen should show:

- prompt,
- response,
- grounding,
- replay status,
- proposal/refusal state,
- and almost nothing else.

Everything deeper should open progressively.

---

## 2. Evidence before persuasion

Never ask the operator to trust the answer emotionally.

Always allow:

- replay,
- provenance inspection,
- trace inspection,
- and mutation-boundary verification.

---

## 3. The deeper you go, the more transparent it becomes

Most frontier systems become more opaque under inspection.

CORE should become more legible.

---

## 4. No dashboard soup

No giant analytics walls.

Every component must answer:

- what happened?
- why?
- can it replay?
- what mutated?
- who has authority?

If not, remove it.

---

# Information Architecture

## Left navigation

Minimal:

- Chat
- Replay
- Proposals
- Evals
- Artifacts
- Runtime

No nested maze.

---

# Module Design

# 1. Chat Surface

## Goal

Minimal interaction layer.

## Layout

### Top Bar

- runtime mode
- backend
- replay status
- session id
- checkpoint status

### Main Conversation Area

Responses show:

- surface
- grounding source
- trace/replay badge
- proposal state
- refusal state

### Right-side Expandable Drawer

Collapsed by default.

Contains:

- articulation surface
- walk surface
- trace metadata
- replay digest
- admissibility evidence
- grounding provenance

---

# 2. Replay Theater

## Goal

Demonstrate deterministic replay visually.

## Core interaction

Select:

- run
- turn
- artifact
- eval result

Then compare:

| Original | Replay |
|---|---|
| trace hash | trace hash |
| surface | surface |
| grounding | grounding |
| replay status | replay status |
| divergences | divergences |

## Visual style

Extremely restrained.

This should feel like:

- debugger,
- theorem proof,
- mission control.

Not:

- animated AI theater.

---

# 3. Proposal Review Queue

## Goal

Make proposal lifecycle understandable.

## Queue item fields

- proposal_id
- state
- source_kind
- replay_equivalent
- downstream effect
- contemplation evidence
- proposal chain
- proposal digest
- created_at

## Detail panel

Should support:

- replay evidence
- downstream comparison
- linked eval artifacts
- cognition chain diff
- provenance graph

## Important

V1 is read-only.

No accept/reject buttons yet.

Only:

- copy CLI command
- open artifact
- inspect replay

---

# 4. Eval Center

## Goal

Turn deterministic evals into visible operational quality.

## Initial lanes

- cognition
- contemplation-quality
- learning-arc

## Per-result display

- pass/fail
- metric table
- drift
- replay status
- source digest
- linked artifacts

## Critical UX detail

Failures must be more visible than successes.

The system should encourage investigation, not vanity metrics.

---

# 5. Runtime / Artifact Explorer

## Goal

Expose runtime state without mutating it.

## Displays

- engine_state manifests
- reboot events
- revision mismatch warnings
- proposal logs
- eval results
- contemplation reports
- telemetry artifacts

Should feel:

- filesystem-like,
- deterministic,
- structured,
- low-noise.

---

# Design Language

## Visual direction

Closest inspirations:

- Linear
- Raycast
- Apple developer tooling
- GitHub PR review
- Mission control

Not:

- neon AI dashboards
- glassmorphism overload
- streaming gimmicks
- fake thinking animations

---

# Motion

Use motion only for:

- panel expansion
- replay comparison transitions
- trace drilldown
- timeline navigation

No decorative movement.

---

# Typography

Prioritize:

- legibility,
- hierarchy,
- audit readability,
- JSON readability,
- terminal readability.

---

# Color Philosophy

Mostly monochrome.

Use color only for:

- replay success/failure
- mutation state
- refusal state
- proposal state
- eval severity

Color should mean something operational.

---

# Backend API Shape

## Read-only endpoints

Initial workbench API should expose:

- GET /runtime/status
- GET /runtime/checkpoints
- POST /chat/turn
- GET /chat/turn/{id}
- GET /trace/{id}
- GET /replay/{id}
- GET /proposals
- GET /proposals/{id}
- GET /evals
- POST /evals/run
- GET /artifacts/{id}

No mutation endpoints in v1.

---

# Security / Doctrine

## Must preserve

- ADR-0057 proposal boundaries
- ADR-0151 contemplation review doctrine
- ADR-0159 read-only eval semantics
- ADR-0146 persistence guarantees

## Must never do silently

- mutate corpus
- accept proposals
- mutate packs
- trigger remote workflow commits
- mutate engine_state outside runtime

---

# Success Condition

The correct reaction from an engineer seeing CORE Workbench is:

> “Wait… I can actually inspect and replay the cognition?”

not:

> “Cool chatbot.”
