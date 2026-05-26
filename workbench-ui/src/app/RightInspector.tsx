// RightInspector — default collapsed in W-027 (no content yet)
export function RightInspector({ collapsed = true }: { collapsed?: boolean }) {
  if (collapsed) return null;
  return (
    <aside
      data-region="inspector"
      className="h-full overflow-y-auto border-l border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-4 text-sm text-[var(--color-text-secondary)]"
    >
      Inspector
    </aside>
  );
}
