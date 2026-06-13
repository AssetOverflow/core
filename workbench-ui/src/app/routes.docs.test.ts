// @vitest-environment node
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { WORKBENCH_ROUTES } from "./routes";

const guide = readFileSync(
  new URL("../../../docs/workbench/UI-UX-GUIDE.md", import.meta.url),
  "utf-8",
);

describe("UI/UX guide route map", () => {
  it("states the current route count", () => {
    expect(guide).toContain(`Current route count: ${WORKBENCH_ROUTES.length}.`);
  });

  it("lists every registry route label and path", () => {
    for (const route of WORKBENCH_ROUTES) {
      expect(guide).toContain(`| ${route.section} | ${route.label} | \`${route.path}\``);
    }
  });
});
