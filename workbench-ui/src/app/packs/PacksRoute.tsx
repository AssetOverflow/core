import { useEffect, useMemo, useState } from "react";
import { Eye } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { usePack, usePacks } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TruncatedCell } from "../../design/components/TruncatedCell";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { TreeView } from "../../design/components/TreeView/TreeView";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { PackDetail, PackSummary } from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvidenceSubject } from "../evidenceContext";

const PACK_TABS: readonly Tab[] = [
  { id: "manifest", label: "Manifest" },
  { id: "checksums", label: "Checksums" },
  { id: "raw", label: "Raw" },
];

const SOURCE_LABEL: Record<string, string> = {
  language_pack: "Language pack",
  runtime_pack: "Runtime pack",
};

function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Packs request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 text-xs text-[var(--color-text-secondary)]">
      {children}
    </span>
  );
}

function PackRow({
  pack,
  selected,
  focused,
  onSelect,
}: {
  pack: PackSummary;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      } ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] pl-[10px]"
          : focused
            ? "border-l-2 border-l-[var(--color-focus-ring)] pl-[10px]"
            : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="min-w-0">
        <span className="block min-w-0">
          <TruncatedCell
            value={pack.pack_id}
            label="pack id"
            mono
            className="text-sm text-[var(--color-text-primary)]"
          />
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
          <span>{sourceLabel(pack.source)}</span>
          {pack.version ? (
            <>
              <span aria-hidden className="text-[var(--color-text-muted)]">·</span>
              <span className="font-mono">{pack.version}</span>
            </>
          ) : null}
          {pack.language ? <span className="text-[var(--color-text-muted)]">{pack.language}</span> : null}
          {pack.modality ? <span className="text-[var(--color-text-muted)]">{pack.modality}</span> : null}
        </span>
      </span>
      <span className="justify-self-end">
        {pack.determinism_class ? <Pill>{pack.determinism_class}</Pill> : null}
      </span>
    </div>
  );
}

function ChecksumsTab({ detail }: { detail: PackDetail }) {
  const manifestDigest = digestPayload(detail.manifest_digest);
  const declared = digestPayload(detail.checksum);
  const fieldRows = Object.entries(detail.checksums).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="grid gap-4">
      <MetadataTable
        rows={[
          {
            key: "manifest_digest",
            value: manifestDigest ? (
              <DigestBadge digest={manifestDigest} truncate={16} />
            ) : (
              "not recorded"
            ),
          },
          {
            key: "checksum",
            value: declared ? <DigestBadge digest={declared} truncate={16} /> : "not declared",
          },
        ]}
      />
      <section>
        <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
          Manifest-declared checksums
        </h3>
        {fieldRows.length === 0 ? (
          <p className="m-0 text-sm text-[var(--color-text-secondary)]">
            This manifest declares no per-field checksums.
          </p>
        ) : (
          <MetadataTable
            rows={fieldRows.map(([field, value]) => ({
              key: field,
              value: <DigestBadge digest={digestPayload(value) ?? value} truncate={16} />,
            }))}
          />
        )}
      </section>
    </div>
  );
}

function RawTab({ detail }: { detail: PackDetail }) {
  const [expanded, setExpanded] = useState(false);
  return expanded ? (
    <StableJsonViewer source={JSON.stringify(detail, null, 2)} />
  ) : (
    <div className="grid justify-items-start gap-2">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        Raw pack JSON is collapsed by default.
      </p>
      <Button type="button" variant="quiet" onClick={() => setExpanded(true)}>
        <Eye size={14} aria-hidden />
        Expand raw JSON
      </Button>
    </div>
  );
}

function PackDetailPanel({ detail }: { detail: PackDetail }) {
  const [activeTab, setActiveTab] = useState("manifest");
  return (
    <Panel
      title={detail.pack_id}
      toolbar={<Pill>{sourceLabel(detail.source)}</Pill>}
    >
      <TabBar tabs={PACK_TABS} activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "manifest" ? (
          <TreeView data={detail.manifest} ariaLabel={`${detail.pack_id} manifest`} />
        ) : null}
        {activeTab === "checksums" ? <ChecksumsTab detail={detail} /> : null}
        {activeTab === "raw" ? <RawTab detail={detail} /> : null}
      </TabBar>
    </Panel>
  );
}

export function PacksRoute() {
  const { packId } = useParams();
  const selectedPackId = packId && packId.length > 0 ? packId : null;
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();
  const [search, setSearch] = useState("");

  const packsQuery = usePacks();
  const packQuery = usePack(selectedPackId);

  const packs = packsQuery.data ?? [];
  const filteredPacks = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return packs;
    return packs.filter(
      (pack) =>
        pack.pack_id.toLowerCase().includes(q) ||
        sourceLabel(pack.source).toLowerCase().includes(q) ||
        (pack.language ?? "").toLowerCase().includes(q),
    );
  }, [search, packs]);

  useEffect(() => {
    if (selectedPackId === null) return;
    setSubject({ kind: "pack", packId: selectedPackId, data: packQuery.data });
  }, [selectedPackId, setSubject, packQuery.data]);

  function selectPack(pack: PackSummary) {
    const subject = { kind: "pack" as const, packId: pack.pack_id };
    const path = subjectToUrl(subject);
    navigate(path, { replace: true });
    pushRecentItem({ label: pack.pack_id, path });
  }

  if (packsQuery.isLoading) {
    return <LoadingState label="Loading packs..." />;
  }

  if (packsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(packsQuery.error)}
        mutationStatus="No packs mutation occurred."
        reproducer="curl /packs"
        retrySafety="Retry: safe"
      />
    );
  }

  if (packs.length === 0) {
    return (
      <EmptyState
        statement="No packs discovered."
        nextAction={{ kind: "cli", command: "core pack validate <path>" }}
      />
    );
  }

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="packs" defaultSplit={38} minSize={320}>
        <Panel title="Packs">
          <div className="grid min-h-0 gap-3">
            <SearchInput
              placeholder="Filter by pack, source, or language"
              value={search}
              onChange={setSearch}
            />
            {filteredPacks.length === 0 ? (
              <EmptyState
                statement="No packs match this filter."
                nextAction={{ kind: "cli", command: "core pack validate <path>" }}
              />
            ) : (
              <VirtualizedList
                ariaLabel="Packs"
                estimateSize={76}
                getKey={(pack) => pack.pack_id}
                height="calc(100vh - 14rem)"
                initialRect={{ width: 480, height: 560 }}
                items={filteredPacks}
                onActivate={(pack) => selectPack(pack)}
                renderItem={(pack, _index, focused) => (
                  <PackRow
                    pack={pack}
                    selected={pack.pack_id === selectedPackId}
                    focused={focused}
                    onSelect={() => selectPack(pack)}
                  />
                )}
              />
            )}
          </div>
        </Panel>

        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedPackId === null ? (
            <EmptyState
              statement="Select a pack to inspect its manifest, checksums, and provenance."
              nextAction={{ kind: "cli", command: "core pack validate <path>" }}
            />
          ) : packQuery.isLoading ? (
            <LoadingState label="Loading pack detail..." />
          ) : packQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(packQuery.error)}
              mutationStatus="No packs mutation occurred."
              reproducer={`curl /packs/${selectedPackId}`}
              retrySafety="Retry: safe"
            />
          ) : packQuery.data ? (
            <PackDetailPanel detail={packQuery.data} />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
