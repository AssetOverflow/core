import { useEffect, useMemo, useState } from "react";
import { Eye } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import {
  useTraceBundle,
  useTraceField,
  useTracePipeline,
  useTraceTurn,
  useTraceTurns,
} from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { FieldInvariantCard } from "../../design/components/FieldInvariantCard/FieldInvariantCard";
import { DagViewer, type DagEdgeInput, type DagNodeInput } from "../../design/components/Dag";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { Timestamp } from "../../design/components/Timestamp/Timestamp";
import { TruncatedCell } from "../../design/components/TruncatedCell";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import {
  EpistemicStateBadge,
  GroundingSourceBadge,
  NormativeClearanceBadge,
  type EpistemicState,
  type GroundingSource,
  type NormativeClearance,
} from "../../design/components/badges";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type {
  CognitivePipelineRecord,
  CognitivePipelineStage,
  EvidenceBundle,
  FieldEvidence,
  TraceIntegrity,
  TurnJournalEntry,
  TurnJournalSummary,
} from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvidenceSubject } from "../evidenceContext";

const TRACE_TABS: readonly Tab[] = [
  { id: "pipeline", label: "Pipeline" },
  { id: "field", label: "Field" },
  { id: "bundle", label: "Bundle" },
  { id: "surfaces", label: "Surfaces" },
  { id: "grounding", label: "Grounding" },
  { id: "verdicts", label: "Verdicts" },
  { id: "metadata", label: "Metadata" },
  { id: "raw", label: "Raw" },
];

function parseTurnId(raw: string | undefined): number | null {
  if (!raw || !/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Trace journal request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function isPipelineTrace(turn: Pick<TurnJournalSummary, "trace_hash" | "trace_integrity">) {
  return turn.trace_integrity === "pipeline_trace" && Boolean(digestPayload(turn.trace_hash));
}

function TraceIntegrityBadge({ value }: { value: TraceIntegrity }) {
  const pipeline = value === "pipeline_trace";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${
        pipeline
          ? "border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)]"
          : "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] text-[var(--color-state-warning-text)]"
      }`}
    >
      {value}
    </span>
  );
}

function TraceCoverage({ turns }: { turns: TurnJournalSummary[] }) {
  const pipelineCount = turns.filter(isPipelineTrace).length;
  const legacyCount = turns.length - pipelineCount;
  return (
    <div className="grid grid-cols-2 gap-2 text-xs">
      <div className="rounded-md border border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] px-3 py-2 text-[var(--color-state-success-text)]">
        <span className="block font-mono text-sm">{pipelineCount}/{turns.length}</span>
        <span className="block uppercase tracking-wide">pipeline hashes</span>
      </div>
      <div className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] px-3 py-2 text-[var(--color-state-warning-text)]">
        <span className="block font-mono text-sm">{legacyCount}</span>
        <span className="block uppercase tracking-wide">legacy_unhashed</span>
      </div>
    </div>
  );
}

function firstLine(value: string): string {
  return value.split(/\r?\n/, 1)[0] || "";
}

function surfaceText(value: string | null): string {
  return value && value.trim() ? value : "Not recorded.";
}

function proposalCandidateLabel(candidate: Record<string, unknown>): string {
  const id = candidate.candidate_id;
  const source = candidate.source_kind;
  if (typeof id === "string" && typeof source === "string") return `${id} (${source})`;
  if (typeof id === "string") return id;
  return JSON.stringify(candidate);
}

function asVerdict(value: unknown): { outcome: string; runtime_detail: string } | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  return {
    outcome: typeof record.outcome === "string" ? record.outcome : "unassessable",
    runtime_detail: typeof record.runtime_detail === "string" ? record.runtime_detail : "",
  };
}

function SurfaceCard({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
      <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
        {label}
      </h3>
      <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-[var(--color-text-primary)]">
        {surfaceText(value)}
      </pre>
    </section>
  );
}

function pipelineDag(record: CognitivePipelineRecord): {
  nodes: DagNodeInput[];
  edges: DagEdgeInput[];
} {
  return {
    nodes: record.stages.map((stage) => ({
      id: stage.stage_id,
      label: stage.label,
      detail: {
        status: stage.status,
        summary: stage.summary,
        detail: stage.detail,
      },
    })),
    edges: record.edges.map((edge) => ({
      from: edge.from_stage,
      to: edge.to_stage,
      label: edge.label ?? undefined,
    })),
  };
}

type PipelineStageId = CognitivePipelineStage["stage_id"];

function versorStatus(value: number | null): string {
  if (typeof value !== "number") return "missing_evidence";
  return value < 1e-6 ? "valid" : "invalid";
}

function PipelineStageStatus({ status }: { status: CognitivePipelineStage["status"] }) {
  const recorded = status === "recorded";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${
        recorded
          ? "border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)]"
          : "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] text-[var(--color-state-warning-text)]"
      }`}
    >
      {status}
    </span>
  );
}

