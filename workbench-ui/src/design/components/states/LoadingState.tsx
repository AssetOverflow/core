export function LoadingState({ label }: { label: string }) {
  if (label.trim().toLowerCase() === "thinking...") {
    throw new Error('LoadingState label must be specific; "Thinking..." is forbidden.');
  }

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">{label}</p>
      <div
        aria-hidden
        className="mt-3 h-3 w-full rounded bg-[var(--color-surface-overlay)] after:block after:h-3 after:w-1/3 after:rounded after:bg-[var(--color-border-strong)] after:content-['']"
        data-shimmer-cycles="2"
      />
    </section>
  );
}
