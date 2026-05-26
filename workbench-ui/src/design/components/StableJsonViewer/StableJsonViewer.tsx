import { Copy, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "../primitives/Button";
import { copyText, cn } from "../../lib";
import { countLeaves, diffLeaves, leaves, parseJsonSource, type DiffKind, type JsonNode } from "./jsonModel";

const MAX_INLINE_BYTES = 16 * 1024 * 1024;
const VIRTUALIZE_LEAVES = 1000;

function bytes(source: string) {
  return new TextEncoder().encode(source);
}

async function sha256(source: string) {
  const hash = await crypto.subtle.digest("SHA-256", bytes(source));
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function nodeRows(node: JsonNode, pointer = "", depth = 0): { pointer: string; depth: number; label: string; raw?: string }[] {
  if (node.kind === "literal") return [{ pointer, depth, label: pointer.split("/").at(-1) || "/", raw: node.raw }];
  if (node.kind === "array") {
    return node.items.flatMap((item, index) => nodeRows(item, `${pointer}/${index}`, depth + 1));
  }
  return node.entries.flatMap((entry) => nodeRows(entry.value, `${pointer}/${entry.key.replaceAll("~", "~0").replaceAll("/", "~1")}`, depth + 1));
}

function DigestBadge({ source }: { source: string }) {
  const [digest, setDigest] = useState("");
  useEffect(() => {
    void sha256(source).then(setDigest);
  }, [source]);
  return (
    <button
      className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 py-1 font-mono text-xs text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      onClick={() => void copyText(digest)}
      type="button"
    >
      sha256:{digest.slice(0, 12) || "pending"}
    </button>
  );
}

function ChangeGlyph({ kind }: { kind: DiffKind }) {
  const glyph = kind === "added" ? "+" : kind === "removed" ? "-" : kind === "changed" ? "~" : " ";
  return <span aria-label={kind} className="inline-block w-4 font-mono">{glyph}</span>;
}

export function StableJsonViewer({
  source,
  compareSource,
}: {
  source: string;
  compareSource?: string;
}) {
  const rawBytes = bytes(source).byteLength;
  const parsed = useMemo(() => (rawBytes <= MAX_INLINE_BYTES ? parseJsonSource(source) : null), [rawBytes, source]);
  const leafCount = parsed ? countLeaves(parsed) : 0;

  if (rawBytes > MAX_INLINE_BYTES) {
    return (
      <section className="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] p-4">
        <div className="mb-3 flex items-center gap-2">
          <DigestBadge source={source} />
        </div>
        <p className="text-sm text-[var(--color-text-secondary)]">JSON is larger than 16 MiB and was not rendered inline.</p>
        <Button onClick={() => void copyText("/")} type="button" variant="quiet">
          <ExternalLink size={14} aria-hidden />
          Open in external viewer
        </Button>
        <Button className="ml-2" onClick={() => void copyText("/")} type="button" variant="quiet">
          <Copy size={14} aria-hidden />
          Copy path /
        </Button>
      </section>
    );
  }

  if (compareSource) {
    const right = parseJsonSource(compareSource);
    const rows = diffLeaves(leaves(parsed!), leaves(right));
    return (
      <section className="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] p-4">
        <div className="mb-3 flex items-center gap-2">
          <DigestBadge source={source} />
          <span className="text-xs text-[var(--color-text-muted)]">diff mode</span>
        </div>
        <div className="grid grid-cols-[1fr_1fr] gap-3" data-testid="json-diff">
          {rows.map((row) => (
            <div className="contents" key={row.pointer}>
              <button
                className={cn("rounded border px-2 py-1 text-left font-mono text-xs", row.kind !== "same" ? "border-[var(--color-state-warning-border)]" : "border-[var(--color-border-subtle)]")}
                onClick={() => void copyText(row.pointer)}
                type="button"
              >
                <ChangeGlyph kind={row.kind} />
                {row.pointer}: {row.before?.raw ?? ""}
              </button>
              <button
                className={cn("rounded border px-2 py-1 text-left font-mono text-xs", row.kind !== "same" ? "border-[var(--color-state-warning-border)]" : "border-[var(--color-border-subtle)]")}
                onClick={() => void copyText(row.pointer)}
                type="button"
              >
                <ChangeGlyph kind={row.kind} />
                {row.pointer}: {row.after?.raw ?? ""}
              </button>
            </div>
          ))}
        </div>
      </section>
    );
  }

  const rows = nodeRows(parsed!);
  const visibleRows = leafCount > VIRTUALIZE_LEAVES ? rows.slice(0, VIRTUALIZE_LEAVES) : rows;
  return (
    <section className="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] p-4">
      <div className="mb-3 flex items-center gap-2">
        <DigestBadge source={source} />
        {leafCount > VIRTUALIZE_LEAVES ? <span data-testid="virtualized-json" className="text-xs text-[var(--color-text-muted)]">virtualized {VIRTUALIZE_LEAVES} of {leafCount} leaves</span> : null}
      </div>
      <div className="grid gap-1" data-testid="json-rows">
        {visibleRows.map((row) => (
          <button
            className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 py-1 text-left font-mono text-xs text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            key={row.pointer}
            onClick={() => void copyText(row.pointer)}
            style={{ paddingLeft: `${8 + row.depth * 12}px` }}
            type="button"
          >
            <span className="text-[var(--color-text-muted)]">{row.pointer || "/"}</span> {row.raw}
          </button>
        ))}
      </div>
    </section>
  );
}