function PipelineStageRail({
  stages,
  selectedStageId,
  onSelect,
}: {
  stages: readonly CognitivePipelineStage[];
  selectedStageId: PipelineStageId;
  onSelect: (stageId: PipelineStageId) => void;
}) {
  return (
    <section
      aria-label="Pipeline stages"
      className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2"
    >
      {stages.map((stage, index) => {
        const selected = stage.stage_id === selectedStageId;
        return (
          <div
            role="button"
            tabIndex={0}
            aria-pressed={selected}
            className={`grid min-h-16 grid-cols-[2rem_minmax(0,1fr)] gap-2 rounded border px-2 py-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
              selected
                ? "border-[var(--color-selected-border)] bg-[var(--color-selected-bg)]"
                : "border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] hover:bg-[var(--color-surface-inset)]"
            }`}
            key={stage.stage_id}
            onClick={() => onSelect(stage.stage_id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(stage.stage_id);
              }
            }}
          >
            <span className="font-mono text-xs text-[var(--color-text-muted)]">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="min-w-0">
              <span className="flex items-center justify-between gap-2">
                <TruncatedCell
                  value={stage.label}
                  label="stage"
                  mono
                  className="text-xs font-semibold text-[var(--color-text-primary)]"
                />
                <PipelineStageStatus status={stage.status} />
              </span>
              <span className="mt-1 block min-w-0">
                <TruncatedCell
                  value={stage.summary}
                  label="summary"
                  wrap="pre-wrap"
                  className="text-xs text-[var(--color-text-secondary)]"
                />
              </span>
            </span>
          </div>
        );
      })}
    </section>
  );
}

function PipelineTransitionList({ record }: { record: CognitivePipelineRecord }) {
  return (
    <section
      aria-label="Pipeline propagation edges"
      className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3"
    >
      <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
        Propagation
      </h3>
      <ol className="m-0 mt-2 grid gap-1 p-0">
        {record.edges.map((edge) => (
          <li
            className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-2 py-1 font-mono text-[11px]"
            key={`${edge.from_stage}:${edge.to_stage}`}
          >
            <TruncatedCell
              value={edge.from_stage}
              label="from stage"
              mono
              className="text-[var(--color-text-secondary)]"
            />
            <span className="text-[var(--color-text-muted)]">{edge.label ?? "propagate"}</span>
            <TruncatedCell
              value={edge.to_stage}
              label="to stage"
              mono
              align="end"
              className="text-[var(--color-text-primary)]"
            />
          </li>
        ))}
      </ol>
    </section>
  );
}

function PipelineStageDetail({ stage }: { stage: CognitivePipelineStage }) {
  return (
    <section
      aria-label="Selected pipeline stage detail"
      className="grid gap-3 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="m-0 truncate text-sm font-semibold text-[var(--color-text-primary)]">
            {stage.label}
          </h3>
          <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-muted)]">
            {stage.stage_id}
          </p>
        </div>
        <PipelineStageStatus status={stage.status} />
      </div>
      <MetadataTable
        rows={[
          { key: "stage_id", value: stage.stage_id, mono: true, copyable: true },
          { key: "status", value: stage.status, mono: true },
          { key: "summary", value: stage.summary },
        ]}
      />
      <StableJsonViewer source={JSON.stringify(stage.detail, null, 2)} />
    </section>
  );
}

