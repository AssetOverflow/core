# Claude-to-CORE Tool Authority Demo

This demo proves one narrow boundary:

```text
Claude/Grok-style proposer suggests a digital action.
CORE alone decides authorized | ask | refused | invalid.
The output is a deterministic authority artifact.
Nothing executes.
```

## What this proves

* A proposer can submit an MCP-shaped action request without gaining execution authority.
* CORE alone derives the final authority status.
* CORE ignores any proposer-supplied trace hash and regenerates its own deterministic trace hash.
* Invalid payloads fail at the typed boundary before authority evaluation.
* An `authorized` result emits only an inert `licensed_action` record, not an execution path.

## What this does not prove

* It is not a production MCP server.
* It does not send email, run shell commands, call a network, or invoke a model API.
* It does not prove runtime integration, serving integration, or embodied authority.
* It does not claim broader safety than the local deterministic envelope encoded here.

## Why no real side effects are executed

The authority substrate never dispatches tools.  `authority.py` validates a closed
payload, evaluates local policy, and returns JSON only.  Even when a proposal is
authorized, the returned `licensed_action` is an inert description with
`effect: "inert_license_only"`.  No file write, email send, shell execution,
network access, subprocess launch, `eval`, or `exec` path exists in the demo.

## Why this is MCP-shaped, not production MCP

The payload is structured like a tool invocation so Anthropic and xAI/Tesla
lanes can hand the same kind of typed request to CORE.  This remains a local
demo contract: no server transport, session handling, production adapter, or
real side-effecting tool substrate is present.

## Relation to #687

#687 proved the earlier reasoning boundary:

```text
Claude/Fable-style System 1 proposal
-> CORE deterministic System 2 verification/refusal/ask/invalid
-> audited envelope
-> deterministic trace artifacts
-> no proposer execution authority
```

This demo advances the same doctrine one layer outward:

```text
Claude/Grok-style proposer
-> proposes digital actions
-> CORE authorizes/refuses/asks/invalidates
-> inert licensed action artifact only when authorized
-> no proposer authority and no execution path
```

It therefore proves digital tool/action authority before any embodied-authority simulation.

## The four scenarios

* `authorized-low-risk-local-action`: low-risk local note request inside the envelope.
* `ask-required-action`: external email draft request without explicit confirmation.
* `refused-outside-envelope-action`: shell command proposal refused as an unauthorized tool.
* `invalid-smuggling-attempt`: proposer tries to smuggle `licensed_action` and authorization state.

## Honesty ledger

* Real: closed schema validation, local authority evaluation, deterministic trace hashing, expected artifact pinning, double-run determinism.
* Simulated: the proposer side is static fixture data standing in for Claude or Grok.
* Not claimed: production MCP, runtime authority integration, external side effects, or any broader guarantee than this fail-closed local envelope.

## Example commands

```bash
python demos/claude_tool_authority/run_demo.py
python demos/claude_tool_authority/run_demo.py --json
python demos/claude_tool_authority/run_demo.py --update-expected
pytest -q tests/test_claude_tool_authority_demo.py
```
