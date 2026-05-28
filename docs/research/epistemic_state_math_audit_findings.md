# Epistemic State Audit — Math Subsystem Findings & Forward Plan

## Context

CORE's math subsystem was audited against the proposed starter epistemic taxonomy:

- `PERCEIVED`
- `EVIDENCED`
- `VERIFIED`
- `DECODED`
- `UNVERIFIED-POSSIBLE`
- `UNVERIFIED-NOVEL`
- `CONTRADICTED`
- `AMBIGUOUS`
- `UNDETERMINED`
- `EPISTEMIC_STATE_NEEDED`

The audit was intentionally bounded to the math subsystem files named in the handoff:

- `generate/math_problem_graph.py`
- `generate/math_parser.py`
- `generate/math_solver.py`
- `generate/math_verifier.py`
- `generate/math_realizer.py`
- `generate/math_candidate_parser.py`
- `generate/math_candidate_graph.py`
- `evals/gsm8k_math/runner.py`
- `evals/gsm8k_math/verify.py`

This document records findings and a phased plan only. It proposes no runtime code changes.

---

## Executive Findings

The math subsystem already operates with a substantial implicit epistemic model.

The starter taxonomy successfully captures the majority of proposition-level semantic states in the parser -> solver -> verifier -> realizer pipeline.

However, newer orchestration layers introduce a second class of states not cleanly representable by the starter taxonomy alone.

Specifically:

1. Proposition epistemics already exist.
2. Operational/meta epistemics also already exist.
3. The current starter taxonomy risks conflating these categories.
4. The eventual ADR should likely formalize both separately.

The epistemic-state effort is therefore not inventing a taxonomy from scratch. It is surfacing and naming distinctions already embedded in the engine.

---

## Prior ADR Compatibility Gate

This document is subordinate to the existing ADR record. It is not an implementation ADR, does not supersede any prior ADR, and must not be used to reinterpret accepted decisions without a separate ratified ADR.

Before Phase 2 or any runtime work proceeds, the following compatibility rules apply.

### ADR chains reviewed for compatibility

| ADR chain / decision area | Compatibility constraint for epistemic-state work |
|---|---|
| ADR-0022 through ADR-0026 — forward semantic control | Preserve deterministic admissibility, honest exhaustion, and trace-evidenced generation behavior. Epistemic labels must not weaken admissibility gates or hide exhaustion. |
| ADR-0027 through ADR-0045 — identity/safety/ethics pack architecture | Preserve pack-governed, auditable behavior. Epistemic states may describe pack-grounded claims but must not bypass pack ratification or safety policy. |
| ADR-0091 through ADR-0111 — domain ratification and audit-passed promotion | Preserve the difference between `reasoning-capable`, `audit-passed`, and future `expert`. Epistemic states must not create an unofficial promotion tier. |
| ADR-0105 / ADR-0119.1 / ADR-0119.7 — sealed holdout discipline | Preserve sealed-holdout boundaries. Epistemic audit labels must not imply knowledge of sealed cases or alter holdout governance. |
| ADR-0114a — anti-overfitting proof obligations | Preserve replay-equal trace requirements, typed refusal, zero-wrong doctrine, deterministic replay, and operation provenance via pack lemmas. |
| ADR-0115 through ADR-0118 — math graph / solver / verifier / realizer | Preserve the existing parser -> graph -> solver -> verifier -> realizer contracts. Epistemic vocabulary may describe these contracts but must not change them. |
| ADR-0119.* — GSM8K eval lane and gates | Preserve `correct` / `wrong` / `refused` / `decoded_unarticulated` as eval/reporting buckets. Do not silently redefine lane metrics as primitive epistemic states. |
| ADR-0126 through ADR-0135 — candidate graph and binding graph substrate | Preserve binding-graph admissibility and downstream solver/verifier behavior. Candidate-graph findings may be audited, but future taxonomy must distinguish historical regex-era machinery from preserved substrate contracts. |
| ADR-0136 / ADR-0136.S.* / ADR-0163 | Treat regex recognizer and statement-layer refusal taxonomies as historical evidence where superseded. Do not revive deprecated regex sentence-template prescriptions under epistemic-state terminology. |
| ADR-0164 — incremental comprehension reader | Preserve the reader as the current front-end direction where it supersedes regex recognizer production. Epistemic routing states must align with reader-first / fallback semantics and must not bypass admissibility. |
| ADR-0165 — regex scope rule | Preserve the lexeme-only regex boundary. No future epistemic-state work may justify sentence-level regex grammar templates unless a new ADR explicitly supersedes ADR-0165 and is ratified. |
| ADR-0150 / ADR-0152 / ADR-0155 / ADR-0161 — contemplation / HITL corridor | Preserve reviewed teaching, proposal, and ratification governance for new lexicon entries, categories, primitives, or future epistemic states. |

