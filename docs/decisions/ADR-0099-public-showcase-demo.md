# ADR-0099 — Public Showcase Demo

**Status:** Proposed
**Date:** 2026-05-21
**Author:** CORE agents + reviewers
**Depends on:** ADR-0096, ADR-0097, ADR-0098

---

## Context

CORE's distinctive properties (deterministic cognition, honest
refusal, reviewed learning, multi-hop composition with replayable
trace) are each measured by a different shipped artifact. A first-time
viewer has to read seven ADRs to assemble the thesis.

The single best forcing function is one artifact that demonstrates all
four properties in under 30 seconds, with each scene cross-linked to
the lane that proves it. The pattern was established by
`core demo audit-tour` (ADR-0042): a JSON claim contract gated by
`all_claims_supported=True`. This ADR generalizes that pattern across
the four key invariants.

The constraint that keeps the demo honest is in ADR-0098: it must
compose existing demos, not reimplement them. Every claim the showcase
makes traces back to an already-passing lane.

---

## Decision

Introduce `core demo showcase` that composes four scenes, each
delegating to a `DemoCommand` (ADR-0098). Output is a single
deterministic JSON contract plus an HTML render.

### Scenes

**Scene 1 — Determinism.**
Delegate: existing `register-tour` `DemoCommand` adapter.
Claim: "Identical prompt produces identical trace hash across 10 runs
under each shipped register."
Evidence: `register-tour` JSON; `trace_hash` set cardinality = 1 per
register.

**Scene 2 — Honest unknown.**
Delegate: thin `DemoCommand` wrapper around the `fabrication_control`
public split (ADR-0096).
Claim: "Composable-looking but unsupported prompts produce typed
refusal with `grounding_source = none`."
Evidence: `fabrication_control` report SHA;
`fabrication_rate ≤ 0.01`.

**Scene 3 — Reviewed learning.**
Delegate: existing `learning-loop` `DemoCommand` adapter.
Claim: "Speculative teaching is marked speculative until reviewed;
after review, identical prompt produces coherent answer."
Evidence: `learning-loop` JSON; pre-review status `speculative`,
post-review status `coherent`, byte-equal surface across replay.

**Scene 4 — Multi-hop with trace.**
Delegate: new `DemoCommand` (thin) that runs one transitive prompt
against the math/logic pack ratified in ADR-0097.
Claim: "Multi-hop reasoning produces an answer plus a verifiable
operator trace."
Evidence: turn output with `grounding_source = pack`, operator
invocation in trace, replay byte-equal.

### Output contract

```jsonc
{
  "showcase_version": 1,
  "generated_at_revision": "<git sha>",
  "scenes": [
    {
      "scene_id": "determinism",
      "demo_id": "register-tour",
      "claims": [...],
      "all_claims_supported": true
    },
    ...
  ],
  "all_claims_supported": true,
  "total_runtime_ms": ...,
  "trace_hash": "..."
}
```

### Hard constraints

- **Total runtime <30s on dev hardware.** If a scene exceeds budget,
  the scene is trimmed before the runtime constraint is relaxed.
- **No new mechanism.** Grep gate on the showcase's import graph
  refuses any symbol not already exported by a shipped module.
- **JSON byte-equality across runs.** HTML may vary in styling; JSON
  must not. Replay verified in CI.
- **Public-safety preserved.** Every surface emitted is already
  emitted by an existing public demo. No new exposure.

---

## Invariant

`public_showcase_pure_composition` — grep gate refuses any symbol in
the showcase's import graph not already exported by `core/`, `chat/`,
`generate/`, `language_packs/`, `teaching/`, or `core.commands.demo_*`.

`public_showcase_all_claims_supported` — CI fails if showcase exits
with `all_claims_supported=False` or runtime >30s.

`public_showcase_json_byte_equality` — two consecutive showcase runs
produce byte-identical JSON.

---

## Lane

`evals/public_demo/` (existing directory, populated by this ADR):

- determinism: showcase JSON byte-equal across two runs
- support: `all_claims_supported=True`
- budget: total runtime <30s on dev hardware reference machine
- composition: grep gate confirms pure composition
- scene-level: each scene's underlying demo lane also passes

---

## Trust Boundary

Showcase writes under operator-specified `--output-dir`. Path traversal
rejection per ADR-0051 / ADR-0098. No network. No shell. No dynamic
imports. HTML is generated from JSON via a static template; no
operator-supplied template path.

---

## Consequences

- One artifact answers "what makes CORE distinct" in under 30 seconds.
- Every claim in that artifact is backed by an already-passing eval
  lane; no marketing layer.
- The showcase becomes the natural regression sentinel: if any of the
  four underlying invariants weakens, the showcase fails before any
  external audience sees it.
- ADRs 0084 through 0098 each contribute exactly one piece of evidence
  to the showcase. The slate closes.

---

## PR Checklist

- Capability added: single artifact composing four CORE invariants under 30s.
- Invariants proved: `public_showcase_pure_composition`, `public_showcase_all_claims_supported`, `public_showcase_json_byte_equality`.
- Lane proving it: `evals/public_demo/`.
- Hidden normalization / stochastic fallback / approximate recall / unreviewed mutation: none. Pure composition enforced by grep gate.
- Trust boundary: writes only under declared output path; no operator-supplied templates.
