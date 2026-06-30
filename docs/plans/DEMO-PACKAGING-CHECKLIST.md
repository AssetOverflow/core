# Public Demo Packaging Checklist

This checklist applies to public CORE demos.

## Scope

- [ ] Demo purpose is stated narrowly.
- [ ] Demo status is clear: merged, draft PR, proposed, or not yet implemented.
- [ ] Demo evidence class is stated: substrate-capability, interface-contract, simulation-only, or proposed.
- [ ] README includes "what this proves."
- [ ] README includes "what this does not prove."
- [ ] README avoids named-company outreach strategy.
- [ ] README avoids funding, sponsorship, runway, or executive-packet language.

## Safety boundary

- [ ] No real external side effects.
- [ ] No network dependency.
- [ ] No model API dependency.
- [ ] No shell execution unless the demo explicitly exists to test shell-denial behavior.
- [ ] No production MCP claim.
- [ ] MCP-shaped interfaces are described as MCP-shaped, not production MCP.
- [ ] Simulation-only demos are labeled simulation-only.
- [ ] Proposed demos are not described as implemented.

## Determinism

- [ ] Runner output is deterministic.
- [ ] Expected artifacts are pinned.
- [ ] Double-run behavior is byte-identical where applicable.
- [ ] Trace hashes are deterministic.
- [ ] No timestamp, random, host-path, or environment-dependent output appears in expected artifacts.

## Authority boundary

- [ ] Proposer input cannot set final authority status.
- [ ] Proposer input cannot smuggle final action artifacts.
- [ ] Proposer input cannot indirectly decide the result through trusted support, independence, verdict, or clearance labels.
- [ ] Invalid payloads fail closed.
- [ ] Refusal and ask outcomes are first-class successes.
- [ ] Authorized outputs, if present, are inert artifacts unless a later production system explicitly implements execution.

## Evidence strength

- [ ] Capability claims route through a real CORE operator, runtime path, sealed eval lane, or independently checked proof surface.
- [ ] Interface-contract demos are not described as substrate-capability demos.
- [ ] Fixture evidence is labeled as fixture evidence.
- [ ] Sealed-corpus or independent-oracle claims name the corpus/oracle and the no-shared-code boundary.
- [ ] Boolean/string policy demos are framed as boundary checks unless another substrate decision is actually present.

## Public hygiene

- [ ] No named-person outreach planning.
- [ ] No named-company approach strategy.
- [ ] No private red-team personas.
- [ ] No speculative current-facts dossiers.
- [ ] No claims of robotics, vehicle, aerospace, defense, or safety-certified deployment unless directly implemented and independently verified.
