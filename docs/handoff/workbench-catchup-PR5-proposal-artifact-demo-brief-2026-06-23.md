# Workbench Catch-up PR-5 Brief — ProposalArtifact Frame + Demo Theater Proof Tour

**Target PR title:** `feat(workbench-ui): add proposal artifact frame`
**Follow-up title:** `feat(workbench-ui): upgrade demo theater proof tour`
**Scope:** frontend shared proposal grammar and demo narrative surfaces

## Goal

Make proposal review and demos coherent across CORE.

Workbench should stop presenting proposals as disconnected route-specific
objects. Math proposals, cognition teaching proposals, construction proposal
previews, and future CORE-Logos proposal-only artifacts should share one visual
review language.

Demo Theater and Tour should then use that same evidence grammar to tell the
partnership story.

## ProposalArtifact visual grammar

The target frame:

```text
ProposalArtifactFrame
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
  suggested_cli
  audit_refs
  ui_disclosure
```

Do not require all fields to exist in v1. Missing fields must render as absent,
not as successful evidence.

## Capability levels

| Level | Meaning | UI may do |
|---|---|---|
| `inspect_only` | Read evidence only. | Read, copy, navigate. |
| `proposal_only` | Draft/preview artifact may exist. | Validate/export/copy, no apply. |
| `ratification_enabled` | Admitted handler exists. | Ratify/reject/defer through handler only. |

No Ratify button may render unless:

```text
capability_level == ratification_enabled
handler_route exists
handler was admitted by prior ADR/tests
backend preconditions pass
```

## Frontend components

Add under a shared proposal directory, e.g.:

```text
workbench-ui/src/app/proposal-artifacts/ProposalArtifactFrame.tsx
workbench-ui/src/app/proposal-artifacts/ProposalCapabilityBadge.tsx
workbench-ui/src/app/proposal-artifacts/ProposalSubjectHeader.tsx
workbench-ui/src/app/proposal-artifacts/ProposalEvidencePointerList.tsx
workbench-ui/src/app/proposal-artifacts/ProposalReasoningTraceViewer.tsx
workbench-ui/src/app/proposal-artifacts/ProposalValidationReport.tsx
workbench-ui/src/app/proposal-artifacts/ProposalSafetyReport.tsx
workbench-ui/src/app/proposal-artifacts/ProposalHandlerDisclosure.tsx
workbench-ui/src/app/proposal-artifacts/ProposalAuditRefs.tsx
```

Start with frontend adapter types if backend universal schema does not exist yet:

```ts
type ProposalCapabilityLevel = "inspect_only" | "proposal_only" | "ratification_enabled";

interface ProposalArtifactView {
  proposal_id: string;
  subject: { kind: string; subject_id: string; display_name: string };
  state: string;
  capability_level: ProposalCapabilityLevel;
  source_kind: string;
  proposed_change?: unknown;
  reasoning_trace?: unknown;
  evidence_pointers?: unknown[];
  validation?: unknown;
  replay_evidence?: unknown;
  safety_report?: unknown;
  handler_route?: string | null;
  suggested_cli?: string | null;
  audit_refs?: unknown[];
  ui_disclosure: string;
}
```

## Initial adapters

Add adapter functions near the existing proposals route first:

```text
adaptMathProposalToArtifact(detail)
adaptCognitionProposalToArtifact(detail)
adaptConstructionProposalToArtifactPreview(proposal, assessment)
```

Initial mapping:

| Source | capability_level |
|---|---|
| Math proposal with admitted handler | `ratification_enabled` |
| Math proposal without handler | `proposal_only` or `inspect_only` depending on data |
| Cognition teaching proposal | existing behavior; usually `inspect_only` unless admitted route exists |
| Construction proposal preview | `inspect_only` |
| CORE-Logos pack evidence | `inspect_only` until future proposal-only artifact PR |

## Demo Theater proof tour

After proposal frames exist, upgrade `/tour` and `/demos` to narrate real evidence.

Each demo step should contain:

```text
Claim
What this proves
What this does not prove
Evidence route
Artifact/digest
Reproducer
Failure mode
```

Flagship proof paths:

1. Deterministic turn evidence:

```text
Chat -> Trace -> Field -> Bundle -> Replay
```

2. Proposal-first construction:

```text
Trace -> Construction -> Contract blockers
```

3. Residual-gated practice:

```text
Evals/Trace -> Candidate -> Replay -> Sealed trace -> Audit
```

4. Generalization audit governance:

```text
Evals -> Generalization -> Report Pins -> Audit
```

## Required demo copy doctrine

Every demo must render both:

```text
What this proves
What this does not prove
```

A demo must never claim generalization from a registered scenario. A replay demo
must not claim to distinguish nondeterminism from unrecorded origin-state
influence unless the backend evidence explicitly supports that distinction.

## Tests to add/run locally

```bash
cd workbench-ui
pnpm test
pnpm build
pnpm test:e2e
```

Focused tests:

- ProposalArtifactFrame renders capability level.
- Ratify controls do not render for `inspect_only` or `proposal_only`.
- Math proposal with admitted handler still renders existing ratification path.
- Construction proposal preview has no apply/run/promote button.
- Demo step renders both proof and non-proof claims.
- Demo evidence links route to existing paths only.

## Non-goals

- No universal backend ProposalArtifact migration in this PR unless separately authorized.
- No new mutation handler.
- No CORE-Logos Studio.
- No new route count.
- No scripted demo data fabrication.