function PipelineTab({
  record,
  isLoading,
  error,
  turnId,
}: {
  record?: CognitivePipelineRecord | null;
  isLoading: boolean;
  error: unknown;
  turnId: number;
}) {
  const [selectedStageId, setSelectedStageId] = useState<PipelineStageId>("input");

  useEffect(() => {
    if (!record || record.status !== "recorded") return;
    if (!record.stages.some((stage) => stage.stage_id === selectedStageId)) {
      setSelectedStageId(record.stages[0]?.stage_id ?? "input");
    }
  }, [record, selectedStageId]);

  if (isLoading) {
    return <LoadingState label="Loading pipeline..." />;
  }
  if (error) {
    return (
      <ErrorState
        whatFailed={errorMessage(error)}
        mutationStatus="No trace mutation occurred."
        reproducer={`curl /trace/${turnId}/pipeline`}
        retrySafety="Retry: safe"
      />
    );
  }
  if (!record || record.status !== "recorded") {
    return (
      <section className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-3 text-sm text-[var(--color-state-warning-text)]">
        <h3 className="m-0 text-xs font-semibold uppercase">missing_evidence</h3>
        <p className="m-0 mt-2">
          Pipeline stage evidence was not persisted for this turn.
        </p>
      </section>
    );
  }

  const dag = pipelineDag(record);
  const selectedStage =
    record.stages.find((stage) => stage.stage_id === selectedStageId) ?? record.stages[0];
  if (!selectedStage) {
    return (
      <ErrorState
        whatFailed="Recorded pipeline has no stage evidence."
        mutationStatus="No trace mutation occurred."
        reproducer={`curl /trace/${turnId}/pipeline`}
        retrySafety="Retry: safe"
      />
    );
  }
  return (
    <div className="grid gap-3">
      <MetadataTable
        rows={[
          { key: "schema_version", value: record.schema_version, mono: true },
          { key: "status", value: record.status, mono: true },
          { key: "stage_count", value: String(record.stages.length), mono: true },
          {
            key: "versor_condition",
            value:
              typeof record.versor_condition === "number"
                ? record.versor_condition.toExponential(3)
                : "missing_evidence",
            mono: true,
          },
          { key: "versor_status", value: versorStatus(record.versor_condition), mono: true },
          {
            key: "trace_hash",
            value: record.trace_hash ? (
              <DigestBadge digest={digestPayload(record.trace_hash) ?? ""} truncate={12} />
            ) : (
              "missing_evidence"
            ),
          },
          {
            key: "field_digest",
            value: record.field_digest ? (
              <DigestBadge digest={digestPayload(record.field_digest) ?? ""} truncate={12} />
            ) : (
              "not persisted"
            ),
          },
        ]}
      />
      <div className="grid gap-3 xl:grid-cols-[minmax(15rem,0.8fr)_minmax(0,1.4fr)]">
        <PipelineStageRail
          stages={record.stages}
          selectedStageId={selectedStage.stage_id}
          onSelect={setSelectedStageId}
        />
        <div className="grid min-w-0 gap-3">
          <DagViewer
            nodes={dag.nodes}
            edges={dag.edges}
            ariaLabel="Cognitive pipeline DAG"
            height={340}
            selectedNodeId={selectedStage.stage_id}
            showInspector={false}
            onInspectNode={(node) => setSelectedStageId(node.id as PipelineStageId)}
          />
          <PipelineTransitionList record={record} />
          <PipelineStageDetail stage={selectedStage} />
        </div>
      </div>
    </div>
  );
}

function FieldTab({
  record,
  isLoading,
  error,
  turnId,
}: {
  record?: FieldEvidence | null;
  isLoading: boolean;
  error: unknown;
  turnId: number;
}) {
  if (isLoading) {
    return <LoadingState label="Loading field invariant..." />;
  }
  if (error) {
    return (
      <ErrorState
        whatFailed={errorMessage(error)}
        mutationStatus="No trace mutation occurred."
        reproducer={`curl /trace/${turnId}/field`}
        retrySafety="Retry: safe"
      />
    );
  }
  if (!record) {
    return <LoadingState label="Loading field invariant..." />;
  }
  return <FieldInvariantCard record={record} />;
}

