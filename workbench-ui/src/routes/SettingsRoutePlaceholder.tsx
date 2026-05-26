import { EmptyState } from "../design/components/states/EmptyState";

export function SettingsRoutePlaceholder() {
  return (
    <EmptyState
      statement="Settings — no data loaded yet."
      nextAction={{ kind: "cli", command: "docs/runtime_contracts.md" }}
    />
  );
}
