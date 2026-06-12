import { expect, test } from "@playwright/test";

const PRIMITIVE_SECTIONS = [
  "Primitives",
  "Badges",
  "States",
  "SplitPane",
  "TabBar",
  "MetadataTable",
  "DigestBadge",
  "Timestamp",
  "SearchInput",
  "Stable JSON Viewer",
] as const;

const LOCAL_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1"]);

test("preview renders every primitive section with external network blocked", async ({ context, page }) => {
  const blockedExternalRequests: string[] = [];

  await context.route("**", async (route) => {
    const url = new URL(route.request().url());
    const isLocal = LOCAL_HOSTNAMES.has(url.hostname);
    if (isLocal || url.protocol === "data:" || url.protocol === "blob:") {
      await route.continue();
      return;
    }

    blockedExternalRequests.push(route.request().url());
    await route.abort("blockedbyclient");
  });

  await page.goto("/preview");

  await expect(
    page.getByRole("heading", { name: "CORE Workbench Design System v1" }),
  ).toBeVisible();
  for (const sectionName of PRIMITIVE_SECTIONS) {
    await expect(page.getByRole("heading", { name: sectionName })).toBeVisible();
  }
  expect(blockedExternalRequests).toEqual([]);
});
