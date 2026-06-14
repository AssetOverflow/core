import type { ReactElement } from "react";

/**
 * Single source of truth for workbench navigation routes (Wave M B3.5-a).
 *
 * Every route list in the app derives from {@link WORKBENCH_ROUTES}:
 *  - App `<Route>` declarations (via {@link ROUTE_ELEMENTS})
 *  - LeftNav (grouped by section)
 *  - the command palette Navigate section
 *  - ⌘-digit navigation shortcuts
 *  - the landing-route preference dropdown
 *  - route-conformance fixtures
 *
 * Adding a route in one place only was the prior failure mode: Demos and
 * Calibration shipped to LeftNav but never reached the command palette, and
 * Replay/Calibration were absent from the landing dropdown. With one list,
 * that drift is structurally impossible.
 *
 * Wayfinding `section`s group the flat route set by the organism's loop
 * (Converse → Cognition → Determinism → Evidence → Discipline → Substrate →
 * Settings). This is a display skin only — one workbench, one address space,
 * one Evidence Chain Rail; never a split into separate apps.
 */

export const ROUTE_SECTIONS = [
  "Converse",
  "Cognition",
  "Determinism",
  "Evidence",
  "Discipline",
  "Substrate",
  "Settings",
] as const;

export type RouteSection = (typeof ROUTE_SECTIONS)[number];

export interface WorkbenchRoute {
  /** Stable id; React key and digit-shortcut anchor. */
  id: string;
  /** Navigation target with no params, e.g. "/trace". */
  path: string;
  /** App `<Route path>` pattern; may carry optional params, e.g. "trace/:turnId?". */
  routePattern: string;
  /** LeftNav / palette label. */
  label: string;
  /** One line: what this route is for. */
  description: string;
  /** Wayfinding group. */
  section: RouteSection;
  /** Rendered in LeftNav. */
  leftNavVisible: boolean;
  /** Listed as a Navigate command in the palette. */
  commandPaletteVisible: boolean;
  /** Eligible as the landing route. */
  landingRouteAllowed: boolean;
  /**
   * Single-digit ⌘ shortcut, or `null` when the route is palette-only.
   * There are more routes than digits (1–9, 0) — the honest model pins the
   * first ten and leaves the rest searchable. KeyboardHelp says so; the
   * palette shows no chord for palette-only routes.
   */
  keyboardDigit: string | null;
  /** Must pass ADR-0162 §6 route conformance (loading/error/empty). */
  routeConformanceRequired: boolean;
}

