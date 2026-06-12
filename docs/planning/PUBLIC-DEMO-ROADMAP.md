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

## Evidence strength

Public demos must distinguish the strength of the evidence they provide.

**Substrate-capability demos** route the proposal through a real CORE operator,
runtime path, sealed eval lane, or independently checked proof surface. These demos
may support capability claims, within their stated envelope.

**Interface-contract demos** prove the typed boundary: closed schema, fail-closed
validation, proposer-held status ignored, inert outputs, deterministic traces, and
no side effects. These demos are useful, but they must not be described as proving
deep CORE reasoning capability by themselves.

This distinction is load-bearing. A demo that only checks strings, booleans, or
schema shape may prove an authority boundary; it does not prove that the geometric
or deductive substrate made a non-trivial decision.

## Demonstrated

### Hybrid Verification Demo (#687 — authority over claims)

Status: merged (PR #687).

Evidence class: substrate-capability demo.

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

Evidence class: interface-contract demo.

Purpose: demonstrate that a model-style proposer may submit a typed action proposal, while CORE alone may authorize, ask, refuse, or invalidate. The authorized output is an inert `licensed_action` artifact only; no external side effect executes and the proposer holds no execution authority.

Evidence caveat: this demo proves the digital-action boundary contract. Its local
authority evaluator is deliberately small, so it must not be described as proving
general tool-safety reasoning or production MCP capability. Its value is that the
proposer cannot self-authorize, inject a license, supply a trusted trace hash, or
cause side effects.

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

### Epistemic Truth-State Demo (#690 — authority over state assignment)

Status: merged (PR #690); hardened in this reconciliation pass to use sealed
evidence references and an entailment-decided inference leg.

Evidence class: local epistemic-state authority demo; the `inferred` leg is a
substrate-capability decision (it routes through the proof-chain entailment
engine with an independent-oracle cross-check).

Purpose: show that a model-style proposer can submit a claim, sealed evidence
references, and `proposed_state`, while CORE emits the canonical typed state and
deterministic trace. The proposer controls neither the assigned state nor the
trace.

Public outcome vocabulary:

- `verified`;
- `evidenced`;
- `inferred`;
- `contradicted`;
- `undetermined`;
- `scope_boundary`;
- `invalid`.

Evidence caveat: the evidence corpus is still local fixture evidence, not live
vault retrieval or arbitrary web evidence. The proposer supplies evidence
references only; CORE resolves them by committed content hash and computes support
and independence from sealed corpus records. `inferred` is assigned only when the
cited premises propositionally entail the claim's atom under the sound-and-complete
ROBDD entailment engine, cross-checked against the independent truth-table oracle;
citing records that merely exist yields `undetermined` (the committed
`unrelated-premise-still-undetermined` scenario exercises that attack). The demo
must not be described as production epistemic evaluation across arbitrary evidence
sources.

### Proof-Carrying Coherence Promotion Demo (#696 — vault-owned certified promotion)

Status: merged (PR #696).

Evidence class: substrate-capability demo within a local deterministic envelope.

Purpose: demonstrate deterministic knowledge-admission authority by
replay-verified proof and vault-owned promotion. A model-style proposer can attach
status, confidence, proof, certificate, and trace-hash garbage, but CORE fresh-reads
store state, recomputes the proof under the pinned deductive engine, replay-verifies
the certificate, and promotes or refuses only through
`VaultStore.apply_certified_promotion`.

Public outcome vocabulary:

- `promoted`;
- `refused`;
- `invalid`.

Evidence caveat: this proves proof-carrying `SPECULATIVE -> COHERENT` promotion
only for curator-certified readings over already-`COHERENT` premises in a
fixture-driven local store arena. It does not prove runtime integration,
open-world autonomous learning, arbitrary evidence ingestion, or normative
clearance.

### Standalone Deductive Entailment Authority Demo (#700 — authority over formal entailment)

Status: merged (PR #700).

Evidence class: substrate-capability demo.

Purpose: demonstrate a non-trivial authority boundary over formal entailment. The
proposer submits premises, a conclusion, and a claimed verdict. CORE decides via
the existing proof-chain / deductive-logic substrate, with trace evidence that can
be checked against the independent truth-table oracle discipline already used by
the deductive lane.

Public outcome vocabulary:

- `entailed`;
- `refuted`;
- `unknown`;
- `refused`;
- `invalid`.

Proof obligations met:

- proposer verdict ignored;
- malformed or out-of-regime logic refused;
- inconsistent premises refused rather than vacuously proving everything;
- at least one scenario where the proposer is wrong and CORE's verdict differs;
- deterministic trace includes canonical proof keys or certificate evidence;
- no shared-code oracle is presented as independent evidence.

Evidence caveat: the demo operates in the propositional regime only, over opaque
atoms. It does not demonstrate NLU, learning, proof-carrying promotion, or
normative clearance. The authority boundary is real within the stated envelope; it
must not be described as general formal-reasoning capability beyond propositional
entailment.

## Proposed

Recommended order of next public evidence:

1. Embodied Authority Simulation Demo (next target; simulation-only);
2. SaaS / On-Prem Boundary Demo.

Merged evidence now establishes five authority boundaries: authority over claims
(#687), proposed tool actions (#688), epistemic state assignment (#690),
vault-owned proof-carrying promotion (#696), and formal entailment (#700). The
next public target should extend the authority pattern to a simulated physical
domain.

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
