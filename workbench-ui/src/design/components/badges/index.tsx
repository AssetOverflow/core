import {
  epistemicStateMeta,
  groundingSourceMeta,
  normativeClearanceMeta,
  reviewStateMeta,
  safetyVerdictMeta,
} from "./mappings";
import { InfoBadge } from "./Badge";
import {
  EpistemicState,
  GroundingSource,
  NormativeClearance,
  ReviewState,
  SafetyVerdict,
} from "./types";

export {
  EpistemicState,
  GroundingSource,
  NormativeClearance,
  ReviewState,
  SafetyVerdict,
};

export function EpistemicStateBadge({ value }: { value: EpistemicState }) {
  return <InfoBadge {...epistemicStateMeta[value]} />;
}

export function NormativeClearanceBadge({ value }: { value: NormativeClearance }) {
  return <InfoBadge {...normativeClearanceMeta[value]} />;
}

export function ReviewStateBadge({ value }: { value: ReviewState }) {
  return <InfoBadge {...reviewStateMeta[value]} />;
}

export function GroundingSourceBadge({ value }: { value: GroundingSource }) {
  return <InfoBadge {...groundingSourceMeta[value]} />;
}

export function SafetyVerdictBadge({ value }: { value: SafetyVerdict }) {
  return <InfoBadge {...safetyVerdictMeta[value]} />;
}

export function TraceHashBadge({
  value,
  truncate = 12,
}: {
  value: string;
  truncate?: number;
}) {
  const label = value.slice(0, truncate);
  return (
    <InfoBadge
      label={label}
      colorToken="--color-text-mono"
      meaning="Deterministic trace hash. Click copy for the full digest."
      adr="ADR-0153 / ADR-0160 / ADR-0162"
      evidence="TurnEvent.trace_hash is present."
      mono
      onCopy={value}
    />
  );
}
