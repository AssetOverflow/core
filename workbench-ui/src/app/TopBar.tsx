import { CommandPalette } from "../design/components/primitives/CommandPalette";
import { useRuntimeStatus } from "../api/queries";
import { WrongZeroFrame } from "./WrongZeroFrame";

export function TopBar({
  paletteOpen,
  onPaletteOpenChange,
}: {
  paletteOpen: boolean;
  onPaletteOpenChange: (open: boolean) => void;
}) {
  const { isLoading, isError } = useRuntimeStatus();

  const connectionPill = (() => {
    if (isLoading) {
      return (
        <span
          className="rounded-full border border-[var(--color-border-subtle)] px-3 py-1 text-xs text-[var(--color-text-secondary)]"
          aria-live="polite"
        >
          Connecting…
        </span>
      );
    }
    if (isError) {
      return (
        <span
          className="rounded-full border border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] px-3 py-1 text-xs text-[var(--color-state-danger-text)]"
          aria-live="polite"
        >
          API: unreachable
        </span>
      );
    }
    return (
      <span
        className="rounded-full border border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] px-3 py-1 text-xs text-[var(--color-state-success-text)]"
        aria-live="polite"
      >
        API: connected
      </span>
    );
  })();

  return (
    <header
      data-region="topbar"
      className="flex items-center gap-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] px-4 py-2"
    >
      <span className="shrink-0 font-mono text-sm font-semibold text-[var(--color-text-primary)]">
        CORE Workbench
      </span>

      <div className="flex flex-1 justify-center">
        <button
          type="button"
          className="flex items-center gap-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-sunken)] px-3 py-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          onClick={() => onPaletteOpenChange(true)}
          aria-label="Open command palette (⌘K)"
        >
          <span>Search commands…</span>
          <kbd className="rounded border border-[var(--color-border-subtle)] px-1 font-mono text-xs">
            ⌘K
          </kbd>
        </button>
      </div>

      <WrongZeroFrame />

      <div className="shrink-0">{connectionPill}</div>

      <CommandPalette open={paletteOpen} onOpenChange={onPaletteOpenChange} />
    </header>
  );
}
