import { useInspector } from "./inspector/InspectorStore";
import { ArtifactInspectorView } from "./inspector/views/ArtifactInspectorView";
import { ProposalInspectorView } from "./inspector/views/ProposalInspectorView";
import { TraceNodeInspectorView } from "./inspector/views/TraceNodeInspectorView";
import { ReplayDiffInspectorView } from "./inspector/views/ReplayDiffInspectorView";

export function RightInspector({ collapsed }: { collapsed?: boolean }) {
  const { state } = useInspector();
  const isCollapsed = collapsed ?? state.collapsed;

  if (isCollapsed) return null;

  return (
    <aside
      id="right-inspector"
      data-region="inspector"
      data-testid="right-inspector"
      className="h-full overflow-y-auto border-l border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-4 text-sm text-[var(--color-text-secondary)]"
      aria-label="Entity inspector"
    >
      {state.entity === null ? (
        <p
          className="m-0 text-xs text-[var(--color-text-secondary)]"
          data-testid="inspector-empty"
        >
          Select an entity to inspect.
        </p>
      ) : state.entity.kind === "artifact" ? (
        <ArtifactInspectorView artifactId={state.entity.artifactId} />
      ) : state.entity.kind === "proposal" ? (
        <ProposalInspectorView proposalId={state.entity.proposalId} />
      ) : state.entity.kind === "trace-node" ? (
        <TraceNodeInspectorView
          artifactId={state.entity.artifactId}
          nodeId={state.entity.nodeId}
        />
      ) : state.entity.kind === "replay-diff" ? (
        <ReplayDiffInspectorView artifactId={state.entity.artifactId} />
      ) : null}
    </aside>
  );
}
