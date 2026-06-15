import { useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import { useHealth, useRuntimeStatus } from "../api/queries";
import { useCopyToClipboard } from "../design/hooks/useCopyToClipboard";

function HealthIndicator() {
  const { data, isError, isLoading } = useHealth();
  const healthy = !isError && data?.status === "ok";
  const pending = isLoading && !data && !isError;

  const label = pending ? "Checking" : healthy ? "Healthy" : "Unhealthy";
  const dotColor = pending
    ? "var(--color-state-neutral-text)"
    : healthy
      ? "var(--color-state-success-text)"
      : "var(--color-state-danger-text)";

  return (
    <span
      data-testid="health-indicator"
      data-health={pending ? "checking" : healthy ? "healthy" : "unhealthy"}
      className="flex items-center gap-1.5 text-[var(--color-text-secondary)]"
      title="Server liveness probe (GET /health)"
      aria-label={`Server health: ${label}`}
    >
      <span
        aria-hidden="true"
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: dotColor }}
      />
      {label}
    </span>
  );
}

export function StatusFooter() {
  const { data, isError } = useRuntimeStatus();
  const chatTurnsPending = useIsMutating({ mutationKey: ["chat-turn"] }) > 0;
  const [revisionExpanded, setRevisionExpanded] = useState(false);
  const { copied: shaCopied, copy: copySha } = useCopyToClipboard();

  if (isError) {
    return (
      <footer
        data-region="statusfooter"
        className="flex items-center gap-[var(--density-shell-gap)] border-t border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] px-[var(--density-shell-padding-x)] py-[var(--density-footer-padding-y)] text-xs"
      >
        <HealthIndicator />
        <span className="text-[var(--color-state-danger-text)]">Status unavailable</span>
      </footer>
    );
  }

  if (!data) return null;

  const { mutation_mode, git_revision, checkpoint_revision, revision_warning } = data;
  const visibleMutationMode = chatTurnsPending ? "runtime_turn" : mutation_mode;

  const shortSha = (sha: string) => sha.slice(0, 8);

  const mutationModeEl =
    visibleMutationMode === "read_only" ? (
      <span
        data-testid="mutation-mode"
        className="cursor-default rounded border border-[var(--color-border-subtle)] px-2 py-0.5 text-[var(--color-text-secondary)]"
        title="Runtime mutation mode — read-only by design (status, not a toggle)"
        aria-label="Mutation mode: Read Only"
      >
        Read Only
      </span>
    ) : (
      <span
        data-testid="mutation-mode"
        className="rounded border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] px-2 py-0.5 text-[var(--color-state-warning-text)]"
        aria-label="Mutation mode: Runtime Turn"
      >
        Runtime Turn
      </span>
    );

  return (
    <footer
      data-region="statusfooter"
      className="flex items-center gap-[var(--density-shell-gap)] border-t border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] px-[var(--density-shell-padding-x)] py-[var(--density-footer-padding-y)] text-xs"
    >
      <HealthIndicator />

      {mutationModeEl}

      <button
        type="button"
        className="font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
        onClick={() => copySha(git_revision)}
        title={shaCopied ? "Copied" : "Copy full git revision SHA"}
        aria-label={`git revision: ${git_revision}. Click to copy.`}
        data-testid="git-revision"
      >
        {shaCopied ? "Copied" : shortSha(git_revision)}
      </button>

      <div className="flex flex-col">
        <button
          type="button"
          className={[
            "font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
            revision_warning
              ? "text-[var(--color-state-warning-text)] hover:opacity-80"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
          ].join(" ")}
          onClick={() => setRevisionExpanded((v) => !v)}
          aria-expanded={revisionExpanded}
          title={`Engine checkpoint revision (${checkpoint_revision}) — click to ${revisionExpanded ? "hide" : "show"} details`}
          aria-label={`checkpoint revision: ${checkpoint_revision}${revision_warning ? " (warning)" : ""}`}
          data-testid="checkpoint-revision"
          data-warning={revision_warning ? "true" : undefined}
        >
          {shortSha(checkpoint_revision)}
        </button>
        {revisionExpanded && (
          <p
            className="mt-1 max-w-xs rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-2 text-xs text-[var(--color-text-secondary)]"
            data-testid="revision-note"
          >
            Engine state was written at {checkpoint_revision}; current revision is {git_revision}.
            ADR-0157 / ADR-0158 govern this behavior.
          </p>
        )}
      </div>
    </footer>
  );
}
