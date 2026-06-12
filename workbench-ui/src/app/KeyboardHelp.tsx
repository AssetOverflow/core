import * as Dialog from "@radix-ui/react-dialog";
import { Kbd } from "../design/components/primitives/Kbd";
import { useShortcuts } from "./shortcutRegistry";

/**
 * Keyboard help overlay — registry-driven (Wave R brief R0d).
 *
 * Rows render from the live shortcut registry, where binding sites register
 * exactly what they handle while mounted. Advertising an unimplemented
 * shortcut is structurally impossible: there is no hand-maintained list to
 * drift. (R0a removed three false rows by hand; this removes the failure
 * mode itself.)
 */
export function KeyboardHelp({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const shortcuts = useShortcuts();

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
            Keyboard shortcuts currently active in the workbench.
          </Dialog.Description>
          <dl className="m-0 grid gap-0">
            {shortcuts.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] py-2 last:border-b-0"
              >
                <dt className="m-0 w-20 shrink-0">
                  <Kbd>{s.keys}</Kbd>
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
