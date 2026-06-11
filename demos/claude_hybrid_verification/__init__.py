"""Claude-to-CORE hybrid verification demo (System 1 proposes, System 2 decides).

A narrow, auditable proof path: a Claude/Fable-style System 1 proposal arrives as
an MCP-shaped tool call; CORE's deterministic derivation lane re-derives, the
verifier/pool — hardened by the demo's gold-audited serving envelope — keep
sole acceptance authority, unsupported cases refuse or ask,
and a deterministic replay/provenance trace proves every decision.

See ``README.md`` in this directory for the boundary contract and the honesty
ledger (what is real CORE, what is simulated, and what is NOT claimed).
"""
