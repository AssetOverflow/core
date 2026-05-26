import { EmptyState } from "../design/components/states/EmptyState";

export function VaultRoutePlaceholder() {
  return (
    <EmptyState
      statement="Vault — no data loaded yet."
      nextAction="Pending W-029"
    />
  );
}
