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

## Phased Plan

### Phase 1 — Separate Semantic vs Operational States

Define which states belong to proposition semantics and which belong to orchestration/runtime policy.

Goal: prevent category collapse.

Deliverable:

| State | Proposition-level? | Operational/meta? | Notes |
|---|---:|---:|---|
| `DECODED` | yes | no | Replay-equal verified proposition. |
| `BOUNDED_REFUSAL` | no | yes | Deterministic computation policy boundary. |
| `AMBIGUOUS` | yes | no | Multiple incompatible admissible propositions. |
| `ROUTE_FALLTHROUGH` | no | yes | Route-level delegation/fallback. |

### Phase 2 — Define Transition Invariants

Extract deterministic transitions:

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
- claim the starter taxonomy is final.

It records bounded findings and prepares the next phase of epistemic-state design.
