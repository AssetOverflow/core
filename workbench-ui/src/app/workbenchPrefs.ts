import { useCallback, useEffect, useState } from "react";
import { LANDING_ROUTE_IDS } from "./routes";

// Local, single-operator workbench preferences (ADR-0160: local-only, no
// cloud, no accounts). Persisted in localStorage; every pref here is read
// by a real consumer — no setting exists that does nothing.

const PREFS_KEY = "core-workbench-prefs";
const PREFS_EVENT = "core-workbench-prefs-change";

// Landing-eligible routes derive from the single route registry (routes.ts),
// so the Settings dropdown can never drift from the real route set. The prior
// hand-maintained tuple was missing Replay and Calibration.
export const LANDING_ROUTES: readonly string[] = LANDING_ROUTE_IDS;

export type LandingRoute = string;
export const DENSITY_MODES = ["comfortable", "compact"] as const;
export type DensityMode = (typeof DENSITY_MODES)[number];

export interface WorkbenchPrefs {
  /** Route the workbench opens to (consumed by the App index redirect). */
  landingRoute: LandingRoute;
  /** Whether the evidence inspector starts open (consumed by EvidenceProvider). */
  inspectorDefaultOpen: boolean;
  /** UI spacing density (consumed by Shell data-density + CSS variables). */
  densityMode: DensityMode;
}

export const DEFAULT_PREFS: WorkbenchPrefs = {
  landingRoute: "chat",
  inspectorDefaultOpen: false,
  densityMode: "comfortable",
};

function isLandingRoute(value: unknown): value is LandingRoute {
  return typeof value === "string" && LANDING_ROUTES.includes(value);
}

function isDensityMode(value: unknown): value is DensityMode {
  return typeof value === "string" && DENSITY_MODES.includes(value as DensityMode);
}

export function getWorkbenchPrefs(): WorkbenchPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return DEFAULT_PREFS;
    const parsed = JSON.parse(raw) as Partial<WorkbenchPrefs>;
    return {
      landingRoute: isLandingRoute(parsed.landingRoute)
        ? parsed.landingRoute
        : DEFAULT_PREFS.landingRoute,
      inspectorDefaultOpen:
        typeof parsed.inspectorDefaultOpen === "boolean"
          ? parsed.inspectorDefaultOpen
          : DEFAULT_PREFS.inspectorDefaultOpen,
      densityMode: isDensityMode(parsed.densityMode)
        ? parsed.densityMode
        : DEFAULT_PREFS.densityMode,
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

export function setWorkbenchPref<K extends keyof WorkbenchPrefs>(
  key: K,
  value: WorkbenchPrefs[K],
): void {
  const next = { ...getWorkbenchPrefs(), [key]: value };
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(next));
  } catch {
    // Best-effort: restricted storage contexts must not break the UI.
  }
  // Notify same-tab listeners (the native `storage` event only fires
  // cross-tab); the Settings controls update live.
  window.dispatchEvent(new Event(PREFS_EVENT));
}

export function useWorkbenchPrefs(): WorkbenchPrefs {
  const [prefs, setPrefs] = useState<WorkbenchPrefs>(getWorkbenchPrefs);

  useEffect(() => {
    const sync = () => setPrefs(getWorkbenchPrefs());
    window.addEventListener(PREFS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(PREFS_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return prefs;
}

export function useSetWorkbenchPref(): typeof setWorkbenchPref {
  return useCallback(setWorkbenchPref, []);
}
