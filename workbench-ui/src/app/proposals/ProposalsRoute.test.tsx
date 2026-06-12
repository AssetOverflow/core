import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { proposalDetail, proposalSummaries } from "../../api/__fixtures__/proposals";
import { SuggestedCLIBox } from "./SuggestedCLIBox";
import { ProposalTable } from "./ProposalTable";
import { ProposalsRoute } from "./ProposalsRoute";

function queryWrapper({ children }: { children: ReactNode }) {
  const client = createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{location.search}</span>;
}

function renderRoute(initialEntry = "/proposals") {
  return render(
    <QueryClientProvider
      client={createTestQueryClient()}
    >
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/proposals" element={<><ProposalsRoute /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubProposalFetch(items = proposalSummaries) {
  const fetchMock = vi.fn((url: string) => {
    if (url.endsWith(`/proposals/${proposalDetail.proposal_id}`)) {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: proposalDetail }),
      });
    }
    return Promise.resolve({
      json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("ProposalTable", () => {
  it("renders empty state when the API returns no proposals", () => {
    render(
      <ProposalTable proposals={[]} selectedProposalId={null} onSelect={vi.fn()} />,
      { wrapper: queryWrapper },
    );

    expect(screen.getByText("No proposals match this queue view.")).toBeInTheDocument();
  });

  it("renders rows from a pending, accepted, and rejected fixture set", () => {
    render(
      <ProposalTable proposals={proposalSummaries} selectedProposalId={null} onSelect={vi.fn()} />,
      { wrapper: queryWrapper },
    );

    expect(screen.getByTitle("proposal-pending-001abcdef")).toBeInTheDocument();
    expect(screen.getByTitle("proposal-accepted-002abcdef")).toBeInTheDocument();
    expect(screen.getByTitle("proposal-rejected-003abcdef")).toBeInTheDocument();
  });
});

describe("ProposalsRoute", () => {
  afterEach(() => vi.restoreAllMocks());

  it("restricts visible rows by filter state", async () => {
    stubProposalFetch();
    const user = userEvent.setup();
    renderRoute("/proposals?state=pending");

    expect(await screen.findByTitle("proposal-pending-001abcdef")).toBeInTheDocument();
    expect(screen.queryByTitle("proposal-accepted-002abcdef")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "accepted" }));
    expect(await screen.findByTitle("proposal-accepted-002abcdef")).toBeInTheDocument();
    expect(screen.queryByTitle("proposal-pending-001abcdef")).not.toBeInTheDocument();
  });

  it("selecting a row updates the URL query param and renders detail", async () => {
    stubProposalFetch();
    const user = userEvent.setup();
    renderRoute("/proposals?state=pending");

    await user.click(await screen.findByRole("button", { name: /proposal-p/i }));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        `?state=pending&proposal_id=${proposalDetail.proposal_id}`,
      ),
    );
    expect(await screen.findByText("Contemplation proposed a coherence relation.")).toBeInTheDocument();
  });

  it("shows LoadingState during fetch", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    renderRoute();

    expect(screen.getByText("Loading proposal queue...")).toBeInTheDocument();
  });

  it("shows ErrorState on API failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            ok: false,
            generated_at: "now",
            error: { code: "read_error", message: "proposal log unavailable" },
          }),
      }),
    );
    renderRoute();

    expect(await screen.findByText("What failed")).toBeInTheDocument();
    expect(screen.getByText("proposal log unavailable")).toBeInTheDocument();
  });

  it("shows EmptyState on empty result", async () => {
    stubProposalFetch([]);
    renderRoute();

    expect(await screen.findByText("No proposals match this queue view.")).toBeInTheDocument();
  });
});

describe("SuggestedCLIBox", () => {
  it("shows the correct terminal review commands for a proposal id", () => {
    render(<SuggestedCLIBox proposalId="proposal-123" />);

    expect(screen.getByText("core teaching review --proposal-id proposal-123 --accept")).toBeInTheDocument();
    expect(screen.getByText("core teaching review --proposal-id proposal-123 --reject")).toBeInTheDocument();
  });
});
