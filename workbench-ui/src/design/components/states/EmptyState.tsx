import { Button } from "../primitives/Button";

type CliAction = { kind: "cli"; command: string };
type NextAction = string | CliAction;

export function EmptyState({
  statement,
  nextAction,
}: {
  statement: string;
  nextAction: NextAction;
}) {
  function handleCopy(command: string) {
    navigator.clipboard.writeText(command).catch(() => {
      // clipboard write may be unavailable in non-secure contexts; fail silently
    });
  }

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      {/* Deterministic monochrome glyph: an empty evidence slot. Static
          inline SVG — same bytes every render, no asset fetch. */}
      <svg
        aria-hidden
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        className="mb-2 text-[var(--color-text-muted)]"
      >
        <rect x="3" y="3" width="14" height="14" rx="3" stroke="currentColor" strokeDasharray="3 3" />
        <circle cx="10" cy="10" r="1.5" fill="currentColor" />
      </svg>
      <p className="m-0 text-sm text-[var(--color-text-primary)] [text-wrap:balance]">{statement}</p>
      {typeof nextAction === "string" ? (
        // A plain-string action is non-runnable guidance, not a command, so it
        // renders as static text — never an interactive control. A click-dead
        // button reads as "I clicked and nothing happened"; runnable steps use
        // the { kind: "cli", command } form below (code + Copy).
        <p className="mt-3 text-sm text-[var(--color-text-secondary)] [text-wrap:balance]">
          {nextAction}
        </p>
      ) : (
        <div className="mt-3 flex items-center gap-2">
          <code className="flex-1 rounded bg-[var(--color-surface-sunken)] px-2 py-1 font-mono text-xs text-[var(--color-text-primary)]">
            {nextAction.command}
          </code>
          <Button
            className="shrink-0"
            variant="quiet"
            type="button"
            aria-label="⌘C to copy"
            title="⌘C to copy"
            onClick={() => handleCopy(nextAction.command)}
          >
            Copy
          </Button>
        </div>
      )}
    </section>
  );
}
