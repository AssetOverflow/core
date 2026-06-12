import { type ReactNode, useState } from "react";
import { Copy, Check } from "lucide-react";
import { copyText } from "../../lib";
import { useManagedTimeout } from "../../hooks/useManagedTimeout";

export interface MetadataRow {
  key: string;
  value: ReactNode;
  copyable?: boolean;
  mono?: boolean;
}

export interface MetadataTableProps {
  rows: readonly MetadataRow[];
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const scheduleReset = useManagedTimeout();

  return (
    <button
      type="button"
      aria-label={`Copy ${text}`}
      className="ml-1 inline-flex items-center opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      style={{
        transitionDuration: "var(--motion-duration-fast)",
        transitionTimingFunction: "var(--motion-ease-standard)",
        background: "none",
        border: "none",
        cursor: "pointer",
        color: "var(--color-text-muted)",
        padding: 0,
      }}
      onClick={() => {
        void copyText(text).then(() => {
          setCopied(true);
          scheduleReset(() => setCopied(false), 1500);
        });
      }}
    >
      {copied ? (
        <Check size={12} aria-hidden />
      ) : (
        <Copy size={12} aria-hidden />
      )}
    </button>
  );
}

export function MetadataTable({ rows }: MetadataTableProps) {
  return (
    <dl
      className="m-0 grid gap-0"
      data-testid="metadata-table"
    >
      {rows.map((row) => (
        <div
          key={row.key}
          className="group flex items-baseline gap-3 border-b border-[var(--color-border-subtle)] px-1 py-2 last:border-b-0"
        >
          <dt
            className="m-0 w-36 shrink-0 text-xs text-[var(--color-text-secondary)]"
            style={{ fontSize: "var(--text-xs)" }}
          >
            {row.key}
          </dt>
          <dd
            className="m-0 flex items-center text-sm text-[var(--color-text-primary)]"
            style={{
              fontSize: "var(--text-sm)",
              fontFamily: row.mono ? "var(--font-mono)" : undefined,
            }}
          >
            {row.value}
            {row.copyable && typeof row.value === "string" && (
              <CopyButton text={row.value} />
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
