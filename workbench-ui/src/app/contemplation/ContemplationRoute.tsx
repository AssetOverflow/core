import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useContemplationRun, useContemplationRuns } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type {
  ContemplationRunDetail,
  ContemplationRunSummary,
  ContemplationScene,
  ContemplationStageRole,
} from "../../types/api";
import { pushRecentItem } from "../commandRegistry";

// The contemplation loop made legible: attempt → enrich → propose → ratify →
// grounded. Labels for the canonical ADR-0172 stage roles.
const STAGE_LABEL: Record<ContemplationStageRole, string> = {
  cold_attempt: "Cold attempt",
  engine_enrichment: "Engine enrichment",
  engine_proposal: "Engine-authored proposal",
  operator_ratifies: "Operator ratifies",
  grounded: "Grounded",
  other: "Stage",
};

function errorMessage(error: unknown): string {
  return error instanceof WorkbenchApiError
    ? error.message
    : "Contemplation request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function boolLabel(value: boolean | null): string {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "not recorded";
}

function RunRow({
  run,
  selected,
  onSelect,
}: {
  run: ContemplationRunSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] bg-[var(--color-selected-bg)] pl-[10px]"
          : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate font-mono text-xs text-[var(--color-text-muted)]">
          {run.run_id}
        </span>
        <span className="mt-1 block text-sm text-[var(--color-text-primary)]">
          {run.prompt ?? "Prompt not recorded"}
        </span>
        <span className="mt-1 block text-xs text-[var(--color-text-secondary)]">
          {run.scene_count} scenes
          {run.cold_subject ? ` · ${run.cold_subject}` : ""}
        </span>
      </span>
      <span className="justify-self-end text-xs text-[var(--color-text-secondary)]">
        {boolLabel(run.learning_arc_closed)}
      </span>
    </button>
  );
}

