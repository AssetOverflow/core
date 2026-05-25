# ADR-0140: CORE Trace Protocol v0

Status: Proposed

## Context

CORE must not use external tool or agent protocols as its native cognition substrate.  MCP, A2A, OpenAPI, and similar interfaces are useful boundary adapters, but they do not carry CORE's internal requirements: deterministic replay, proof binding, epistemic state, normative clearance, invariant status, causation, and algebraic payload references.

CORE already computes deterministic trace hashes over semantically meaningful turn outputs.  ADR-0140 makes that discipline protocol-level: every meaningful command, observation, proposal, verdict, proof, and state transition can be represented as a typed, versioned, canonical event.

## Decision

Introduce CORE Trace Protocol (CTP) v0 as the native event envelope for cognition-ledger messages.

CTP v0 is:

- typed: every event has a versioned `message_type`
- canonical: event bytes are serialized with sorted-key UTF-8 JSON
- content-addressed: `message_id` is the SHA-256 hash of canonical content excluding `message_id`
- causally linked: events may point to the message that caused them
- epistemic-aware: completed/refused turns require epistemic metadata
- proof-aware: completed/refused turns require a trace hash
- adapter-neutral: external protocols translate into CTP; they do not govern runtime semantics

Algebraic payloads may later use VMP (`vmp.binary.v1`) inside the CTP `payload` field.  VMP is a payload encoding, not the outer protocol.

## Non-goals

ADR-0140 does not wire CTP into `ChatRuntime` yet.  It does not define the full VMP binary codec.  It does not replace existing trace-hash code.  It does not expose an MCP server.  It creates the deterministic envelope and replayable JSONL spine required before runtime integration.

## Protocol families

Initial v0 families:

- `core.turn.*`
- `core.evidence.*`
- `core.tool.*`
- `core.learning.*`
- `core.verdict.*`
- `core.proof.*`

## Acceptance gates

1. Identical semantic envelopes produce byte-identical canonical JSON.
2. Identical semantic envelopes produce identical message IDs.
3. Semantic payload changes change the message ID.
4. NaN and Infinity are rejected.
5. Negative zero canonicalizes to positive zero.
6. Completed/refused turns require epistemic metadata.
7. Completed/refused turns require `proof.trace_hash`.
8. JSONL event logs round-trip into typed envelopes.
9. Replay verification detects causation-chain breaks.
10. The v0 package is isolated and does not mutate live runtime behavior.

## Consequences

CTP gives CORE an internal cognition ledger: tool calls become observations, teaching updates become proposals, refusals become verdict-bearing events, and final outputs remain replayable proof-carrying transitions.  This keeps MCP and other ecosystem protocols at the perimeter while preserving CORE's own truth, replay, and clearance semantics internally.