// Array order is the LeftNav display order (already grouped by section).
export const WORKBENCH_ROUTES: readonly WorkbenchRoute[] = [
  {
    id: "chat",
    path: "/chat",
    routePattern: "chat",
    label: "Chat",
    description: "Ask CORE a question and create turn evidence.",
    section: "Converse",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "1",
    routeConformanceRequired: true,
  },
  {
    id: "trace",
    path: "/trace",
    routePattern: "trace/:turnId?",
    label: "Trace",
    description: "Inspect the cognitive turn pipeline for a turn.",
    section: "Cognition",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "2",
    routeConformanceRequired: true,
  },
  {
    id: "contemplation",
    path: "/contemplation",
    routePattern: "contemplation/:runId?",
    label: "Contemplation",
    description: "Inspect persisted contemplation process traces.",
    section: "Cognition",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: null,
    routeConformanceRequired: true,
  },
  {
    id: "tour",
    path: "/tour",
    routePattern: "tour",
    label: "Tour",
    description: "Guided determinism tour over the real demos.",
    section: "Determinism",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: null,
    routeConformanceRequired: true,
  },
  {
    id: "replay",
    path: "/replay",
    routePattern: "replay/:turnId?",
    label: "Replay",
    description: "Re-run a turn and compare trace hashes.",
    section: "Determinism",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "3",
    routeConformanceRequired: true,
  },
  {
    id: "demos",
    path: "/demos",
    routePattern: "demos/:demoId?",
    label: "Demos",
    description: "Run a registered determinism demo end to end.",
    section: "Determinism",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: null,
    routeConformanceRequired: true,
  },
  {
    id: "proposals",
    path: "/proposals",
    routePattern: "proposals/:proposalId?",
    label: "Proposals",
    description: "Review the teaching proposal queue and HITL ratification.",
    section: "Evidence",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "4",
    routeConformanceRequired: true,
  },
  {
    id: "runs",
    path: "/runs",
    routePattern: "runs/:sessionId?",
    label: "Runs",
    description: "Browse recorded session runs.",
    section: "Evidence",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "6",
    routeConformanceRequired: true,
  },
  {
    id: "vault",
    path: "/vault",
    routePattern: "vault",
    label: "Vault",
    description: "Inspect persisted session memory.",
    section: "Evidence",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "8",
    routeConformanceRequired: true,
  },
  {
    id: "audit",
    path: "/audit",
    routePattern: "audit",
    label: "Audit",
    description: "Read the deterministic audit event log.",
    section: "Evidence",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "9",
    routeConformanceRequired: true,
  },
  {
    id: "evals",
    path: "/evals",
    routePattern: "evals/:laneId?",
    label: "Evals",
    description: "Run eval lanes and read the wrong=0 ledger.",
    section: "Discipline",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "5",
    routeConformanceRequired: true,
  },
  {
    id: "calibration",
    path: "/calibration",
    routePattern: "calibration",
    label: "Calibration",
    description: "See the gold-tether arena earn the right to guess.",
    section: "Discipline",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: null,
    routeConformanceRequired: true,
  },
  {
    id: "packs",
    path: "/packs",
    routePattern: "packs/:packId?",
    label: "Packs",
    description: "Browse language/identity packs (CORE-Logos studio).",
    section: "Substrate",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "7",
    routeConformanceRequired: true,
  },
  {
    id: "settings",
    path: "/settings",
    routePattern: "settings",
    label: "Settings",
    description: "Local workbench preferences (read-only to the engine).",
    section: "Settings",
    leftNavVisible: true,
    commandPaletteVisible: true,
    landingRouteAllowed: true,
    keyboardDigit: "0",
    routeConformanceRequired: true,
  },
];

/** Routes shown in LeftNav, in display order. */
export const LEFT_NAV_ROUTES = WORKBENCH_ROUTES.filter((r) => r.leftNavVisible);

/** Routes listed in the command palette Navigate section, in display order. */
export const PALETTE_ROUTES = WORKBENCH_ROUTES.filter(
  (r) => r.commandPaletteVisible,
);

/** Route ids eligible as the workbench landing route. */
export const LANDING_ROUTE_IDS = WORKBENCH_ROUTES.filter(
  (r) => r.landingRouteAllowed,
).map((r) => r.id);

/** ⌘-digit → navigation path, for the ten pinned routes. */
export const ROUTE_DIGIT_MAP: Record<string, string> = Object.fromEntries(
  WORKBENCH_ROUTES.filter((r) => r.keyboardDigit !== null).map((r) => [
    r.keyboardDigit as string,
    r.path,
  ]),
);

/** LeftNav routes grouped by section, in section then route order. */
export function leftNavSections(): {
  section: RouteSection;
  routes: WorkbenchRoute[];
}[] {
  const groups = new Map<RouteSection, WorkbenchRoute[]>(
    ROUTE_SECTIONS.map((s) => [s, []]),
  );
  for (const route of LEFT_NAV_ROUTES) {
    groups.get(route.section)!.push(route);
  }
  return ROUTE_SECTIONS.map((section) => ({
    section,
    routes: groups.get(section)!,
  })).filter((group) => group.routes.length > 0);
}

/**
 * The element registry consumed by `App`. Keyed by route id so that adding a
 * route to {@link WORKBENCH_ROUTES} without giving it an element is caught by
 * `routes.test.tsx` rather than rendering `undefined`. Populated in `App.tsx`
 * (it owns the route-component imports); declared here so the contract — every
 * route id has an element — lives next to the route list.
 */
export type RouteElementMap = Record<string, ReactElement>;
