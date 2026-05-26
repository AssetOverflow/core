import * as Dialog from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { EmptyState } from "../states/EmptyState";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/55" data-testid="overlay" />
        <Dialog.Content className="fixed left-1/2 top-[18vh] w-[min(560px,calc(100vw-32px))] -translate-x-1/2 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-4 shadow-[var(--shadow-overlay)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]">
          <Dialog.Title className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Search size={16} aria-hidden />
            Command Palette
          </Dialog.Title>
          <Dialog.Description className="sr-only">
            Empty command palette stub for the Branch 1 keyboard contract.
          </Dialog.Description>
          <EmptyState
            statement="No commands are registered in Branch 1."
            nextAction="W-027 will add command content behind this keybinding."
          />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
