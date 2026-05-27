import { ReviewState, ReviewStateBadge } from "../../design/components/badges";
import { InfoBadge } from "../../design/components/badges/Badge";
import type { ProposalState } from "../../types/api";

export function ProposalStateBadge({ value }: { value: ProposalState }) {
  switch (value) {
    case "pending":
      return <ReviewStateBadge value={ReviewState.PENDING} />;
    case "accepted":
      return <ReviewStateBadge value={ReviewState.ACCEPTED} />;
    case "rejected":
      return <ReviewStateBadge value={ReviewState.REJECTED} />;
    case "withdrawn":
      return <ReviewStateBadge value={ReviewState.WITHDRAWN} />;
    case "unknown":
      return (
        <InfoBadge
          label="Unknown"
          colorToken="--color-state-undetermined"
          meaning="The proposal read model could not map this state to a terminal review state."
          adr="ADR-0160 / ADR-0162"
          evidence="ProposalSummary.state is unknown."
        />
      );
  }
}
