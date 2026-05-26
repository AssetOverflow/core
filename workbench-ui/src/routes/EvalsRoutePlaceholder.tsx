import { EmptyState } from "../design/components/states/EmptyState";

export function EvalsRoutePlaceholder() {
  return (
    <EmptyState
      statement="Evals — no data loaded yet."
      nextAction={{ kind: "cli", command: "core eval --list" }}
    />
  );
}
