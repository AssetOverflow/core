import { Copy } from "lucide-react";
import { copyText } from "../../design/lib";

export function CopyableHash({ value, label = "trace_hash" }: { value: string; label?: string }) {
  const short = value.length > 18 ? `${value.slice(0, 18)}...` : value;
  return (
    <button
      type="button"
      onClick={() => void copyText(value)}
      className="inline-flex items-center gap-1 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 py-1 font-mono text-xs text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      aria-label={`${label}: ${value}`}
    >
      <Copy size={12} aria-hidden />
      {label}:{short}
    </button>
  );
}
