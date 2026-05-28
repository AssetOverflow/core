# Epistemic State Audit — Math Subsystem Findings & Forward Plan

## Context

CORE's math subsystem was audited against the proposed starter epistemic taxonomy, then checked against the runtime enum in `core/epistemic_state.py` to avoid nomenclature drift.

Runtime epistemic state names use upper-snake enum names and lower-snake serialized values. This document follows the enum-name spelling where a state already exists in runtime.

Existing runtime states relevant to this audit include:

- `PERCEIVED`
- `EVIDENCED`
- `EVIDENCED_INCOMPLETE`
- `VERIFIED`
- `DECODED`
- `DECODED_UNARTICULATED`
- `INFERRED`
- `UNVERIFIED_POSSIBLE`
- `UNVERIFIED_NOVEL`
- `CONTRADICTED`
- `AMBIGUOUS`
- `UNDETERMINED`
- `SCOPE_BOUNDARY`
- `COMPUTATIONALLY_BOUNDED`
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

However, newer orchestration layers introduce a second class of states not cleanly representable by the initial starter taxonomy alone.

A follow-up compatibility check found that some suspected “new candidate states” already have runtime analogues:

- `DECODED_UNARTICULATED` already exists.
- `COMPUTATIONALLY_BOUNDED` is the better runtime-aligned name for bounded refusal.
- `SCOPE_BOUNDARY` may cover some substrate/out-of-scope refusals.
- `INFERRED` may cover some deterministic derivation cases.
- `EVIDENCED_INCOMPLETE` may cover partially grounded but incomplete lifts.

Therefore the next ADR must distinguish three categories:

1. already-ratified/runtime states,
2. proposed aliases or refinements over existing runtime states,
3. genuinely missing states, if any remain after transition audit.

The epistemic-state effort is therefore not inventing a taxonomy from scratch. It is surfacing, aligning, and naming distinctions already embedded in the engine.

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
| Runtime enum: `core/epistemic_state.py` | Preserve existing enum names and serialized values. Any rename, alias, split, or new state requires a separate ADR-level compatibility decision. |

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
- accepted lane-shape thresholds or promotion contracts,
- existing `core.epistemic_state.EpistemicState` enum names or serialized values.

### Supersession discipline

If future epistemic-state work appears to contradict, weaken, rename, or replace an accepted ADR contract or runtime enum value, it must stop and produce a new ADR-level decision request.

That request must explicitly state:

1. the prior ADR(s) or runtime enum value(s) affected,
2. the exact clause, contract, enum, or serialized value being changed,
3. whether the change is a clarification, amendment, alias, split, or supersession,
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
- any future runtime adoption will preserve existing replay, refusal, provenance, enum, and governance contracts.

---

## Strongly Confirmed Proposition States

The following states mapped cleanly and repeatedly across the classic math spine.

| State | Practical meaning in the math subsystem |
|---|---|
| `PERCEIVED` | Token/span observed before semantic lift. |
| `EVIDENCED` | Grounded candidate or feature lifted from source spans. |
| `EVIDENCED_INCOMPLETE` | Some evidence exists, but the lift is partial or missing required closure. |
| `VERIFIED` | Independently re-derived or cross-checked against pack/oracle/solver state. |
| `DECODED` | Replay-equal deterministic verified trace or canonical artifact equality. |
| `DECODED_UNARTICULATED` | Decoded proposition exists but the articulation surface failed. |
| `INFERRED` | Deterministically derived from grounded inputs without being directly literal in the source. |
| `UNVERIFIED_POSSIBLE` | Consistent but not directly verified. |
| `UNVERIFIED_NOVEL` | Non-contradicting and structurally unseen. |
| `CONTRADICTED` | Proposition conflicts with typed semantic rules or verifier replay. |
| `AMBIGUOUS` | Multiple incompatible admissible interpretations exist. |
| `UNDETERMINED` | Insufficient structure to complete semantic lift or solve. |
| `SCOPE_BOUNDARY` | Refusal or non-admission due to declared substrate/scope boundary. |
| `COMPUTATIONALLY_BOUNDED` | Refusal due to deterministic computation/search bound. |

These states align well with:

- parser grounding,
- typed graph construction,
- solver semantics,
- verifier replay,
- canonical hashing,
- GSM8K evaluation discipline.

---

## Critical Taxonomy Gap

The candidate-graph, recognizer, and comprehension-reader layers introduce axis-crossing events that are not always pure proposition truth states.

