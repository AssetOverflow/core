import { Copy } from "lucide-react";
import { Button } from "../../design/components/primitives/Button";
import { copyText } from "../../design/lib";
import type { ProposalDetail } from "../../types/api";

function fallbackCommands(proposalId: string): string[] {
  return [
    `core teaching review --proposal-id ${proposalId} --accept`,
    `core teaching review --proposal-id ${proposalId} --reject`,
  ];
}

export function SuggestedCLIBox({ proposal }: { proposal: Pick<ProposalDetail, "proposal_id" | "suggested_cli"> }) {
  const commands = proposal.suggested_cli
    ? [proposal.suggested_cli]
    : fallbackCommands(proposal.proposal_id);

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Operator CLI review</h3>
      <div className="mt-3 grid gap-2">
        {commands.map((command) => (
          <div className="flex items-center gap-2" key={command}>
            <code
              className="min-w-0 flex-1 select-all overflow-x-auto rounded-md bg-[var(--color-surface-inset)] px-2 py-2 font-mono text-xs text-[var(--color-text-primary)]"
            >
              {command}
            </code>
            <Button
              aria-label={`Copy ${command}`}
              className="shrink-0"
              onClick={() => void copyText(command)}
              title="Copy command"
              type="button"
              variant="quiet"
            >
              <Copy size={14} aria-hidden />
              Copy
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}
