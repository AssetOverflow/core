import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useEvidenceSubject } from "../evidenceContext";
import { useCommandRegistry } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvalLanes, useEvalRun } from "../../api/queries";
import { EvalLaneCard } from "./EvalLaneCard";
import { Panel } from "../../design/components/Panel/Panel";
import { EvalRunButton } from "./EvalRunButton";
import { EvalMetricGrid } from "./EvalMetricGrid";
import { EvalFailureViewer } from "./EvalFailureViewer";
import { EvalArtifactLink } from "./EvalArtifactLink";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { EvalRunResult } from "../../types/api";
import { WorkbenchApiError } from "../../api/client";

export function EvalsRoute() {
  const { data: lanes, isLoading, isError, error } = useEvalLanes();
  const { laneId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSubject } = useEvidenceSubject();
  const selectedLaneName = laneId ?? "";

  // Maintain per-lane run states (pending, result, error)
  const [runStates, setRunStates] = useState<
    Record<
      string,
      {
        isPending: boolean;
        result?: EvalRunResult;
        error?: WorkbenchApiError;
      }
    >
  >({});

  const selectedRunResult = selectedLaneName
    ? runStates[selectedLaneName]?.result
    : undefined;

  // Palette verbs (Wave R brief R0d): one "Run eval lane <lane>" command per
  // read-only lane, registered while this route is mounted. Executes the
  // same read-only POST /evals/run as EvalRunButton's defaults (first
  // version, public split) and navigates here to show the run state.
  const paletteRun = useEvalRun();
  const paletteMutate = paletteRun.mutate;
  const { register, unregister } = useCommandRegistry();
  useEffect(() => {
    const runnable = (lanes ?? []).filter((l) => l.read_only);
    if (runnable.length === 0) return;
    register(
      runnable.map((l) => ({
        id: `action-run-eval-${l.lane}`,
        label: `Run eval lane ${l.lane}`,
        section: "Actions",
        kind: "action" as const,
        action: () => {
          navigate(`/evals/${encodeURIComponent(l.lane)}`);
          setRunStates((prev) => ({ ...prev, [l.lane]: { isPending: true } }));
          paletteMutate(
            { lane: l.lane, version: l.versions[0] || "v1", split: "public" },
            {
              onSuccess: (result) =>
                setRunStates((prev) => ({
                  ...prev,
                  [l.lane]: { isPending: false, result },
                })),
              onError: (err) =>
                setRunStates((prev) => ({
                  ...prev,
                  [l.lane]: { isPending: false, error: err },
                })),
            },
          );
        },
      })),
    );
    return () => unregister(runnable.map((l) => `action-run-eval-${l.lane}`));
  }, [lanes, register, unregister, navigate, paletteMutate]);

  // Publish the selected lane as the evidence subject: identity immediately,
  // run-result data once a run completes in this session.
  useEffect(() => {
    if (!selectedLaneName) return;
    setSubject({
      kind: "eval_result",
      lane: selectedLaneName,
      data: selectedRunResult,
    });
  }, [selectedLaneName, selectedRunResult, setSubject]);

  function selectLane(lane: string) {
    const search = searchParams.toString();
    const path = subjectToUrl({ kind: "eval_result", lane });
    // Selection churn must not pollute history: replace, never push.
    navigate(search ? `${path}?${search}` : path, { replace: true });
  }

  if (isLoading) {
    return <LoadingState label="Loading eval lanes..." />;
  }

  if (isError) {
    return (
      <ErrorState
        whatFailed={error instanceof Error ? error.message : "Failed to load eval lanes."}
        mutationStatus="No corpus mutation occurred."
        reproducer="curl -X GET http://127.0.0.1:8765/evals"
        retrySafety="Retry: safe"
      />
    );
  }

  const selectedLane = lanes?.find((l) => l.lane === selectedLaneName) || null;
  const currentRunState = selectedLaneName ? runStates[selectedLaneName] : null;

  return (
    <div className="grid h-full grid-cols-1 gap-4 md:grid-cols-[18rem_1fr]" data-testid="evals-route">
      {/* Left Pane: Lane List */}
      <Panel title="Eval Lanes">
        <div className="flex flex-col gap-2">
          {lanes && lanes.length > 0 ? (
            lanes.map((lane) => (
              <EvalLaneCard
                key={lane.lane}
                lane={lane}
                isSelected={lane.lane === selectedLaneName}
                onSelect={() => selectLane(lane.lane)}
              />
            ))
          ) : (
            <EmptyState
              statement="No eval lanes discovered."
              nextAction={{ kind: "cli", command: "core eval --list" }}
            />
          )}
        </div>
      </Panel>

      {/* Right Pane: Results / Form */}
      <div className="flex flex-col gap-4 overflow-y-auto pl-2">
        {selectedLane ? (
          <>
            {/* Header info */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border-subtle)] pb-3">
              <div>
                <h2 className="text-lg font-semibold text-[var(--color-text-primary)] font-mono">
                  {selectedLane.lane}
                </h2>
                {selectedLane.description && (
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    {selectedLane.description}
                  </p>
                )}
              </div>
            </div>

            {/* Run Button configuration if read-only */}
            {selectedLane.read_only ? (
              <EvalRunButton
                lane={selectedLane}
                onRunStart={() => {
                  setRunStates((prev) => ({
                    ...prev,
                    [selectedLane.lane]: { isPending: true },
                  }));
                }}
                onRunSuccess={(result) => {
                  setRunStates((prev) => ({
                    ...prev,
                    [selectedLane.lane]: { isPending: false, result },
                  }));
                }}
                onRunError={(err) => {
                  setRunStates((prev) => ({
                    ...prev,
                    [selectedLane.lane]: { isPending: false, error: err },
                  }));
                }}
              />
            ) : (
              <div className="text-xs text-[var(--color-text-muted)] bg-[var(--color-surface-inset)] p-3 rounded-lg border border-[var(--color-border-subtle)] font-medium">
                ⚠️ API runs disabled for write-active lane. Use local CLI to execute this lane:
                <code className="block mt-1 font-mono text-[var(--color-text-primary)] bg-[var(--color-surface-base)] p-1.5 rounded">
                  core eval --lane {selectedLane.lane}
                </code>
              </div>
            )}

            {/* Result display */}
            {currentRunState?.isPending ? (
              <LoadingState label="Running eval lane..." />
            ) : currentRunState?.error ? (
              <ErrorState
                whatFailed={currentRunState.error.message}
                mutationStatus="No corpus mutation occurred."
                reproducer={`core eval --lane ${selectedLane.lane}`}
                retrySafety="Retry: safe"
              />
            ) : currentRunState?.result ? (
              <div className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-xs text-[var(--color-text-secondary)] font-semibold">
                    Status:
                  </span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-semibold ${
                      currentRunState.result.passed
                        ? "bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)] border border-[var(--color-state-success-border)]"
                        : "bg-[var(--color-state-danger-bg)] text-[var(--color-state-danger-text)] border border-[var(--color-state-danger-border)]"
                    }`}
                  >
                    {currentRunState.result.passed ? "Passed" : "Failed"}
                  </span>
                  {currentRunState.result.source_digest && (
                    <EvalArtifactLink
                      lane={selectedLane.lane}
                      sourceDigest={currentRunState.result.source_digest}
                    />
                  )}
                </div>

                <div className="flex flex-col gap-2">
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Metrics</h3>
                  <EvalMetricGrid metrics={currentRunState.result.metrics} />
                </div>

                <EvalFailureViewer
                  cases={currentRunState.result.cases}
                  passed={currentRunState.result.passed}
                  laneName={selectedLane.lane}
                />
              </div>
            ) : (
              <EmptyState
                statement={
                  selectedLane.read_only
                    ? `No run results for lane "${selectedLane.lane}" in this session. Trigger a run above.`
                    : `Eval lane "${selectedLane.lane}" is CLI-only. No session results available.`
                }
                nextAction={{ kind: "cli", command: `core eval --lane ${selectedLane.lane}` }}
              />
            )}
          </>
        ) : (
          <EmptyState
            statement="Select an eval lane from the list to view results or run checks."
            nextAction={{ kind: "cli", command: "core eval --list" }}
          />
        )}
      </div>
    </div>
  );
}
