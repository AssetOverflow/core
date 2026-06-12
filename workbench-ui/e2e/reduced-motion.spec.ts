import { expect, test, type Locator, type Page } from "@playwright/test";

const API_ORIGIN = "http://127.0.0.1:8765";

const runtimeStatus = {
  backend: "numpy",
  git_revision: "abcdef1234567890",
  engine_state_present: true,
  checkpoint_revision: "deadbeef12345678",
  revision_warning: false,
  active_session_id: null,
  mutation_mode: "read_only",
};

const chatTurn = {
  prompt: "What is truth?",
  surface: "Truth is what is true. pack-grounded (en_core_cognition_v1).",
  articulation_surface: "Truth is what is true.",
  walk_surface: "truth -> true",
  grounding_source: "pack",
  epistemic_state: "decoded",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: "sha256:0123456789abcdef0123456789abcdef",
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "runtime_turn",
  identity_verdict: { outcome: "cleared", runtime_detail: "" },
  safety_verdict: { outcome: "cleared", runtime_detail: "" },
  ethics_verdict: { outcome: "cleared", runtime_detail: "" },
  proposal_candidates: [{ candidate_id: "cand_123", source_kind: "discovery" }],
  turn_cost_ms: 42,
  checkpoint_emitted: true,
};

function ok(data: unknown) {
  return {
    ok: true,
    generated_at: "2026-06-12T00:00:00Z",
    data,
  };
}

async function stubChatBackend(page: Page) {
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/runtime/status") {
      await route.fulfill({ json: ok(runtimeStatus) });
      return;
    }
    if (url.pathname === "/chat/turn") {
      await route.fulfill({ json: ok(chatTurn) });
      return;
    }
    await route.abort("failed");
  });
}

async function expectInstantMotion(locator: Locator) {
  const durations = await locator.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      animationDuration: style.animationDuration,
      transitionDuration: style.transitionDuration,
    };
  });

  for (const durationList of Object.values(durations)) {
    for (const duration of durationList.split(",")) {
      expect(duration.trim()).toBe("0s");
    }
  }
}

test.use({ reducedMotion: "reduce" });

test("reduced motion collapses palette and drawer durations to instant", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await stubChatBackend(page);
  await page.goto("/chat");
  expect(
    await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches),
  ).toBe(true);

  await page.keyboard.press("ControlOrMeta+K");
  const palette = page.getByRole("dialog", { name: "Command Palette" });
  await expect(palette).toBeVisible();
  await expectInstantMotion(palette);
  await page.keyboard.press("Escape");

  await page.getByPlaceholder("Ask CORE a question...").fill("What is truth?");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Truth is what is true.")).toBeVisible();

  await page.getByRole("button", { name: "Open trace drawer" }).click();
  const drawer = page.getByRole("dialog", { name: "Turn trace" });
  await expect(drawer).toBeVisible();
  await expectInstantMotion(drawer);
});
