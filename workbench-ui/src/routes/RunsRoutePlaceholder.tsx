import { EmptyState } from "../design/components/states/EmptyState";

export function RunsRoutePlaceholder() {
  return (
    <EmptyState
      statement="Runs — no data loaded yet."
      nextAction="Pending W-030"
    />
  );
}