function BundleTab({
  bundle,
  isLoading,
  error,
  turnId,
}: {
  bundle?: EvidenceBundle | null;
  isLoading: boolean;
  error: unknown;
  turnId: number;
}) {
  // Deterministic export: a stable object URL over the bundle JSON, revoked on
  // unmount. The bundle is already content-addressed by the backend.
  const downloadUrl = useMemo(() => {
    if (!bundle) return null;
    return URL.createObjectURL(
      new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" }),
    );
  }, [bundle]);
  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  if (isLoading) {
    return <LoadingState label="Assembling evidence bundle..." />;
  }
  if (error) {
    return (
      <ErrorState
        whatFailed={errorMessage(error)}
        mutationStatus="No trace mutation occurred."
        reproducer={`curl /trace/${turnId}/bundle`}
        retrySafety="Retry: safe"
      />
    );
  }
  if (!bundle) {
    return <LoadingState label="Assembling evidence bundle..." />;
  }

  const digest = digestPayload(bundle.bundle_digest);
  const fileName = `evidence-bundle-turn-${bundle.turn_id}-${(digest ?? "").slice(0, 12)}.json`;
  return (
    <section className="flex flex-col gap-3" data-testid="evidence-bundle">
      <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
            citable digest
          </span>
          {digest ? <DigestBadge digest={digest} truncate={16} /> : null}
        </div>
        <p className="m-0 mt-2 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">
          <span className="font-semibold text-[var(--color-text-primary)]">Proves:</span> this
          exact evidence (trace, pipeline, field, leeway) is reproducible — re-run the prompt over a
          sealed runtime, confirm the trace hash, recompute the bundle, and this digest matches.{" "}
          <span className="font-semibold text-[var(--color-text-primary)]">Does not prove:</span>{" "}
          anything about a different prompt, model, or runtime.
        </p>
        {downloadUrl ? (
          <a
            className="mt-3 inline-flex items-center gap-2 text-sm underline"
            href={downloadUrl}
            download={fileName}
            data-testid="bundle-download"
          >
            Download evidence bundle
          </a>
        ) : null}
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold text-[var(--color-text-secondary)]">
          reproducer
        </div>
        <code className="block overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2 font-mono text-xs text-[var(--color-text-primary)]">
          {bundle.replay_reproducer}
        </code>
      </div>
      <div className="max-h-[28rem] overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2">
        <StableJsonViewer source={JSON.stringify(bundle, null, 2)} />
      </div>
    </section>
  );
}

function TraceRow({
  turn,
  selected,
  focused,
  onSelect,
}: {
  turn: TurnJournalSummary;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  const digest = digestPayload(turn.trace_hash);
  return (
    <div
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      } ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] pl-[10px]"
          : focused
            ? "border-l-2 border-l-[var(--color-focus-ring)] pl-[10px]"
            : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="min-w-0">
        <span className="block text-xs text-[var(--color-text-secondary)]">
          <Timestamp iso={turn.timestamp} format="relative" />
        </span>
        <span className="mt-1 block min-w-0">
          <TruncatedCell
            value={firstLine(turn.prompt_excerpt) || `Turn #${turn.turn_id}`}
            label="prompt"
            wrap="pre-wrap"
            className="text-sm text-[var(--color-text-primary)]"
          />
        </span>
        <span className="mt-1 block min-w-0">
          <TruncatedCell
            value={turn.surface_excerpt}
            label="surface"
            wrap="pre-wrap"
            className="text-xs text-[var(--color-text-muted)]"
          />
        </span>
      </span>
      <span className="justify-self-end">
        {digest && isPipelineTrace(turn) ? (
          <DigestBadge digest={digest} truncate={12} />
        ) : (
          <TraceIntegrityBadge value={turn.trace_integrity} />
        )}
      </span>
    </div>
  );
}

function SurfacesTab({ turn }: { turn: TurnJournalEntry }) {
  return (
    <div className="grid gap-3">
      <SurfaceCard label="User Surface (response)" value={turn.surface} />
      <SurfaceCard label="Articulation Surface (realizer)" value={turn.articulation_surface} />
      <SurfaceCard label="Walk Surface (telemetry/evidence)" value={turn.walk_surface} />
    </div>
  );
}

function GroundingTab({ turn }: { turn: TurnJournalEntry }) {
  return (
    <MetadataTable
      rows={[
        {
          key: "grounding_source",
          value: <GroundingSourceBadge value={turn.grounding_source as GroundingSource} />,
        },
        {
          key: "epistemic_state",
          value: <EpistemicStateBadge value={turn.epistemic_state as EpistemicState} />,
        },
        {
          key: "normative_clearance",
          value: <NormativeClearanceBadge value={turn.normative_clearance as NormativeClearance} />,
        },
      ]}
    />
  );
}

