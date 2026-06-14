import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import {
  useLogosPackOverview,
  useLogosPacks,
  useLogosPackSafety,
} from "../../api/queries";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import {
  SafetyVerdict as BadgeSafetyVerdict,
  SafetyVerdictBadge,
} from "../../design/components/badges";
import type {
  LogosAlignmentTargetIssue,
  LogosMorphologyLinkIssue,
  LogosPackOverview,
  LogosPackSummary,
  LogosSafetyReport,
  SafetyVerdict,
} from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvidenceSubject } from "../evidenceContext";

const LOGOS_TABS: readonly Tab[] = [
  { id: "overview", label: "Overview" },
  { id: "identity", label: "Identity" },
  { id: "safety", label: "Safety" },
];

const ROLE_ORDER = ["depth_root", "depth_relation", "logos-cognition", "other"] as const;

const ROLE_LABELS: Record<string, string> = {
  depth_root: "Depth root",
  depth_relation: "Depth relation",
  "logos-cognition": "Logos cognition",
  other: "Other Logos packs",
};

const TRI_LANGUAGE = [
  {
    id: "en",
    label: "English",
    role: "operational articulation",
  },
  {
    id: "he",
    label: "Hebrew",
    role: "depth-root compression",
  },
  {
    id: "grc",
    label: "Koine Greek",
    role: "depth-relation precision",
  },
] as const;

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError
    ? error.message
    : "CORE-Logos request failed.";
}

function safetyVerdict(value: SafetyVerdict): BadgeSafetyVerdict {
  return value as BadgeSafetyVerdict;
}

function roleKey(pack: LogosPackSummary): (typeof ROLE_ORDER)[number] {
  if (pack.role === "logos-cognition" || pack.pack_id.includes("cognition")) {
    return "logos-cognition";
  }
  if (pack.role === "depth_root" || pack.role === "depth_relation") {
    return pack.role;
  }
  return "other";
}

function roleLabel(role: string | null): string {
  if (!role) return "not declared";
  return ROLE_LABELS[role] ?? role.replaceAll("_", " ");
}

function languageLabel(language: string | null): string {
  if (language === "he") return "Hebrew";
  if (language === "grc") return "Koine Greek";
  if (language === "en") return "English";
  return language ?? "not declared";
}

function CountBadge({ label, value }: { label: string; value: number }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 text-xs text-[var(--color-text-secondary)]">
      <span className="font-mono text-[var(--color-text-primary)]">{value}</span>
      <span className="ml-1">{label}</span>
    </span>
  );
}

function StatusPill({
  tone,
  children,
}: {
  tone: "neutral" | "warning" | "danger";
  children: ReactNode;
}) {
  const className =
    tone === "warning"
      ? "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] text-[var(--color-state-warning-text)]"
      : tone === "danger"
        ? "border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] text-[var(--color-state-danger-text)]"
        : "border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)]";
  return (
    <span className={`inline-flex h-6 items-center rounded-md border px-2 text-xs ${className}`}>
      {children}
    </span>
  );
}

function PackRow({
  pack,
  selected,
  onSelect,
}: {
  pack: LogosPackSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        onSelect();
      }}
      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] bg-[var(--color-selected-bg)] pl-[10px]"
          : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate font-mono text-sm text-[var(--color-text-primary)]">
          {pack.pack_id}
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
          <span>{roleLabel(pack.role)}</span>
          <span aria-hidden className="text-[var(--color-text-muted)]">
            ·
          </span>
          <span>{languageLabel(pack.language)}</span>
          {pack.script ? <span>{pack.script}</span> : null}
        </span>
        <span className="mt-2 flex flex-wrap gap-1.5">
          <CountBadge label="lex" value={pack.lexicon_count} />
          <CountBadge label="gloss" value={pack.gloss_count} />
          <CountBadge label="morph" value={pack.morphology_count} />
          <CountBadge label="align" value={pack.alignment_edge_count} />
          <CountBadge label="holonomy" value={pack.holonomy_case_count} />
        </span>
      </span>
      <span
        className="justify-self-end"
        onClick={(event) => event.stopPropagation()}
      >
        <SafetyVerdictBadge value={safetyVerdict(pack.safety_status)} />
      </span>
    </div>
  );
}

