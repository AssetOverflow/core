import { WorkbenchApiError } from "../../api/client";
import { useRuntimeStatus } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import {
  DENSITY_MODES,
  LANDING_ROUTES,
  useSetWorkbenchPref,
  useWorkbenchPrefs,
  type DensityMode,
  type LandingRoute,
} from "../workbenchPrefs";

const CLI_ONLY_STATEMENT =
  "Engine configuration is CLI-only. This page mutates nothing on the server.";

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Runtime status request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function PrefRow({
  label,
  hint,
  control,
}: {
  label: string;
  hint: string;
  control: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-[var(--color-border-subtle)] py-3 last:border-b-0">
      <span className="min-w-0">
        <span className="block text-sm text-[var(--color-text-primary)]">{label}</span>
        <span className="mt-0.5 block text-xs text-[var(--color-text-muted)]">{hint}</span>
      </span>
      <span className="justify-self-end">{control}</span>
    </div>
  );
}

function PreferencesPanel() {
  const prefs = useWorkbenchPrefs();
  const setPref = useSetWorkbenchPref();
  return (
    <Panel title="Workbench preferences">
      <p className="m-0 mb-1 text-xs text-[var(--color-text-muted)]">
        Local to this browser. Visual density applies immediately; startup preferences apply on the next workbench load.
      </p>
      <PrefRow
        label="Density"
        hint="Adjust shell, panel, row, and control spacing."
        control={
          <select
            aria-label="Density"
            value={prefs.densityMode}
            onChange={(e) => setPref("densityMode", e.target.value as DensityMode)}
            className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 py-1 text-sm text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            {DENSITY_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
        }
      />
      <PrefRow
        label="Landing route"
        hint="Where the workbench opens."
        control={
          <select
            aria-label="Landing route"
            value={prefs.landingRoute}
            onChange={(e) => setPref("landingRoute", e.target.value as LandingRoute)}
            className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 py-1 text-sm text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            {LANDING_ROUTES.map((route) => (
              <option key={route} value={route}>
                /{route}
              </option>
            ))}
          </select>
        }
      />
      <PrefRow
        label="Inspector open by default"
        hint="Start each session with the evidence inspector visible."
        control={
          <button
            type="button"
            role="switch"
            aria-checked={prefs.inspectorDefaultOpen}
            aria-label="Inspector open by default"
            onClick={() => setPref("inspectorDefaultOpen", !prefs.inspectorDefaultOpen)}
            className={`inline-flex h-6 items-center rounded-md border px-2 text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
              prefs.inspectorDefaultOpen
                ? "border-[var(--color-selected-border)] bg-[var(--color-selected-bg)] text-[var(--color-text-primary)]"
                : "border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)]"
            }`}
          >
            {prefs.inspectorDefaultOpen ? "On" : "Off"}
          </button>
        }
      />
    </Panel>
  );
}

function RuntimePanel() {
  const statusQuery = useRuntimeStatus();
  const status = statusQuery.data;
  const gitDigest = digestPayload(status?.git_revision);
  return (
    <Panel title="Runtime">
      <p className="m-0 mb-3 text-xs text-[var(--color-text-muted)]">{CLI_ONLY_STATEMENT}</p>
      {statusQuery.isLoading ? (
        <LoadingState label="Loading runtime status..." />
      ) : statusQuery.isError ? (
        <ErrorState
          whatFailed={errorMessage(statusQuery.error)}
          mutationStatus="No settings mutation occurred."
          reproducer="curl /runtime/status"
          retrySafety="Retry: safe"
        />
      ) : status ? (
        <MetadataTable
          rows={[
            { key: "backend", value: status.backend, mono: true },
            {
              key: "git_revision",
              value: gitDigest ? <DigestBadge digest={gitDigest} truncate={12} /> : "unknown",
            },
            { key: "engine_state_present", value: status.engine_state_present ? "yes" : "no" },
            {
              key: "checkpoint_revision",
              value: status.checkpoint_revision || "none",
              mono: true,
            },
            {
              key: "revision_warning",
              value: status.revision_warning ? (
                <span className="text-[var(--color-state-warning-text)]">revision mismatch</span>
              ) : (
                "none"
              ),
            },
            { key: "active_session_id", value: status.active_session_id ?? "none", mono: true },
            { key: "mutation_mode", value: status.mutation_mode, mono: true },
          ]}
        />
      ) : null}
    </Panel>
  );
}

export function SettingsRoute() {
  return (
    <div className="grid gap-4 overflow-y-auto p-1">
      <PreferencesPanel />
      <RuntimePanel />
    </div>
  );
}
