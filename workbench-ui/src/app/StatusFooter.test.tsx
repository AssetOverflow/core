import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../test/createTestQueryClient";
import type { RuntimeStatus } from "../types/api";

vi.mock("../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/queries")>();
  return { ...actual, useRuntimeStatus: vi.fn() };
});

import { useRuntimeStatus } from "../api/queries";
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
});
