import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { proposalDetail, proposalSummaries } from "../../api/__fixtures__/proposals";
import { EvidenceProvider, useEvidenceSubject } from "../evidenceContext";
import { isAddressable, subjectToUrl } from "../evidenceAddress";
import { SuggestedCLIBox } from "./SuggestedCLIBox";
import { ProposalTable } from "./ProposalTable";
import { ProposalsRoute } from "./ProposalsRoute";
import type { MathProposalDetail, MathProposalSummary } from "../../types/api";

function queryWrapper({ children }: { children: ReactNode }) {
  const client = createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return (
    <>
      <span data-testid="location">{`${location.pathname}${location.search}`}</span>
      <span data-testid="nav-type">{navigationType}</span>
    </>
  );
}

function SubjectProbe() {
  const { subject } = useEvidenceSubject();
  const path = isAddressable(subject) ? subjectToUrl(subject) : "none";
  const label =
    subject.kind === "proposal"
      ? `${subject.kind}:${subject.domain ?? "cognition"}:${subject.proposalId}`
      : subject.kind;
  return (
    <>
      <span data-testid="subject">{label}</span>
      <span data-testid="subject-url">{path}</span>
    </>
  );
}

function renderRoute(initialEntry = "/proposals") {
  return render(
    <QueryClientProvider
      client={createTestQueryClient()}
    >
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/proposals/:proposalId?"
              element={<><ProposalsRoute /><LocationProbe /><SubjectProbe /></>}
            />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mathSummary: MathProposalSummary = {
  proposal_id: "math-proposal-1",
  domain: "math",
  shape_category: "numeric_reasoning",
  proposed_change_kind: "handler_route",
  structural_commonality: "arithmetic transfer",
  evidence_count: 2,
  replay_equivalence_hash: "sha256:math-replay",
};

const mathDetail: MathProposalDetail = {
  ...mathSummary,
  wrong_zero_assertion: "wrong=0 for sampled arithmetic corridor",
  proposed_change_payload: { route: "math" },
  reasoning_trace_id: "math-trace-1",
  reasoning_trace_steps: [
    {
      step_index: 1,
      step_kind: "compare",
      claim: "addition and subtraction share quantity state",
      justification: "same parse corridor",
      input_pointers: ["case-1"],
      output_payload: { ok: true },
    },
  ],
  evidence_hashes: ["sha256:evidence-1"],
  handler_name: null,
  suggested_ratify_cli: "core math proposal ratify math-proposal-1",
};

function stubMixedProposalFetch() {
  const fetchMock = vi.fn((rawUrl: string) => {
    const url = new URL(rawUrl);
    if (url.pathname === "/math-proposals") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: [mathSummary] } }),
      });
    }
    if (url.pathname === `/math-proposals/${mathDetail.proposal_id}`) {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: mathDetail }),
      });
    }
    if (url.pathname === `/proposals/${proposalDetail.proposal_id}`) {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: proposalDetail }),
      });
    }
    if (url.pathname === "/proposals") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: proposalSummaries } }),
      });
    }
    return Promise.resolve({
      json: () =>
        Promise.resolve({
          ok: false,
          generated_at: "now",
          error: { code: "not_found", message: `unexpected path ${url.pathname}` },
        }),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
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

  it("selecting a row writes the path param (replace) and renders detail", async () => {
    stubProposalFetch();
    const user = userEvent.setup();
    renderRoute("/proposals?state=pending");

    await user.click(await screen.findByRole("button", { name: /proposal-p/i }));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        `/proposals/${proposalDetail.proposal_id}?state=pending`,
      ),
    );
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    expect(await screen.findByText("Contemplation proposed a coherence relation.")).toBeInTheDocument();
  });

  it("restores selection from a deep-linked path param", async () => {
    stubProposalFetch();
    renderRoute(`/proposals/${proposalDetail.proposal_id}?state=pending`);

    expect(
      await screen.findByText("Contemplation proposed a coherence relation."),
    ).toBeInTheDocument();
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

  it("publishes math-domain selections as proposal inspector subjects", async () => {
    stubMixedProposalFetch();
    const user = userEvent.setup();
    renderRoute("/proposals?domain=math&state=pending");

    const row = (await screen.findByTitle("math-proposal-1")).closest('[role="button"]');
    expect(row).not.toBeNull();
    await user.click(row!);

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/proposals/math-proposal-1?domain=math&state=pending",
      ),
    );
    expect(screen.getByTestId("subject")).toHaveTextContent("proposal:math:math-proposal-1");
    expect(await screen.findByText("wrong=0 for sampled arithmetic corridor")).toBeInTheDocument();
  });

  it("keeps domain=math in the selected proposal evidence address", async () => {
    stubMixedProposalFetch();
    const user = userEvent.setup();
    renderRoute("/proposals?domain=math&state=pending");

    const row = (await screen.findByTitle("math-proposal-1")).closest('[role="button"]');
    expect(row).not.toBeNull();
    await user.click(row!);

    await waitFor(() =>
      expect(screen.getByTestId("subject-url")).toHaveTextContent(
        "/proposals/math-proposal-1?domain=math",
      ),
    );
  });
});

describe("SuggestedCLIBox", () => {
  it("shows the correct terminal review commands for a proposal id", () => {
    render(<SuggestedCLIBox proposalId="proposal-123" />);

    expect(screen.getByText("core teaching review --proposal-id proposal-123 --accept")).toBeInTheDocument();
    expect(screen.getByText("core teaching review --proposal-id proposal-123 --reject")).toBeInTheDocument();
  });
});