Examples include:

- computational boundedness,
- route fallthrough,
- authoritative parser admission,
- decoded-but-unarticulated outputs,
- deterministic preference between multiple admissible parses,
- grounded derivation where output values are not literal source spans.

Some of these already have runtime states (`COMPUTATIONALLY_BOUNDED`, `DECODED_UNARTICULATED`, `INFERRED`, `SCOPE_BOUNDARY`). Others may be better modeled as operational event metadata rather than new `EpistemicState` enum values.

Flattening operational events into proposition states would create category errors.

For example:

> branch count exceeded deterministic cap

is operational boundedness, not semantic ambiguity.

Likewise:

> realizer failed after verifier replay passed

is articulation failure, not failure to decode the answer.

---

## Proposed Direction

The taxonomy should be pressure-tested as a multi-axis model rather than a single flat enum.

### 1. Proposition Epistemic States

Truth / grounding / replay status of a proposition.

Examples:

- `PERCEIVED`
- `EVIDENCED`
- `EVIDENCED_INCOMPLETE`
- `VERIFIED`
- `DECODED`
- `DECODED_UNARTICULATED`
- `INFERRED`
- `UNVERIFIED_POSSIBLE`
- `UNVERIFIED_NOVEL`
- `CONTRADICTED`
- `AMBIGUOUS`
- `UNDETERMINED`
- `SCOPE_BOUNDARY`
- `COMPUTATIONALLY_BOUNDED`

### 2. Operational / Meta Epistemic Events

Events describing the engine's attempt to reach, route, bound, select, or surface propositions.

Candidate examples:

- `ROUTE_FALLTHROUGH`
- `AUTHORITY_ADMITTED`
- `PREFERRED_EVIDENCED`

These should not automatically become enum states. They may belong in trace/event metadata layered alongside existing runtime states.

This preserves semantic clarity while exposing deterministic orchestration behavior.

---

## Candidate Refinements / Event Labels

The initial audit used several candidate labels. After runtime enum compatibility review, they should be interpreted as follows.

| Initial audit label | Runtime-aligned interpretation | Notes |
|---|---|---|
| `DERIVED_EVIDENCED` | likely `INFERRED` over evidenced inputs | Do not add a new state unless transition audit proves `INFERRED` is insufficient. |
| `BOUNDED_REFUSAL` | `COMPUTATIONALLY_BOUNDED` | Prefer existing runtime enum spelling. |
| `DECODED_UNARTICULATED` | existing runtime state | Already present; no new state needed. |
| `PREFERRED_EVIDENCED` | likely operational selection event over `EVIDENCED` candidates | Preserve as event metadata unless ADR ratifies enum expansion. |
| `AUTHORITY_ADMITTED` | likely operational admission event plus proposition state | Preserve as event metadata unless ADR ratifies enum expansion. |
| `ROUTE_FALLTHROUGH` | likely operational routing event | Preserve as event metadata unless ADR ratifies enum expansion. |
| substrate/out-of-scope refusal | possible `SCOPE_BOUNDARY` | Needs transition audit to separate from `UNDETERMINED` and `COMPUTATIONALLY_BOUNDED`. |
| partial lift with missing closure | possible `EVIDENCED_INCOMPLETE` | Needs transition audit to distinguish from `UNDETERMINED`. |

---

## Phase 1 — Separate Semantic vs Operational States

Phase 1 completes the first pressure-test required before an ADR can safely define a final epistemic vocabulary.

The central decision is that a state must not be classified by its surface spelling alone. It must be classified by what kind of fact it reports and whether that fact already has a runtime enum representation.

### Axis Definitions

| Axis | Reports | Does not report | Canonical question |
|---|---|---|---|
| Proposition epistemic axis | The semantic status of a proposition, candidate, graph, trace, or answer. | Which subsystem route was used, why a route fell through, or whether a runtime policy boundary was hit. | What is known about this proposition? |
| Operational/meta event axis | The engine's deterministic attempt to reach, select, bound, route, or surface a proposition. | Whether the proposition itself is true, grounded, contradicted, or replay-equal. | What happened while trying to know or surface it? |
| Artifact/replay axis | Whether a graph, trace, answer, or report is byte-stable and replay-equal. | Whether the proposition was easy to parse or whether all possible routes were explored. | Can this result be reproduced exactly? |
| Articulation axis | Whether a decoded proposition can be rendered on the user-facing surface. | Whether the decoded answer is semantically correct. | Can the known proposition be spoken faithfully? |