function PackUniverse({
  packs,
  selectedPackId,
  onSelect,
}: {
  packs: readonly LogosPackSummary[];
  selectedPackId: string | null;
  onSelect: (pack: LogosPackSummary) => void;
}) {
  const groups = useMemo(() => {
    const byRole = new Map<(typeof ROLE_ORDER)[number], LogosPackSummary[]>(
      ROLE_ORDER.map((role) => [role, []]),
    );
    for (const pack of packs) byRole.get(roleKey(pack))!.push(pack);
    return ROLE_ORDER.map((role) => ({
      role,
      packs: byRole.get(role)!.toSorted((a, b) => a.pack_id.localeCompare(b.pack_id)),
    })).filter((group) => group.packs.length > 0);
  }, [packs]);

  return (
    <Panel title="Pack Universe">
      <div className="grid min-h-0 gap-4">
        {groups.map((group) => (
          <section key={group.role} aria-labelledby={`logos-group-${group.role}`}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3
                id={`logos-group-${group.role}`}
                className="m-0 text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                {ROLE_LABELS[group.role]}
              </h3>
              <CountBadge label="packs" value={group.packs.length} />
            </div>
            <div className="overflow-hidden rounded-md border border-[var(--color-border-subtle)]">
              {group.packs.map((pack) => (
                <PackRow
                  key={pack.pack_id}
                  pack={pack}
                  selected={pack.pack_id === selectedPackId}
                  onSelect={() => onSelect(pack)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </Panel>
  );
}

function OverviewTab({ overview }: { overview: LogosPackOverview }) {
  const counts = [
    ["lexicon", overview.lexicon_count],
    ["glosses", overview.gloss_count],
    ["morphology", overview.morphology_count],
    ["frames", overview.frame_count],
    ["compositions", overview.composition_count],
    ["alignment_edges", overview.alignment_edge_count],
  ] as const;

  return (
    <div className="grid gap-4">
      <section className="grid gap-3 sm:grid-cols-3">
        {TRI_LANGUAGE.map((item) => {
          const active =
            overview.language === item.id ||
            (item.id === "he" && overview.role === "depth_root") ||
            (item.id === "grc" && overview.role === "depth_relation");
          return (
            <div
              key={item.id}
              className={`rounded-md border p-3 ${
                active
                  ? "border-[var(--color-focus-ring)] bg-[var(--color-surface-inset)]"
                  : "border-[var(--color-border-subtle)]"
              }`}
            >
              <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
                {item.label}
              </h3>
              <p className="m-0 mt-1 text-xs text-[var(--color-text-secondary)]">
                {item.role}
              </p>
            </div>
          );
        })}
      </section>

      <MetadataTable
        rows={[
          { key: "role", value: roleLabel(overview.role) },
          { key: "language", value: languageLabel(overview.language) },
          { key: "script", value: overview.script ?? "not declared" },
          { key: "version", value: overview.version ?? "not declared", mono: true },
          {
            key: "determinism",
            value: overview.determinism_class ?? "not declared",
          },
          {
            key: "gate",
            value: overview.gate_engaged ? "engaged" : "not engaged",
          },
          { key: "OOV", value: overview.oov_policy ?? "not declared" },
          {
            key: "safety",
            value: <SafetyVerdictBadge value={safetyVerdict(overview.safety_status)} />,
          },
        ]}
      />

      <section className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {counts.map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--color-border-subtle)] p-3"
          >
            <div className="font-mono text-lg text-[var(--color-text-primary)]">
              {value}
            </div>
            <div className="text-xs text-[var(--color-text-secondary)]">{label}</div>
          </div>
        ))}
        <div className="rounded-md border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-3">
          <div className="font-mono text-lg text-[var(--color-state-warning-text)]">
            {overview.holonomy_case_count}
          </div>
          <div className="text-xs text-[var(--color-state-warning-text)]">
            holonomy_cases · missing_evidence
          </div>
        </div>
      </section>
    </div>
  );
}

function IdentityTab({ overview }: { overview: LogosPackOverview }) {
  return (
    <div className="grid gap-4">
      <MetadataTable
        rows={[
          { key: "pack_id", value: overview.pack_id, mono: true, copyable: true },
          { key: "manifest_path", value: overview.manifest_path, mono: true, copyable: true },
          {
            key: "manifest_digest",
            value: overview.manifest_digest,
            mono: true,
            copyable: true,
          },
          {
            key: "source_manifest",
            value: overview.source_manifest ?? "not declared",
            mono: overview.source_manifest !== null,
          },
          {
            key: "normalization",
            value: overview.normalization_policy ?? "not declared",
          },
          { key: "known_gaps", value: overview.known_gaps.length.toString(), mono: true },
        ]}
      />
      <section>
        <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
          Raw overview projection
        </h3>
        <StableJsonViewer source={JSON.stringify(overview, null, 2)} />
      </section>
    </div>
  );
}

function IssueList({
  title,
  empty,
  items,
}: {
  title: string;
  empty: string;
  items: readonly ReactNode[];
}) {
  return (
    <section className="rounded-md border border-[var(--color-border-subtle)] p-3">
      <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
        {title}
      </h3>
      {items.length > 0 ? (
        <div className="grid gap-2">{items}</div>
      ) : (
        <p className="m-0 text-sm text-[var(--color-text-secondary)]">{empty}</p>
      )}
    </section>
  );
}

function MorphologyIssue({ issue }: { issue: LogosMorphologyLinkIssue }) {
  return (
    <div className="rounded border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-2 text-xs text-[var(--color-state-warning-text)]">
      <span className="font-mono">{issue.entry_id}</span>
      <span> references missing morphology </span>
      <span className="font-mono">{issue.morphology_id}</span>
    </div>
  );
}

function AlignmentIssue({ issue }: { issue: LogosAlignmentTargetIssue }) {
  return (
    <div className="rounded border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-2 text-xs text-[var(--color-state-warning-text)]">
      <span className="font-mono">{issue.edge_id}</span>
      <span> invalid target </span>
      <span className="font-mono">{issue.target_id}</span>
      <span> via {issue.relation}</span>
      {issue.target_pack_id ? (
        <span>
          {" "}
          in <span className="font-mono">{issue.target_pack_id}</span>
        </span>
      ) : null}
    </div>
  );
}

function SafetyTab({ report }: { report: LogosSafetyReport }) {
  const epistemicRows = Object.entries(report.epistemic_status_counts).sort(([a], [b]) =>
    a.localeCompare(b),
  );
  return (
    <div className="grid gap-4">
      <MetadataTable
        rows={[
          {
            key: "verdict",
            value: <SafetyVerdictBadge value={safetyVerdict(report.verdict)} />,
          },
          {
            key: "checksum",
            value: <SafetyVerdictBadge value={safetyVerdict(report.checksum_status)} />,
          },
          {
            key: "domain_contract",
            value: (
              <SafetyVerdictBadge value={safetyVerdict(report.domain_contract_status)} />
            ),
          },
          {
            key: "missing_holonomy_refs",
            value: (
              <SafetyVerdictBadge value={safetyVerdict(report.missing_holonomy_refs)} />
            ),
          },
          {
            key: "OOV policy",
            value: report.oov_policy_ok ? (
              <StatusPill tone="neutral">ok</StatusPill>
            ) : (
              <StatusPill tone="danger">failed</StatusPill>
            ),
          },
          {
            key: "gate policy",
            value: report.gate_policy_ok ? (
              <StatusPill tone="neutral">ok</StatusPill>
            ) : (
              <StatusPill tone="danger">failed</StatusPill>
            ),
          },
          {
            key: "path safety",
            value: report.path_safety_ok ? (
              <StatusPill tone="neutral">ok</StatusPill>
            ) : (
              <StatusPill tone="danger">failed</StatusPill>
            ),
          },
        ]}
      />

      <section className="grid gap-3 md:grid-cols-2">
        <IssueList
          title="Checksum errors"
          empty="none recorded"
          items={report.checksum_errors.map((item) => (
            <div
              key={item}
              className="rounded border border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] p-2 text-xs text-[var(--color-state-danger-text)]"
            >
              {item}
            </div>
          ))}
        />
        <IssueList
          title="Known gaps"
          empty="none recorded"
          items={report.known_gaps.map((item) => (
            <div
              key={item}
              className="rounded border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] p-2 text-xs text-[var(--color-state-warning-text)]"
            >
              {item}
            </div>
          ))}
        />
        <IssueList
          title="Dangling morphology links"
          empty="none recorded"
          items={report.dangling_morphology_links.map((issue) => (
            <MorphologyIssue key={`${issue.entry_id}:${issue.morphology_id}`} issue={issue} />
          ))}
        />
        <IssueList
          title="Invalid alignment targets"
          empty="none recorded"
          items={report.invalid_alignment_targets.map((issue) => (
            <AlignmentIssue key={issue.edge_id} issue={issue} />
          ))}
        />
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-[var(--color-border-subtle)] p-3">
          <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
            Epistemic counts
          </h3>
          {epistemicRows.length === 0 ? (
            <p className="m-0 text-sm text-[var(--color-text-secondary)]">none recorded</p>
          ) : (
            <MetadataTable
              rows={epistemicRows.map(([key, value]) => ({
                key,
                value: String(value),
                mono: true,
              }))}
            />
          )}
        </div>
        <div className="rounded-md border border-[var(--color-border-subtle)] p-3">
          <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
            Epistemic entry sets
          </h3>
          <MetadataTable
            rows={[
              {
                key: "speculative",
                value: String(report.speculative_entries.length),
                mono: true,
              },
              {
                key: "contested",
                value: String(report.contested_entries.length),
                mono: true,
              },
              {
                key: "falsified",
                value: String(report.falsified_entries.length),
                mono: true,
              },
            ]}
          />
        </div>
      </section>
    </div>
  );
}

function StatusStrip({
  selectedPackId,
  overview,
  safety,
}: {
  selectedPackId: string | null;
  overview?: LogosPackOverview;
  safety?: LogosSafetyReport;
}) {
  const selected = overview?.pack_id ?? selectedPackId ?? "no pack selected";
  const checksum = safety?.checksum_status ?? "unknown";
  const gateOov = overview
    ? `gate ${overview.gate_engaged ? "engaged" : "not engaged"} / OOV ${
        overview.oov_policy ?? "unknown"
      }`
    : "gate/OOV unknown";
  return (
    <footer className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--color-border-subtle)] pt-2 text-xs text-[var(--color-text-secondary)]">
      <span className="font-mono text-[var(--color-text-primary)]">{selected}</span>
      <span aria-hidden>·</span>
      <span>checksum {checksum}</span>
      <span aria-hidden>·</span>
      <span>{gateOov}</span>
      <span aria-hidden>·</span>
      <span>proposal mode: none — read-only</span>
    </footer>
  );
}

function Workspace({
  selectedPackId,
  overview,
  overviewLoading,
  overviewError,
  safety,
  safetyLoading,
  safetyError,
}: {
  selectedPackId: string | null;
  overview?: LogosPackOverview;
  overviewLoading: boolean;
  overviewError: unknown;
  safety?: LogosSafetyReport;
  safetyLoading: boolean;
  safetyError: unknown;
}) {
  const [activeTab, setActiveTab] = useState("overview");

  if (selectedPackId === null) {
    return (
      <EmptyState
        statement="Select a CORE-Logos pack to inspect overview, identity, and safety evidence."
        nextAction={{ kind: "cli", command: "core pack validate <path>" }}
      />
    );
  }

  if (overviewLoading) {
    return <LoadingState label="Loading CORE-Logos pack..." />;
  }

  if (overviewError) {
    return (
      <ErrorState
        whatFailed={errorMessage(overviewError)}
        mutationStatus="No Logos mutation occurred."
        reproducer={`curl /logos/packs/${selectedPackId}`}
        retrySafety="Retry: safe"
      />
    );
  }

  if (!overview) return null;

  return (
    <Panel
      title={overview.pack_id}
      toolbar={<SafetyVerdictBadge value={safetyVerdict(overview.safety_status)} />}
    >
      <TabBar tabs={LOGOS_TABS} activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "overview" ? <OverviewTab overview={overview} /> : null}
        {activeTab === "identity" ? <IdentityTab overview={overview} /> : null}
        {activeTab === "safety" ? (
          safetyLoading ? (
            <LoadingState label="Loading CORE-Logos safety..." />
          ) : safetyError ? (
            <ErrorState
              whatFailed={errorMessage(safetyError)}
              mutationStatus="No Logos mutation occurred."
              reproducer={`curl /logos/packs/${selectedPackId}/safety`}
              retrySafety="Retry: safe"
            />
          ) : safety ? (
            <SafetyTab report={safety} />
          ) : null
        ) : null}
      </TabBar>
    </Panel>
  );
}

