import { Search } from "lucide-react";
import { Button } from "../../design/components/primitives/Button";
import type { ChatTurnResult } from "../../types/api";
import { EvidenceStrip, type TraceFocus } from "./EvidenceStrip";

export function ResponseCard({
  result,
  onOpenTrace,
}: {
  result: ChatTurnResult;
  onOpenTrace: (focus: TraceFocus) => void;
}) {
  return (
    <article className="grid gap-4 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <div className="prose prose-invert max-w-none text-sm text-[var(--color-text-primary)]">
        {result.surface}
      </div>
      <EvidenceStrip result={result} onOpen={onOpenTrace} />
      <div>
        <Button type="button" variant="quiet" onClick={() => onOpenTrace("metadata")}>
          <Search size={14} aria-hidden />
          Open trace drawer
        </Button>
      </div>
    </article>
  );
}
