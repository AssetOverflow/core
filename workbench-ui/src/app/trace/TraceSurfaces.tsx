import type { ChatTurnResult } from "../../types/api";

/**
 * Renders the three runtime surfaces as visually distinct elements with
 * explicit role labels, per addendum §2. This component carries the
 * runtime-contract obligation: surface / articulation_surface / walk_surface
 * MUST NOT be collapsed into a single "response" pane.
 *
 * Read-only. Does not mutate input.
 */
export function TraceSurfaces({ result }: { result: ChatTurnResult }) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3"
      data-testid="trace-surfaces"
      aria-label="Runtime surfaces"
    >
      <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
        Surfaces
      </h3>

      <div
        className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
        data-testid="trace-surface-surface"
      >
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            surface
          </span>
          <span className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            user-facing response
          </span>
        </div>
        <p className="m-0 mt-1 text-sm text-[var(--color-text-primary)]">
          {result.surface}
        </p>
      </div>

      <div
        className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
        data-testid="trace-surface-articulation"
      >
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            articulation_surface
          </span>
          <span className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            realizer output
          </span>
        </div>
        <p className="m-0 mt-1 text-sm text-[var(--color-text-primary)]">
          {result.articulation_surface ?? (
            <span className="text-[var(--color-text-secondary)]">not emitted</span>
          )}
        </p>
      </div>

      <div
        className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
        data-testid="trace-surface-walk"
      >
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            walk_surface
          </span>
          <span className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            manifold evidence
          </span>
        </div>
        <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-primary)]">
          {result.walk_surface ?? (
            <span className="text-[var(--color-text-secondary)]">not emitted</span>
          )}
        </p>
      </div>
    </section>
  );
}