### Non-overrides

This document does not override:

- `wrong = 0` as a gate where prior ADRs require it,
- typed refusal as the safe failure mode,
- replay-equal `SolutionTrace` as the evidence substrate for correct answers,
- pack-lemma operation provenance,
- sealed holdout governance,
- HITL ratification for new learned structures,
- ADR-0164's reader direction,
- ADR-0165's lexeme-only regex boundary,
- accepted lane-shape thresholds or promotion contracts.

### Supersession discipline

If future epistemic-state work appears to contradict, weaken, rename, or replace an accepted ADR contract, it must stop and produce a new ADR-level decision request.

That request must explicitly state:

1. the prior ADR(s) affected,
2. the exact clause or contract being changed,
3. whether the change is a clarification, amendment, or supersession,
4. what evidence justifies the change,
5. what invariants remain preserved,
6. what new acceptance gates apply,
7. that the change requires operator ratification before implementation.

### Phase 2 gate

Phase 2 must not proceed until reviewers accept that:

- this document is advisory and descriptive, not supersessive,
- candidate-graph / recognizer observations are treated in light of ADR-0164 and ADR-0165,
- `correct`, `wrong`, `refused`, and `decoded_unarticulated` remain eval/reporting outcomes unless a later ADR ratifies a deeper internal representation,
- no deprecated regex-sentence-template path is being revived,
- any future runtime adoption will preserve existing replay, refusal, provenance, and governance contracts.

---

## Strongly Confirmed Proposition States

The following starter states mapped cleanly and repeatedly across the classic math spine.

| State | Practical meaning in the math subsystem |
|---|---|
| `PERCEIVED` | Token/span observed before semantic lift. |
| `EVIDENCED` | Grounded candidate or feature lifted from source spans. |
| `VERIFIED` | Independently re-derived or cross-checked against pack/oracle/solver state. |
| `DECODED` | Replay-equal deterministic verified trace or canonical artifact equality. |
| `CONTRADICTED` | Proposition conflicts with typed semantic rules or verifier replay. |
| `AMBIGUOUS` | Multiple incompatible admissible interpretations exist. |
| `UNDETERMINED` | Insufficient structure to complete semantic lift or solve. |

These states align well with:

- parser grounding,
- typed graph construction,
- solver semantics,
- verifier replay,
- canonical hashing,
- GSM8K evaluation discipline.

---

## Critical Taxonomy Gap

The candidate-graph, recognizer, and comprehension-reader layers introduce states that are not proposition truth states.

Examples include:

- bounded refusal,
- route fallthrough,
- authoritative parser admission,
- decoded-but-unarticulated outputs,
- deterministic preference between multiple admissible parses,
- grounded derivation where output values are not literal source spans.

These are not adequately represented by `UNDETERMINED`, `AMBIGUOUS`, or `VERIFIED`.

Flattening them into proposition states would create category errors.

For example:

> branch count exceeded deterministic cap

is operational boundedness, not semantic ambiguity.

Likewise:

> realizer failed after verifier replay passed

is articulation failure, not failure to decode the answer.

---

## Proposed Direction

