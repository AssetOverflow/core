import * as Popover from "@radix-ui/react-popover";
import { Copy } from "lucide-react";
import type { CSSProperties } from "react";
import { copyText, cn } from "../../lib";

export function InfoBadge({
  label,
  colorToken,
  meaning,
  adr,
  evidence,
  mono = false,
  onCopy,
}: {
  label: string;
  colorToken: string;
  meaning: string;
  adr: string;
  evidence: string;
  mono?: boolean;
  onCopy?: string;
}) {
  const style = {
    backgroundColor: `color-mix(in srgb, var(${colorToken}) 18%, transparent)`,
    borderColor: `var(${colorToken})`,
    color: `var(${colorToken})`,
  } as CSSProperties;

  return (
    <Popover.Root>
      <Popover.Trigger
        className={cn(
          "inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs font-medium transition-colors motion-standard focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
          mono && "font-mono",
        )}
        style={style}
      >
        {label}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          className="z-50 w-72 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-3 text-sm text-[var(--color-text-primary)] shadow-[var(--shadow-overlay)]"
        >
          <div className="font-semibold">{label}</div>
          <p className="my-2 text-[var(--color-text-secondary)]">{meaning}</p>
          <dl className="m-0 grid gap-1 text-xs">
            <dt className="text-[var(--color-text-muted)]">Pinned by</dt>
            <dd className="m-0">{adr}</dd>
            <dt className="text-[var(--color-text-muted)]">Evidence example</dt>
            <dd className="m-0">{evidence}</dd>
          </dl>
          {onCopy ? (
            <button
              className="mt-3 inline-flex items-center gap-1 rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              onClick={() => void copyText(onCopy)}
              type="button"
            >
              <Copy size={12} aria-hidden />
              Copy
            </button>
          ) : null}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
