# CORE Workbench UI/UX Guide Addendum — Catch-up Baseline

**Date:** 2026-06-23  
**Status:** Addendum to `docs/workbench/UI-UX-GUIDE.md`  
**Reason:** Workbench/UI must catch up to proposal-first construction, residual-gated practice, quantity-entity candidate operators, and generalization audit governance.

## 1. Authoritative posture

This addendum does not replace the Workbench guide. It sharpens it for the post
proposal-first/kernel-governance work.

Workbench remains a local operator/auditor surface. It is allowed to:

- read committed evidence;
- run existing allowlisted read-only or explicitly admitted local paths;
- expose evidence, replay, audit, and proposal boundaries;
- make absence visible;
- make non-authority visible.

Workbench is not allowed to:

- synthesize evidence;
- imply serving authority from diagnostic evidence;
- expose raw sealed benchmark items;
- directly patch packs/policies/corpora from eval failures;
- create route-level mutation affordances without an admitted handler;
- create CORE-Logos Studio semantics before proposal-only artifacts exist.

## 2. New catch-up pillars

### 2.1 Construction evidence must be first-class in Trace

Trace currently shows pipeline, field, bundle, surfaces, grounding, verdicts,
metadata, and raw evidence. The next required evidence surface is construction:

```text
surface/process cue
-> ConstructionProposal(status="proposed")
-> exact spans and bindings
-> ContractAssessment
-> diagnostic runnable/refused
```

The UI must say plainly:

```text
Proposal != Runnable
Contract Determines
Diagnostic Only
Serving Disallowed
Exact Span Required
```

### 2.2 Quantity-entity evidence must not be generic NLP extraction

`binding.quantity_entity` is a local exact grounding seam. It is not an ontology
extractor, semantic tagger, or natural-language guess. Workbench must render it
as local quantity/entity evidence with exact spans and blocker codes.

### 2.3 Candidate operators and sealed practice are diagnostic

The residual/practice spine must be visible only as evidence:

```text
ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateOperatorResult
-> CandidateAttemptRunBinding
-> ReplayAdapterResult | ReplayAdapterRefusal
-> SealedPracticeTrace
```

This chain does not answer, serve, mutate, ratify, teach, or promote. If the UI
shows any part of it, each card must disclose that it is diagnostic/inert unless
a future ADR admits more authority.

### 2.4 Generalization audits are governance artifacts

Generalization benchmark reports are not practice data and not patch targets.
Workbench must treat them as audit artifacts:

- aggregate-only reports;
- no raw sealed item exposure;
- license/checksum/cache visibility;
- committed report pin vs ephemeral local output distinction;
- governed rebaseline event trail.

### 2.5 ProposalArtifact is the target visual grammar

Math proposals, cognition proposals, construction proposal previews, future
CORE-Logos proposals, and later modalities should converge into one review
language:

```text
subject
state
capability_level
source
proposed_change
reasoning_trace
evidence_pointers
validation
replay_evidence
safety_report
affected_artifacts
handler_route
audit_refs
ui_disclosure
```

Capability levels:

| Level | Meaning | UI may do |
|---|---|---|
| `inspect_only` | read evidence only | read, copy, navigate |
| `proposal_only` | draft/preview artifact may exist | validate, export, copy, no apply |
| `ratification_enabled` | admitted handler exists | ratify/reject/defer through handler only |

## 3. Route-specific catch-up table

| Route | Required catch-up |
|---|---|
| `/trace` | Add Construction tab backed by read-only construction evidence endpoint. |
| `/proposals` | Introduce shared ProposalArtifact frame and adapt math/cognition details into it. |
| `/evals` | Add Generalization Audits and Report Pins views; distinguish committed vs ephemeral. |
| `/audit` | Add governance filters and event cards for reports, practice traces, candidate operators, startup guards. |
| `/tour` | Convert into guided proof tour over real evidence routes. |
| `/demos` | Add demo script/evidence links/reproducer panels. |
| `/logos` | Polish read-only evidence, safety, alignment, holonomy; defer Studio. |
| `/packs` | Cross-link to CORE-Logos where pack identity/safety evidence exists. |

## 4. Implementation order

```text
1. docs/readme/addendum/master plan
2. backend construction evidence read model
3. Trace Construction tab
4. residual/practice evidence projections
5. ProposalArtifact frame
6. generalization audit summaries in Evals
7. audit governance expansion
8. demo theater proof tour
9. CORE-Logos read-only polish
10. visual/capture hardening
```

## 5. Acceptance doctrine for every PR

Every UI/Workbench PR must answer:

```text
What evidence is shown?
Where did it come from?
Can it replay?
Did mutation happen?
Could mutation happen?
What authority boundary controls it?
What does this not prove?
```

If any answer is unknown, the UI must say so rather than smooth it over.
