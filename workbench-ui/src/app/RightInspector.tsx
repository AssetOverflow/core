import { useEffect, useState } from "react";
import { useEvidenceSubject, type EvidenceSubject } from "./evidenceContext";
import { EvidenceChainRail } from "./EvidenceChainRail";
import { MetadataTable } from "../design/components/MetadataTable/MetadataTable";
import { DigestBadge } from "../design/components/DigestBadge/DigestBadge";
import { Timestamp } from "../design/components/Timestamp/Timestamp";
import {
  EpistemicStateBadge,
  GroundingSourceBadge,
  NormativeClearanceBadge,
  SafetyVerdictBadge,
  type EpistemicState,
  type GroundingSource,
  type NormativeClearance,
  type SafetyVerdict,
} from "../design/components/badges";
import type { LeewayEvidence } from "../types/api";

// Rendered when a subject was restored from a URL but its detail has not
// loaded in this session yet.  An honest absence state, not a guess.
function DetailNotLoaded() {
  return (
    <p className="m-0 text-xs text-[var(--color-text-muted)]">
      Detail not loaded in this session. Open the subject&apos;s route to load
      its evidence.
    </p>
  );
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function leewaySummary(value?: LeewayEvidence | null): string {
  if (!value) return "none recorded";
  const theta = value.theta === null ? "" : ` θ ${pct(value.theta)}`;
  return `${value.class_name} / ${value.license}${theta} / ${value.claim_disclosure}`;
}

function TurnInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "turn" }> }) {
  const { data } = subject;
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Turn #{subject.turnId}</h3>
        <DetailNotLoaded />
      </div>
    );
  }
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
          { key: "leeway", value: leewaySummary(data.leeway_evidence) },
        ]}
      />
    </div>
  );
}

function ProposalInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "proposal" }> }) {
  const { data } = subject;
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Proposal</h3>
        <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">{subject.proposalId}</p>
        <DetailNotLoaded />
      </div>
    );
  }
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Proposal</h3>
      <MetadataTable
        rows={[
          { key: "id", value: data.proposal_id, copyable: true, mono: true },
          ...("state" in data ? [{ key: "state", value: data.state }] : []),
          ...("source_kind" in data
            ? [{ key: "source", value: data.source_kind }]
            : [{ key: "source", value: `math / ${data.proposed_change_kind}` }]),
          ...("replay_equivalent" in data
            ? [
                {
                  key: "replay_eq",
                  value:
                    data.replay_equivalent === null
                      ? "unknown"
                      : data.replay_equivalent
                        ? "yes"
                        : "no",
                },
              ]
            : [{ key: "replay_hash", value: data.replay_equivalence_hash, mono: true }]),
          ...("suggested_cli" in data && data.suggested_cli
            ? [{ key: "CLI", value: data.suggested_cli, copyable: true, mono: true }]
            : []),
          ...("suggested_ratify_cli" in data && data.suggested_ratify_cli
            ? [{ key: "CLI", value: data.suggested_ratify_cli, copyable: true, mono: true }]
            : []),
          { key: "leeway", value: leewaySummary(data.leeway_evidence) },
        ]}
      />
    </div>
  );
}

function CalibrationInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "calibration_class" }>;
}) {
  const { data } = subject;
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Calibration Class
        </h3>
        <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
          {subject.className}
        </p>
        <DetailNotLoaded />
      </div>
    );
  }

  const license = data.serve_licensed
    ? "SERVE"
    : data.propose_licensed
      ? "PROPOSE"
      : "blocked";
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        Calibration Class
      </h3>
      <MetadataTable
        rows={[
          { key: "class", value: data.class_name, mono: true },
          { key: "correct", value: String(data.correct), mono: true },
          { key: "wrong", value: String(data.wrong), mono: true },
          { key: "refused", value: String(data.refused), mono: true },
          { key: "committed", value: String(data.committed), mono: true },
          { key: "coverage", value: pct(data.coverage), mono: true },
          { key: "Wilson floor", value: pct(data.reliability_floor), mono: true },
          {
            key: "PROPOSE",
            value: `${data.propose_licensed ? "licensed" : "blocked"} at θ ${pct(
              data.propose_required,
            )}`,
          },
          {
            key: "SERVE",
            value: `${data.serve_licensed ? "licensed" : "blocked"} at θ ${pct(
              data.serve_required,
            )}`,
          },
          { key: "license", value: license, mono: true },
          { key: "source", value: data.source_path, mono: true },
          {
            key: "digest",
            value: data.source_digest,
            mono: true,
            copyable: true,
          },
        ]}
      />
    </div>
  );
}

function RunInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "run" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Run</h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">{subject.sessionId}</p>
      {data ? (
        <MetadataTable
          rows={[
            ...(data.source ? [{ key: "source", value: data.source }] : []),
            { key: "checkpoint", value: data.checkpoint_present ? "present" : "not recorded" },
            ...(data.checkpoint_revision
              ? [{ key: "revision", value: data.checkpoint_revision, mono: true }]
              : []),
            ...(data.evidence_gap ? [{ key: "gap", value: data.evidence_gap }] : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function PackInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "pack" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Pack</h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">{subject.packId}</p>
      {data ? (
        <MetadataTable
          rows={[
            ...(data.checksum ? [{ key: "checksum", value: data.checksum, mono: true, copyable: true }] : []),
            ...(data.manifest_digest
              ? [{ key: "manifest", value: data.manifest_digest, mono: true, copyable: true }]
              : []),
            ...(data.determinism_class ? [{ key: "determinism", value: data.determinism_class }] : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function LogosPackInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "logos_pack" }>;
}) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        CORE-Logos Pack
      </h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
        {subject.packId}
      </p>
      {data ? (
        <MetadataTable
          rows={[
            ...(data.safety_status
              ? [
                  {
                    key: "safety",
                    value: (
                      <SafetyVerdictBadge value={data.safety_status as SafetyVerdict} />
                    ),
                  },
                ]
              : []),
            ...(data.checksum_status
              ? [
                  {
                    key: "checksum",
                    value: (
                      <SafetyVerdictBadge value={data.checksum_status as SafetyVerdict} />
                    ),
                  },
                ]
              : []),
            ...(data.manifest_digest
              ? [
                  {
                    key: "manifest",
                    value: data.manifest_digest,
                    mono: true,
                    copyable: true,
                  },
                ]
              : []),
            ...(data.role ? [{ key: "role", value: data.role }] : []),
            ...(data.language ? [{ key: "language", value: data.language }] : []),
            ...(typeof data.holonomy_case_count === "number"
              ? [
                  {
                    key: "holonomy",
                    value:
                      data.holonomy_case_count === 0
                        ? "0 / missing_evidence"
                        : String(data.holonomy_case_count),
                  },
                ]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function VaultEntryInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "vault_entry" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Vault Entry</h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">#{subject.entryIndex}</p>
      {data ? (
        <MetadataTable
          rows={[
            ...(data.epistemic_state ? [{ key: "epistemic", value: data.epistemic_state }] : []),
            ...(data.versor_digest
              ? [{ key: "versor", value: data.versor_digest, mono: true, copyable: true }]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function AuditEventInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "audit_event" }> }) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Audit Event</h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">{subject.eventId}</p>
      {data ? (
        <MetadataTable
          rows={[
            { key: "mutation_boundary", value: data.mutation_boundary ? "yes" : "no" },
            ...(data.payload_digest
              ? [{ key: "payload", value: data.payload_digest, mono: true, copyable: true }]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function ArtifactInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "artifact" }> }) {
  const { data } = subject;
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Artifact</h3>
        <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">{subject.artifactId}</p>
        <DetailNotLoaded />
      </div>
    );
  }
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
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Eval: {subject.lane}</h3>
        <DetailNotLoaded />
      </div>
    );
  }
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

  return (
    <div className="grid content-start gap-2">
      <EvidenceChainRail subject={subject} />
      <InspectorProjection subject={subject} />
    </div>
  );
}

function InspectorProjection({ subject }: { subject: EvidenceSubject }) {
  switch (subject.kind) {
    case "turn":
      return <TurnInspector subject={subject} />;
    case "proposal":
      return <ProposalInspector subject={subject} />;
    case "artifact":
      return <ArtifactInspector subject={subject} />;
    case "eval_result":
      return <EvalInspector subject={subject} />;
    case "run":
      return <RunInspector subject={subject} />;
    case "pack":
      return <PackInspector subject={subject} />;
    case "logos_pack":
      return <LogosPackInspector subject={subject} />;
    case "vault_entry":
      return <VaultEntryInspector subject={subject} />;
    case "audit_event":
      return <AuditEventInspector subject={subject} />;
    case "calibration_class":
      return <CalibrationInspector subject={subject} />;
    case "none":
      return <NoneInspector />;
  }
}

const COPY_FEEDBACK_MS = 2000;

export function RightInspector() {
  const { addressCopyCount } = useEvidenceSubject();
  const [showCopied, setShowCopied] = useState(false);

  // Transient inline confirmation for Cmd+Shift+C; confirmation only, never
  // audit context (per ADR-0162 no auto-dismissing audit events).
  useEffect(() => {
    if (addressCopyCount === 0) return;
    setShowCopied(true);
    const timer = setTimeout(() => setShowCopied(false), COPY_FEEDBACK_MS);
    return () => clearTimeout(timer);
  }, [addressCopyCount]);

  return (
    <aside
      data-region="inspector"
      className="flex h-full flex-col overflow-y-auto border-l border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-3"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Inspector
        </span>
        <span className="flex items-center gap-2">
          {showCopied && (
            <span
              data-testid="address-copied"
              className="text-[10px] font-semibold text-[var(--color-state-success-text)]"
            >
              Copied
            </span>
          )}
          <kbd className="rounded border border-[var(--color-border-subtle)] px-1 text-[10px] text-[var(--color-text-muted)]">
            ⌘I
          </kbd>
        </span>
      </div>
      <InspectorContent />
    </aside>
  );
}
