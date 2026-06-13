import { useMemo, useState } from "react";
import { Play } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useDemoRun, useDemos } from "../../api/queries";
import { DagViewer, type DagEdgeInput, type DagNodeInput } from "../../design/components/Dag";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { Button } from "../../design/components/primitives/Button";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type {
  DemoEvidenceDag,
  DemoRunResult,
  DemoScenarioRunResult,
  DemoSummary,
  EvidenceClass,
} from "../../types/api";

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Demo API request failed.";
}

function evidenceClassLabel(value: EvidenceClass) {
  return value.replaceAll("_", " ");
}

function EvidenceClassBadge({ value }: { value: EvidenceClass }) {
  return (
    <span className="rounded-md border border-[var(--color-state-info-border)] bg-[var(--color-state-info-bg)] px-2 py-0.5 text-xs font-semibold text-[var(--color-state-info-text)]">
      {evidenceClassLabel(value)}
    </span>
  );
}

function DemoRow({
  demo,
  selected,
  focused,
  onSelect,
}: {
  demo: DemoSummary;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid gap-1 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      } ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] pl-[10px]"
          : focused
            ? "border-l-2 border-l-[var(--color-focus-ring)] pl-[10px]"
            : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="truncate text-sm font-semibold text-[var(--color-text-primary)]">
        {demo.title}
      </span>
      <span className="font-mono text-xs text-[var(--color-text-muted)]">
        {demo.scenario_count} scenarios
      </span>
    </div>
  );
}

function HonestyCards({ demo }: { demo: Pick<DemoSummary, "scenarios"> }) {
  const first = demo.scenarios[0];
  if (!first) return null;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
          What this proves
        </h3>
        <p className="mb-0 mt-2 text-sm text-[var(--color-text-primary)]">
          {first.what_this_proves}
        </p>
      </section>
      <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
          What this does not prove
        </h3>
        <p className="mb-0 mt-2 text-sm text-[var(--color-text-primary)]">
          {first.what_this_does_not_prove}
        </p>
      </section>
    </div>
  );
}

