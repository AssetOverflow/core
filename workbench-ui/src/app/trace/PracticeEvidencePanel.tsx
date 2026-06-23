import { useMemo } from "react";
import type { PracticeEvidence } from "../../types/practiceEvidence";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { tracePracticeReproducer } from "./practiceEvidenceEndpoint";
import {
  type PracticeEvidenceDetailSection,
  practiceEvidencePanelModel,
} from "./practiceEvidencePanelModel";

export interface PracticeEvidencePanelProps {
  evidence?: PracticeEvidence | null;
  isLoading: boolean;
  error: unknown;
  turnId: number;
  errorMessage: (error: unknown) => string;
}

function DetailSection({ section }: { section: PracticeEvidenceDetailSection }) {
  return (
    <section className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] p-3">
      <h3 className="m-0 text-xs font-semibold uppercase text-[var(--color-text-secondary)]">
        {section.title}
      </h3>
      {section.items.length === 0 ? (
        <p className="m-0 text-sm text-[var(--color-text-secondary)]">{section.emptyMessage}</p>
      ) : (
        <div className="grid gap-3">
          {section.items.map((item) => (
            <article className="grid gap-2" key={item.title}>
              <h4 className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
                {item.title}
              </h4>
              <MetadataTable
                rows={item.rows.map((row) => ({
                  key: row.key,
                  value: row.value,
                  mono: true,
                }))}
              />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function PracticeEvidencePanel({
  evidence,
  isLoading,
  error,
  turnId,
  errorMessage,
}: PracticeEvidencePanelProps) {
  const reproducer = tracePracticeReproducer(turnId);
  const rawJson = useMemo(
    () => (evidence ? JSON.stringify(evidence, null, 2) : ""),
    [evidence],
  );
  const model = useMemo(
    () => (evidence ? practiceEvidencePanelModel(evidence) : null),
    [evidence],
  );

  if (isLoading) {
    return <LoadingState label="Loading sealed practice evidence..." />;
  }
  if (error) {
    return (
      <ErrorState
        whatFailed={errorMessage(error)}
        mutationStatus="No trace mutation occurred."
        reproducer={reproducer}
        retrySafety="Retry: safe"
      />
    );
  }
  if (!evidence || model === null) {
    return (
      <EmptyState
        statement="No sealed practice evidence recorded for this turn."
        nextAction={{ kind: "cli", command: reproducer }}
      />
    );
  }

  return (
    <section className="grid gap-3" data-testid="practice-evidence-panel">
      {model.emptyMessage ? (
        <div className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-3 text-sm text-[var(--color-state-warning-text)]">
          <h3 className="m-0 text-xs font-semibold uppercase">{model.status}</h3>
          <p className="m-0 mt-2">{model.emptyMessage}</p>
        </div>
      ) : null}

      <div className="grid gap-3 xl:grid-cols-2">
        <MetadataTable
          rows={model.authorityRows.map((row) => ({
            key: row.key,
            value: row.value,
            mono: true,
          }))}
        />
        <MetadataTable
          rows={model.countRows.map((row) => ({
            key: row.key,
            value: row.value,
            mono: true,
          }))}
        />
      </div>

      {model.chainRows.length > 0 ? (
        <MetadataTable
          rows={model.chainRows.map((row) => ({
            key: row.key,
            value: row.value,
            mono: true,
          }))}
        />
      ) : null}

      <div className="grid gap-3" data-testid="practice-evidence-details">
        {model.detailSections.map((section) => (
          <DetailSection key={section.title} section={section} />
        ))}
      </div>

      <section className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] p-3">
        <h3 className="m-0 text-xs font-semibold uppercase text-[var(--color-text-secondary)]">
          Source spans
        </h3>
        {model.sourceSpanRows.length > 0 ? (
          <MetadataTable
            rows={model.sourceSpanRows.map((row) => ({
              key: row.key,
              value: row.value,
              mono: true,
            }))}
          />
        ) : (
          <p className="m-0 text-sm text-[var(--color-text-secondary)]">
            No source spans recorded.
          </p>
        )}
      </section>

      <div>
        <div className="mb-1 text-xs font-semibold text-[var(--color-text-secondary)]">
          reproducer
        </div>
        <code className="block overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2 font-mono text-xs text-[var(--color-text-primary)]">
          {model.reproducer}
        </code>
      </div>

      {model.showRaw ? (
        <div className="max-h-[28rem] overflow-auto rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2">
          <StableJsonViewer source={rawJson} />
        </div>
      ) : null}
    </section>
  );
}
