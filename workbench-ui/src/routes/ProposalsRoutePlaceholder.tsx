import { EmptyState } from "../design/components/states/EmptyState";

export function ProposalsRoutePlaceholder() {
  return (
    <EmptyState
      statement="Proposals — no data loaded yet."
      nextAction={{ kind: "cli", command: "core teaching hitl-queue list" }}
    />
  );
}
