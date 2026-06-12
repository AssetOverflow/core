import { useEffect, useState } from "react";
import { StableJsonViewer } from "../design/components/StableJsonViewer";
import {
  EpistemicState,
  EpistemicStateBadge,
  GroundingSource,
  GroundingSourceBadge,
  NormativeClearance,
  NormativeClearanceBadge,
  ReviewState,
  ReviewStateBadge,
  TraceHashBadge,
} from "../design/components/badges";
import { Button } from "../design/components/primitives/Button";
import { CommandPalette } from "../design/components/primitives/CommandPalette";
import { EmptyState } from "../design/components/states/EmptyState";
import { ErrorState } from "../design/components/states/ErrorState";
import { LoadingState } from "../design/components/states/LoadingState";
import { SplitPane } from "../design/components/SplitPane/SplitPane";
import { TabBar } from "../design/components/TabBar/TabBar";
import { MetadataTable } from "../design/components/MetadataTable/MetadataTable";
import { DigestBadge } from "../design/components/DigestBadge/DigestBadge";
import { Timestamp } from "../design/components/Timestamp/Timestamp";
import { SearchInput } from "../design/components/SearchInput/SearchInput";
import { Kbd } from "../design/components/primitives/Kbd";
import { Panel } from "../design/components/Panel/Panel";
import { VirtualizedList } from "../design/components/VirtualizedList/VirtualizedList";

