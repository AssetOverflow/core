import { useQuery } from "@tanstack/react-query";
import { apiFetch, WorkbenchApiError } from "../../api/client";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { Panel } from "../../design/components/Panel/Panel";

export const APPLE_UMA_LOADING = "Loading Apple UMA report...";
export const APPLE_UMA_ABSENCE_STATEMENT = "No Apple UMA report projection available.";
export const APPLE_UMA_ABSENCE_ACTION =
  "CORE_BACKEND=rust uv run python -m benchmarks.apple_uma_mechanical_sympathy --write-report";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

interface AppleUmaMlxCase {
  N: number | null;
  top_k: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  mean_ms: number | null;
  rows_per_sec: number | null;
  parity: Record<string, JsonValue>;
  copy_in_boundary: string | null;
  copy_out_boundary: string | null;
}

interface AppleUmaMlxTrack {
  present: boolean;
  skipped: boolean;
  reason: string | null;
  benchmark_only?: boolean;
  serving_authorized?: boolean;
  semantic_backend?: string | null;
  score_computation?: string | null;
  top_k_ordering?: string | null;
  copy_boundary?: Record<string, JsonValue> | null;
  mlx_status?: Record<string, JsonValue>;
  case_count: number;
  all_cases_parity_pass: boolean;
  cases: AppleUmaMlxCase[];
}

interface AppleUmaReport {
  read_only: boolean;
  report_id: string;
  source_path: string;
  source_digest: string;
  benchmark_name: string;
  benchmark_version: string;
  metadata: Record<string, JsonValue>;
  backend_status: Record<string, JsonValue>;
  tracks: {
    available: string[];
    required: string[];
    missing_required: string[];
    mlx_exact_cga_recall: AppleUmaMlxTrack;
  };
  copy_boundaries: Array<Record<string, JsonValue>>;
  non_claims: string[];
  claim_safety: {
    safe_claims: string[];
    rust_backend_notes: string[];
    known_copy_paths: string[];
    known_zero_copy_input_paths: string[];
    future_work: string[];
  };
}

