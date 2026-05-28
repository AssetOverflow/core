import { useEffect } from "react";
import { registerCommands, unregisterCommands } from "../../commands/registry";
import type { ProposalSummary } from "../../types/api";
import { shortProposalId } from "./proposalView";

export function useProposalCommands(proposals: ProposalSummary[]): void {
  useEffect(() => {
    const cmds = proposals.map((p) => ({
      name: `Open proposal ${shortProposalId(p.proposal_id)}`,
      path: `/proposals?proposal_id=${encodeURIComponent(p.proposal_id)}&state=${p.state}`,
    }));
    registerCommands(cmds);
    return () => unregisterCommands(cmds.map((c) => c.path));
  }, [proposals]);
}
