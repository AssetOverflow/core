import { useEffect, useState } from "react";
import { useEvidenceSubject, type EvidenceSubject } from "./evidenceContext";
import { EvidenceChainRail } from "./EvidenceChainRail";
import { MetadataTable, type MetadataRow } from "../design/components/MetadataTable/MetadataTable";
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
import { useVaultEntryRecall } from "../api/queries";

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

function LogosEntryInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "logos_entry" }>;
}) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        CORE-Logos Entry
      </h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
        {subject.packId} · {subject.entryId}
      </p>
      {data ? (
        <MetadataTable
          rows={[
            { key: "surface", value: data.surface },
            { key: "lemma", value: data.lemma },
            { key: "language", value: data.language },
            ...(data.pos ?? data.part_of_speech
              ? [{ key: "pos", value: (data.pos ?? data.part_of_speech) as string }]
              : []),
            ...(data.morphology_id
              ? [{ key: "morphology", value: data.morphology_id, mono: true }]
              : []),
            { key: "epistemic", value: data.epistemic_status },
            ...(data.semantic_domains.length > 0
              ? [{ key: "domains", value: data.semantic_domains.join(", ") }]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function LogosGlossInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "logos_gloss" }>;
}) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        CORE-Logos Gloss
      </h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
        {subject.packId} · {subject.glossId}
      </p>
      {data ? (
        <MetadataTable
          rows={[
            { key: "lemma", value: data.lemma },
            { key: "gloss", value: data.gloss },
            ...(data.pos ? [{ key: "pos", value: data.pos }] : []),
            ...(data.entry_ids.length > 0
              ? [{ key: "entries", value: data.entry_ids.join(", "), mono: true }]
              : []),
            ...(data.epistemic_status
              ? [{ key: "epistemic", value: data.epistemic_status }]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function LogosMorphologyInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "logos_morphology" }>;
}) {
  const { data } = subject;
  // Render the operator chain in schema order — ordering is load-bearing for
  // Semitic root / Koine grammar, never re-sorted.
  const chain = data
    ? [
        ...data.prefix_chain,
        ...(data.root ? [`√${data.root}`] : data.stem ? [data.stem] : []),
        ...data.suffix_chain,
      ].join(" · ")
    : "";
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        CORE-Logos Morphology
      </h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
        {subject.packId} · {subject.morphologyId}
      </p>
      {data ? (
        <MetadataTable
          rows={[
            { key: "surface", value: data.surface },
            { key: "lemma", value: data.lemma },
            { key: "language", value: data.language },
            ...(data.root ? [{ key: "root", value: data.root, mono: true }] : []),
            ...(chain ? [{ key: "chain", value: chain, mono: true }] : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

function LogosAlignmentEdgeInspector({
  subject,
}: {
  subject: Extract<EvidenceSubject, { kind: "logos_alignment_edge" }>;
}) {
  const { data } = subject;
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">
        CORE-Logos Alignment Edge
      </h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">
        {subject.packId} · {subject.edgeId}
      </p>
      {data ? (
        <MetadataTable
          rows={[
            { key: "source", value: data.source_id, mono: true },
            { key: "target", value: data.target_id, mono: true },
            { key: "relation", value: data.relation },
            { key: "weight", value: data.weight.toFixed(2), mono: true },
            {
              key: "target_pack",
              value: data.target_pack_id ?? "unresolved",
              mono: data.target_pack_id !== null,
            },
            {
              key: "target",
              value: data.invalid_target ? "invalid (dangling)" : "resolved",
            },
            ...(data.evidence_ids.length > 0
              ? [{ key: "evidence", value: data.evidence_ids.join(", "), mono: true }]
              : []),
          ]}
        />
      ) : (
        <DetailNotLoaded />
      )}
    </div>
  );
}

// Honest absence for a core identity field that every session entry should
// carry — shown rather than silently dropped.
const NOT_RECORDED = "not recorded";

// Read one metadata field as a display string, or null when genuinely absent.
// The vault metadata dict is open; values are strings/numbers/booleans (turn,
// role, energy_*, corrected, propositional_form, ...).
function vaultMetaValue(
  metadata: Record<string, unknown> | undefined,
  key: string,
): string | null {
  if (!metadata) return null;
  const value = metadata[key];
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

// Deterministic, recursively key-sorted JSON for the raw drawer — same bytes
// every render regardless of backend key order, so the drawer never churns.
function stableJson(value: unknown): string {
  return JSON.stringify(
    value,
    (_key, val) =>
      val && typeof val === "object" && !Array.isArray(val)
        ? Object.fromEntries(
            Object.keys(val as Record<string, unknown>)
              .sort()
              .map((k) => [k, (val as Record<string, unknown>)[k]]),
          )
        : val,
    2,
  );
}

// Optional rows surfaced only when the (open) metadata actually carries them —
// these don't exist on every entry, so absence is correct, not "not recorded".
const VAULT_OPTIONAL_FIELDS: { key: string; mono?: boolean; copyable?: boolean }[] = [
  { key: "corrected" },
  { key: "energy_class" },
  { key: "energy_raw", mono: true },
  { key: "coherence_residual", mono: true },
  { key: "promotion_certificate_digest", mono: true, copyable: true },
];

function VaultEntryInspector({ subject }: { subject: Extract<EvidenceSubject, { kind: "vault_entry" }> }) {
  const { data } = subject;
  const handle = `vault:${subject.entryIndex}`;
  if (!data) {
    return (
      <div className="grid gap-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Vault Entry</h3>
        <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">#{subject.entryIndex}</p>
        <DetailNotLoaded />
      </div>
    );
  }

  const metadata = data.metadata;
  // Headline only a string propositional_form; structured forms stay in the drawer.
  const propositionalForm =
    metadata && typeof metadata.propositional_form === "string"
      ? metadata.propositional_form
      : null;

  // Core identity rows — always shown, with honest "not recorded" when absent.
  // epistemic_status (storage tier) and epistemic_state (trust display) are
  // distinct fields and must read distinctly.
  const coreRows: MetadataRow[] = [
    { key: "epistemic_status", value: data.epistemic_status ?? NOT_RECORDED },
    { key: "epistemic_state", value: data.epistemic_state ?? NOT_RECORDED },
    { key: "turn", value: vaultMetaValue(metadata, "turn") ?? NOT_RECORDED, mono: true },
    { key: "role", value: vaultMetaValue(metadata, "role") ?? NOT_RECORDED },
  ];

  const optionalRows: MetadataRow[] = VAULT_OPTIONAL_FIELDS.flatMap(({ key, mono, copyable }) => {
    const value = vaultMetaValue(metadata, key);
    return value === null ? [] : [{ key, value, mono, copyable }];
  });

  // Copyable handles: the evidence address and the versor digest.
  const handleRows: MetadataRow[] = [
    { key: "handle", value: handle, mono: true, copyable: true },
    ...(data.versor_digest
      ? [{ key: "versor_digest", value: data.versor_digest, mono: true, copyable: true } as const]
      : []),
  ];

  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold text-[var(--color-text-secondary)]">Vault Entry</h3>
      <p className="m-0 font-mono text-xs text-[var(--color-text-primary)]">#{subject.entryIndex}</p>
      {propositionalForm ? (
        <p className="m-0 text-sm text-[var(--color-text-primary)] [text-wrap:balance]">
          {propositionalForm}
        </p>
      ) : null}
      <MetadataTable rows={[...coreRows, ...optionalRows, ...handleRows]} />
      {metadata && Object.keys(metadata).length > 0 ? (
        <details className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)]">
          <summary className="cursor-pointer px-3 py-2 text-xs text-[var(--color-text-secondary)]">
            Raw metadata
          </summary>
          <pre className="m-0 max-h-80 overflow-auto border-t border-[var(--color-border-subtle)] px-3 py-2 font-mono text-xs text-[var(--color-text-primary)]">
            {stableJson(metadata)}
          </pre>
        </details>
      ) : null}
      <VaultRecallSection entryIndex={subject.entryIndex} />
    </div>
  );
}

function formatCgaInner(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return Math.abs(value) < 1e-4 ? value.toExponential(2) : value.toPrecision(5);
}

// Exact-CGA recall evidence for a selected vault entry. Collapsed by default so
// the read-only recall fetch is opt-in (the hook lives in VaultRecallBody, which
// only mounts when expanded). Doctrine: "exact CGA recall" / cga_inner only —
// never similarity / relevance / cosine / ANN / approximate.
function VaultRecallSection({ entryIndex }: { entryIndex: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="grid gap-2">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="justify-self-start rounded-md border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
      >
        {open ? "Hide exact CGA recall" : "Show exact CGA recall"}
      </button>
      {open ? <VaultRecallBody entryIndex={entryIndex} /> : null}
    </div>
  );
}

function VaultRecallBody({ entryIndex }: { entryIndex: number }) {
  const recall = useVaultEntryRecall(entryIndex);

  if (recall.isPending) {
    return <p className="m-0 text-xs text-[var(--color-text-muted)]">Running exact CGA recall…</p>;
  }
  if (recall.isError || !recall.data) {
    return (
      <p className="m-0 text-xs text-[var(--color-text-muted)] [text-wrap:balance]">
        {recall.error?.message ?? "Exact CGA recall evidence is unavailable for this entry."}
      </p>
    );
  }

  const data = recall.data;
  const handleRows: MetadataRow[] = [
    ...(data.query_versor_digest
      ? [{ key: "query_versor", value: data.query_versor_digest, mono: true, copyable: true } as const]
      : []),
    {
      key: "self_recall",
      value: data.self_hit_found
        ? `recalls itself at rank ${data.self_hit_rank}`
        : "not within top results",
    },
    { key: "exact_cga", value: data.exact_cga ? "yes" : "no" },
  ];

  return (
    <div className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3">
      <p className="m-0 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">
        CORE&apos;s exact <span className="font-mono">cga_inner</span> recall over the persisted
        vault snapshot, querying with this entry&apos;s own stored versor. Read-only — the live
        runtime is untouched.
      </p>
      <MetadataTable rows={handleRows} />
      <p className="m-0 text-[11px] italic text-[var(--color-text-muted)] [text-wrap:balance]">
        Rank is CORE&apos;s actual recall order. An exact byte-identical self-match is promoted to
        the front — stored versors are CGA null vectors, so the self{" "}
        <span className="font-mono">cga_inner</span> is ~0; identity is proven by exact
        byte-equality, not a maximal value.
      </p>
      <ul className="m-0 grid list-none gap-1 p-0">
        {data.hits.map((hit) => (
          <li
            key={hit.rank}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-2 font-mono text-xs text-[var(--color-text-primary)]"
          >
            <span className="text-[var(--color-text-muted)]">#{hit.rank}</span>
            <span>
              vault:{hit.entry_index}
              {hit.exact_self_match ? (
                <span className="ml-1 text-[var(--color-text-secondary)]">(exact match)</span>
              ) : null}
            </span>
            <span className="text-[var(--color-text-secondary)]">
              cga_inner {formatCgaInner(hit.cga_inner)}
            </span>
          </li>
        ))}
      </ul>
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
    case "logos_entry":
      return <LogosEntryInspector subject={subject} />;
    case "logos_gloss":
      return <LogosGlossInspector subject={subject} />;
    case "logos_morphology":
      return <LogosMorphologyInspector subject={subject} />;
    case "logos_alignment_edge":
      return <LogosAlignmentEdgeInspector subject={subject} />;
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
