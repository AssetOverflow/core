import { TruncatedCell } from "../../design/components/TruncatedCell";
import type { EvalRunResult } from "../../types/api";

interface CaseRecord {
  case_id?: string;
  id?: string;
  passed?: boolean;
  status?: string;
  decision?: string;
  refusal_reason?: string;
  failure_reason?: string;
  failure_reasons?: string[];
  [key: string]: unknown;
}

export interface LedgerCase {
  id: string;
  kind: "correct" | "refused" | "wrong";
  reason: string;
}

export interface WrongZeroLedger {
  correct: number;
  refused: number;
  wrong: number;
  total: number;
  refusalReasons: { id: string; reason: string }[];
  orderedCases: LedgerCase[];
}

function numericMetric(metrics: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = metrics[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function caseId(record: CaseRecord, index: number) {
  return record.case_id || record.id || `case-${index + 1}`;
}

function refusalReason(record: CaseRecord): string | null {
  if (typeof record.refusal_reason === "string" && record.refusal_reason.trim()) {
    return record.refusal_reason;
  }
  if (typeof record.status === "string" && record.status.toLowerCase() === "refused") {
    return typeof record.decision === "string" && record.decision.trim()
      ? record.decision
      : "refused";
  }
  const reasons = record.failure_reasons;
  if (Array.isArray(reasons)) {
    const refusal = reasons.find((reason) => String(reason).toLowerCase().includes("refus"));
    if (refusal) return String(refusal);
  }
  if (
    typeof record.failure_reason === "string" &&
    record.failure_reason.toLowerCase().includes("refus")
  ) {
    return record.failure_reason;
  }
  return null;
}

function classifyCase(record: CaseRecord): "correct" | "refused" | "wrong" {
  if (refusalReason(record)) return "refused";
  if (record.passed === true) return "correct";
  if (typeof record.status === "string") {
    const status = record.status.toLowerCase();
    if (["correct", "passed", "ok", "promoted", "verified"].includes(status)) return "correct";
    if (["wrong", "incorrect", "failed"].includes(status)) return "wrong";
  }
  return record.passed === false ? "wrong" : "correct";
}

function caseReason(record: CaseRecord, kind: LedgerCase["kind"]) {
  if (kind === "refused") return refusalReason(record) || "refused";
  if (typeof record.failure_reason === "string" && record.failure_reason.trim()) {
    return record.failure_reason;
  }
  return kind;
}

export function normalizeWrongZeroLedger(result: EvalRunResult): WrongZeroLedger {
  const metrics = result.metrics;
  const cases = result.cases as CaseRecord[];
  const orderedCases = cases.map((record, index) => {
    const kind = classifyCase(record);
    return {
      id: caseId(record, index),
      kind,
      reason: caseReason(record, kind),
    };
  });

  const explicitCorrect = numericMetric(metrics, ["correct", "correct_count", "num_correct"]);
  const explicitRefused = numericMetric(metrics, ["refused", "refused_count", "refusal_count"]);
  const explicitWrong = numericMetric(metrics, ["wrong", "wrong_count", "num_wrong", "incorrect"]);

  let correct = explicitCorrect;
  let refused = explicitRefused;
  let wrong = explicitWrong;
  if (correct === null || refused === null || wrong === null) {
    const fromCases = {
      correct: orderedCases.filter((item) => item.kind === "correct").length,
      refused: orderedCases.filter((item) => item.kind === "refused").length,
      wrong: orderedCases.filter((item) => item.kind === "wrong").length,
    };
    correct =
      correct ??
      (typeof metrics.passed === "number" && Number.isFinite(metrics.passed)
        ? metrics.passed
        : fromCases.correct);
    refused = refused ?? fromCases.refused;
    wrong =
      wrong ??
      (typeof metrics.failed === "number" && Number.isFinite(metrics.failed)
        ? Math.max(0, metrics.failed - fromCases.refused)
        : fromCases.wrong);
  }

  const totalMetric = numericMetric(metrics, ["total", "case_count", "num_cases"]);
  const total = totalMetric ?? Math.max(cases.length, correct + refused + wrong);
  const refusalReasons = orderedCases
    .filter((item) => item.kind === "refused")
    .map((item) => ({ id: item.id, reason: item.reason }));

  return {
    correct,
    refused,
    wrong,
    total,
    refusalReasons,
    orderedCases: [...orderedCases].sort(
      (a, b) =>
        (a.kind === "wrong" ? 0 : a.kind === "refused" ? 1 : 2) -
          (b.kind === "wrong" ? 0 : b.kind === "refused" ? 1 : 2) ||
        a.id.localeCompare(b.id),
    ),
  };
}

function LedgerCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)]"
      : tone === "warning"
        ? "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] text-[var(--color-state-warning-text)]"
        : "border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] text-[var(--color-state-danger-text)]";
  return (
    <div className={`rounded-md border p-3 ${toneClass}`} data-testid={`ledger-${label}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wide">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

export function EvalWrongZeroLedger({ result }: { result: EvalRunResult }) {
  const ledger = normalizeWrongZeroLedger(result);
  return (
    <section className="grid gap-3" data-testid="wrong-zero-ledger">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
          wrong=0 ledger
        </h3>
        <span
          className={`rounded-md border px-2 py-1 font-mono text-xs font-semibold ${
            ledger.wrong === 0
              ? "border-[var(--color-state-success-border)] text-[var(--color-state-success-text)]"
              : "border-[var(--color-state-danger-border)] text-[var(--color-state-danger-text)]"
          }`}
        >
          wrong={ledger.wrong}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <LedgerCell label="correct" value={ledger.correct} tone="success" />
        <LedgerCell label="refused" value={ledger.refused} tone="warning" />
        <LedgerCell label="wrong" value={ledger.wrong} tone={ledger.wrong === 0 ? "success" : "danger"} />
      </div>

      {ledger.refusalReasons.length > 0 ? (
        <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
          <div className="text-xs font-semibold text-[var(--color-text-secondary)]">
            Refusal reasons
          </div>
          <ul className="m-0 mt-2 grid list-none gap-1 p-0">
            {ledger.refusalReasons.map((item) => (
              <li key={item.id} className="grid grid-cols-[minmax(0,10rem)_1fr] gap-2 text-xs">
                <TruncatedCell
                  value={item.id}
                  label="case id"
                  mono
                  className="text-[var(--color-text-primary)]"
                />
                <span className="text-[var(--color-text-secondary)]">{item.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        <div className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Case ledger ({ledger.total})
        </div>
        <ol className="m-0 mt-2 grid max-h-44 list-none gap-1 overflow-auto p-0">
          {ledger.orderedCases.map((item) => (
            <li
              key={item.id}
              className="grid grid-cols-[minmax(0,10rem)_5rem_1fr] gap-2 text-xs"
            >
              <TruncatedCell
                value={item.id}
                label="case id"
                mono
                className="text-[var(--color-text-primary)]"
              />
              <span
                className={
                  item.kind === "wrong"
                    ? "font-semibold text-[var(--color-state-danger-text)]"
                    : item.kind === "refused"
                      ? "font-semibold text-[var(--color-state-warning-text)]"
                      : "text-[var(--color-state-success-text)]"
                }
              >
                {item.kind}
              </span>
              <TruncatedCell
                value={item.reason}
                label="reason"
                wrap="pre-wrap"
                className="text-[var(--color-text-secondary)]"
              />
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