function VerdictsTab({ turn }: { turn: TurnJournalEntry }) {
  const identity = asVerdict(turn.verdicts.identity);
  const safety = asVerdict(turn.verdicts.safety);
  const ethics = asVerdict(turn.verdicts.ethics);
  return (
    <MetadataTable
      rows={[
        { key: "identity", value: identity ? identity.outcome : "not recorded" },
        { key: "identity_detail", value: identity?.runtime_detail || "none" },
        { key: "safety", value: safety ? safety.outcome : "not recorded" },
        { key: "safety_detail", value: safety?.runtime_detail || "none" },
        { key: "ethics", value: ethics ? ethics.outcome : "not recorded" },
        { key: "ethics_detail", value: ethics?.runtime_detail || "none" },
        { key: "refusal_emitted", value: turn.refusal_emitted ? "yes" : "no" },
        { key: "hedge_injected", value: turn.hedge_injected ? "yes" : "no" },
      ]}
    />
  );
}

function MetadataTab({ turn }: { turn: TurnJournalEntry }) {
  const traceDigest = digestPayload(turn.trace_hash);
  const journalDigest = digestPayload(turn.journal_digest);
  return (
    <MetadataTable
      rows={[
        { key: "turn_id", value: String(turn.turn_id), mono: true, copyable: true },
        { key: "timestamp", value: <Timestamp iso={turn.timestamp} /> },
        { key: "turn_cost_ms", value: `${turn.turn_cost_ms}ms`, mono: true },
        { key: "checkpoint_emitted", value: turn.checkpoint_emitted ? "yes" : "no" },
        {
          key: "trace_integrity",
          value: <TraceIntegrityBadge value={turn.trace_integrity} />,
        },
        {
          key: "trace_hash",
          value: traceDigest ? <DigestBadge digest={traceDigest} truncate={12} /> : "not recorded",
        },
        {
          key: "journal_digest",
          value: journalDigest ? <DigestBadge digest={journalDigest} truncate={12} /> : "not recorded",
        },
        {
          key: "proposal_candidates",
          value:
            turn.proposal_candidates.length > 0
              ? turn.proposal_candidates.map(proposalCandidateLabel).join(", ")
              : "none",
        },
      ]}
    />
  );
}

function RawTab({ turn }: { turn: TurnJournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  return expanded ? (
    <StableJsonViewer source={JSON.stringify(turn, null, 2)} />
  ) : (
    <div className="grid justify-items-start gap-2">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        Raw journal JSON is collapsed by default.
      </p>
      <Button type="button" variant="quiet" onClick={() => setExpanded(true)}>
        <Eye size={14} aria-hidden />
        Expand raw JSON
      </Button>
    </div>
  );
}

function TraceDetail({
  turn,
  pipelineRecord,
  pipelineLoading,
  pipelineError,
  fieldEvidence,
  fieldLoading,
  fieldError,
  bundle,
  bundleLoading,
  bundleError,
}: {
  turn: TurnJournalEntry;
  pipelineRecord?: CognitivePipelineRecord | null;
  pipelineLoading: boolean;
  pipelineError: unknown;
  fieldEvidence?: FieldEvidence | null;
  fieldLoading: boolean;
  fieldError: unknown;
  bundle?: EvidenceBundle | null;
  bundleLoading: boolean;
  bundleError: unknown;
}) {
  const [activeTab, setActiveTab] = useState("pipeline");
  return (
    <Panel
      title={`Turn #${turn.turn_id}`}
      toolbar={
        turn.trace_hash ? (
          <DigestBadge digest={digestPayload(turn.trace_hash) ?? ""} truncate={12} />
        ) : (
          <TraceIntegrityBadge value={turn.trace_integrity} />
        )
      }
    >
      <TabBar tabs={TRACE_TABS} activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "pipeline" ? (
          <PipelineTab
            record={pipelineRecord}
            isLoading={pipelineLoading}
            error={pipelineError}
            turnId={turn.turn_id}
          />
        ) : null}
        {activeTab === "field" ? (
          <FieldTab
            record={fieldEvidence}
            isLoading={fieldLoading}
            error={fieldError}
            turnId={turn.turn_id}
          />
        ) : null}
        {activeTab === "bundle" ? (
          <BundleTab
            bundle={bundle}
            isLoading={bundleLoading}
            error={bundleError}
            turnId={turn.turn_id}
          />
        ) : null}
        {activeTab === "surfaces" ? <SurfacesTab turn={turn} /> : null}
        {activeTab === "grounding" ? <GroundingTab turn={turn} /> : null}
        {activeTab === "verdicts" ? <VerdictsTab turn={turn} /> : null}
        {activeTab === "metadata" ? <MetadataTab turn={turn} /> : null}
        {activeTab === "raw" ? <RawTab turn={turn} /> : null}
      </TabBar>
    </Panel>
  );
}

