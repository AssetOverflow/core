import { useEffect, useMemo, useState } from "react";
import { WorkbenchApiError } from "../../api/client";
import { useCalibrationClasses, useServingMetrics } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { CalibrationClass, ServingMetrics } from "../../types/api";
import { useEvidenceSubject } from "../evidenceContext";

const DETAIL_TABS: readonly Tab[] = [
  { id: "counts", label: "Counts" },
  { id: "license", label: "License math" },
  { id: "raw", label: "Raw" },
];

// Sealed practice is opt-in evidence; absence is honest, not an error.
const FAIL_CLOSED_STATEMENT =
  "No calibration evidence yet. The per-class arena ledger is populated by the sealed practice lane (ADR-0175).";
const FAIL_CLOSED_ACTION = "core eval math-contemplation";

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Calibration request failed.";
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function verdict(c: CalibrationClass): { label: string; tone: "serve" | "propose" | "none" } {
  if (c.serve_licensed) return { label: "earned SERVE", tone: "serve" };
  if (c.propose_licensed) return { label: "earned PROPOSE", tone: "propose" };
  return { label: "not yet licensed", tone: "none" };
}

function VerdictPill({ c }: { c: CalibrationClass }) {
  const v = verdict(c);
  const cls =
    v.tone === "serve"
      ? "border-[var(--color-state-verified)] text-[var(--color-state-verified)]"
      : v.tone === "propose"
        ? "border-[var(--color-state-warning-text)] text-[var(--color-state-warning-text)]"
        : "border-[var(--color-border-subtle)] text-[var(--color-text-muted)]";
  return (
    <span className={`inline-flex h-6 items-center rounded-md border px-2 text-xs ${cls}`}>
      {v.label}
    </span>
  );
}

// reliability_floor as a fill, with the two θ thresholds marked. A class
// "earns the right to guess" when its fill crosses the marker.
function ReliabilityBar({ c }: { c: CalibrationClass }) {
  return (
    <div
      className="relative h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-inset)]"
      role="img"
      aria-label={`reliability ${pct(c.reliability_floor)}, PROPOSE θ ${pct(
        c.propose_required,
      )}, SERVE θ ${pct(c.serve_required)}`}
    >
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-[var(--color-state-verified)]"
        style={{ width: pct(Math.max(0, Math.min(1, c.reliability_floor))) }}
      />
      <div
        className="absolute inset-y-0 w-px bg-[var(--color-text-secondary)]"
        style={{ left: pct(c.propose_required) }}
      />
      <div
        className="absolute inset-y-0 w-px bg-[var(--color-text-primary)]"
        style={{ left: pct(c.serve_required) }}
      />
    </div>
  );
}

