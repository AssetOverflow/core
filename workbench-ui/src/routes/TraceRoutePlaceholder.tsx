import { EmptyState } from "../design/components/states/EmptyState";

export function TraceRoutePlaceholder() {
  return (
    <EmptyState
      statement="Trace — no data loaded yet."
      nextAction={{ kind: "cli", command: "core trace <prompt>" }}
    />
  );
}
