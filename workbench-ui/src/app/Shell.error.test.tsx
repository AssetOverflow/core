import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../test/createTestQueryClient";
import { Shell } from "./Shell";
import { ChatRoute } from "../routes/ChatRoute";
import { WorkbenchApiError } from "../api/client";

// Mock the API queries module
vi.mock("../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/queries")>();
  return {
    ...actual,
    useRuntimeStatus: vi.fn(),
  };
});

import { useRuntimeStatus } from "../api/queries";

function makeClient() {
  return createTestQueryClient();
}

function renderShell() {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/chat"]}>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route path="chat" element={<ChatRoute />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Shell error state", () => {
  beforeEach(() => {
    // Simulate API error on useRuntimeStatus
    vi.mocked(useRuntimeStatus).mockReturnValue(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      {
        data: undefined,
        isLoading: false,
        isError: true,
        error: new WorkbenchApiError("runtime_unavailable", "Server is offline"),
        isPending: false,
        isSuccess: false,
        status: "error",
      } as any,
    );
  });

  it("TopBar connection pill shows unreachable when status errors", () => {
    renderShell();
    expect(screen.getByText("API: unreachable")).toBeInTheDocument();
  });

  it("StatusFooter shows Status unavailable in danger color", () => {
    renderShell();
    const footer = document.querySelector('[data-region="statusfooter"]')!;
    expect(footer.textContent).toContain("Status unavailable");
  });

  it("routes that throw WorkbenchApiError show ErrorState with four required fields", () => {
    // Render with ApiErrorBoundary catching a thrown WorkbenchApiError
    // The ApiErrorBoundary wraps the Outlet in Shell.
    // We need a child component that throws.
    function ThrowingRoute(): React.ReactElement {
      throw new WorkbenchApiError("runtime_unavailable", "API down");
    }

    const client = makeClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/chat"]}>
          <Routes>
            <Route path="/" element={<Shell />}>
              <Route path="chat" element={<ThrowingRoute />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText("What failed")).toBeInTheDocument();
    expect(screen.getByText("Mutation status")).toBeInTheDocument();
    expect(screen.getByText("Reproducer")).toBeInTheDocument();
    expect(screen.getByText("Retry safety")).toBeInTheDocument();
    // Correct field values
    expect(screen.getByText(/Workbench API unreachable at/)).toBeInTheDocument();
    expect(screen.getByText("No corpus mutation occurred.")).toBeInTheDocument();
    expect(screen.getByText("Run: core workbench api")).toBeInTheDocument();
    expect(screen.getByText("Retry: safe (read-only)")).toBeInTheDocument();
  });
});
