import type { LeewayEvidence } from "../types/api";
import { DigestBadge } from "../design/components/DigestBadge/DigestBadge";

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function calibrationHref(ref: string | null | undefined): string | null {
  if (!ref?.startsWith("calibration:")) return null;
  return `/calibration?inspect=${encodeURIComponent(ref)}`;
}

export function LeewayEvidenceCard({
  evidence,
  title = "Leeway evidence",
}: {
  evidence?: LeewayEvidence | null;
  title?: string;
}) {
  if (!evidence) {
    return (
      <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
          {title}
        </h3>
        <p className="mt-1 mb-0 text-xs text-[var(--color-text-muted)]">
          No leeway evidence recorded.
        </p>
      </section>
    );
  }

  const href = calibrationHref(evidence.calibration_evidence_ref);
  return (
    <section className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-surface-inset)] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
          {title}
        </h3>
        <span className="rounded border border-[var(--color-state-warning-border)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-state-warning-text)]">
          {evidence.claim_disclosure}
        </span>
      </div>
      <dl className="mt-3 grid gap-2 text-xs">
        <div className="grid grid-cols-[7rem_1fr] gap-2">
          <dt className="text-[var(--color-text-muted)]">class</dt>
          <dd className="m-0 font-mono text-[var(--color-text-primary)]">
            {evidence.class_name}
          </dd>
        </div>
        <div className="grid grid-cols-[7rem_1fr] gap-2">
          <dt className="text-[var(--color-text-muted)]">license</dt>
          <dd className="m-0 font-mono text-[var(--color-text-primary)]">
            {evidence.license}
            {evidence.theta === null ? "" : ` · θ ${pct(evidence.theta)}`}
          </dd>
        </div>
        <div className="grid grid-cols-[7rem_1fr] gap-2">
          <dt className="text-[var(--color-text-muted)]">calibration</dt>
          <dd className="m-0 min-w-0">
            {href ? (
              <a
                href={href}
                className="font-mono text-[var(--color-link)] underline-offset-2 hover:underline"
              >
                {evidence.calibration_evidence_ref}
              </a>
            ) : (
              <span className="text-[var(--color-text-muted)]">not recorded</span>
            )}
          </dd>
        </div>
        <div className="grid grid-cols-[7rem_1fr] gap-2">
          <dt className="text-[var(--color-text-muted)]">source</dt>
          <dd className="m-0">
            {evidence.source_digest ? (
              <DigestBadge
                digest={evidence.source_digest.replace(/^sha256:/, "")}
                truncate={12}
              />
            ) : (
              <span className="text-[var(--color-text-muted)]">not recorded</span>
            )}
          </dd>
        </div>
      </dl>
    </section>
  );
}
