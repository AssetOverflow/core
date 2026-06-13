import { useCallback, useEffect, useState } from "react";

// Local, single-operator workbench preferences (ADR-0160: local-only, no
// cloud, no accounts). Persisted in localStorage; every pref here is read
// by a real consumer — no setting exists that does nothing.

const PREFS_KEY = "core-workbench-prefs";
const PREFS_EVENT = "core-workbench-prefs-change";

export const LANDING_ROUTES = [
  "chat",
  "trace",
  "proposals",
  "evals",
  "runs",
  "packs",
  "vault",
  "audit",
  "settings",
] as const;

export type LandingRoute = (typeof LANDING_ROUTES)[number];

export interface WorkbenchPrefs {
  /** Route the workbench opens to (consumed by the App index redirect). */
  landingRoute: LandingRoute;
  /** Whether the evidence inspector starts open (consumed by EvidenceProvider). */
  inspectorDefaultOpen: boolean;
}

export const DEFAULT_PREFS: WorkbenchPrefs = {
  landingRoute: "chat",
  inspectorDefaultOpen: false,
};

function isLandingRoute(value: unknown): value is LandingRoute {
  return typeof value === "string" && (LANDING_ROUTES as readonly string[]).includes(value);
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
