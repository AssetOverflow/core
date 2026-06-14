import { Link } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useTour } from "../../api/queries";
import { Panel } from "../../design/components/Panel/Panel";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { TourStep } from "../../types/api";

function errorMessage(error: unknown): string {
  return error instanceof WorkbenchApiError ? error.message : "Tour request failed.";
}

const KIND_LABEL: Record<TourStep["kind"], string> = {
  intro: "Start here",
  demo: "Live demo",
  payoff: "The payoff",
};

function StepCard({ step }: { step: TourStep }) {
  return (
    <li className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-3">
      <div className="flex justify-center">
        <span className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] font-mono text-xs text-[var(--color-text-secondary)]">
          {step.order + 1}
        </span>
      </div>
      <div className="min-w-0 border-l border-[var(--color-border-subtle)] pl-3 pb-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
            {step.headline}
          </span>
          <span className="rounded-sm bg-[var(--color-surface-inset)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">
            {KIND_LABEL[step.kind]}
          </span>
        </div>
        <p className="m-0 mt-1 text-sm text-[var(--color-text-secondary)] [text-wrap:balance]">
          {step.narrative}
        </p>

        {step.demo_id && step.demo_title ? (
          <p className="m-0 mt-2 text-xs text-[var(--color-text-muted)]">
            demo: <span className="text-[var(--color-text-primary)]">{step.demo_title}</span>
          </p>
        ) : null}

        {step.what_this_proves ? (
          <div className="mt-2 rounded-md border border-[var(--color-state-success-border)] bg-[var(--color-state-success-bg)] p-2">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-state-success-text)]">
              what this proves
            </div>
            <p className="m-0 mt-1 text-xs text-[var(--color-text-primary)] [text-wrap:balance]">
              {step.what_this_proves}
            </p>
          </div>
        ) : null}

        {step.what_this_does_not_prove ? (
          <div className="mt-2 rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-2">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-state-warning-text)]">
              what this does not prove
            </div>
            <p className="m-0 mt-1 text-xs text-[var(--color-text-primary)] [text-wrap:balance]">
              {step.what_this_does_not_prove}
            </p>
          </div>
        ) : null}

        {step.route_hint ? (
          <Link
            to={step.route_hint}
            className="mt-2 inline-flex items-center gap-1 text-sm underline"
            data-testid={`tour-link-${step.step_id}`}
          >
            {step.kind === "demo" ? "Run this demo" : "Go there"} →
          </Link>
        ) : null}
      </div>
    </li>
  );
}

export function TourRoute() {
  const tourQuery = useTour();

  if (tourQuery.isLoading) {
    return <LoadingState label="Loading the determinism tour..." />;
  }
  if (tourQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(tourQuery.error)}
        mutationStatus="No mutation occurred."
        reproducer="curl /tour"
        retrySafety="Retry: safe"
      />
    );
  }
  const tour = tourQuery.data;
  if (!tour) {
    return <LoadingState label="Loading the determinism tour..." />;
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <Panel title={tour.title}>
        <div className="grid gap-4">
          <section className="rounded-md border border-[var(--color-state-info-border)] bg-[var(--color-state-info-bg)] p-3">
            <h2 className="m-0 text-xs font-semibold uppercase tracking-wide text-[var(--color-state-info-text)]">
              the pitch
            </h2>
            <p className="m-0 mt-2 text-sm text-[var(--color-text-primary)] [text-wrap:balance]">
              {tour.thesis}
            </p>
          </section>
          <ol className="m-0 grid list-none gap-4 p-0">
            {tour.steps.map((step) => (
              <StepCard key={step.step_id} step={step} />
            ))}
          </ol>
        </div>
      </Panel>
    </div>
  );
}
