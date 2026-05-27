import { InfoBadge } from "../../design/components/badges/Badge";

export function ProposalReplayBadge({ value }: { value: boolean | null }) {
  if (value === true) {
    return (
      <InfoBadge
        label="Replay match"
        colorToken="--color-state-verified"
        meaning="Replay evidence is equivalent to the original artifact."
        adr="ADR-0160"
        evidence="ProposalSummary.replay_equivalent is true."
      />
    );
  }
  if (value === false) {
    return (
      <InfoBadge
        label="Replay differs"
        colorToken="--color-state-contradicted"
        meaning="Replay evidence diverged from the original artifact."
        adr="ADR-0160"
        evidence="ProposalSummary.replay_equivalent is false."
      />
    );
  }
  return (
    <InfoBadge
      label="Replay unknown"
      colorToken="--color-state-undetermined"
      meaning="No replay-equivalence result is present for this proposal."
      adr="ADR-0160"
      evidence="ProposalSummary.replay_equivalent is null."
    />
  );
}
