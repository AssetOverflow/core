import { EmptyState } from "../design/components/states/EmptyState";

export function PacksRoutePlaceholder() {
  return (
    <EmptyState
      statement="Packs — no data loaded yet."
      nextAction={{ kind: "cli", command: "core pack list" }}
    />
  );
}
