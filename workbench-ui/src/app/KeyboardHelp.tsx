import * as Dialog from "@radix-ui/react-dialog";

const SHORTCUTS = [
  { keys: "⌘K", action: "Command palette" },
  { keys: "⌘I", action: "Toggle inspector" },
  { keys: "⌘1–0", action: "Navigate to route 1–10" },
  { keys: "Esc", action: "Close overlay" },
  { keys: "?", action: "This help" },
] as const;

export function KeyboardHelp({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/55" />
        <Dialog.Content
          className="fixed left-1/2 top-[18vh] w-[min(400px,calc(100vw-32px))] -translate-x-1/2 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-4 shadow-[var(--shadow-overlay)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          aria-label="Keyboard shortcuts"
        >
          <Dialog.Title className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
            Keyboard Shortcuts
          </Dialog.Title>
          <Dialog.Description className="sr-only">
            Available keyboard shortcuts for the workbench.
          </Dialog.Description>
          <dl className="m-0 grid gap-0">
            {SHORTCUTS.map((s) => (
              <div
                key={s.keys}
                className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] py-2 last:border-b-0"
              >
                <dt className="m-0 w-20 shrink-0">
                  <kbd className="rounded border border-[var(--color-border-subtle)] px-1.5 py-0.5 font-mono text-xs text-[var(--color-text-mono)]">
                    {s.keys}
                  </kbd>
                </dt>
                <dd className="m-0 text-sm text-[var(--color-text-secondary)]">
                  {s.action}
                </dd>
              </div>
            ))}
          </dl>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
