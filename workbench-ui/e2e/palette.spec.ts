import { expect, test, type Page } from "@playwright/test";

const API_ORIGIN = "http://127.0.0.1:8765";

const APP_ROUTES = [
  { label: "Chat", path: "/chat", command: "Open Chat" },
  { label: "Trace", path: "/trace", command: "Open Trace" },
  { label: "Replay", path: "/replay", command: "Open Replay" },
  { label: "Proposals", path: "/proposals", command: "Open Proposals" },
  { label: "Evals", path: "/evals", command: "Open Evals" },
  { label: "Runs", path: "/runs", command: "Open Runs" },
  { label: "Packs", path: "/packs", command: "Open Packs" },
  { label: "Vault", path: "/vault", command: "Open Vault" },
  { label: "Audit", path: "/audit", command: "Open Audit" },
  { label: "Settings", path: "/settings", command: "Open Settings" },
] as const;

async function makeBackendAbsent(page: Page) {
  await page.route(`${API_ORIGIN}/**`, (route) => route.abort("failed"));
}

async function expectUsableRoute(page: Page) {
  const main = page.locator('[data-region="main"]');
  await expect(main).toBeVisible();
  await expect(main).not.toHaveText(/^\s*$/);
}

async function openPalette(page: Page) {
  await page.keyboard.press("ControlOrMeta+K");
  await expect(page.getByRole("dialog", { name: "Command Palette" })).toBeVisible();
}

test.describe("command palette route smoke", () => {
  test.beforeEach(async ({ page }) => {
    await makeBackendAbsent(page);
  });

  for (const startRoute of APP_ROUTES) {
    test(`opens with Meta+K and reaches every route from ${startRoute.label}`, async ({ page }) => {
      for (const targetRoute of APP_ROUTES) {
        await page.goto(startRoute.path);
        await expectUsableRoute(page);

        await openPalette(page);
        await page.getByRole("button", { name: targetRoute.command }).click();

        await expect(page).toHaveURL(new RegExp(`${targetRoute.path}$`));
        await expectUsableRoute(page);
      }
    });
  }
});