The taxonomy should be pressure-tested as a two-axis model rather than a single flat enum.

### 1. Proposition Epistemic States

Truth / grounding / replay status of a proposition.

Examples:

- `PERCEIVED`
- `EVIDENCED`
- `VERIFIED`
- `DECODED`
- `CONTRADICTED`
- `AMBIGUOUS`
- `UNDETERMINED`

### 2. Operational / Meta Epistemic States

States describing the engine's attempt to reach, route, bound, or surface propositions.

Candidate examples:

- `ROUTE_FALLTHROUGH`
- `BOUNDED_REFUSAL`
- `AUTHORITY_ADMITTED`
- `DECODED_UNARTICULATED`
- `PREFERRED_EVIDENCED`
- `DERIVED_EVIDENCED`

This preserves semantic clarity while exposing deterministic orchestration behavior.

---

## Proposed New Candidate States

### `DERIVED_EVIDENCED`

Grounded input operands exist directly in source spans, but the surfaced proposition is deterministically derived from them.

Example:

- `3 appointments at $400 each` -> derived value `1200`, even though literal `1200` does not appear in source.

This is stronger than merely possible, but different from literal span evidence.

### `PREFERRED_EVIDENCED`

Multiple admissible grounded parses exist, but one is deterministically preferred by a policy such as `most-grounded-slots-wins`.

This is not the same as unresolved ambiguity when the candidates collapse safely or one candidate is structurally tighter.

### `AUTHORITY_ADMITTED`

A subsystem admits a proposition authoritatively enough that downstream fallback parsing should not reinterpret it differently.

This is route authority, not just proposition verification.

### `ROUTE_FALLTHROUGH`

One capability path refuses or fails, but another deterministic path is allowed to attempt the proposition.

This is orchestration state, not proposition truth state.

### `BOUNDED_REFUSAL`

The engine refuses because deterministic bounded-computation policy was exceeded, rather than because the proposition is contradictory, ambiguous, or impossible.

### `DECODED_UNARTICULATED`

A proposition is replay-verified and semantically decoded, but articulation/surface realization failed.

This state already effectively exists in the GSM8K runner as `decoded_unarticulated`.

---

## Phase 1 — Separate Semantic vs Operational States

Phase 1 completes the first pressure-test required before an ADR can safely define a final epistemic vocabulary.

The central decision is that a state must not be classified by its surface spelling alone. It must be classified by what kind of fact it reports.

### Axis Definitions

| Axis | Reports | Does not report | Canonical question |
|---|---|---|---|
| Proposition epistemic axis | The semantic status of a proposition, candidate, graph, trace, or answer. | Which subsystem route was used, why a route fell through, or whether a runtime policy boundary was hit. | What is known about this proposition? |
| Operational/meta epistemic axis | The engine's deterministic attempt to reach, select, bound, route, or surface a proposition. | Whether the proposition itself is true, grounded, contradicted, or replay-equal. | What happened while trying to know or surface it? |
| Artifact/replay axis | Whether a graph, trace, answer, or report is byte-stable and replay-equal. | Whether the proposition was easy to parse or whether all possible routes were explored. | Can this result be reproduced exactly? |
| Articulation axis | Whether a decoded proposition can be rendered on the user-facing surface. | Whether the decoded answer is semantically correct. | Can the known proposition be spoken faithfully? |

### Boundary Rule

A state is **proposition-level** only when changing the state would change what CORE claims about the proposition itself.

A state is **operational/meta-level** when changing the state would change the route, refusal reason, boundedness, or surface behavior without necessarily changing the proposition's truth status.

A state is **artifact/replay-level** when it reports byte equality, canonical identity, deterministic replay, or stable trace/report reproduction.

A state is **articulation-level** when the proposition is already semantically available but the rendering/surface path succeeds or fails.

### Phase 1 Classification Matrix

