import {
  EpistemicState,
  EpistemicStateBadge,
  GroundingSource,
  GroundingSourceBadge,
  NormativeClearance,
  NormativeClearanceBadge,
  ReviewState,
  ReviewStateBadge,
} from "../../design/components/badges";
import type { KeyboardEvent, ReactNode } from "react";
import type { ChatTurnResult } from "../../types/api";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";

export type TraceFocus =
  | "metadata"
  | "surfaces"
  | "grounding"
  | "verdicts"
  | "proposals"
  | "trace";

function BadgeRegion({
  children,
  onClick,
  label,
}: {
  children: ReactNode;
  onClick: () => void;
  label: string;
}) {
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={label}
      onClickCapture={onClick}
      onKeyDown={onKeyDown}
      className="rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
    >
      {children}
    </div>
  );
}

export function EvidenceStrip({
  result,
  onOpen,
}: {
  result: ChatTurnResult;
  onOpen: (focus: TraceFocus) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Turn evidence">
      <BadgeRegion label="Open grounding evidence" onClick={() => onOpen("grounding")}>
        <GroundingSourceBadge value={result.grounding_source as GroundingSource} />
      </BadgeRegion>
      <BadgeRegion label="Open epistemic evidence" onClick={() => onOpen("grounding")}>
        <EpistemicStateBadge value={result.epistemic_state as EpistemicState} />
      </BadgeRegion>
      <BadgeRegion label="Open clearance evidence" onClick={() => onOpen("verdicts")}>
        <NormativeClearanceBadge value={result.normative_clearance as NormativeClearance} />
      </BadgeRegion>
      {result.refusal_emitted ? (
        <button
          type="button"
          onClick={() => onOpen("verdicts")}
          className="rounded border border-[var(--color-clearance-suppressed)] px-2 py-1 text-xs text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          Refusal
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => onOpen("metadata")}
        className="rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        {result.checkpoint_emitted ? "Checkpoint" : "No checkpoint"}
      </button>
      <button
        type="button"
        onClick={() => onOpen("metadata")}
        className="rounded border border-[var(--color-state-warning-border)] px-2 py-1 text-xs text-[var(--color-state-warning-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        Runtime Turn
      </button>
      {result.proposal_candidates.length > 0 ? (
        <BadgeRegion label="Open proposal candidates" onClick={() => onOpen("proposals")}>
          <ReviewStateBadge value={ReviewState.PENDING} />
        </BadgeRegion>
      ) : null}
      {result.trace_hash ? (
        <span onClick={() => onOpen("trace")}>
          <DigestBadge digest={result.trace_hash.replace("sha256:", "")} />
        </span>
      ) : null}
    </div>
  );
}
