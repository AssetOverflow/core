import { InfoBadge } from "../../design/components/badges/Badge";

export function EvalArtifactLink({
  lane,
  sourceDigest,
}: {
  lane: string;
  sourceDigest: string;
}) {
  const label = sourceDigest.slice(0, 12);
  const location = lane.includes("contemplation") 
    ? "engine_state/" 
    : `evals/${lane}/results/`;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs" data-testid="eval-artifact-link">
      <span className="text-[var(--color-text-secondary)] font-medium">Source Digest:</span>
      <InfoBadge
        label={label}
        colorToken="--color-text-mono"
        meaning="Deterministic source digest for this run. Click to copy."
        adr="ADR-0160 / ADR-0162"
        evidence="EvalRunResult.source_digest is present."
        mono
        onCopy={sourceDigest}
      />
      <span className="text-[var(--color-text-muted)]">
        Located at: <code className="font-mono bg-[var(--color-surface-inset)] px-1.5 py-0.5 rounded border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]">{location}</code>
      </span>
    </div>
  );
}
