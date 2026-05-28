import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useEvalLanes, useEvalLane } from "../../api/queries";
import { EvalLaneCard } from "./EvalLaneCard";
import { EvalRunButton } from "./EvalRunButton";
import { EvalMetricGrid } from "./EvalMetricGrid";
import { EvalFailureViewer } from "./EvalFailureViewer";
import { EvalArtifactLink } from "./EvalArtifactLink";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { EvalRunResult } from "../../types/api";
import { WorkbenchApiError } from "../../api/client";
import { useEvalCommands } from "./useEvalCommands";

export function EvalsRoute() {
  const { data: lanes, isLoading, isError, error } = useEvalLanes();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedLaneName = searchParams.get("lane") || "";
  const queryClient = useQueryClient();

  useEvalCommands(lanes ?? []);

  const {
    data: lastRunResult,
    isLoading: isLaneLoading,
    isError: isLaneError,
    error: laneError,
  } = useEvalLane(selectedLaneName);

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

  // Auto-select the first lane on load if no selection is in the URL
  useEffect(() => {
    if (!selectedLaneName && lanes && lanes.length > 0) {
      setSearchParams({ lane: lanes[0].lane }, { replace: true });
    }
  }, [selectedLaneName, lanes, setSearchParams]);

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
  const isNotFoundError =
    laneError instanceof WorkbenchApiError && laneError.code === "not_found";

  function renderHeaderAndForm(lane: typeof selectedLane) {
    if (!lane) return null;
    return (
      <>
        {/* Header info */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border-subtle)] pb-3">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] font-mono">
              {lane.lane}
            </h2>
            {lane.description && (
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                {lane.description}
              </p>
            )}
          </div>
        </div>

        {/* Run Button configuration if read-only */}
        {lane.read_only ? (
          <EvalRunButton
            lane={lane}
            onRunStart={() => {
              setRunStates((prev) => ({
                ...prev,
                [lane.lane]: { isPending: true },
              }));
            }}
            onRunSuccess={(result) => {
              setRunStates((prev) => ({
                ...prev,
                [lane.lane]: { isPending: false, result },
              }));
              queryClient.invalidateQueries({ queryKey: ["api", "eval", lane.lane] });
            }}
            onRunError={(err) => {
              setRunStates((prev) => ({
                ...prev,
                [lane.lane]: { isPending: false, error: err },
              }));
            }}
          />
        ) : (
          <div className="text-xs text-[var(--color-text-muted)] bg-[var(--color-surface-inset)] p-3 rounded-lg border border-[var(--color-border-subtle)] font-medium">
            ⚠️ API runs disabled for write-active lane. Use local CLI to execute this lane:
            <code className="block mt-1 font-mono text-[var(--color-text-primary)] bg-[var(--color-surface-base)] p-1.5 rounded">
              core eval --lane {lane.lane}
            </code>
          </div>
        )}
      </>
    );
  }

  const renderRightPane = () => {
    if (!selectedLaneName) {
      return (
        <EmptyState
          statement="Select an eval lane from the list to view results or run checks."
          nextAction={{ kind: "cli", command: "core eval --list" }}
        />
      );
    }

    if (!selectedLane) {
      return (
        <EmptyState
          statement={`Selected lane "${selectedLaneName}" not found.`}
          nextAction={{ kind: "cli", command: "core eval --list" }}
        />
      );
    }

    // 1. Loading state for fetching the lane's last run details
    if (isLaneLoading && !lastRunResult) {
      return <LoadingState label="Loading eval lane details..." />;
    }

    // 2. Error state for fetching the lane details (excluding not_found)
    if (isLaneError && !isNotFoundError) {
      return (
        <ErrorState
          whatFailed={laneError instanceof Error ? laneError.message : "Failed to load eval lane details."}
          mutationStatus="No corpus mutation occurred."
          reproducer={`core eval --lane ${selectedLaneName}`}
          retrySafety="Retry: safe"
        />
      );
    }

    // 3. Current run execution state
    if (currentRunState?.isPending) {
      return (
        <div className="flex flex-col gap-4">
          {renderHeaderAndForm(selectedLane)}
          <LoadingState label="Running eval lane..." />
        </div>
      );
    }

    if (currentRunState?.error) {
      return (
        <div className="flex flex-col gap-4">
          {renderHeaderAndForm(selectedLane)}
          <ErrorState
            whatFailed={currentRunState.error.message}
            mutationStatus="No corpus mutation occurred."
            reproducer={`core eval --lane ${selectedLane.lane}`}
            retrySafety="Retry: safe"
          />
        </div>
      );
    }

    // 4. Success or Empty state
    const result = currentRunState?.result || (lastRunResult as EvalRunResult | undefined);
    if (result && result.metrics) {
      return (
        <div className="flex flex-col gap-4">
          {renderHeaderAndForm(selectedLane)}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-[var(--color-text-secondary)] font-semibold">
              Status:
            </span>
            <span
              className={`rounded-md px-2 py-0.5 text-xs font-semibold ${
                result.passed
                  ? "bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)] border border-[var(--color-state-success-border)]"
                  : "bg-[var(--color-state-danger-bg)] text-[var(--color-state-danger-text)] border border-[var(--color-state-danger-border)]"
              }`}
            >
              {result.passed ? "Passed" : "Failed"}
            </span>
            {result.source_digest && (
              <EvalArtifactLink
                lane={selectedLane.lane}
                sourceDigest={result.source_digest}
              />
            )}
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Metrics</h3>
            <EvalMetricGrid metrics={result.metrics} />
          </div>

          <EvalFailureViewer
            cases={result.cases}
            passed={result.passed}
            laneName={selectedLane.lane}
          />
        </div>
      );
    }

    return (
      <div className="flex flex-col gap-4">
        {renderHeaderAndForm(selectedLane)}
        <EmptyState
          statement={
            selectedLane.read_only
              ? `No run results for lane "${selectedLane.lane}" in this session. Trigger a run above.`
              : `Eval lane "${selectedLane.lane}" is CLI-only. No session results available.`
          }
          nextAction={{ kind: "cli", command: `core eval --lane ${selectedLane.lane}` }}
        />
      </div>
    );
  };

  return (
    <div className="grid h-full grid-cols-1 gap-4 md:grid-cols-[18rem_1fr]" data-testid="evals-route">
      {/* Left Pane: Lane List */}
      <div className="flex flex-col gap-3 border-r border-[var(--color-border-subtle)] pr-4 overflow-y-auto">
        <h2 className="text-md font-semibold text-[var(--color-text-primary)]">Eval Lanes</h2>
        <div className="flex flex-col gap-2">
          {lanes && lanes.length > 0 ? (
            lanes.map((lane) => (
              <EvalLaneCard
                key={lane.lane}
                lane={lane}
                isSelected={lane.lane === selectedLaneName}
                onSelect={() => setSearchParams({ lane: lane.lane })}
              />
            ))
          ) : (
            <EmptyState
              statement="No eval lanes discovered."
              nextAction={{ kind: "cli", command: "core eval --list" }}
            />
          )}
        </div>
      </div>

      {/* Right Pane: Results / Form */}
      <div className="flex flex-col gap-4 overflow-y-auto pl-2">
        {renderRightPane()}
      </div>
    </div>
  );
}
