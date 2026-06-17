# ProblemRepresentation + ReasoningAuditArtifact Ratification

**Date:** 2026-06-17
**Status:** Draft for review
**Author:** Internal architectural review

## Summary

This document proposes the introduction of two new typed, replayable artifact layers:

- `ProblemRepresentation`
- `ReasoningAuditArtifact`

These serve as pre-solver and post-solver inspection surfaces for Ladder A/B/D work and as mining inputs for Ladder C (Contemplation / proposal generation).

They are **not** durable truth mutations. They are inspection and proposal-generation artifacts. All promotion to ratified state continues to go through existing review, proof, and ratification gates.

## Motivation

Current refusals in GSM8K / Ladder A work are frequently not "solver cannot solve" failures but "recognized something but could not safely produce a typed, grounded representation that allows correct operator injection."

A canonical `ProblemRepresentation` artifact creates a stable audit point before any operator injection or solving occurs. A `ReasoningAuditArtifact` provides structured post-hoc reflection that can be mined by Contemplation without collapsing into claim status.

This directly supports the principles in the Capability Roadmap while preserving CORE’s existing epistemic, proposal, and runtime boundaries.

## Core Design Principles

1. **Separation of concerns**  
   - `ProblemRepresentation` describes the problem (knowns, unknowns, typed relations, scope).  
   - `ReasoningAuditArtifact` describes the reasoning process (assumptions, verification steps, failure modes, reflection).  
   - Neither mutates `claim status`, `EpistemicState`, or `DisclosureClaim`.

2. **Replayable and inspectable**  
   Both artifacts must be fully replayable and linkable from Workbench views, traces, and proposals.

3. **Proposal-only promotion**  
   These artifacts may generate candidate proposals. They do not themselves constitute ratified truth or operator injection.

4. **Scoped application**  
   Heavy `ProblemRepresentation` is mandatory only for non-trivial paths (multi-step math, graph planning, operator injection, closed-frame verdicts, proposal generation). It is optional or bypassed for simple retrieval, static inspection, or explicit refusal paths.

## Proposed Artifact Shapes (Initial)

### ProblemRepresentation

```json
{
  "source_id": string,
  "case_id": string,
  "knowns": [...],
  "unknowns": [...],
  "quantities": [...],
  "units": [...],
  "actors_entities": [...],
  "typed_relations": [...],
  "candidate_problem_class": string,
  "required_operators": [...],
  "refusal_hazards": [...],
  "open_world_or_closed_frame": "open" | "closed",
  "representation_status": "complete" | "incomplete" | "ambiguous" | "refused"
}
```

### ReasoningAuditArtifact

```json
{
  "representation_id": string,
  "reasoning_mode": "recognition" | "injection" | "proof" | "closed_frame" | "analogy_candidate" | "solve" | "refusal",
  "assumptions": [...],
  "grounding_dependencies": [...],
  "verification_checks_performed": [...],
  "confuser_classes_considered": [...],
  "failure_mode_flags": [...],
  "reflection_summary": string,
  "proposal_candidates": [...]
}
```

## Integration Points

- **Ladder A**: `ProblemRepresentation` emitted before operator injection for selected GSM8K frontier classes.
- **Ladder B**: `ReasoningAuditArtifact` records reasoning mode to help enforce open/closed-world separation.
- **Ladder C**: Both artifacts become primary mining inputs for Contemplation (refusal clusters, weakness annotation, targeted proposals).
- **Ladder D**: Both artifacts become first-class inspectable surfaces in CORE-Logos and Workbench.

## Governance

- These artifacts follow existing proposal/review/ratification paths.
- They do **not** expand or mutate claim status.
- Analogical reasoning is treated strictly as candidate generation (structural signature → explicit slot mapping → independent verification). It may never determine truth or bypass grounding.
- Metrics for "metacognitive quality" are objective and structural (completeness of representation fields, provenance of assumptions, verification checks passed, review yield, reduction in repeated refusal classes) rather than narrative quality.

## Next Steps (Recommended)

1. Ratify this document.
2. Implement smallest useful `ProblemRepresentation` slice for 1–2 high-refusal GSM8K families.
3. Wire `ReasoningAuditArtifact` generation into post-solver / post-proposal paths.
4. Update Contemplation mining logic to consume these artifacts for targeted proposal generation.
5. Add corresponding prompt section to the agent prompt library.

## Status

Draft. Open for review and ratification.