### Boundary Rule

A state is **proposition-level** only when changing the state would change what CORE claims about the proposition itself.

A label is **operational/meta-level** when changing it would change the route, refusal reason, boundedness, selection, or surface behavior without necessarily changing the proposition's truth status.

A state is **artifact/replay-level** when it reports byte equality, canonical identity, deterministic replay, or stable trace/report reproduction.

A state is **articulation-level** when the proposition is already semantically available but the rendering/surface path succeeds or fails.

### Phase 1 Classification Matrix

| State / label | Proposition-level? | Operational/meta? | Artifact/replay? | Articulation? | Existing runtime enum? | Classification | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| `PERCEIVED` | yes | no | no | no | yes | Proposition | Span/token has been observed but not yet committed to meaning. |
| `EVIDENCED` | yes | no | no | no | yes | Proposition | Source-grounded features or candidates exist. |
| `EVIDENCED_INCOMPLETE` | yes | no | no | no | yes | Proposition | Partial evidence exists but required closure is missing. |
| `VERIFIED` | yes | no | partly | no | yes | Proposition | Cross-checked against pack/oracle/solver/verifier semantics. |
| `DECODED` | yes | no | yes | no | yes | Proposition + replay | Verified proposition with replay equality / canonical identity. |
| `DECODED_UNARTICULATED` | yes | no | yes | yes | yes | Proposition + articulation failure | The answer remains decoded; the surface failed. |
| `INFERRED` | yes | partly | no | no | yes | Proposition + derivation | Deterministically derived from grounded inputs. Use before inventing `DERIVED_EVIDENCED`. |
| `UNVERIFIED_POSSIBLE` | yes | no | no | no | yes | Proposition | Consistent but not directly verified. |
| `UNVERIFIED_NOVEL` | yes | no | no | no | yes | Proposition | Non-contradicting and structurally unseen. |
| `CONTRADICTED` | yes | no | sometimes | no | yes | Proposition | Conflicts with typed semantic rules, graph integrity, or replay checks. |
| `AMBIGUOUS` | yes | no | no | no | yes | Proposition | Input supports multiple incompatible admissible propositions. |
| `UNDETERMINED` | yes | no | no | no | yes | Proposition | Feature lift, graph construction, solving, or answer resolution cannot complete. |
| `SCOPE_BOUNDARY` | yes | yes | no | no | yes | Proposition/scope boundary | Declared out-of-scope or substrate boundary; must not be conflated with contradiction. |
| `COMPUTATIONALLY_BOUNDED` | partly | yes | no | no | yes | Operational boundary state | Deterministic search/computation bound, not semantic contradiction. |
| `ROUTE_FALLTHROUGH` | no | yes | no | no | no | Operational event | One path refused or failed and another path may continue. |
| `AUTHORITY_ADMITTED` | partly | yes | no | no | no | Operational admission event | A route admits authoritatively enough to prevent fallback reinterpretation. The admitted proposition still needs its proposition state. |
| `PREFERRED_EVIDENCED` | yes | yes | no | no | no | Selection event over proposition state | Candidate remains evidenced, but deterministic preference selected it. Prefer event metadata unless ADR ratifies enum expansion. |
| `REFUSED` | no | yes | no | no | no | Operational surface bucket | Runner-level bucket that can hide `UNDETERMINED`, `AMBIGUOUS`, `COMPUTATIONALLY_BOUNDED`, `SCOPE_BOUNDARY`, or `CONTRADICTED`. |
| `WRONG` | partly | yes | sometimes | no | no | Eval surface bucket | Usually external-oracle contradiction, but not a primitive epistemic state. |
| `CORRECT` | partly | yes | sometimes | no | no | Eval surface bucket | Usually decoded + oracle match, but should not replace the lower-level state. |

### Non-Conflation Rules

The ADR should preserve these distinctions:

1. `REFUSED` is not a proposition state.
   - It is a surface outcome bucket.
   - It must carry a cause such as `UNDETERMINED`, `AMBIGUOUS`, `COMPUTATIONALLY_BOUNDED`, `SCOPE_BOUNDARY`, or `CONTRADICTED`.

2. `WRONG` is not a primitive proposition state.
   - It is an eval outcome.
   - Internally it usually means `CONTRADICTED` against verifier replay or external oracle expectation.

