import type { FieldEvidence } from "../../../types/api";
import { DigestBadge } from "../DigestBadge/DigestBadge";

/**
 * C3 field-substrate surface — the geometry that can't fake coherence.
 *
 * Renders only the EXACT scalar invariants the engine computed over a turn's
 * CL(4,1) field: `versor_condition` measured against the `< 1e-6` ceiling, the
 * `cga_inner` transition value, and a content-addressed `field_digest`. There
 * is deliberately no multivector blob and no motion — the honesty is the
 * impressiveness: these are the real numbers, exact, and they decide validity.
 */

function formatCondition(value: number): string {
  // Tiny invariant values (e.g. 6.5e-13) read clearest in scientific notation.
  return value.toExponential(3);
}

function formatInner(value: number): string {
  return Number.isInteger(value) ? value.toFixed(1) : value.toExponential(6);
}

function digestPayload(value: string | null): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

export function FieldInvariantCard({ record }: { record: FieldEvidence }) {
  if (record.status !== "recorded") {
    return (
      <section
        data-testid="field-missing"
        className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-3 text-sm text-[var(--color-state-warning-text)]"
      >
        <h3 className="m-0 text-xs font-semibold uppercase tracking-wide">
          missing_evidence
        </h3>
        <p className="m-0 mt-2">
          No field evidence was persisted for this turn
          {record.missing_reason ? ` (${record.missing_reason})` : ""}.
        </p>
      </section>
    );
  }

  const condition = record.versor_condition ?? 0;
  const valid = record.field_valid === true;
  // Literal class strings (not interpolated) so Tailwind's JIT emits them.
  const cardClass = valid
    ? "rounded-md border border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] p-3"
    : "rounded-md border border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] p-3";
  const headClass = valid
    ? "m-0 text-xs font-semibold uppercase tracking-wide text-[var(--color-state-success-text)]"
    : "m-0 text-xs font-semibold uppercase tracking-wide text-[var(--color-state-danger-text)]";

  return (
    <section className="flex flex-col gap-3" data-testid="field-invariant">
      <div className={cardClass}>
        <h3 className={headClass}>{valid ? "field valid" : "field breach"}</h3>
        <p className="m-0 mt-2 flex flex-wrap items-baseline gap-2 font-mono text-sm tabular-nums text-[var(--color-text-primary)]">
          <span data-testid="field-versor-condition">versor_condition = {formatCondition(condition)}</span>
          <span aria-hidden className="text-[var(--color-text-secondary)]">
            {valid ? "<" : "≥"}
          </span>
          <span className="text-[var(--color-text-secondary)]">
            {record.versor_condition_ceiling.toExponential(0)}
          </span>
        </p>
        <p className="m-0 mt-1 text-xs text-[var(--color-text-secondary)]">
          {valid
            ? "The field state stays on the versor manifold; geometric coherence holds by construction."
            : "The field state breaches the versor ceiling — the engine cannot claim a valid field here."}
        </p>
      </div>

      <dl className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 text-sm">
        <dt className="text-[var(--color-text-secondary)]">field_digest</dt>
        <dd className="m-0">
          {digestPayload(record.field_digest) ? (
            <DigestBadge digest={digestPayload(record.field_digest) as string} truncate={12} />
          ) : (
            <span className="text-[var(--color-text-secondary)]">—</span>
          )}
        </dd>

        <dt className="text-[var(--color-text-secondary)]">parent_field_digest</dt>
        <dd className="m-0">
          {digestPayload(record.parent_field_digest) ? (
            <DigestBadge
              digest={digestPayload(record.parent_field_digest) as string}
              truncate={12}
            />
          ) : (
            <span className="text-[var(--color-text-secondary)]">first turn — no prior field</span>
          )}
        </dd>

        <dt className="text-[var(--color-text-secondary)]">cga_inner(before, after)</dt>
        <dd className="m-0 font-mono text-sm tabular-nums text-[var(--color-text-primary)]">
          {record.transition_inner_product === null ? (
            <span className="font-sans text-[var(--color-text-secondary)]">
              first turn — no transition
            </span>
          ) : (
            <span data-testid="field-transition">{formatInner(record.transition_inner_product)}</span>
          )}
        </dd>
      </dl>
    </section>
  );
}