function useAppleUmaReport() {
  return useQuery<AppleUmaReport, WorkbenchApiError>({
    queryKey: ["api", "benchmarks", "apple-uma", "report"],
    queryFn: () => apiFetch<AppleUmaReport>("/benchmarks/apple-uma/report"),
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

function isAppleUmaReport(value: unknown): value is AppleUmaReport {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<AppleUmaReport>;
  return (
    candidate.read_only === true &&
    candidate.report_id === "apple_uma_mechanical_sympathy_latest" &&
    typeof candidate.benchmark_name === "string" &&
    typeof candidate.benchmark_version === "string" &&
    !!candidate.tracks &&
    typeof candidate.tracks === "object"
  );
}

function boolLabel(value: unknown): string {
  if (value === true) return "true";
  if (value === false) return "false";
  if (value === null || value === undefined || value === "") return "not declared";
  return String(value);
}

function numericLabel(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/a";
  return value.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

function statusTone(kind: "good" | "warn" | "neutral") {
  if (kind === "good") {
    return "border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)]";
  }
  if (kind === "warn") {
    return "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] text-[var(--color-state-warning-text)]";
  }
  return "border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)]";
}

function StatusPill({ children, kind = "neutral" }: { children: string; kind?: "good" | "warn" | "neutral" }) {
  return <span className={`inline-flex rounded-md border px-2 py-0.5 text-xs ${statusTone(kind)}`}>{children}</span>;
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
      <div className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">{label}</div>
      <div className="mt-1 font-mono text-lg text-[var(--color-text-primary)]">{value}</div>
      {detail ? <div className="mt-1 text-xs text-[var(--color-text-secondary)]">{detail}</div> : null}
    </div>
  );
}

function StaleReportNotice({ report }: { report: AppleUmaReport }) {
  const missing = report.tracks.missing_required.join(", ");
  return (
    <section className="rounded-lg border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-4 text-sm text-[var(--color-state-warning-text)]">
      <h3 className="m-0 text-sm font-semibold">Report artifact needs refresh</h3>
      <p className="mt-2 mb-0">
        The Workbench read-model is functioning, but the committed report is stale and lacks: {missing || "no required tracks"}.
        No MLX success is being inferred from absent data.
      </p>
      <code className="mt-3 block rounded bg-[var(--color-surface-sunken)] px-2 py-1 font-mono text-xs text-[var(--color-text-primary)]">
        {APPLE_UMA_ABSENCE_ACTION}
      </code>
    </section>
  );
}

function BackendPanel({ report }: { report: AppleUmaReport }) {
  const backend = report.backend_status;
  return (
    <Panel title="Backend & report identity">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Native status" value={boolLabel(backend.native_status)} detail="Reported by benchmark artifact" />
        <MetricCard label="Using Rust" value={boolLabel(backend.using_rust)} detail="Read-only projection" />
        <MetricCard label="Benchmark version" value={report.benchmark_version} detail={report.report_id} />
        <MetricCard label="Source digest" value={report.source_digest.slice(0, 18) + "…"} detail={report.source_path} />
      </div>
    </Panel>
  );
}

function TrackInventoryPanel({ report }: { report: AppleUmaReport }) {
  return (
    <Panel title="Track inventory">
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="m-0 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">Available tracks</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {report.tracks.available.map((track) => (
              <StatusPill key={track}>{track}</StatusPill>
            ))}
          </div>
        </div>
        <div>
          <h3 className="m-0 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">Missing required tracks</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {report.tracks.missing_required.length === 0 ? (
              <StatusPill kind="good">none</StatusPill>
            ) : (
              report.tracks.missing_required.map((track) => (
                <StatusPill key={track} kind="warn">{track}</StatusPill>
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function MlxPanel({ report }: { report: AppleUmaReport }) {
  const mlx = report.tracks.mlx_exact_cga_recall;
  const parityKind = mlx.all_cases_parity_pass ? "good" : "warn";
  return (
    <Panel title="MLX exact CGA recall">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          <StatusPill kind={mlx.present ? "good" : "warn"}>{mlx.present ? "track present" : "track absent"}</StatusPill>
          <StatusPill kind={mlx.skipped ? "warn" : "good"}>{mlx.skipped ? "skipped" : "executed"}</StatusPill>
          <StatusPill kind={parityKind}>parity {boolLabel(mlx.all_cases_parity_pass)}</StatusPill>
          <StatusPill kind={mlx.serving_authorized ? "warn" : "good"}>serving authorized {boolLabel(mlx.serving_authorized)}</StatusPill>
        </div>
        {mlx.reason ? <p className="m-0 text-sm text-[var(--color-text-secondary)]">{mlx.reason}</p> : null}
        <div className="grid gap-3 md:grid-cols-3">
          <MetricCard label="Cases" value={String(mlx.case_count)} detail="MLX-present report cases" />
          <MetricCard label="Backend" value={mlx.semantic_backend ?? "not declared"} detail="Semantic authority remains canonical" />
          <MetricCard label="Ordering" value={mlx.top_k_ordering ?? "not declared"} detail="Stable top-k boundary" />
        </div>
        {mlx.cases.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-[var(--color-border-subtle)]">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-[var(--color-surface-inset)] text-xs uppercase text-[var(--color-text-secondary)]">
                <tr>
                  <th className="px-3 py-2">N</th>
                  <th className="px-3 py-2">p50 ms</th>
                  <th className="px-3 py-2">rows/sec</th>
                  <th className="px-3 py-2">parity</th>
                  <th className="px-3 py-2">copy boundary</th>
                </tr>
              </thead>
              <tbody>
                {mlx.cases.map((entry) => (
                  <tr key={`${entry.N}-${entry.top_k}`} className="border-t border-[var(--color-border-subtle)]">
                    <td className="px-3 py-2 font-mono">{entry.N ?? "n/a"}</td>
                    <td className="px-3 py-2 font-mono">{numericLabel(entry.p50_ms)}</td>
                    <td className="px-3 py-2 font-mono">{numericLabel(entry.rows_per_sec)}</td>
                    <td className="px-3 py-2">{boolLabel(entry.parity.parity_pass)}</td>
                    <td className="px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                      <div>{entry.copy_in_boundary ?? "copy-in not declared"}</div>
                      <div>{entry.copy_out_boundary ?? "copy-out not declared"}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

function CopyBoundaryPanel({ report }: { report: AppleUmaReport }) {
  return (
    <Panel title="Copy / zero-copy truth table">
      <div className="grid gap-2">
        {report.copy_boundaries.map((row, index) => (
          <div key={`${row.path}-${index}`} className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3 text-sm">
            <div className="font-mono text-xs text-[var(--color-text-primary)]">{boolLabel(row.path)}</div>
            <div className="mt-2 grid gap-1 text-xs text-[var(--color-text-secondary)] md:grid-cols-3">
              <span>input: {boolLabel(row.input)}</span>
              <span>output: {boolLabel(row.output)}</span>
              <span>zero-copy input: {boolLabel(row.zero_copy_input)}</span>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function NonClaimsPanel({ report }: { report: AppleUmaReport }) {
  return (
    <Panel title="Explicit non-claims">
      <ul className="m-0 grid gap-2 pl-4 text-sm text-[var(--color-text-secondary)]">
        {report.non_claims.map((claim) => (
          <li key={claim}>{claim}</li>
        ))}
      </ul>
    </Panel>
  );
}

export function AppleUmaReportRoute() {
  const { data, isLoading, isError, error } = useAppleUmaReport();

  if (isLoading) return <LoadingState label={APPLE_UMA_LOADING} />;

  if (isError) {
    return (
      <ErrorState
        whatFailed={error instanceof Error ? error.message : "Failed to load Apple UMA report."}
        mutationStatus="No benchmark execution or report mutation occurred."
        reproducer="curl -X GET http://127.0.0.1:8765/benchmarks/apple-uma/report"
        retrySafety="Retry: safe"
      />
    );
  }

  if (!isAppleUmaReport(data)) {
    return (
      <EmptyState
        statement={APPLE_UMA_ABSENCE_STATEMENT}
        nextAction={{ kind: "cli", command: APPLE_UMA_ABSENCE_ACTION }}
      />
    );
  }

  const stale = data.tracks.missing_required.includes("mlx_exact_cga_recall");

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto" data-testid="apple-uma-report-route">
      <header className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="m-0 text-xs uppercase tracking-wide text-[var(--color-text-muted)]">Apple Silicon / UMA</p>
            <h1 className="m-0 mt-1 text-xl font-semibold text-[var(--color-text-primary)]">{data.benchmark_name}</h1>
            <p className="mt-2 mb-0 max-w-4xl text-sm text-[var(--color-text-secondary)]">
              Read-only evidence surface for Python, Rust, and MLX benchmark tracks. This view never runs benchmarks and never upgrades absent evidence into success.
            </p>
          </div>
          <StatusPill kind={data.read_only ? "good" : "warn"}>read-only {boolLabel(data.read_only)}</StatusPill>
        </div>
      </header>

      {stale ? <StaleReportNotice report={data} /> : null}
      <BackendPanel report={data} />
      <TrackInventoryPanel report={data} />
      <MlxPanel report={data} />
      <CopyBoundaryPanel report={data} />
      <NonClaimsPanel report={data} />
    </div>
  );
}
