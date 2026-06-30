# Workbench Catch-up PR-3 Brief — Trace Construction Tab

**Target PR title:** `feat(workbench-ui): add Trace construction tab`
**Base:** after `feat(workbench): expose construction evidence read model`
**Scope:** frontend UI and client hooks only

## Goal

Add a Trace tab that visualizes construction/proposal-first evidence for the
selected turn.

The operator must be able to see:

```text
surface/process cue
-> ConstructionProposal(status="proposed")
-> exact spans / bindings / relations
-> ContractAssessment
-> runnable/refused + blockers
```

## Required prior PR

This PR assumes the backend endpoint exists:

```text
GET /trace/<turn_id>/construction
```

and that `workbench-ui/src/types/api.ts` contains `ConstructionEvidence` and
related types.

## Files to inspect first

- `workbench-ui/src/app/trace/TraceRoute.tsx`
- `workbench-ui/src/api/client.ts`
- `workbench-ui/src/api/queries.ts`
- `workbench-ui/src/types/api.ts`
- `workbench-ui/src/design/components/TabBar/TabBar.tsx`
- `workbench-ui/src/design/components/MetadataTable/MetadataTable.tsx`
- `workbench-ui/src/design/components/StableJsonViewer.tsx`
- `workbench-ui/src/design/components/TruncatedCell.tsx`
- `workbench-ui/src/app/routeConformance.test.tsx`

## API client additions

In `client.ts`:

```ts
export async function fetchTraceConstruction(turnId: number): Promise<ConstructionEvidence> {
  return apiFetch<ConstructionEvidence>(
    `/trace/${encodeURIComponent(String(turnId))}/construction`,
  );
}
```

In `queries.ts`:

```ts
export function useTraceConstruction(turnId?: number | null) {
  return useQuery<ConstructionEvidence, WorkbenchApiError>({
    queryKey: ["api", "trace", "construction", turnId ?? null],
    queryFn: () => fetchTraceConstruction(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
```

## Trace tab addition

Add to `TRACE_TABS`:

```ts
{ id: "construction", label: "Construction" }
```

Recommended order:

```text
Pipeline | Construction | Field | Bundle | Surfaces | Grounding | Verdicts | Metadata | Raw
```

Thread query state through `TraceRoute` and `TraceDetail` exactly like pipeline,
field, and bundle.

## Components

Add either local components inside `TraceRoute.tsx` first, or separate files if
size becomes excessive:

```text
ConstructionTab
ConstructionAuthorityBanner
SourceTextWithSpans
ConstructionProposalCard
RoleObligationTable
MentionBindingTable
BoundRelationTable
ContractAssessmentPanel
ConstructionMissingEvidence
```

### ConstructionAuthorityBanner

Required visible statements:

```text
Proposal != Runnable
Contract Determines
Diagnostic Only
Serving Disallowed
Exact Span Required
```

### SourceTextWithSpans

Minimum acceptable v1:

- render `problem_text` in monospace/pre-wrap;
- list source spans in a table with start/end/text;
- highlight exact span rows on hover if easy;
- never alter span text;
- show `missing_evidence` if problem_text is absent.

### Proposal cards

Each proposal card must show:

```text
family_id
relation_type
candidate_organ
status
role obligations
source spans
diagnostic_only
serving_allowed
```

### Contract assessment cards

Each assessment card must show:

```text
candidate_organ
family_id
runnable yes/no
missing_bindings
unresolved_hazards
explanation
evidence_spans
```

Use danger/warning/success tokens honestly. Do not use success styling merely
because a proposal exists.

## Empty/error/loading contracts

Required states:

- loading label: `Loading construction evidence...`
- empty/missing statement: `No construction evidence recorded for this turn.`
- error mutation status: `No trace mutation occurred.`
- reproducer: `curl /trace/<turn_id>/construction`
- retry: `Retry: safe`

## Route conformance updates

If `routeConformance.test.tsx` needs no new route case, add focused tests under
Trace instead. The route count must remain 16.

## Tests to add/run locally

```bash
cd workbench-ui
pnpm test
pnpm build
```

Focused tests:

- Trace renders the Construction tab label.
- Missing construction evidence renders honest empty/missing state.
- Error renders `What failed`, `Mutation status`, `Reproducer`, `Retry safety`.
- Proposal cards show `Diagnostic Only` and `Serving Disallowed`.
- Contract refused row shows missing bindings and unresolved hazards.
- No button text includes apply, promote, serve, mutate, or ratify.

## Non-goals

- No backend schema changes in this PR.
- No new route.
- No proposal ratification changes.
- No candidate operator execution.
- No replay execution.
- No CORE-Logos Studio.