3. `CORRECT` is not a primitive proposition state.
   - It is an eval outcome.
   - Internally it usually means `DECODED` plus expected-answer agreement.

4. `DECODED_UNARTICULATED` must not downgrade the proposition to `UNDETERMINED`.
   - The proposition was decoded.
   - The articulation path failed.

5. `COMPUTATIONALLY_BOUNDED` must not become `AMBIGUOUS`.
   - Branch cap refusal says exploration exceeded policy bounds.
   - It does not assert that multiple incompatible propositions were found.

6. `ROUTE_FALLTHROUGH` must not become `UNDETERMINED`.
   - A route may fail while another route succeeds.
   - The failed route is not final knowledge about the proposition.

7. Deterministic derivation should first be checked against `INFERRED`.
   - The derived value may be absent from the literal span.
   - The derivation can still be grounded in evidenced operands.
   - Do not add `DERIVED_EVIDENCED` unless `INFERRED` is proven insufficient.

8. Partial grounding should first be checked against `EVIDENCED_INCOMPLETE`.
   - Do not collapse partial evidence to `UNDETERMINED` unless no meaningful feature lift exists.

9. Out-of-scope refusal should first be checked against `SCOPE_BOUNDARY`.
   - Do not collapse scope boundaries to contradiction or generic refusal.

### Recommended Phase 1 ADR Shape

A future ADR should avoid a single unqualified enum as the internal model.

The minimum safe internal shape is a pair:

```text
(proposition_state, operational_event?)
```

A stronger shape is a typed event record:

```text
EpistemicEvent {
  proposition_state?: EpistemicState,
  operational_event?: OperationalEpistemicEvent,
  artifact_state?: ArtifactReplayState,
  articulation_state?: ArticulationState,
  evidence_ref: ...,
  transition_reason: ...,
}
```

The reporting surface may still collapse this to human-readable labels, but the trace should preserve the axes and must not rename existing runtime enum values without a ratified ADR.

### Phase 1 Completion Criteria

Phase 1 is complete when the project agrees that:

- proposition states and operational/meta events are separate axes,
- existing runtime enum names and serialized values are authoritative unless superseded by ADR,
- runner buckets like `correct`, `wrong`, and `refused` are not primitive epistemic states,
- decoded-but-unarticulated is an articulation failure over a decoded proposition,
- computational boundedness is operational policy, not semantic ambiguity,
- future transition audits must record both proposition state and operational/meta event when both are present,
- prior ADR compatibility has been reviewed and no supersession proceeds without explicit operator ratification.

---

## Phased Plan

### Phase 2 — Define Transition Invariants

Phase 2 is blocked until the Prior ADR Compatibility Gate above is accepted by reviewers / operator.

Once unblocked, extract deterministic transitions using runtime-aligned enum names:

| From | To | Trigger |
|---|---|---|
| `PERCEIVED` | `EVIDENCED` | Grounding succeeds. |
| `PERCEIVED` | `EVIDENCED_INCOMPLETE` | Some feature lift succeeds but required closure is missing. |
| `PERCEIVED` | `UNDETERMINED` | Feature lift cannot complete. |
| `EVIDENCED` | `VERIFIED` | Solver/pack/verifier cross-check succeeds. |
| `EVIDENCED` | `INFERRED` | Deterministic derivation over grounded inputs succeeds. |
| `EVIDENCED` | `AMBIGUOUS` | Multiple incompatible admissible branches exist. |
| `EVIDENCED` | `CONTRADICTED` | Typed semantic rule or replay check fails. |
| `EVIDENCED` | `SCOPE_BOUNDARY` | Grounded shape is real but outside declared substrate scope. |
| `VERIFIED` | `DECODED` | Deterministic replay equality holds. |
| `DECODED` | `DECODED_UNARTICULATED` | Articulation surface fails after decoded answer exists. |
| any active state | `COMPUTATIONALLY_BOUNDED` | Deterministic search/computation bound prevents completion. |

This becomes the core epistemic state machine.

### Phase 3 — Determine Lattice Structure

Current evidence suggests the taxonomy is likely:

```text
semantic axis x operational event axis
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

1. one flat state enum only,
2. the existing `EpistemicState` enum plus operational event metadata,
3. or a richer trace event model that records state, event, artifact, and articulation axes.

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
- supersede or amend any existing ADR,
- rename existing runtime enum values.

It records bounded findings and prepares the next phase of epistemic-state design under prior ADR and runtime-enum governance.
