import { type ReactNode, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Popover from "@radix-ui/react-popover";
import { Check, Copy, Expand, Maximize2 } from "lucide-react";
import { cn } from "../../lib";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";

/**
 * Truncated table cell with a full-content escape hatch.
 *
 * Every grid "table" in the workbench truncates dense values (proposal ids,
 * source kinds, digests, paths) to keep rows scannable. That hides the full
 * value. `TruncatedCell` keeps the compact display but attaches one
 * hover/focus-revealed trigger that opens a popover showing the *complete*
 * value — selectable, scrollable, copyable — and, for long/structured values,
 * an "Open full view" button into a roomy modal.
 *
 * One component, two reveals: a lightweight popover for the common case and a
 * dynamic modal for the long case. Drop it in wherever a `truncate` span lives.
 *
 * The reveal trigger calls `stopPropagation`, so it never steals a row's
 * click/select behaviour — opening the full value and selecting the row stay
 * independent affordances.
 */

const MODAL_THRESHOLD = 160;

export interface TruncatedCellProps {
  /** Full value — the source of truth shown in the reveal/modal and copied. */
  value: string;
  /**
   * Optional compact display node. Defaults to `value` rendered with the
   * `truncate` ellipsis from the parent cell width.
   */
  display?: ReactNode;
  /** Column/field name — labels the trigger, popover, and modal for a11y. */
  label?: string;
  /** Render display + full value in the monospace face. */
  mono?: boolean;
  /**
   * How to render the full value. `break-all` suits opaque ids/digests;
   * `pre-wrap` preserves whitespace for prose/JSON. Defaults to `break-all`.
   */
  wrap?: "break-all" | "pre-wrap";
  /** Class applied to the inline display span. */
  className?: string;
  /**
   * Horizontal alignment of the cell content. `end` hugs the right edge (for
   * right-aligned table columns) and right-justifies the display text.
   * Defaults to `start`.
   */
  align?: "start" | "end";
}

function shouldOfferModal(value: string) {
  return value.length > MODAL_THRESHOLD || value.includes("\n");
}

function CopyAction({ value, label }: { value: string; label: string }) {
  const { copied, copy } = useCopyToClipboard();
  return (
    <button
      type="button"
      onClick={() => copy(value)}
      aria-label={copied ? "Copied" : `Copy ${label}`}
      className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border-subtle)] bg-transparent px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
    >
      {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function FullValue({
  value,
  mono,
  wrap,
}: {
  value: string;
  mono?: boolean;
  wrap: "break-all" | "pre-wrap";
}) {
  return (
    <div
      className={cn(
        "max-h-64 overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2 text-sm text-[var(--color-text-primary)] select-text",
        mono && "font-mono",
        wrap === "break-all" ? "break-all" : "whitespace-pre-wrap break-words",
      )}
    >
      {value}
    </div>
  );
}

export function TruncatedCell({
  value,
  display,
  label = "value",
  mono,
  wrap = "break-all",
  className,
  align = "start",
}: TruncatedCellProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const offerModal = shouldOfferModal(value);

  const stop = (event: { stopPropagation: () => void }) => event.stopPropagation();

  return (
    <span
      className={cn(
        "group/cell flex min-w-0 items-center gap-1",
        align === "end" && "justify-end",
        mono && "font-mono",
      )}
    >
      <span
        className={cn("truncate", align === "end" && "text-right", className)}
        title={value}
      >
        {display ?? value}
      </span>
      <Popover.Root>
        <Popover.Trigger asChild>
          <button
            type="button"
            onClick={stop}
            onKeyDown={stop}
            aria-label={`Show full ${label}`}
            className="inline-flex shrink-0 items-center rounded-sm p-0.5 text-[var(--color-text-muted)] opacity-0 transition-opacity hover:text-[var(--color-text-primary)] focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] group-hover/cell:opacity-100 data-[state=open]:opacity-100"
          >
            <Expand size={12} aria-hidden />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            side="bottom"
            sideOffset={4}
            collisionPadding={8}
            onClick={stop}
            onKeyDown={stop}
            className="z-50 w-[min(420px,calc(100vw-32px))] rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-3 shadow-[var(--shadow-overlay)] focus-visible:outline-none"
          >
            <div className="mb-2 text-xs font-medium uppercase tracking-normal text-[var(--color-text-muted)]">
              {label}
            </div>
            <FullValue value={value} mono={mono} wrap={wrap} />
            <div className="mt-2 flex items-center justify-end gap-2">
              {offerModal ? (
                <button
                  type="button"
                  onClick={() => setModalOpen(true)}
                  className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border-subtle)] bg-transparent px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  <Maximize2 size={12} aria-hidden />
                  Open full view
                </button>
              ) : null}
              <CopyAction value={value} label={label} />
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>

      <Dialog.Root open={modalOpen} onOpenChange={setModalOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/55" />
          <Dialog.Content
            onClick={stop}
            aria-label={label}
            className="fixed left-1/2 top-[12vh] z-50 flex max-h-[76vh] w-[min(720px,calc(100vw-32px))] -translate-x-1/2 flex-col rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-4 shadow-[var(--shadow-overlay)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            <Dialog.Title className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
              {label}
            </Dialog.Title>
            <Dialog.Description className="sr-only">
              Full contents of the {label} cell.
            </Dialog.Description>
            <div className="min-h-0 flex-1 overflow-auto">
              <div
                className={cn(
                  "rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3 text-sm text-[var(--color-text-primary)] select-text",
                  mono && "font-mono",
                  wrap === "break-all" ? "break-all" : "whitespace-pre-wrap break-words",
                )}
              >
                {value}
              </div>
            </div>
            <div className="mt-3 flex items-center justify-end gap-2">
              <CopyAction value={value} label={label} />
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="inline-flex items-center rounded-md border border-[var(--color-border-subtle)] bg-transparent px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  Close
                </button>
              </Dialog.Close>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </span>
  );
}
