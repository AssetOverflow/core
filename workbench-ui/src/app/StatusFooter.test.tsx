import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../test/createTestQueryClient";
import type { HealthStatus, RuntimeStatus } from "../types/api";

vi.mock("../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/queries")>();
  return { ...actual, useRuntimeStatus: vi.fn(), useHealth: vi.fn() };
});

import { useHealth, useRuntimeStatus } from "../api/queries";
import { StatusFooter } from "./StatusFooter";

const status: RuntimeStatus = {
  backend: "numpy",
  git_revision: "5474a152057d9999",
  engine_state_present: false,
  checkpoint_revision: "unknown",
  revision_warning: false,
  active_session_id: null,
  mutation_mode: "read_only",
};

function mockHealth(
  value: Partial<ReturnType<typeof useHealth>> & { data?: HealthStatus },
) {
  vi.mocked(useHealth).mockReturnValue({
    data: undefined,
    isError: false,
    isLoading: false,
    ...value,
  } as unknown as ReturnType<typeof useHealth>);
}

function renderFooter() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <StatusFooter />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(useRuntimeStatus).mockReturnValue({
    data: status,
    isError: false,
  } as unknown as ReturnType<typeof useRuntimeStatus>);
  mockHealth({ data: { status: "ok" } });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StatusFooter", () => {
  it("labels Read Only as a non-interactive status, not a toggle", () => {
    renderFooter();
    const chip = screen.getByText("Read Only");
    expect(chip).toHaveAttribute(
      "title",
      "Runtime mutation mode — read-only by design (status, not a toggle)",
    );
    expect(chip.tagName).toBe("SPAN"); // status display, never a button
  });

  it("copies the full SHA and shows a transient confirmation on click", async () => {
    // userEvent.setup() installs its own clipboard stub; read it back to verify
    // the full SHA was copied (not just the short display form).
    const user = userEvent.setup();
    renderFooter();

    const sha = screen.getByTestId("git-revision");
    expect(sha).toHaveAttribute("title", "Copy full git revision SHA");
    expect(sha).toHaveTextContent("5474a152"); // short SHA before copy

    await user.click(sha);

    // The confirmation the silent-copy version lacked.
    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe("5474a152057d9999");
  });

  it("gives the checkpoint-revision toggle an explanatory tooltip", () => {
    renderFooter();
    const checkpoint = screen.getByTestId("checkpoint-revision");
    expect(checkpoint.getAttribute("title")).toMatch(/checkpoint revision/i);
    expect(checkpoint.getAttribute("title")).toMatch(/unknown/);
  });

  it("shows a healthy liveness indicator when GET /health reports ok", () => {
    renderFooter();
    const health = screen.getByTestId("health-indicator");
    expect(health).toHaveAttribute("data-health", "healthy");
    expect(health).toHaveTextContent("Healthy");
  });

  it("marks the server unhealthy when /health errors", () => {
    mockHealth({ isError: true });
    renderFooter();
    const health = screen.getByTestId("health-indicator");
    expect(health).toHaveAttribute("data-health", "unhealthy");
    expect(health).toHaveTextContent("Unhealthy");
  });

  it("marks the server unhealthy when /health returns a non-ok status", () => {
    mockHealth({ data: { status: "degraded" } });
    renderFooter();
    expect(screen.getByTestId("health-indicator")).toHaveAttribute(
      "data-health",
      "unhealthy",
    );
  });

  it("shows a checking state before the first probe resolves", () => {
    mockHealth({ isLoading: true });
    renderFooter();
    const health = screen.getByTestId("health-indicator");
    expect(health).toHaveAttribute("data-health", "checking");
    expect(health).toHaveTextContent("Checking");
  });

  it("still reports health when runtime status is unavailable", () => {
    vi.mocked(useRuntimeStatus).mockReturnValue({
      data: undefined,
      isError: true,
    } as unknown as ReturnType<typeof useRuntimeStatus>);
    mockHealth({ data: { status: "ok" } });
    renderFooter();
    expect(screen.getByText("Status unavailable")).toBeInTheDocument();
    expect(screen.getByTestId("health-indicator")).toHaveAttribute(
      "data-health",
      "healthy",
    );
  });
});
