import { useState, type ReactNode } from "react";
import { Activity, HeartPulse } from "lucide-react";
import { Link } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useLivedLife } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { LivedLife, LivedLifeHeartbeat } from "../../types/api";

// Conformance contract strings (ADR-0162 §6) — kept verbatim in
// routeConformance.test.tsx; the absence state IS the primary state until an
// always-on run lands an artifact (fail-closed, like Vault/Calibration).
export const LIVED_LIFE_LOADING = "Loading lived life...";
export const LIVED_LIFE_ABSENCE_STATEMENT =
  "No always-on run recorded yet. The continuous-life heartbeat persists its evidence here when it runs.";
export const LIVED_LIFE_ABSENCE_ACTION =
  "Run the always-on heartbeat to persist engine_state/lived_life.json";

function errorMessage(error: unknown): string {
  return error instanceof WorkbenchApiError
    ? error.message
    : "Lived-life request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function closureDisplay(versorCondition: number | null): string {
  return typeof versorCondition === "number"
    ? versorCondition.toExponential(3)
    : "no field yet";
}

/** A small status pill. `tone` maps to a state color token. */
function Pill({
  tone,
  children,
}: {
  tone: "verified" | "warning" | "muted";
  children: ReactNode;
}) {
  const color =
    tone === "verified"
      ? "var(--color-state-verified)"
      : tone === "warning"
        ? "var(--color-state-warning-text)"
        : "var(--color-text-secondary)";
  return (
    <span
      className="inline-flex h-6 items-center gap-1 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 text-xs"
      style={{ color }}
    >
      {children}
    </span>
  );
}

/** The headline: one continuous life, stated as falsifiable facts. */
function LifeHeadline({ life }: { life: LivedLife }) {
  const closureTone = life.closure_held ? "verified" : "warning";
  return (
    <Panel
      title="One continuous life"
      toolbar={
        <span className="inline-flex items-center gap-1 text-[var(--color-text-muted)]">
          <HeartPulse size={14} aria-hidden />
          <span className="text-xs">always-on heartbeat</span>
        </span>
      }
    >
      <div className="grid gap-3">
        <p className="m-0 text-sm text-[var(--color-text-secondary)] [text-wrap:balance]">
          CORE held itself alive over {life.heartbeats}{" "}
          {life.heartbeats === 1 ? "heartbeat" : "heartbeats"} with no user turn,
          learned while idle, and kept its field valid by construction — the
          heartbeat READS closure as evidence, it never repairs it.
        </p>
        <div className="flex flex-wrap gap-2">
          <Pill tone="muted">
            {life.heartbeats}{" "}
            {life.heartbeats === 1 ? "heartbeat" : "heartbeats"}
          </Pill>
          <Pill tone={closureTone}>
            {life.closure_observed
              ? life.closure_held
                ? `closure held < ${life.closure_ceiling.toExponential(0)}`
                : "closure BREACHED"
              : "no field observed"}
          </Pill>
          <Pill tone={life.total_facts_consolidated > 0 ? "verified" : "muted"}>
            {life.total_facts_consolidated} learned while idle
          </Pill>
          {life.total_proposals_created > 0 ? (
            <Pill tone="muted">
              {life.total_proposals_created} proposals (reviewable)
            </Pill>
          ) : null}
          <Pill tone={life.converged ? "verified" : "muted"}>
            {life.converged ? "at rest" : "still churning"}
          </Pill>
          <Pill tone={resumeTone(life.resume_status)}>
            {life.resume_status === "would_resume"
              ? "resumes as same life"
              : life.resume_status === "substrate_changed"
                ? "substrate changed"
                : "resume unknown"}
          </Pill>
        </div>
      </div>
    </Panel>
  );
}

function resumeTone(
  status: LivedLife["resume_status"],
): "verified" | "warning" | "muted" {
  if (status === "would_resume") return "verified";
  if (status === "substrate_changed") return "warning";
  return "muted";
}

function LifeSummary({ life }: { life: LivedLife }) {
  const identity = digestPayload(life.identity);
  const current = digestPayload(life.current_identity);
  const artifact = digestPayload(life.artifact?.digest);
  return (
    <MetadataTable
      rows={[
        {
          key: "identity",
          value: identity ? (
            <DigestBadge digest={identity} truncate={16} />
          ) : (
            <span className="text-[var(--color-text-muted)]">not recorded</span>
          ),
        },
        { key: "heartbeats", value: String(life.heartbeats), mono: true },
        {
          key: "closure_observed",
          value: life.closure_observed ? "yes" : "no field this run",
          mono: true,
        },
        {
          key: "closure_held",
          value: life.closure_held
            ? `held (< ${life.closure_ceiling.toExponential(0)})`
            : "BREACHED",
          mono: true,
        },
        {
          key: "facts_consolidated",
          value: String(life.total_facts_consolidated),
          mono: true,
        },
        {
          key: "proposals_created",
          value: String(life.total_proposals_created),
          mono: true,
        },
        {
          key: "converged",
          value: life.converged ? "yes (final beat at rest)" : "no (still working)",
          mono: true,
        },
        {
          key: "final_checkpoint_ok",
          value: life.final_checkpoint_ok ? "yes" : "FAILED",
          mono: true,
        },
        {
          key: "current_identity",
          value: current ? (
            <DigestBadge digest={current} truncate={16} />
          ) : (
            <span className="text-[var(--color-text-muted)]">not recomputed</span>
          ),
        },
        {
          key: "artifact",
          value: artifact ? (
            <DigestBadge digest={artifact} truncate={12} />
          ) : (
            <span className="text-[var(--color-text-muted)]">not linked</span>
          ),
        },
      ]}
    />
  );
}