| State | Proposition-level? | Operational/meta? | Artifact/replay? | Articulation? | Clean starter state? | Classification | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| `PERCEIVED` | yes | no | no | no | yes | Proposition | Span/token has been observed but not yet committed to meaning. |
| `EVIDENCED` | yes | no | no | no | yes | Proposition | Source-grounded features or candidates exist. |
| `DERIVED_EVIDENCED` | yes | partly | no | no | no | Proposition + derivation qualifier | Inputs are evidenced, while output value/structure is deterministic derivation. Should not collapse to plain `EVIDENCED` without recording derivation. |
| `PREFERRED_EVIDENCED` | yes | yes | no | no | no | Proposition + selection qualifier | Candidate remains evidenced, but a deterministic preference policy selected it over alternatives. Selection must remain visible. |
| `VERIFIED` | yes | no | partly | no | yes | Proposition | Cross-checked against pack/oracle/solver/verifier semantics. May involve artifacts, but core meaning is proposition-level verification. |
| `DECODED` | yes | no | yes | no | yes | Proposition + replay | Verified proposition with replay equality / canonical identity. Strongest semantic state in the current math spine. |
| `DECODED_UNARTICULATED` | yes | no | yes | yes | no | Proposition + articulation failure | The answer remains decoded; the surface failed. This is not `UNDETERMINED` and not `CONTRADICTED`. |
| `UNVERIFIED-POSSIBLE` | yes | no | no | no | yes | Proposition | Consistent but not directly verified. Useful for candidate futures but not strongly used in the audited classic path. |
| `UNVERIFIED-NOVEL` | yes | no | no | no | yes | Proposition | Non-contradicting and structurally unseen. Likely important for future recognition/teaching paths. |
| `CONTRADICTED` | yes | no | sometimes | no | yes | Proposition | Conflicts with typed semantic rules, graph integrity, or replay checks. |
| `AMBIGUOUS` | yes | no | no | no | yes | Proposition | Input supports multiple incompatible admissible propositions. |
| `UNDETERMINED` | yes | no | no | no | yes | Proposition | Feature lift, graph construction, solving, or answer resolution cannot complete. |
| `ROUTE_FALLTHROUGH` | no | yes | no | no | no | Operational/meta | One path refused or failed and another path may continue. This is not a claim about proposition truth. |
| `AUTHORITY_ADMITTED` | partly | yes | no | no | no | Operational/meta + admission qualifier | A route admits authoritatively enough to prevent fallback reinterpretation. The admitted proposition still needs its proposition state. |
| `BOUNDED_REFUSAL` | no | yes | no | no | no | Operational/meta | Refusal caused by deterministic computation/search boundary, not semantic contradiction. |
| `REFUSED` | no | yes | no | no | no | Operational surface bucket | Runner-level bucket that can hide `UNDETERMINED`, `AMBIGUOUS`, `BOUNDED_REFUSAL`, or `CONTRADICTED`. Must not become a proposition state by itself. |
| `WRONG` | partly | yes | sometimes | no | no | Eval surface bucket | Usually external-oracle contradiction, but not a primitive epistemic state. It is an eval classification over a trace/result. |
| `CORRECT` | partly | yes | sometimes | no | no | Eval surface bucket | Usually decoded + oracle match, but should not replace the lower-level state. |

### Non-Conflation Rules

The ADR should preserve these distinctions:

1. `REFUSED` is not a proposition state.
   - It is a surface outcome bucket.
   - It must carry a cause such as `UNDETERMINED`, `AMBIGUOUS`, `BOUNDED_REFUSAL`, or `CONTRADICTED`.

2. `WRONG` is not a primitive proposition state.
   - It is an eval outcome.
   - Internally it usually means `CONTRADICTED` against verifier replay or external oracle expectation.

3. `CORRECT` is not a primitive proposition state.
   - It is an eval outcome.
   - Internally it usually means `DECODED` plus expected-answer agreement.

4. `DECODED_UNARTICULATED` must not downgrade the proposition to `UNDETERMINED`.
   - The proposition was decoded.
   - The articulation path failed.