function ClassRow({
  c,
  selected,
  focused,
  onSelect,
}: {
  c: CalibrationClass;
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
      className={`grid w-full gap-2 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      } ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] pl-[10px]"
          : focused
            ? "border-l-2 border-l-[var(--color-focus-ring)] pl-[10px]"
            : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm text-[var(--color-text-primary)]">{c.class_name}</span>
        <VerdictPill c={c} />
      </span>
      <ReliabilityBar c={c} />
      <span className="flex items-center gap-3 text-xs tabular-nums">
        <span className="text-[var(--color-text-secondary)]">
          reliability {pct(c.reliability_floor)} · committed {c.committed}
        </span>
        <span className="text-[var(--color-text-muted)]">{c.correct} correct</span>
        <span className="text-[var(--color-text-muted)]">{c.refused} refused</span>
        <span
          className={
            c.wrong > 0
              ? "text-[var(--color-state-contradicted)]"
              : "text-[var(--color-text-muted)]"
          }
        >
          {c.wrong} wrong
        </span>
      </span>
    </div>
  );
}

function ServingStrip({ metrics }: { metrics: ServingMetrics[] }) {
  return (
    <section className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
      <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
        Live serving outcome — the discipline's result
      </h3>
      <div className="grid gap-1">
        {metrics.map((m) => (
          <div key={m.lane} className="flex items-center gap-3 text-xs tabular-nums">
            <span className="font-mono text-[var(--color-text-primary)]">{m.lane}</span>
            <span className="text-[var(--color-text-muted)]">{m.correct} correct</span>
            <span className="text-[var(--color-text-muted)]">{m.refused} refused</span>
            <span
              className={
                m.wrong > 0
                  ? "font-semibold text-[var(--color-state-contradicted)]"
                  : "font-semibold text-[var(--color-state-verified)]"
              }
            >
              {m.wrong} wrong
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function LicenseMath({ c }: { c: CalibrationClass }) {
  const row = (action: string, required: number, licensed: boolean) => ({
    key: action,
    value: (
      <span className="tabular-nums">
        measured {pct(c.reliability_floor)} {licensed ? "≥" : "<"} θ {pct(required)} →{" "}
        <span
          className={
            licensed
              ? "text-[var(--color-state-verified)]"
              : "text-[var(--color-text-muted)]"
          }
        >
          {licensed ? "licensed" : "not licensed"}
        </span>
      </span>
    ),
  });
  return (
    <div className="grid gap-3">
      <p className="m-0 text-xs text-[var(--color-text-muted)]">
        Reliability is the engine's one-sided Wilson conservative floor on commitment precision
        (correct / committed), and is 0 below N_MIN=10 committed trials. A class is licensed for an
        action when its measured reliability clears that action's θ. The workbench computes none of
        this — it is read from <span className="font-mono">core.reliability_gate</span>.
      </p>
      <MetadataTable
        rows={[
          { key: "committed (N)", value: String(c.committed), mono: true },
          { key: "reliability floor", value: pct(c.reliability_floor), mono: true },
          row("PROPOSE", c.propose_required, c.propose_licensed),
          row("SERVE", c.serve_required, c.serve_licensed),
        ]}
      />
    </div>
  );
}

function ClassDetail({ c }: { c: CalibrationClass }) {
  const [tab, setTab] = useState("counts");
  return (
    <Panel title={c.class_name} toolbar={<VerdictPill c={c} />}>
      <TabBar tabs={DETAIL_TABS} activeTab={tab} onTabChange={setTab}>
        {tab === "counts" ? (
          <MetadataTable
            rows={[
              { key: "correct", value: String(c.correct), mono: true },
              { key: "wrong", value: String(c.wrong), mono: true },
              { key: "refused", value: String(c.refused), mono: true },
              { key: "committed", value: String(c.committed), mono: true },
              { key: "coverage", value: pct(c.coverage), mono: true },
              { key: "source", value: c.source_path, mono: true },
              { key: "source_digest", value: c.source_digest, mono: true, copyable: true },
            ]}
          />
        ) : null}
        {tab === "license" ? <LicenseMath c={c} /> : null}
        {tab === "raw" ? <StableJsonViewer source={JSON.stringify(c, null, 2)} /> : null}
      </TabBar>
    </Panel>
  );
}

export function CalibrationRoute() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const { subject, setSubject, setInspectorOpen } = useEvidenceSubject();

  const classesQuery = useCalibrationClasses();
  const metricsQuery = useServingMetrics();

  const classes = classesQuery.data ?? [];
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return classes;
    return classes.filter((c) => c.class_name.toLowerCase().includes(q));
  }, [search, classes]);

  const selectedClass = classes.find((c) => c.class_name === selected) ?? null;

  useEffect(() => {
    if (subject.kind === "calibration_class" && subject.className !== selected) {
      setSelected(subject.className);
    }
  }, [selected, subject]);

  useEffect(() => {
    if (!selectedClass) return;
    setSubject({
      kind: "calibration_class",
      className: selectedClass.class_name,
      data: selectedClass,
    });
  }, [selectedClass, setSubject]);

  function selectClass(c: CalibrationClass) {
    setSelected(c.class_name);
    setSubject({ kind: "calibration_class", className: c.class_name, data: c });
    setInspectorOpen(true);
  }

  if (classesQuery.isLoading) {
    return <LoadingState label="Loading calibration..." />;
  }

  if (classesQuery.isError) {
    if (classesQuery.error.code === "evidence_unavailable") {
      return <EmptyState statement={FAIL_CLOSED_STATEMENT} nextAction={{ kind: "cli", command: FAIL_CLOSED_ACTION }} />;
    }
    return (
      <ErrorState
        whatFailed={errorMessage(classesQuery.error)}
        mutationStatus="No calibration mutation occurred."
        reproducer="curl /calibration/classes"
        retrySafety="Retry: safe"
      />
    );
  }

  if (classes.length === 0) {
    return <EmptyState statement={FAIL_CLOSED_STATEMENT} nextAction={{ kind: "cli", command: FAIL_CLOSED_ACTION }} />;
  }

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="calibration" defaultSplit={44} minSize={340}>
        <Panel title="Gold-tether classes">
          <div className="grid min-h-0 gap-3">
            {metricsQuery.data && metricsQuery.data.length > 0 ? (
              <ServingStrip metrics={metricsQuery.data} />
            ) : null}
            <SearchInput placeholder="Filter by class" value={search} onChange={setSearch} />
            <VirtualizedList
              ariaLabel="Calibration classes"
              estimateSize={92}
              getKey={(c) => c.class_name}
              height="calc(100vh - 20rem)"
              initialRect={{ width: 520, height: 560 }}
              items={filtered}
              onActivate={selectClass}
              renderItem={(c, _index, focused) => (
                <ClassRow
                  c={c}
                  selected={c.class_name === selected}
                  focused={focused}
                  onSelect={() => selectClass(c)}
                />
              )}
            />
          </div>
        </Panel>

        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedClass ? (
            <ClassDetail c={selectedClass} />
          ) : (
            <EmptyState
              statement="Select a class to see how it earns — or doesn't earn — the right to guess."
              nextAction={{ kind: "cli", command: FAIL_CLOSED_ACTION }}
            />
          )}
          {metricsQuery.data && metricsQuery.data.length > 0 ? (
            <div className="mt-3 grid gap-1 px-1 text-xs text-[var(--color-text-muted)]">
              {metricsQuery.data.map((m) => (
                <span key={`src-${m.lane}`} className="flex items-center gap-2">
                  {m.lane} source
                  <DigestBadge digest={m.source_digest.replace(/^sha256:/, "")} truncate={12} />
                </span>
              ))}
            </div>
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
