import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "./Shell";
import { ChatRoute } from "../routes/ChatRoute";
import { ProposalsRoute } from "./proposals/ProposalsRoute";
import type { RuntimeStatus } from "../types/api";

// Mock the API queries module
vi.mock("../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/queries")>();
  return {
    ...actual,
    useRuntimeStatus: vi.fn(),
  };
});

import { useRuntimeStatus } from "../api/queries";

const mockStatus: RuntimeStatus = {
  backend: "numpy",
  git_revision: "abcdef1234567890",
  engine_state_present: true,
  checkpoint_revision: "deadbeef12345678",
  revision_warning: false,
  active_session_id: null,
  mutation_mode: "read_only",
};

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderShell(initialPath = "/chat") {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route path="chat" element={<ChatRoute />} />
            <Route path="proposals" element={<ProposalsRoute />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useRuntimeStatus).mockReturnValue({
      data: mockStatus,
      isLoading: false,
      isError: false,
      isPending: false,
      isSuccess: true,
      status: "success",
      error: null,
    } as any);
  });

  it("renders five named regions", () => {
    renderShell();
    expect(screen.getByRole("banner")).toBeInTheDocument(); // topbar is a header
    expect(document.querySelector('[data-region="topbar"]')).toBeInTheDocument();
    expect(document.querySelector('[data-region="leftnav"]')).toBeInTheDocument();
    expect(document.querySelector('[data-region="main"]')).toBeInTheDocument();
    expect(document.querySelector('[data-region="statusfooter"]')).toBeInTheDocument();
  });

  it("LeftNav has exactly 10 items in order", () => {
    renderShell();
    const nav = document.querySelector('[data-region="leftnav"]')!;
    const links = nav.querySelectorAll("a");
    expect(links).toHaveLength(10);
    const labels = Array.from(links).map((l) => l.textContent);
    expect(labels).toEqual([
      "Chat",
      "Trace",
      "Replay",
      "Proposals",
      "Evals",
      "Runs",
      "Packs",
      "Vault",
      "Audit",
      "Settings",
    ]);
  });

  it("clicking a nav item changes route (main shows new content)", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    renderShell("/chat");
    expect(screen.getByText("Ask CORE a question.")).toBeInTheDocument();

    // Click Proposals nav link
    const proposalsLink = screen.getByRole("link", { name: "Proposals" });
    fireEvent.click(proposalsLink);

    expect(screen.getByText("Loading proposal queue...")).toBeInTheDocument();
  });

  it("StatusFooter shows mutation_mode Read Only label for read_only", () => {
    renderShell();
    const footer = document.querySelector('[data-region="statusfooter"]')!;
    expect(footer.textContent).toContain("Read Only");
    expect(footer.textContent).not.toContain("Runtime Turn");
  });

  it("StatusFooter shows git_revision short SHA", () => {
    renderShell();
    const el = document.querySelector('[data-testid="git-revision"]');
    expect(el).toBeInTheDocument();
    expect(el!.textContent).toBe("abcdef12");
  });

  it("StatusFooter shows checkpoint_revision short SHA", () => {
    renderShell();
    const el = document.querySelector('[data-testid="checkpoint-revision"]');
    expect(el).toBeInTheDocument();
    expect(el!.textContent).toBe("deadbeef");
  });

  it("mutation_mode runtime_turn renders amber styling and Runtime Turn label", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useRuntimeStatus).mockReturnValue({
      data: { ...mockStatus, mutation_mode: "runtime_turn" },
      isLoading: false,
      isError: false,
      isPending: false,
      isSuccess: true,
      status: "success",
      error: null,
    } as any);

    renderShell();
    const mutationEl = document.querySelector('[data-testid="mutation-mode"]')!;
    expect(mutationEl.textContent).toBe("Runtime Turn");
    // Should use warning color class (amber)
    expect(mutationEl.className).toContain("warning");
  });

  it("revision_warning=true makes checkpoint_revision show warning attr, clicking expands note", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useRuntimeStatus).mockReturnValue({
      data: { ...mockStatus, revision_warning: true },
      isLoading: false,
      isError: false,
      isPending: false,
      isSuccess: true,
      status: "success",
      error: null,
    } as any);

    renderShell();
    const cpBtn = document.querySelector('[data-testid="checkpoint-revision"]')!;
    expect(cpBtn.getAttribute("data-warning")).toBe("true");

    // Click to expand note
    fireEvent.click(cpBtn);
    const note = document.querySelector('[data-testid="revision-note"]');
    expect(note).toBeInTheDocument();
    expect(note!.textContent).toContain("ADR-0157 / ADR-0158");
  });
});
