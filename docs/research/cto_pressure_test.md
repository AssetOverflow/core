# Skeptical CTO Pressure Test

Purpose: a hard-question rubric for a first technical conversation with Brain
Corp. The standard is honesty under pressure. Any answer that converts "not yet"
into "basically done" fails the product.

## 1. Where is the external validation?

Honest answer:

CORE has internal deterministic evidence and demos, but external validation is
not established unless a named third party has reviewed a specific artifact.
The claims ledger says no domain is at `expert`; `mathematics_logic`,
`physics`, and `systems_software` are `audit-passed`, with the prior expert
promotion fail-closed-reverted. `audit-passed` means CORE claim-shape compliance
per ADR-0113: signed digest, replay determinism, typed refusal, exact recall,
and grounding provenance. It is not a raw-capability or expert-level claim.

Weak answer to avoid:

We have strong results and are already ahead of conventional systems. The exact
external validation can come later.

## 2. Show me working vision and motor control.

Honest answer:

Do not claim working CORE-native vision or motor. The current robotics-adjacent
demo is an abstract decision/accountability substrate over simulated situation
records. It is not perception, SLAM, localization, path planning, motor control,
or a robot integration. Ledger multimodal status is: text is an active
capability; audio is substrate with the capability gate CLOSED; vision and
motor are proposed only.

Weak answer to avoid:

The same substrate naturally extends to vision and motor, so this is basically
a robot brain.

## 3. Why should Brain Corp care if BrainOS already handles perception,
navigation, safety, fleet telemetry, and operations?

Honest answer:

They should not replace BrainOS with CORE. The possible fit is beneath or beside
the autonomy stack: replayable decision provenance, refusal-on-ambiguity, and
accountability records for bounded decisions where a system must show why it
proceeded, stopped, or refused. BrainOS is the deployed robotics platform; CORE
is only a candidate substrate for traceable cognition/control evidence.

Weak answer to avoid:

BrainOS is conventional robotics infrastructure and CORE is the more advanced
foundation.

## 4. What exactly works today?

Honest answer:

Say only what the prepared demo proves: a simulated AMR-style situation record
can be reduced into `PROCEED`, `STOP`, or `REFUSE`; the under-determined case
materializes a CORE refusal reason; two fresh runs produce byte-identical replay
artifacts; the demo preserves the versor closure invariant. Ledger-wide
determinism framing is stronger and still bounded: byte-identical replay/digest
evidence is stable across processes and `PYTHONHASHSEED`; the expert revert was
a single-source evidence-drift in a non-gating coverage metric, and the system
caught that drift by failing closed to `audit-passed`, never to a false expert.
None of this proves robotics-grade control.

Weak answer to avoid:

This demonstrates reliable robotics decision-making.

## 5. Are you using LLMs, stochastic generation, or hidden heuristics?

Honest answer:

For the demo, the policy reducer is explicit and tiny; CORE supplies the real
runtime trace/refusal/replay surfaces. The demo should name what is simulated
and should not hide the reducer as "emergent cognition." If any future surface
uses stochastic models, that must be disclosed as outside CORE's deterministic
substrate.

Weak answer to avoid:

No heuristics; the geometry handles the decision.

## 6. What happens on out-of-distribution or ambiguous input?

Honest answer:

The demo refuses. More generally, the desired contract is refuse rather than
guess. If a current component fails to refuse where it should, that is a defect
to report, not a behavior to explain away. Use the ledger's exact GSM8K framing
if the subject comes up: A sealed-real `0/0/1319` is the honest external number,
showing zero-confabulation discipline plus an honest coverage gap, not an
accuracy result; B synthetic-public `150/150/0` is CORE-authored and never "100%
on GSM8K"; C train_sample `6/44/0` has exit-criterion NOT met, and the stricter
probe reads `4/46` on the same 50; D composite `185/14/40/50 wrong=0` is
CORE-authored and currently reverted.

Weak answer to avoid:

It generalizes gracefully because the manifold structure is robust.

## 7. Who besides the founder has verified this?

Honest answer:

Name only actual reviewers, tests, audits, or PRs that have occurred. If the
answer is "not yet externally verified," say that. The Brain Corp conversation
is preparation for scrutiny, not proof of validation.

Weak answer to avoid:

Several technical people have looked at it and found it promising.

## 8. Why is this not just a fancy audit log?

Honest answer:

An audit log records what happened. The intended CORE distinction is that
decision, refusal, trace hash, invariant checks, and replay equality are
load-bearing in the runtime contract. The current demo shows the trace/replay
surface, not a full robotics-grade control proof.

Weak answer to avoid:

Audit logs are passive; CORE is intelligent.

## 9. Can this improve Brain Corp's deployed safety case?

Honest answer:

Not by assertion. The narrow possible value is a secondary accountability layer
that can refuse under-determined decisions and replay the same trace
byte-for-byte. Whether that helps a deployed safety case requires Brain Corp's
requirements, certification constraints, and integration boundaries.

Weak answer to avoid:

Yes, because deterministic refusal is inherently safer.

## 10. What would a real pilot have to prove?

Honest answer:

A credible pilot would need a bounded decision interface, a written non-goal
list, replayable traces, refusal cases, operator-review flow, and a comparison
against an existing BrainOS decision/audit mechanism. It would also need failure
criteria: if CORE cannot add clearer accountability without increasing
integration risk, the pilot should stop. Single-signer attestation is also a
known boundary: the reviewer registry has one signer, `shay-j`, and a partner
may reasonably probe that.

Weak answer to avoid:

Give us data and we can show broad improvement.

## 11. What are the hardest objections?

Honest answer:

- CORE does not currently demonstrate robot perception or motor emission.
- The demo uses simulated facts, not sensors.
- External validation is pending.
- The domain-policy reducer is not CORE-native robotics intelligence.
- Brain Corp already has a mature deployed stack; CORE must earn a narrow
  interface, not demand architectural replacement.

Weak answer to avoid:

The objections are mostly about maturity, not architecture.

## 12. What should Opus's brief be graded against?

It should pass these checks:

- No benchmark numbers unless copied from the approved claims ledger.
- No claim that CORE has working vision/motor.
- No claim that any domain is `expert`; `audit-passed` is claim-shape compliance,
  not expert capability.
- No implication that BrainOS is obsolete.
- No hidden slide from simulated demo to real robot readiness.
- Clear distinction between substrate, policy reducer, perception, planning,
  actuation, and fleet operations.
- Every strong claim has either a cited external source, a repo artifact, or
  the exact claims-ledger value and framing.
