import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { proposalDetail, proposalSummaries } from "../../api/__fixtures__/proposals";
import { getExtraCommands, unregisterCommands } from "../../commands/registry";
import { SuggestedCLIBox } from "./SuggestedCLIBox";
import { ProposalStateBadge } from "./ProposalStateBadge";
import { ProposalTable } from "./ProposalTable";
import { ProposalsRoute } from "./ProposalsRoute";

function queryWrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{location.search}</span>;
}

function renderRoute(initialEntry = "/proposals") {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}
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
  it("shows fallback commands when suggested_cli is null", () => {
    render(<SuggestedCLIBox proposal={{ proposal_id: "proposal-123", suggested_cli: null }} />);

    expect(screen.getByText("core teaching review --proposal-id proposal-123 --accept")).toBeInTheDocument();
    expect(screen.getByText("core teaching review --proposal-id proposal-123 --reject")).toBeInTheDocument();
  });

  it("shows suggested_cli from the API when present", () => {
    render(
      <SuggestedCLIBox
        proposal={{ proposal_id: "proposal-123", suggested_cli: "core teaching review --proposal-id proposal-123 --accept --auto" }}
      />,
    );

    expect(
      screen.getByText("core teaching review --proposal-id proposal-123 --accept --auto"),
    ).toBeInTheDocument();
    expect(screen.queryByText("--reject")).not.toBeInTheDocument();
  });

  it("code element carries select-all class for keyboard copy", () => {
    const { container } = render(
      <SuggestedCLIBox proposal={{ proposal_id: "proposal-123", suggested_cli: null }} />,
    );

    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.className).toContain("select-all");
  });
});

describe("⌘K proposal command registration", () => {
  beforeEach(() => {
    // Clear any commands registered by previous tests.
    unregisterCommands(getExtraCommands().map((c) => c.path));
  });

  afterEach(() => {
    unregisterCommands(getExtraCommands().map((c) => c.path));
    vi.restoreAllMocks();
  });

  it("registers proposal commands when the route mounts with proposals", async () => {
    stubProposalFetch(proposalSummaries);
    renderRoute("/proposals?state=pending");

    await waitFor(() => {
      const cmds = getExtraCommands();
      expect(cmds.some((c) => c.name.includes("proposal-p"))).toBe(true);
    });
  });

  it("registered commands contain a /proposals path with proposal_id", async () => {
    stubProposalFetch(proposalSummaries);
    renderRoute("/proposals?state=pending");

    await waitFor(() => {
      const cmds = getExtraCommands();
      const proposalCmd = cmds.find((c) => c.path.includes("proposal_id="));
      expect(proposalCmd).toBeDefined();
      expect(proposalCmd!.path).toMatch(/^\/proposals\?/);
    });
  });
});

describe("ProposalStateBadge lifecycle colors", () => {
  const STATES = ["pending", "accepted", "rejected", "withdrawn"] as const;

  it.each(STATES)("renders %s state using a CSS custom property token", (state) => {
    const { container } = render(<ProposalStateBadge value={state} />);
    // InfoBadge renders a Popover.Trigger button with inline style containing the color token.
    const trigger = container.querySelector("button");
    expect(trigger).not.toBeNull();
    const styleAttr = trigger!.getAttribute("style") ?? "";
    // Must reference a CSS custom property from the review palette.
    expect(styleAttr).toMatch(/--color-review-/);
    // Must not embed a raw hex literal.
    expect(styleAttr).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });
});
