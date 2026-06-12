import { useEffect } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useEvidenceSubject } from "../evidenceContext";
import { subjectToUrl } from "../evidenceAddress";
import { useArtifacts, useArtifactDetail, useReplayComparison } from "../../api/queries";
import { ArtifactList } from "./ArtifactList";
import { ReplayComparisonPanel } from "./ReplayComparisonPanel";
import { LoadingState } from "../../design/components/states/LoadingState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { EmptyState } from "../../design/components/states/EmptyState";
import { WorkbenchApiError } from "../../api/client";
import { ReplayStatus } from "../../design/components/badges";

export function ReplayRoute() {
  const { artifactId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSubject } = useEvidenceSubject();
  const selectedId = artifactId ?? null;

  const artifactsQuery = useArtifacts();
  const detailQuery = useArtifactDetail(selectedId || "");
  const comparisonQuery = useReplayComparison(selectedId || "");

  // Publish the selected artifact as the evidence subject: identity
  // immediately, detail once the query resolves.
  const detailData = detailQuery.data;
  useEffect(() => {
    if (!selectedId) return;
    setSubject({ kind: "artifact", artifactId: selectedId, data: detailData });
  }, [selectedId, detailData, setSubject]);

  function handleSelect(id: string) {
    const search = searchParams.toString();
    const path = subjectToUrl({ kind: "artifact", artifactId: id });
    // Selection churn must not pollute history: replace, never push.
    navigate(search ? `${path}?${search}` : path, { replace: true });
  }

  // Handle loading states
  const isLoadingArtifacts = artifactsQuery.isPending;
  const isLoadingDetail = selectedId ? detailQuery.isPending : false;
  const isLoadingComparison = selectedId ? comparisonQuery.isPending : false;

  // Determine if comparison error is the unsupported (evidence_unavailable) case
  const isUnsupportedError =
    comparisonQuery.error instanceof WorkbenchApiError &&
    comparisonQuery.error.code === "unsupported";

  // Check for genuine API errors
  const artifactsError = artifactsQuery.error;
  const detailError = detailQuery.error;
  const comparisonError = comparisonQuery.error;

  const hasGenuineError =
    artifactsQuery.isError ||
    detailQuery.isError ||
    (comparisonQuery.isError && !isUnsupportedError);

  const getGenuineErrorDetails = () => {
    if (artifactsQuery.isError && artifactsError) {
      return {
        message:
          artifactsError instanceof WorkbenchApiError
            ? artifactsError.message
            : "Failed to load artifacts.",
        reproducer: "curl -X GET /artifacts",
      };
    }
    if (detailQuery.isError && detailError) {
      return {
        message:
          detailError instanceof WorkbenchApiError
            ? detailError.message
            : "Failed to load artifact details.",
        reproducer: `curl -X GET /artifacts/${selectedId || ""}`,
      };
    }
    if (comparisonQuery.isError && comparisonError && !isUnsupportedError) {
      return {
        message:
          comparisonError instanceof WorkbenchApiError
            ? comparisonError.message
            : "Failed to load replay comparison.",
        reproducer: `curl -X GET /replay/${selectedId || ""}`,
      };
    }
    return null;
  };

  const errorDetails = getGenuineErrorDetails();

  return (
    <div
      className="grid grid-cols-[18rem_1fr] h-[calc(100vh-8rem)] gap-4 overflow-hidden"
      data-testid="replay-theater-route"
    >
      {/* Left Pane: Artifact list */}
      <div className="border-r border-[var(--color-border-subtle)] overflow-y-auto pr-2">
        {isLoadingArtifacts ? (
          <LoadingState label="Loading artifacts..." />
        ) : artifactsQuery.isError ? (
          <ErrorState
            whatFailed={
              artifactsError instanceof WorkbenchApiError
                ? artifactsError.message
                : "Failed to load artifacts."
            }
            mutationStatus="No corpus mutation occurred."
            reproducer="curl http://127.0.0.1:8765/artifacts"
            retrySafety="Retry: safe"
          />
        ) : (
          <ArtifactList
            artifacts={artifactsQuery.data || []}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
        )}
      </div>

      {/* Right Pane: Replay detail comparison */}
      <div className="overflow-y-auto pl-2 pr-4">
        {hasGenuineError && errorDetails ? (
          <ErrorState
            whatFailed={errorDetails.message}
            mutationStatus="No corpus mutation occurred."
            reproducer={errorDetails.reproducer}
            retrySafety="Retry: safe"
          />
        ) : isLoadingDetail || isLoadingComparison ? (
          <LoadingState
            label={isLoadingComparison ? "Comparing artifacts..." : "Comparing artifacts..."}
          />
        ) : !selectedId ? (
          <EmptyState
            statement="No artifact selected."
            nextAction="Select an artifact from the list to inspect replay evidence."
          />
        ) : detailQuery.data ? (
          <ReplayComparisonPanel
            artifact={detailQuery.data}
            comparison={isUnsupportedError ? null : comparisonQuery.data}
            status={
              isUnsupportedError
                ? ReplayStatus.EVIDENCE_UNAVAILABLE
                : comparisonQuery.data?.equivalent
                ? ReplayStatus.EQUIVALENT
                : comparisonQuery.data?.replay_hash === null
                ? ReplayStatus.NOT_YET_REPLAYED
                : ReplayStatus.DIVERGED
            }
          />
        ) : null}
      </div>
    </div>
  );
}