function HeartbeatRow({ beat }: { beat: LivedLifeHeartbeat }) {
  const valid = beat.field_valid;
  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 last:border-b-0">
      <span className="font-mono text-xs text-[var(--color-text-muted)]">
        beat {beat.tick}
      </span>
      <span className="flex items-center gap-2 text-xs">
        <span
          className="font-mono"
          style={{
            color: valid
              ? "var(--color-state-verified)"
              : "var(--color-state-warning-text)",
          }}
          title="versor_condition (field closure) — read, never repaired"
        >
          {closureDisplay(beat.versor_condition)}
        </span>
        <span className="text-[var(--color-text-muted)]">
          {valid ? "valid" : "INVALID"}
        </span>
      </span>
      <span className="justify-self-end text-xs text-[var(--color-text-secondary)]">
        {beat.did_work ? (
          <span className="inline-flex items-center gap-1">
            <Activity size={12} aria-hidden />
            {beat.facts_consolidated > 0
              ? `+${beat.facts_consolidated} fact${beat.facts_consolidated === 1 ? "" : "s"}`
              : null}
            {beat.proposals_created > 0
              ? ` +${beat.proposals_created} prop${beat.proposals_created === 1 ? "" : "s"}`
              : null}
            {beat.facts_consolidated === 0 && beat.proposals_created === 0
              ? "working"
              : null}
          </span>
        ) : (
          <span className="text-[var(--color-text-muted)]">at rest</span>
        )}
      </span>
    </div>
  );
}

function HeartbeatTimeline({ life }: { life: LivedLife }) {
  if (life.records.length === 0) {
    return (
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        This run recorded no heartbeats.
      </p>
    );
  }
  return (
    <div className="grid gap-3">
      <p className="m-0 text-xs text-[var(--color-text-muted)]">
        Each beat advances continuous learning, then reads the field's closure
        (<span className="font-mono">versor_condition</span>) as evidence. Closure
        stays flat below the ceiling across the life — the engine never patches the
        field to keep it valid.
      </p>
      <div className="rounded-md border border-[var(--color-border-subtle)]">
        {life.records.map((beat) => (
          <HeartbeatRow key={beat.tick} beat={beat} />
        ))}
      </div>
    </div>
  );
}

function ResumeVerdict({ life }: { life: LivedLife }) {
  const tone = resumeTone(life.resume_status);
  const color =
    tone === "verified"
      ? "var(--color-state-verified)"
      : tone === "warning"
        ? "var(--color-state-warning-text)"
        : "var(--color-text-muted)";
  return (
    <div
      className="grid gap-1 border-l-2 pl-3"
      style={{ borderColor: color }}
    >
      <p className="m-0 text-sm" style={{ color }}>
        {life.resume_summary}
      </p>
      <p className="m-0 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">
        This is the resume guarantee made felt: a reboot recomputes the engine
        identity and refuses if it differs from the persisted one, so this life
        wakes up as <em>itself</em>, not a copy. The per-reboot lineage chain
        lives under{" "}
        <Link
          to="/runs"
          className="text-[var(--color-text-primary)] underline underline-offset-2"
        >
          Runs › Identity
        </Link>
        .
      </p>
    </div>
  );
}

function RawJson({ life }: { life: LivedLife }) {
  const [expanded, setExpanded] = useState(false);
  return expanded ? (
    <StableJsonViewer source={JSON.stringify(life, null, 2)} />
  ) : (
    <div className="grid justify-items-start gap-2">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        Raw lived-life JSON is collapsed by default.
      </p>
      <Button type="button" variant="quiet" onClick={() => setExpanded(true)}>
        Expand raw JSON
      </Button>
    </div>
  );
}

export function LivedLifeRoute() {
  const query = useLivedLife();

  if (query.isLoading) {
    return <LoadingState label={LIVED_LIFE_LOADING} />;
  }

  if (query.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(query.error)}
        mutationStatus="No lived-life mutation occurred."
        reproducer="curl /lived-life"
        retrySafety="Retry: safe"
      />
    );
  }

  const life = query.data;
  if (!life || life.status !== "recorded") {
    return (
      <EmptyState
        statement={LIVED_LIFE_ABSENCE_STATEMENT}
        nextAction={LIVED_LIFE_ABSENCE_ACTION}
      />
    );
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="mx-auto grid max-w-3xl gap-4 p-1">
        <LifeHeadline life={life} />
        <Panel title="Life summary">
          <div className="grid gap-4">
            <LifeSummary life={life} />
            <ResumeVerdict life={life} />
          </div>
        </Panel>
        <Panel title="Heartbeat timeline">
          <HeartbeatTimeline life={life} />
        </Panel>
        <Panel title="Raw">
          <RawJson life={life} />
        </Panel>
      </div>
    </div>
  );
}
