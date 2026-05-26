import { EmptyState } from "../design/components/states/EmptyState";

export function AuditRoutePlaceholder() {
  return (
    <EmptyState
      statement="Audit — no data loaded yet."
      nextAction={{ kind: "cli", command: "teaching/proposals/proposals.jsonl" }}
    />
  );
}
