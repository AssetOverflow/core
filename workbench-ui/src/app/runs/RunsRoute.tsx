import { useSearchParams } from "react-router-dom";
import { useArtifacts } from "../../api/queries";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { RunsListTable } from "./RunsListTable";
import { RunDetail } from "./RunDetail";
import { useRunCommands } from "./useRunCommands";

export function RunsRoute() {
  const { data: runs, isLoading, isError, error } = useArtifacts();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("runId");

  useRunCommands(runs ?? []);

  function handleSelect(id: string) {
    const next = new URLSearchParams(searchParams);
    next.set("runId", id);
    setSearchParams(next, { replace: false });
  }

  if (isLoading) {
    return (
      <div className="p-4" data-testid="runs-route">
        <LoadingState label="Loading runs…" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4" data-testid="runs-route">
        <ErrorState
          whatFailed="Failed to load runs index"
          mutationStatus="No changes were made"
          reproducer="GET /artifacts"
          retrySafety={
            error?.message ?? "Safe to retry — read-only operation"
          }
        />
      </div>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="p-4" data-testid="runs-route">
        <EmptyState
          statement="No runs recorded yet."
          nextAction={{
            kind: "cli",
            command: "core eval cognition",
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="grid h-full grid-cols-1 gap-4 p-4 md:grid-cols-[1fr_minmax(20rem,28rem)]"
      data-testid="runs-route"
    >
      <div className="overflow-y-auto">
        <RunsListTable
          runs={runs}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
      </div>
      <aside className="overflow-y-auto">
        {selectedId ? (
          <RunDetail runId={selectedId} />
        ) : (
          <EmptyState
            statement="Select a run to see details."
            nextAction="Pick any row on the left."
          />
        )}
      </aside>
    </div>
  );
}
