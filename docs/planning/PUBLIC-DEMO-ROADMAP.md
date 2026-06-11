# Public Demo Roadmap

This document tracks public, evidence-oriented CORE demos. It intentionally excludes private outreach strategy, named-company planning, fundraising material, and executive packet work.

## Public boundary

Public repository docs may describe:

- implemented demos;
- proposed demos;
- deterministic test requirements;
- trace artifacts;
- honesty ledgers;
- public-safe architecture boundaries.

Public repository docs must not include:

- named-company outreach strategy;
- named-person contact plans;
- sponsorship or runway asks;
- private packet planning;
- company-specific red-team personas;
- current-facts dossiers for outreach.

## Demonstrated

### Hybrid Verification Demo

Status: merged.

Purpose: demonstrate a bounded proposer-to-substrate verification path with typed outcomes.

Public outcome vocabulary:

- `verified`
- `refused`
- `ask`
- `invalid`

Public safety boundary:

- no model API;
- no network;
- no external side effects;
- deterministic trace artifacts;
- honesty ledger included.

## In progress

### Tool Authority Demo

Status: draft PR / in review.

Purpose: demonstrate that a model-style proposer may submit a typed action proposal, while CORE alone may authorize, ask, refuse, or invalidate.

Public outcome vocabulary:

- `authorized`
- `ask`
- `refused`
- `invalid`

Public safety boundary:

- no real tool execution;
- no real email sending;
- no shell execution;
- no network;
- inert `licensed_action` artifact only;
- MCP-shaped, not production MCP.

## Proposed

### Epistemic Truth-State Demo

Status: proposed.

Purpose: make epistemic state transitions visible and replayable in a public-safe demo.

Possible states include:

- perceived;
- evidenced;
- verified;
- inferred;
- contradicted;
- undetermined;
- refused;
- ask.

No claim is made here that the full demo is implemented until a PR lands.

### Embodied Authority Simulation Demo

Status: proposed, simulation-only.

Purpose: demonstrate an authority-boundary pattern for model-proposed simulated transitions.

Public safety boundary:

- no real robot;
- no real actuator;
- no vehicle-control claim;
- no production robotics claim;
- no certified functional-safety claim;
- simulation-only fixtures.

### SaaS / On-Prem Boundary Demo

Status: proposed.

Purpose: demonstrate a public-safe split between coordination metadata and local authority decisions.

No claim is made here that a production SaaS or on-prem deployment exists.

## Packaging rule

Each public demo should include:

- README;
- fixtures;
- expected outputs;
- deterministic runner;
- tests;
- honesty ledger;
- "what this proves";
- "what this does not prove."
