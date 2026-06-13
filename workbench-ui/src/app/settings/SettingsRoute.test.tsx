import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { RuntimeStatus } from "../../types/api";
import { getWorkbenchPrefs } from "../workbenchPrefs";
import { SettingsRoute } from "./SettingsRoute";

const status: RuntimeStatus = {
  backend: "numpy",
  git_revision: "sha256:abcdef0123456789",
  engine_state_present: true,
  checkpoint_revision: "rev-42",
  revision_warning: false,
  active_session_id: null,
  mutation_mode: "read_only",
};

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/settings"]}>
        <SettingsRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubStatus(ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        json: () =>
          Promise.resolve(
            ok
              ? { ok: true, generated_at: "now", data: status }
              : { ok: false, generated_at: "now", error: { code: "read_error", message: "boom" } },
          ),
      }),
    ),
  );
}

describe("SettingsRoute", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders both panels with the CLI-only statement and runtime status", async () => {
    stubStatus();
    renderRoute();

    expect(screen.getByText("Workbench preferences")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Engine configuration is CLI-only. This page mutates nothing on the server.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("backend")).toBeInTheDocument();
    expect(screen.getByText("mutation_mode")).toBeInTheDocument();
  });

  it("changing the landing route persists and survives reload", async () => {
    stubStatus();
    const user = userEvent.setup();
    renderRoute();

    await user.selectOptions(screen.getByLabelText("Landing route"), "vault");

    expect(getWorkbenchPrefs().landingRoute).toBe("vault");
    expect((screen.getByLabelText("Landing route") as HTMLSelectElement).value).toBe("vault");
  });

  it("changing density persists immediately", async () => {
    stubStatus();
    const user = userEvent.setup();
    renderRoute();

    await user.selectOptions(screen.getByLabelText("Density"), "compact");

    expect(getWorkbenchPrefs().densityMode).toBe("compact");
    expect((screen.getByLabelText("Density") as HTMLSelectElement).value).toBe("compact");
  });

  it("toggling inspector-open-by-default persists immediately", async () => {
    stubStatus();
    const user = userEvent.setup();
    renderRoute();

    const toggle = screen.getByRole("switch", { name: "Inspector open by default" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    await user.click(toggle);

    expect(getWorkbenchPrefs().inspectorDefaultOpen).toBe(true);
    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
  });

  it("surfaces a runtime-status error without claiming a mutation", async () => {
    stubStatus(false);
    renderRoute();

    expect(await screen.findByText("What failed")).toBeInTheDocument();
    expect(screen.getByText(/No settings mutation occurred\./)).toBeInTheDocument();
  });
});
