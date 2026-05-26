import { EmptyState } from "../design/components/states/EmptyState";

export function ChatRoutePlaceholder() {
  return (
    <EmptyState
      statement="Chat — no data loaded yet."
      nextAction={{ kind: "cli", command: "core chat" }}
    />
  );
}
