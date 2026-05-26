import { EmptyState } from "../design/components/states/EmptyState";

export function ReplayRoutePlaceholder() {
  return (
    <EmptyState
      statement="Replay — no data loaded yet."
      nextAction="Pending W-031"
    />
  );
}
