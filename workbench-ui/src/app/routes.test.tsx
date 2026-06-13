import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { CommandPalette } from "../design/components/primitives/CommandPalette";
import { ROUTE_ELEMENTS } from "./App";
import {
  WORKBENCH_ROUTES,
  PALETTE_ROUTES,
  LANDING_ROUTE_IDS,
  ROUTE_DIGIT_MAP,
  ROUTE_SECTIONS,
  leftNavSections,
} from "./routes";

/**
 * B3.5-a — the route registry is the single source of truth. These guards
 * fail loudly if a route is added to App without the registry, if a registry
 * route loses an element, or if a navigable route falls out of the command
 * palette (the prior Demos/Calibration drift).
 */

describe("route registry ↔ App element map", () => {
  it("every route has exactly one element, and no element is orphaned", () => {
    const routeIds = WORKBENCH_ROUTES.map((r) => r.id).sort();
    const elementIds = Object.keys(ROUTE_ELEMENTS).sort();
    expect(elementIds).toEqual(routeIds);
  });

  it("no route element is undefined (a registry route without an element)", () => {
    for (const route of WORKBENCH_ROUTES) {
      expect(ROUTE_ELEMENTS[route.id]).toBeDefined();
    }
  });

  it("route ids and paths are unique", () => {
    const ids = WORKBENCH_ROUTES.map((r) => r.id);
    const paths = WORKBENCH_ROUTES.map((r) => r.path);
    expect(new Set(ids).size).toBe(ids.length);
    expect(new Set(paths).size).toBe(paths.length);
  });
});

describe("keyboard-digit assignment is honest", () => {
  it("digits are unique and within 0–9", () => {
    const digits = WORKBENCH_ROUTES.map((r) => r.keyboardDigit).filter(
      (d): d is string => d !== null,
    );
    expect(new Set(digits).size).toBe(digits.length);
    for (const d of digits) expect(d).toMatch(/^[0-9]$/);
  });

  it("ROUTE_DIGIT_MAP maps each pinned digit to its route path", () => {
    for (const route of WORKBENCH_ROUTES) {
      if (route.keyboardDigit === null) continue;
      expect(ROUTE_DIGIT_MAP[route.keyboardDigit]).toBe(route.path);
    }
    const pinned = WORKBENCH_ROUTES.filter((r) => r.keyboardDigit !== null);
    expect(Object.keys(ROUTE_DIGIT_MAP)).toHaveLength(pinned.length);
  });

  it("more routes than digits — at least one route is palette-only (honest model)", () => {
    const paletteOnly = WORKBENCH_ROUTES.filter((r) => r.keyboardDigit === null);
    expect(paletteOnly.length).toBeGreaterThan(0);
  });
});

describe("landing routes derive from the registry", () => {
  it("includes Replay and Calibration (the prior drift)", () => {
    expect(LANDING_ROUTE_IDS).toContain("replay");
    expect(LANDING_ROUTE_IDS).toContain("calibration");
  });
});

describe("leftNavSections", () => {
  it("covers every LeftNav route exactly once, in section order", () => {
    const flattened = leftNavSections().flatMap((g) => g.routes.map((r) => r.id));
    const expected = WORKBENCH_ROUTES.filter((r) => r.leftNavVisible).map((r) => r.id);
    expect(flattened).toEqual(expected);
  });

  it("only emits known sections", () => {
    for (const group of leftNavSections()) {
      expect(ROUTE_SECTIONS).toContain(group.section);
    }
  });
});

describe("command palette reachability", () => {
  it("every palette-visible route is reachable as a Navigate command", () => {
    render(
      <MemoryRouter>
        <CommandPalette open onOpenChange={() => {}} />
      </MemoryRouter>,
    );
    for (const route of PALETTE_ROUTES) {
      expect(
        screen.getByRole("button", { name: `Open ${route.label}` }),
      ).toBeInTheDocument();
    }
  });

  it("Demos and Calibration are present (the regression they fell out of)", () => {
    render(
      <MemoryRouter>
        <CommandPalette open onOpenChange={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Open Demos" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Calibration" }),
    ).toBeInTheDocument();
  });
});
