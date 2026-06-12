import { useEvidenceSubject, type EvidenceSubject } from "./evidenceContext";
import { MetadataTable } from "../design/components/MetadataTable/MetadataTable";
import { DigestBadge } from "../design/components/DigestBadge/DigestBadge";
import { Timestamp } from "../design/components/Timestamp/Timestamp";
import {
  EpistemicStateBadge,
  GroundingSourceBadge,
  NormativeClearanceBadge,
  type EpistemicState,
  type GroundingSource,
  type NormativeClearance,
} from "../design/components/badges";

function TurnInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "turn" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Turn #{subject.turnId}</h3>
      {data.trace_hash && (
        <DigestBadge digest={data.trace_hash.replace("sha256:", "")} truncate={12} />
      )}
      <MetadataTable
        rows={[
          {
            key: "surface",
            value: data.surface.length > 80 ? `${data.surface.slice(0, 80)}...` : data.surface,
          },
          {
            key: "grounding",
            value: <GroundingSourceBadge value={data.grounding_source as GroundingSource} />,
          },
          {
            key: "epistemic",
            value: <EpistemicStateBadge value={data.epistemic_state as EpistemicState} />,
          },
          {
            key: "clearance",
            value: <NormativeClearanceBadge value={data.normative_clearance as NormativeClearance} />,
          },
          { key: "cost", value: `${data.turn_cost_ms}ms`, mono: true },
          { key: "refusal", value: data.refusal_emitted ? "yes" : "no" },
          { key: "hedge", value: data.hedge_injected ? "yes" : "no" },
        ]}
      />
    </div>
  );
}

function ProposalInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "proposal" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Proposal</h3>
      <MetadataTable
        rows={[
          { key: "id", value: data.proposal_id, copyable: true, mono: true },
          { key: "state", value: data.state },
          { key: "source", value: data.source_kind },
          { key: "replay_eq", value: data.replay_equivalent === null ? "unknown" : data.replay_equivalent ? "yes" : "no" },
          ...(data.suggested_cli ? [{ key: "CLI", value: data.suggested_cli, copyable: true, mono: true }] : []),
        ]}
      />
    </div>
  );
}

function ArtifactInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "artifact" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Artifact</h3>
      {data.digest && <DigestBadge digest={data.digest} truncate={12} />}
      <MetadataTable
        rows={[
          { key: "id", value: data.artifact_id, copyable: true, mono: true },
          { key: "kind", value: data.kind },
          { key: "path", value: data.path, mono: true },
          { key: "content_type", value: data.content_type },
          ...(data.created_at ? [{ key: "created", value: <Timestamp iso={data.created_at} /> }] : []),
        ]}
      />
    </div>
  );
}

function EvalInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "eval_result" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Eval: {data.lane}</h3>
      <MetadataTable
        rows={[
          { key: "lane", value: data.lane },
          { key: "version", value: data.version, mono: true },
          { key: "split", value: data.split },
          {
            key: "result",
            value: data.passed === null ? "pending" : data.passed ? "passed" : "failed",
          },
          ...(data.source_digest ? [{ key: "digest", value: data.source_digest, copyable: true, mono: true }] : []),
        ]}
      />
    </div>
  );
}

function NoneInspector() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-muted)]">
      <p>Select an item to inspect its evidence.</p>
    </div>
  );
}

function InspectorContent() {
  const { subject } = useEvidenceSubject();

  switch (subject.kind) {
    case "turn":
      return <TurnInspector subject={subject} />;
    case "proposal":
      return <ProposalInspector subject={subject} />;
    case "artifact":
      return <ArtifactInspector subject={subject} />;
    case "eval_result":
      return <EvalInspector subject={subject} />;
    case "none":
      return <NoneInspector />;
  }
}

export function RightInspector() {
  return (
    <aside
      data-region="inspector"
      className="flex h-full flex-col overflow-y-auto border-l border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-3"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Inspector
        </span>
        <kbd className="rounded border border-[var(--color-border-subtle)] px-1 text-[10px] text-[var(--color-text-muted)]">
          ⌘I
        </kbd>
      </div>
      <InspectorContent />
    </aside>
  );
}
