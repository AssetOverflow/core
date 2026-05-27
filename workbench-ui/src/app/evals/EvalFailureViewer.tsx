import { StableJsonViewer } from "../../design/components/StableJsonViewer/StableJsonViewer";
import { EmptyState } from "../../design/components/states/EmptyState";

interface CaseItem {
  case_id?: string;
  id?: string;
  passed?: boolean;
  expected?: unknown;
  actual?: unknown;
  failure_reason?: string;
  failure_reasons?: string[];
  [key: string]: unknown;
}

function ensureJsonString(val: unknown): string {
  if (val === undefined) return "";
  if (typeof val === "string") {
    try {
      JSON.parse(val);
      return val;
    } catch {
      return JSON.stringify(val);
    }
  }
  return JSON.stringify(val, null, 2);
}

export function EvalFailureViewer({
  cases,
  passed,
  laneName,
}: {
  cases: any[];
  passed: boolean | null;
  laneName: string;
}) {
  const typedCases = cases as CaseItem[];
  const failures = typedCases.filter((c) => c.passed === false);

  if (passed === true || failures.length === 0) {
    return (
      <EmptyState
        statement={`All checks passed for eval lane ${laneName}.`}
        nextAction={{ kind: "cli", command: `core eval --lane ${laneName}` }}
      />
    );
  }

  return (
    <div className="grid gap-4" data-testid="eval-failures">
      <h3 className="font-semibold text-lg text-[var(--color-state-contradicted)]">
        Failures ({failures.length})
      </h3>
      <div className="grid gap-4">
        {failures.map((c, idx) => {
          const caseId = c.case_id || c.id || `case-${idx}`;
          const reason = c.failure_reason || (Array.isArray(c.failure_reasons) ? c.failure_reasons.join(", ") : "") || "No reason specified";
          
          const hasExpectedActual = c.expected !== undefined || c.actual !== undefined;
          
          const expectedStr = c.expected !== undefined 
            ? ensureJsonString(c.expected)
            : JSON.stringify(c, null, 2);
          const actualStr = c.actual !== undefined
            ? ensureJsonString(c.actual)
            : "";

          return (
            <div
              key={caseId}
              className="rounded-lg border border-[var(--color-state-danger-border)] bg-[var(--color-surface-raised)] p-4 shadow-sm"
              data-testid="failure-card"
            >
              <div className="flex items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-2 mb-3">
                <span className="font-mono text-sm font-semibold text-[var(--color-text-primary)]">
                  {caseId}
                </span>
                <span className="rounded bg-[var(--color-state-contradicted)]/10 px-2 py-0.5 text-xs font-semibold text-[var(--color-state-contradicted)]">
                  Failed
                </span>
              </div>
              
              <div className="mb-3">
                <div className="font-semibold text-xs text-[var(--color-text-secondary)] mb-1">Reason</div>
                <div className="text-sm text-[var(--color-text-primary)] font-mono bg-[var(--color-surface-inset)] p-2 rounded border border-[var(--color-border-subtle)]">
                  {reason}
                </div>
              </div>

              <div>
                <div className="font-semibold text-xs text-[var(--color-text-secondary)] mb-1">
                  {hasExpectedActual ? "Expected vs Actual" : "Case Details"}
                </div>
                {hasExpectedActual ? (
                  <StableJsonViewer source={expectedStr} compareSource={actualStr} />
                ) : (
                  <StableJsonViewer source={expectedStr} />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