export function LogosRoute() {
  const { logosPackId } = useParams();
  const selectedPackId = logosPackId && logosPackId.length > 0 ? logosPackId : null;
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();

  const packsQuery = useLogosPacks();
  const overviewQuery = useLogosPackOverview(selectedPackId);
  const safetyQuery = useLogosPackSafety(selectedPackId);

  useEffect(() => {
    if (selectedPackId === null) return;
    setSubject({
      kind: "logos_pack",
      packId: selectedPackId,
      data: overviewQuery.data
        ? {
            ...overviewQuery.data,
            checksum_status: safetyQuery.data?.checksum_status ?? null,
          }
        : undefined,
    });
  }, [selectedPackId, setSubject, overviewQuery.data, safetyQuery.data]);

  function selectPack(pack: LogosPackSummary) {
    const subject = { kind: "logos_pack" as const, packId: pack.pack_id };
    const path = subjectToUrl(subject);
    navigate(path, { replace: true });
    pushRecentItem({ label: pack.pack_id, path });
  }

  if (packsQuery.isLoading) {
    return <LoadingState label="Loading CORE-Logos packs..." />;
  }

  if (packsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(packsQuery.error)}
        mutationStatus="No Logos mutation occurred."
        reproducer="curl /logos/packs"
        retrySafety="Retry: safe"
      />
    );
  }

  const packs = packsQuery.data ?? [];
  if (packs.length === 0) {
    return (
      <EmptyState
        statement="No CORE-Logos packs discovered."
        nextAction={{ kind: "cli", command: "core pack validate <path>" }}
      />
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1">
        <SplitPane direction="horizontal" id="logos" defaultSplit={34} minSize={300}>
          <PackUniverse
            packs={packs}
            selectedPackId={selectedPackId}
            onSelect={selectPack}
          />
          <section className="h-full min-h-0 overflow-y-auto pl-3">
            <Workspace
              selectedPackId={selectedPackId}
              overview={overviewQuery.data}
              overviewLoading={overviewQuery.isLoading}
              overviewError={overviewQuery.isError ? overviewQuery.error : null}
              safety={safetyQuery.data}
              safetyLoading={safetyQuery.isLoading}
              safetyError={safetyQuery.isError ? safetyQuery.error : null}
            />
          </section>
        </SplitPane>
      </div>
      <StatusStrip
        selectedPackId={selectedPackId}
        overview={overviewQuery.data}
        safety={safetyQuery.data}
      />
    </div>
  );
}