function StageEvidence({ scene }: { scene: ContemplationScene }) {
  // The loop's connective tissue, pulled out of the raw detail. Ids are
  // surfaced as evidence (copyable); cross-route navigation is intentionally
  // NOT a live link yet — these fixture proposals do not resolve in the live
  // proposal log, and a dead link would be theater.
  const rows: { label: string; value: string }[] = [];
  if (scene.grounding_source) rows.push({ label: "grounding", value: scene.grounding_source });
  if (scene.candidate_id) rows.push({ label: "candidate", value: scene.candidate_id });
  if (scene.proposal_id) {
    rows.push({
      label: "proposal",
      value: scene.proposal_state
        ? `${scene.proposal_id} · ${scene.proposal_state}`
        : scene.proposal_id,
    });
  }
  if (rows.length === 0) return null;
  return (
    <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs">
      {rows.map((row) => (
        <div key={row.label} className="contents">
          <dt className="text-[var(--color-text-secondary)]">{row.label}</dt>
          <dd className="m-0 truncate font-mono text-[var(--color-text-primary)]" title={row.value}>
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ProcessStageCard({ scene, index }: { scene: ContemplationScene; index: number }) {
  return (
    <li className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-3">
      <div className="flex justify-center">
        <span className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] font-mono text-xs text-[var(--color-text-secondary)]">
          {index + 1}
        </span>
      </div>
      <div className="min-w-0 border-l border-[var(--color-border-subtle)] pl-3">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
            {STAGE_LABEL[scene.stage_role]}
          </span>
          <span className="font-mono text-xs text-[var(--color-text-muted)]">
            {scene.scene_id}
          </span>
        </div>
        <p className="m-0 mt-1 text-sm text-[var(--color-text-primary)] [text-wrap:balance]">
          {scene.claim}
        </p>
        <StageEvidence scene={scene} />
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-[var(--color-text-secondary)]">
            raw detail
          </summary>
          <div className="mt-1 max-h-80 overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2">
            <StableJsonViewer source={JSON.stringify(scene.detail, null, 2)} />
          </div>
        </details>
      </div>
    </li>
  );
}

function Bookend({
  label,
  payload,
}: {
  label: string;
  payload: Record<string, unknown> | null | undefined;
}) {
  const surface = typeof payload?.surface === "string" ? payload.surface : null;
  const grounding =
    typeof payload?.grounding_source === "string" ? payload.grounding_source : null;
  return (
    <div className="min-w-0 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-secondary)]">{label}</span>
        {grounding ? (
          <span className="font-mono text-xs text-[var(--color-text-muted)]">{grounding}</span>
        ) : null}
      </div>
      {surface ? (
        <p className="m-0 text-sm text-[var(--color-text-primary)] [text-wrap:balance]">{surface}</p>
      ) : (
        <span className="text-xs text-[var(--color-text-secondary)]">not recorded</span>
      )}
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-[var(--color-text-secondary)]">
          raw
        </summary>
        <div className="mt-1 overflow-auto">
          <StableJsonViewer source={JSON.stringify(payload ?? {}, null, 2)} />
        </div>
      </details>
    </div>
  );
}

function DetailPanel({ detail }: { detail: ContemplationRunDetail }) {
  const digest = digestPayload(detail.source_digest);
  return (
    <Panel
      title="Process Trace"
      toolbar={digest ? <DigestBadge digest={digest} truncate={12} /> : null}
    >
      <div className="grid gap-4">
        <MetadataTable
          rows={[
            { key: "run_id", value: detail.run_id, mono: true, copyable: true },
            { key: "prompt", value: detail.prompt ?? "not recorded" },
            { key: "cold_subject", value: detail.cold_subject ?? "not recorded" },
            { key: "scenes", value: String(detail.scene_count) },
            { key: "arc_closed", value: boolLabel(detail.learning_arc_closed) },
            { key: "claims_supported", value: boolLabel(detail.all_claims_supported) },
            {
              key: "corpus_unchanged",
              value: boolLabel(detail.active_corpus_byte_identical),
            },
            {
              key: "engine_chain",
              value: detail.engine_chain
                ? JSON.stringify(detail.engine_chain)
                : "not recorded",
              mono: !!detail.engine_chain,
            },
          ]}
        />
        <div className="grid gap-3 md:grid-cols-2">
          <Bookend label="Cold session (before)" payload={detail.before} />
          <Bookend label="Grounded session (after)" payload={detail.after} />
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
            Learning loop · attempt → enrich → propose → ratify → grounded
          </div>
          <ol className="m-0 grid list-none gap-4 p-0">
            {detail.scenes.map((scene, index) => (
              <ProcessStageCard key={`${scene.scene_id}-${index}`} scene={scene} index={index} />
            ))}
          </ol>
        </div>
      </div>
    </Panel>
  );
}

export function ContemplationRoute() {
  const { runId } = useParams();
  const selectedRunId = runId && runId.length > 0 ? runId : null;
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const runsQuery = useContemplationRuns();
  const detailQuery = useContemplationRun(selectedRunId);

  const runs = runsQuery.data ?? [];
  const filteredRuns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return runs;
    return runs.filter(
      (run) =>
        run.run_id.toLowerCase().includes(q) ||
        (run.prompt ?? "").toLowerCase().includes(q) ||
        (run.cold_subject ?? "").toLowerCase().includes(q),
    );
  }, [runs, search]);

  function selectRun(run: ContemplationRunSummary) {
    navigate(`/contemplation/${encodeURIComponent(run.run_id)}`, { replace: true });
    pushRecentItem({
      label: `Contemplation ${run.run_id}`,
      path: `/contemplation/${encodeURIComponent(run.run_id)}`,
    });
  }

  if (runsQuery.isLoading) {
    return <LoadingState label="Loading contemplation runs..." />;
  }

  if (runsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(runsQuery.error)}
        mutationStatus="No contemplation mutation occurred."
        reproducer="curl /contemplation/runs"
        retrySafety="Retry: safe"
      />
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        statement="No contemplation process reports recorded."
        nextAction={{ kind: "cli", command: "core contemplate" }}
      />
    );
  }

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="contemplation" defaultSplit={36} minSize={320}>
        <Panel title="Contemplation Runs">
          <div className="grid min-h-0 gap-3">
            <SearchInput
              placeholder="Filter by run, prompt, or subject"
              value={search}
              onChange={setSearch}
            />
            {filteredRuns.length === 0 ? (
              <EmptyState
                statement="No contemplation runs match this filter."
                nextAction={{ kind: "cli", command: "core contemplate" }}
              />
            ) : (
              <div className="overflow-hidden rounded-md border border-[var(--color-border-subtle)]">
                {filteredRuns.map((run) => (
                  <RunRow
                    key={run.run_id}
                    run={run}
                    selected={run.run_id === selectedRunId}
                    onSelect={() => selectRun(run)}
                  />
                ))}
              </div>
            )}
          </div>
        </Panel>
        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedRunId === null ? (
            <EmptyState
              statement="Select a contemplation run to inspect its process trace."
              nextAction={{ kind: "cli", command: "core contemplate" }}
            />
          ) : detailQuery.isLoading ? (
            <LoadingState label="Loading contemplation detail..." />
          ) : detailQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(detailQuery.error)}
              mutationStatus="No contemplation mutation occurred."
              reproducer={`curl /contemplation/runs/${selectedRunId}`}
              retrySafety="Retry: safe"
            />
          ) : detailQuery.data ? (
            <DetailPanel detail={detailQuery.data} />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
