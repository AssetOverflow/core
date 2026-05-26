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
      <p className="m-0 text-sm text-[var(--color-text-primary)]">{statement}</p>
      {typeof nextAction === "string" ? (
        <Button className="mt-3" variant="quiet" type="button">
          {nextAction}
        </Button>
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