5. `BOUNDED_REFUSAL` must not become `AMBIGUOUS`.
   - Branch cap refusal says exploration exceeded policy bounds.
   - It does not assert that multiple incompatible propositions were found.

6. `ROUTE_FALLTHROUGH` must not become `UNDETERMINED`.
   - A route may fail while another route succeeds.
   - The failed route is not final knowledge about the proposition.

7. `DERIVED_EVIDENCED` must not be treated as unsupported novelty.
   - The derived value may be absent from the literal span.
   - The derivation can still be grounded in evidenced operands.

### Recommended Phase 1 ADR Shape

A future ADR should avoid a single unqualified enum as the internal model.

The minimum safe internal shape is a pair:

```text
(proposition_state, operational_state?)
```

A stronger shape is a typed event record:

```text
EpistemicEvent {
  proposition_state?: PropositionEpistemicState,
  operational_state?: OperationalEpistemicState,
  artifact_state?: ArtifactReplayState,
  articulation_state?: ArticulationState,
  evidence_ref: ...,
  transition_reason: ...,
}
```

The reporting surface may still collapse this to human-readable labels, but the trace should preserve the axes.

### Phase 1 Completion Criteria

Phase 1 is complete when the project agrees that:

- proposition states and operational/meta states are separate axes,
- runner buckets like `correct`, `wrong`, and `refused` are not primitive epistemic states,
- decoded-but-unarticulated is an articulation failure over a decoded proposition,
- bounded refusal is operational policy, not semantic ambiguity,
- future transition audits must record both proposition state and operational/meta state when both are present,
- prior ADR compatibility has been reviewed and no supersession proceeds without explicit operator ratification.

---

## Phased Plan

### Phase 2 — Define Transition Invariants

Phase 2 is blocked until the Prior ADR Compatibility Gate above is accepted by reviewers / operator.

Once unblocked, extract deterministic transitions:

| From | To | Trigger |
|---|---|---|
| `PERCEIVED` | `EVIDENCED` | Grounding succeeds. |
| `EVIDENCED` | `VERIFIED` | Solver/pack/verifier cross-check succeeds. |
| `VERIFIED` | `DECODED` | Deterministic replay equality holds. |
| `EVIDENCED` | `AMBIGUOUS` | Multiple incompatible admissible branches exist. |
| `EVIDENCED` | `CONTRADICTED` | Typed semantic rule or replay check fails. |
| `PERCEIVED` | `UNDETERMINED` | Feature lift cannot complete. |

This becomes the core epistemic state machine.

### Phase 3 — Determine Lattice Structure

Current evidence suggests the taxonomy is likely:

```text
semantic axis x operational axis
```

rather than one flat enum.

A single enum may still be useful as a reporting surface, but the underlying model should preserve orthogonality.

### Phase 4 — Audit Transition Sites

Next bounded audit pass should enumerate every point where:

- a proposition changes epistemic state,
- a branch is refused,
- ambiguity is introduced,
- authority/fallthrough is applied,
- or replay verification upgrades certainty.

This likely becomes the core substrate for the epistemic-state ADR.

### Phase 5 — Decide ADR Shape

The ADR should decide whether CORE exposes:

1. one flat state enum,
2. a proposition state plus operational state pair,
3. or a richer trace event model that records both.

The audit currently favors option 2 or option 3.

---

## Architectural Importance

This work is load-bearing because it directly affects:

- refusal semantics,
- replay guarantees,
- comprehension-reader integration,
- candidate-graph orchestration,
- future recognition systems,
- teaching-derived structure formation,
- introspectable reasoning claims,
- deterministic truth-state reporting.

The math subsystem already contains the beginning of a coherent epistemic architecture. The next task is formalization and invariant discipline.

---

## Non-Goals For This Document

This document does not:

- propose runtime implementation details,
- modify code,
- define a final ADR,
- audit non-math subsystems,
- claim the starter taxonomy is final,
- supersede or amend any existing ADR.

It records bounded findings and prepares the next phase of epistemic-state design under prior ADR governance.
