import type { ReactNode } from "react";

/** Keyboard-chord chip. Token-only; consumed by KeyboardHelp + palette hints. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd
      className="rounded border px-1.5 py-0.5 text-xs"
      style={{
        borderColor: "var(--color-border-subtle)",
        background: "var(--color-surface-inset)",
        color: "var(--color-text-mono)",
        fontFamily: "var(--font-mono)",
      }}
    >
      {children}
    </kbd>
  );
}
