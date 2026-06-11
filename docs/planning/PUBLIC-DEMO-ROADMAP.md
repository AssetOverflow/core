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

### Hybrid Verification Demo (#687 — authority over claims)

Status: merged (PR #687).

Purpose: demonstrate a bounded proposer-to-substrate verification path with typed outcomes. A model-style proposer submits a claim; the substrate, not the proposer, decides the typed outcome.

Hard finding recorded by this demo: agreement between reasoning paths is not reliable safety. Multiple paths can agree and still be wrong. Authority must live at the typed boundary, not merely in multiple model outputs.

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

### Tool Authority Demo (#688 — authority over proposed tool actions)

Status: merged (PR #688, merge commit `c55f7dfb`).

Purpose: demonstrate that a model-style proposer may submit a typed action proposal, while CORE alone may authorize, ask, refuse, or invalidate. The authorized output is an inert `licensed_action` artifact only; no external side effect executes and the proposer holds no execution authority.

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

Recommended order of next public evidence:

1. Epistemic Truth-State Demo (next target);
2. Embodied Authority Simulation Demo (simulation-only);
3. SaaS / On-Prem Boundary Demo.

Merged evidence so far establishes two authority boundaries: authority over claims (#687) and authority over proposed tool actions (#688). The next target extends the same pattern to epistemic state.

### Epistemic Truth-State Demo (next public evidence target)

Status: proposed.

Purpose: show that a model-style proposer can submit a claim, answer, or state proposal, but CORE assigns the typed epistemic state and emits deterministic, replayable evidence. The proposer controls neither the assigned state nor the trace.

Possible states (illustrative; the implementing PR fixes the closed set):

- `perceived`;
- `evidenced`;
- `verified`;
- `decoded`;
- `inferred`;
- `refused`;
- `undetermined`;
- `scope_boundary`;
- `invalid`.

Possible outputs:

- state ledger entry;
- evidence / provenance spans;
- deterministic trace hash;
- `ask` or refusal when evidence is insufficient;
- no proposer-controlled state;
- no proposer-controlled trace;
- `invalid` rejected before state evaluation.

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