export function PreviewPage() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("surfaces");
  const [searchValue, setSearchValue] = useState("");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <main className="mx-auto grid max-w-6xl gap-8 px-5 py-8">
      <header>
        <h1 className="m-0 text-xl font-semibold">CORE Workbench Design System v1</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--color-text-secondary)]">
          Static Branch 1 substrate preview. No backend, no API client, no runtime mutation surface.
        </p>
      </header>

      <section aria-labelledby="primitive-heading" className="grid gap-3">
        <h2 id="primitive-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Primitives</h2>
        <div className="flex flex-wrap gap-2">
          <Button type="button">Primary action</Button>
          <Button type="button" variant="quiet">Quiet action</Button>
        </div>
      </section>

      <section aria-labelledby="badge-heading" className="grid gap-3">
        <h2 id="badge-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Badges</h2>
        <div className="flex flex-wrap gap-2">
          {Object.values(EpistemicState).map((value) => <EpistemicStateBadge key={value} value={value} />)}
          {Object.values(NormativeClearance).map((value) => <NormativeClearanceBadge key={value} value={value} />)}
          {Object.values(ReviewState).map((value) => <ReviewStateBadge key={value} value={value} />)}
          {Object.values(GroundingSource).map((value) => <GroundingSourceBadge key={value} value={value} />)}
          <TraceHashBadge value="4f80f7e12c7e8ca1f1a277f8ccecf2846f08bb9d8f22354e6d3f30eb7fb34c80" />
        </div>
      </section>

      <section aria-labelledby="state-heading" className="grid gap-3">
        <h2 id="state-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">States</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <EmptyState statement="No artifact selected." nextAction="Select an artifact." />
          <ErrorState
            whatFailed="Preview artifact failed validation."
            mutationStatus="No mutation attempted."
            reproducer="cd workbench-ui && pnpm test"
            retrySafety="Retry reads static fixtures only."
          />
          <LoadingState label="Loading preview fixture." />
        </div>
      </section>

      <section aria-labelledby="splitpane-heading" className="grid gap-3">
        <h2 id="splitpane-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">SplitPane</h2>
        <div className="h-48 rounded-lg border border-[var(--color-border-subtle)]">
          <SplitPane direction="horizontal" defaultSplit={35} id="preview-split">
            <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-muted)]">
              Left pane (35%)
            </div>
            <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-muted)]">
              Right pane (65%)
            </div>
          </SplitPane>
        </div>
        <div className="h-48 rounded-lg border border-[var(--color-border-subtle)]">
          <SplitPane direction="vertical" defaultSplit={40} id="preview-split-v">
            <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-muted)]">
              Top pane (40%)
            </div>
            <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-muted)]">
              Bottom pane (60%)
            </div>
          </SplitPane>
        </div>
      </section>

      <section aria-labelledby="tabbar-heading" className="grid gap-3">
        <h2 id="tabbar-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">TabBar</h2>
        <div className="rounded-lg border border-[var(--color-border-subtle)] p-3">
          <TabBar
            tabs={[
              { id: "surfaces", label: "Surfaces" },
              { id: "grounding", label: "Grounding" },
              { id: "verdicts", label: "Verdicts" },
              { id: "metadata", label: "Metadata" },
              { id: "raw", label: "Raw" },
            ]}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          >
            <div className="text-sm text-[var(--color-text-secondary)]">
              Active tab: <span className="text-[var(--color-text-primary)]">{activeTab}</span>
            </div>
          </TabBar>
        </div>
      </section>

      <section aria-labelledby="metadata-heading" className="grid gap-3">
        <h2 id="metadata-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">MetadataTable</h2>
        <div className="max-w-lg rounded-lg border border-[var(--color-border-subtle)] p-3">
          <MetadataTable
            rows={[
              { key: "trace_hash", value: "4f80f7e12c7e8ca1", copyable: true, mono: true },
              { key: "grounding_source", value: "teaching" },
              { key: "epistemic_state", value: "decoded" },
              { key: "turn_cost_ms", value: "17", mono: true },
              { key: "checkpoint_emitted", value: "true" },
            ]}
          />
        </div>
      </section>

      <section aria-labelledby="digest-heading" className="grid gap-3">
        <h2 id="digest-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">DigestBadge</h2>
        <div className="flex flex-wrap items-center gap-3">
          <DigestBadge
            digest="4f80f7e12c7e8ca1f1a277f8ccecf2846f08bb9d8f22354e6d3f30eb7fb34c80"
            verified={true}
          />
          <DigestBadge
            digest="deadbeef00000000000000000000000000000000000000000000000000000000"
            verified={false}
            truncate={12}
          />
          <DigestBadge
            digest="aabbccdd"
            verified={null}
            algorithm="blake3"
          />
          <DigestBadge digest="abc123" />
        </div>
      </section>

      <section aria-labelledby="timestamp-heading" className="grid gap-3">
        <h2 id="timestamp-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Timestamp</h2>
        <div className="flex flex-wrap items-center gap-6">
          <div className="grid gap-1">
            <span className="text-xs text-[var(--color-text-muted)]">both (default)</span>
            <Timestamp iso={new Date(Date.now() - 3 * 60_000).toISOString()} />
          </div>
          <div className="grid gap-1">
            <span className="text-xs text-[var(--color-text-muted)]">relative</span>
            <Timestamp iso={new Date(Date.now() - 2 * 3_600_000).toISOString()} format="relative" />
          </div>
          <div className="grid gap-1">
            <span className="text-xs text-[var(--color-text-muted)]">absolute</span>
            <Timestamp iso="2026-06-12T10:30:00Z" format="absolute" />
          </div>
          <div className="grid gap-1">
            <span className="text-xs text-[var(--color-text-muted)]">yesterday</span>
            <Timestamp iso={new Date(Date.now() - 28 * 3_600_000).toISOString()} format="relative" />
          </div>
        </div>
      </section>

      <section aria-labelledby="search-heading" className="grid gap-3">
        <h2 id="search-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">SearchInput</h2>
        <div className="max-w-sm">
          <SearchInput
            placeholder="Search turns by prompt or trace hash..."
            value={searchValue}
            onChange={setSearchValue}
          />
        </div>
        {searchValue && (
          <p className="text-xs text-[var(--color-text-muted)]">
            Filtering: &ldquo;{searchValue}&rdquo;
          </p>
        )}
      </section>

      <section aria-labelledby="json-heading" className="grid gap-3">
        <h2 id="json-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Stable JSON Viewer</h2>
        <StableJsonViewer source='{"trace_hash":"4f80f7e12c7e","scenes":[{"detail":{"object":"lens","epsilon":1e-6}}],"state":"decoded"}' />
      </section>

      <section aria-labelledby="kbd-heading" className="grid gap-3">
        <h2 id="kbd-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Kbd</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Press <Kbd>\u2318K</Kbd> for the palette, <Kbd>j / k</Kbd> to move, <Kbd>Enter</Kbd> to open.
        </p>
      </section>

      <section aria-labelledby="panel-heading" className="grid gap-3">
        <h2 id="panel-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Panel</h2>
        <Panel title="Evidence" toolbar={<Kbd>/</Kbd>}>
          <p className="m-0 text-sm text-[var(--color-text-secondary)]">Panel body content.</p>
        </Panel>
      </section>

      <section aria-labelledby="vlist-heading" className="grid gap-3">
        <h2 id="vlist-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">VirtualizedList (1,000 rows)</h2>
        <VirtualizedList
          items={Array.from({ length: 1000 }, (_, i) => `turn-${i}`)}
          getKey={(item) => item}
          renderItem={(item, _i, focused) => (
            <div className={focused ? "bg-[var(--color-surface-raised)] px-2 py-1 text-sm" : "px-2 py-1 text-sm text-[var(--color-text-secondary)]"}>
              {item}
            </div>
          )}
          estimateSize={28}
          height={160}
          ariaLabel="Preview virtual list"
        />
      </section>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </main>
  );
}