function ScenarioCatalog({ demo }: { demo: DemoSummary }) {
  return (
    <section className="grid gap-2">
      <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
        Scenarios
      </h3>
      <div className="grid gap-2">
        {demo.scenarios.map((scenario) => (
          <div
            key={scenario.scenario_id}
            className={`grid gap-1 rounded-md border p-3 ${
              scenario.proposer_wrong
                ? "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)]"
                : "border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)]"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
                {scenario.scenario_id}
              </span>
              <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                expected: {scenario.expected_status}
              </span>
            </div>
            {scenario.proposer_wrong ? (
              <span className="text-xs font-semibold text-[var(--color-state-warning-text)]">
                Proposer was wrong
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function graphInputs(dag: DemoEvidenceDag): { nodes: DagNodeInput[]; edges: DagEdgeInput[] } {
  return {
    nodes: dag.nodes.map((node) => ({
      id: node.node_id,
      label: node.label,
      detail: {
        summary: node.summary,
        ...node.detail,
      },
    })),
    edges: dag.edges.map((edge) => ({
      from: edge.from_node,
      to: edge.to_node,
      label: edge.label ?? undefined,
    })),
  };
}

function EvidenceDagPanel({ dag }: { dag: DemoEvidenceDag }) {
  const graph = graphInputs(dag);
  const digest = digestPayload(dag.source_digest);
  return (
    <section className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
            {dag.title}
          </h3>
          <p className="m-0 mt-1 font-mono text-[10px] text-[var(--color-text-muted)]">
            {dag.graph_kind}
          </p>
        </div>
        {digest ? <DigestBadge digest={digest} truncate={12} /> : null}
      </div>
      <DagViewer
        nodes={graph.nodes}
        edges={graph.edges}
        ariaLabel={dag.title}
        height={300}
      />
    </section>
  );
}

function ResultRow({ scenario }: { scenario: DemoScenarioRunResult }) {
  return (
    <article
      className={`grid gap-2 rounded-md border p-3 ${
        scenario.passed
          ? scenario.proposer_wrong
            ? "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)]"
            : "border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)]"
          : "border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)]"
      }`}
      data-testid="demo-scenario-result"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
          {scenario.scenario_id}
        </span>
        <span className="font-mono text-xs text-[var(--color-text-secondary)]">
          {scenario.status}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded border px-2 py-0.5 text-xs font-semibold ${
            scenario.passed
              ? "border-[var(--color-state-success-border)] text-[var(--color-state-success-text)]"
              : "border-[var(--color-state-danger-border)] text-[var(--color-state-danger-text)]"
          }`}
        >
          {scenario.passed ? "Passed" : "Failed"}
        </span>
        {scenario.proposer_wrong ? (
          <span className="rounded border border-[var(--color-state-warning-border)] px-2 py-0.5 text-xs font-semibold text-[var(--color-state-warning-text)]">
            proposer-wrong
          </span>
        ) : null}
      </div>
      {scenario.decision_reason ? (
        <p className="m-0 text-xs text-[var(--color-text-secondary)]">
          {scenario.decision_reason}
        </p>
      ) : null}
      {scenario.trace_hash ? (
        <code className="truncate font-mono text-xs text-[var(--color-text-muted)]">
          {scenario.trace_hash}
        </code>
      ) : null}
      {scenario.problems.length > 0 ? (
        <ul className="m-0 grid list-none gap-1 p-0">
          {scenario.problems.map((problem) => (
            <li key={problem} className="text-xs text-[var(--color-state-danger-text)]">
              {problem}
            </li>
          ))}
        </ul>
      ) : null}
      {scenario.evidence_dag ? <EvidenceDagPanel dag={scenario.evidence_dag} /> : null}
    </article>
  );
}

function RunResults({ result }: { result: DemoRunResult }) {
  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-secondary)]">Run status</span>
        <span
          className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${
            result.all_passed
              ? "border-[var(--color-state-success-border)] text-[var(--color-state-success-text)]"
              : "border-[var(--color-state-danger-border)] text-[var(--color-state-danger-text)]"
          }`}
        >
          {result.all_passed ? "All scenarios passed" : "Scenario drift detected"}
        </span>
      </div>
      <div className="grid gap-2">
        {result.scenarios.map((scenario) => (
          <ResultRow key={scenario.scenario_id} scenario={scenario} />
        ))}
      </div>
    </section>
  );
}

export function DemoTheaterRoute() {
  const { demoId } = useParams();
  const navigate = useNavigate();
  const demosQuery = useDemos();
  const demoRun = useDemoRun();
  const [search, setSearch] = useState("");
  const [runStates, setRunStates] = useState<
    Record<string, { isPending: boolean; result?: DemoRunResult; error?: WorkbenchApiError }>
  >({});

  const demos = demosQuery.data ?? [];
  const filteredDemos = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return demos;
    return demos.filter(
      (demo) =>
        demo.demo_id.toLowerCase().includes(q) ||
        demo.title.toLowerCase().includes(q) ||
        demo.description.toLowerCase().includes(q),
    );
  }, [demos, search]);
  const selectedDemo = demos.find((demo) => demo.demo_id === demoId) ?? null;
  const selectedRunState = selectedDemo ? runStates[selectedDemo.demo_id] : null;

  function selectDemo(demo: DemoSummary) {
    navigate(`/demos/${encodeURIComponent(demo.demo_id)}`, { replace: true });
  }

  function runSelectedDemo(demo: DemoSummary) {
    setRunStates((prev) => ({ ...prev, [demo.demo_id]: { isPending: true } }));
    demoRun.mutate(
      { demoId: demo.demo_id },
      {
        onSuccess: (result) =>
          setRunStates((prev) => ({
            ...prev,
            [demo.demo_id]: { isPending: false, result },
          })),
        onError: (error) =>
          setRunStates((prev) => ({
            ...prev,
            [demo.demo_id]: { isPending: false, error },
          })),
      },
    );
  }

  if (demosQuery.isLoading) {
    return <LoadingState label="Loading demos..." />;
  }

  if (demosQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(demosQuery.error)}
        mutationStatus="No demo mutation occurred."
        reproducer="curl /demos"
        retrySafety="Retry: safe"
      />
    );
  }

  if (demos.length === 0) {
    return (
      <EmptyState
        statement="No demos registered."
        nextAction={{ kind: "cli", command: "core demo --list" }}
      />
    );
  }

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[22rem_1fr]" data-testid="demo-theater-route">
      <Panel title="Demo Theater">
        <div className="grid min-h-0 gap-3">
          <SearchInput placeholder="Filter demos" value={search} onChange={setSearch} />
          {filteredDemos.length === 0 ? (
            <EmptyState
              statement="No demos match this filter."
              nextAction={{ kind: "cli", command: "core demo --list" }}
            />
          ) : (
            <VirtualizedList
              ariaLabel="Registered demos"
              estimateSize={68}
              getKey={(demo) => demo.demo_id}
              height="calc(100vh - 14rem)"
              initialRect={{ width: 360, height: 560 }}
              items={filteredDemos}
              onActivate={(demo) => selectDemo(demo)}
              renderItem={(demo, _index, focused) => (
                <DemoRow
                  demo={demo}
                  selected={demo.demo_id === selectedDemo?.demo_id}
                  focused={focused}
                  onSelect={() => selectDemo(demo)}
                />
              )}
            />
          )}
        </div>
      </Panel>

      <section className="min-h-0 overflow-y-auto pr-1">
        {!selectedDemo ? (
          <EmptyState
            statement="Select a demo to inspect scenarios and run proof surface."
            nextAction={{ kind: "cli", command: "core demo --list" }}
          />
        ) : (
          <div className="grid gap-4">
            <Panel
              title={selectedDemo.title}
              toolbar={
                <EvidenceClassBadge value={selectedDemo.evidence_class} />
              }
            >
              <div className="grid gap-4">
                <p className="m-0 text-sm text-[var(--color-text-secondary)]">
                  {selectedDemo.description}
                </p>
                <HonestyCards demo={selectedDemo} />
                <Button
                  disabled={selectedRunState?.isPending}
                  onClick={() => runSelectedDemo(selectedDemo)}
                  type="button"
                >
                  <Play size={15} aria-hidden />
                  Run demo
                </Button>
              </div>
            </Panel>

            <ScenarioCatalog demo={selectedDemo} />

            {selectedRunState?.isPending ? (
              <LoadingState label="Running demo..." />
            ) : selectedRunState?.error ? (
              <ErrorState
                whatFailed={errorMessage(selectedRunState.error)}
                mutationStatus="No demo mutation occurred."
                reproducer={`curl -X POST /demos/${selectedDemo.demo_id}/run`}
                retrySafety="Retry: safe"
              />
            ) : selectedRunState?.result ? (
              <RunResults result={selectedRunState.result} />
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