export function TraceRoute() {
  const { turnId } = useParams();
  const selectedTurnId = parseTurnId(turnId);
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();
  const [search, setSearch] = useState("");

  const turnsQuery = useTraceTurns();
  const turnQuery = useTraceTurn(selectedTurnId);
  const pipelineQuery = useTracePipeline(selectedTurnId);
  const fieldQuery = useTraceField(selectedTurnId);
  const bundleQuery = useTraceBundle(selectedTurnId);

  const turns = turnsQuery.data ?? [];
  const filteredTurns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return turns;
    return turns.filter((turn) => {
      const trace = turn.trace_hash?.replace(/^sha256:/, "").toLowerCase() ?? "";
      return (
        turn.prompt_excerpt.toLowerCase().includes(q) ||
        trace.startsWith(q) ||
        trace.includes(q)
      );
    });
  }, [search, turns]);

  useEffect(() => {
    if (selectedTurnId === null) return;
    setSubject({ kind: "turn", turnId: selectedTurnId, data: turnQuery.data });
  }, [selectedTurnId, setSubject, turnQuery.data]);

  function selectTurn(turn: TurnJournalSummary) {
    const subject = { kind: "turn" as const, turnId: turn.turn_id };
    const path = subjectToUrl(subject);
    navigate(path, { replace: true });
    pushRecentItem({ label: `Turn #${turn.turn_id}`, path });
  }

  if (turnsQuery.isLoading) {
    return <LoadingState label="Loading trace..." />;
  }

  if (turnsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(turnsQuery.error)}
        mutationStatus="No trace mutation occurred."
        reproducer="curl /trace/turns"
        retrySafety="Retry: safe"
      />
    );
  }

  if (turns.length === 0) {
    return (
      <EmptyState
        statement="No turns recorded yet. Use Chat to create evidence."
        nextAction={{ kind: "cli", command: "core chat" }}
      />
    );
  }

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="trace" defaultSplit={38} minSize={320}>
        <Panel title="Turn Timeline">
          <div className="grid min-h-0 gap-3">
            <TraceCoverage turns={turns} />
            <SearchInput
              placeholder="Filter by prompt or trace hash"
              value={search}
              onChange={setSearch}
            />
            {filteredTurns.length === 0 ? (
              <EmptyState
                statement="No turns match this trace filter."
                nextAction={{ kind: "cli", command: "core chat" }}
              />
            ) : (
              <VirtualizedList
                ariaLabel="Trace turns"
                estimateSize={84}
                getKey={(turn) => String(turn.turn_id)}
                height="calc(100vh - 14rem)"
                initialRect={{ width: 480, height: 560 }}
                items={filteredTurns}
                onActivate={(turn) => selectTurn(turn)}
                renderItem={(turn, _index, focused) => (
                  <TraceRow
                    turn={turn}
                    selected={turn.turn_id === selectedTurnId}
                    focused={focused}
                    onSelect={() => selectTurn(turn)}
                  />
                )}
              />
            )}
          </div>
        </Panel>

        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedTurnId === null ? (
            <EmptyState
              statement="Select a turn to inspect surfaces, grounding, verdicts, and metadata."
              nextAction={{ kind: "cli", command: "core chat" }}
            />
          ) : turnQuery.isLoading ? (
            <LoadingState label="Loading trace turn..." />
          ) : turnQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(turnQuery.error)}
              mutationStatus="No trace mutation occurred."
              reproducer={`curl /trace/${selectedTurnId}`}
              retrySafety="Retry: safe"
            />
          ) : turnQuery.data ? (
            <TraceDetail
              turn={turnQuery.data}
              pipelineRecord={pipelineQuery.data}
              pipelineLoading={pipelineQuery.isLoading}
              pipelineError={pipelineQuery.isError ? pipelineQuery.error : null}
              fieldEvidence={fieldQuery.data}
              fieldLoading={fieldQuery.isLoading}
              fieldError={fieldQuery.isError ? fieldQuery.error : null}
              bundle={bundleQuery.data}
              bundleLoading={bundleQuery.isLoading}
              bundleError={bundleQuery.isError ? bundleQuery.error : null}
            />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
