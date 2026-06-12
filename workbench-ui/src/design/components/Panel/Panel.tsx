import type { ReactNode } from "react";

export interface PanelProps {
  title: string;
  /** Right-aligned header slot for actions/filters. */
  toolbar?: ReactNode;
  children: ReactNode;
}

/**
 * Standard panel chrome (Wave R brief R0d) — header (title + toolbar slot)
 * over a body. Routes compose this instead of hand-rolling borders.
 */
export function Panel({ title, toolbar, children }: PanelProps) {
  return (
    <section
      className="flex min-h-0 flex-col rounded-lg border"
      style={{
        borderColor: "var(--color-border-subtle)",
        background: "var(--color-surface-raised)",
      }}
      data-testid="panel"
    >
      <header
        className="flex items-center justify-between gap-3 border-b px-3 py-2"
        style={{ borderColor: "var(--color-border-subtle)" }}
      >
        <h2
          className="m-0 text-sm font-semibold [text-wrap:balance]"
          style={{ color: "var(--color-text-primary)" }}
        >
          {title}
        </h2>
        {toolbar ? <div className="flex items-center gap-2">{toolbar}</div> : null}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">{children}</div>
    </section>
  );
}
