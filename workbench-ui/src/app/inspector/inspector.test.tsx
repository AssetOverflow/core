import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { Shell } from "../Shell";
import { RightInspector } from "../RightInspector";
import { InspectorProvider, useInspector } from "./InspectorStore";
import { ArtifactInspectorView } from "./views/ArtifactInspectorView";
import { ProposalInspectorView } from "./views/ProposalInspectorView";
import { TraceNodeInspectorView } from "./views/TraceNodeInspectorView";
import { ReplayDiffInspectorView } from "./views/ReplayDiffInspectorView";
import { RunsRoute } from "../runs/RunsRoute";
import { ProposalsRoute } from "../proposals/ProposalsRoute";
import { TraceRoute } from "../trace/TraceRoute";
import type {
  ArtifactDetail,
  ArtifactRef,
  ProposalDetail,
  ProposalSummary,
  ReplayComparison,
  RuntimeStatus,
} from "../../types/api";

vi.mock("../../api/queries", async () => {
  const actual = await vi.importActual<typeof import("../../api/queries")>(
    "../../api/queries",
  );
  return {
    ...actual,
    useArtifacts: vi.fn(),
    useArtifact: vi.fn(),
    useArtifactDetail: vi.fn(),
    useReplayComparison: vi.fn(),
    useProposals: vi.fn(),
    useProposalDetail: vi.fn(),
    useRuntimeStatus: vi.fn(),
  };
});

import {
  useArtifacts,
  useArtifact,
  useReplayComparison,
  useProposals,
  useProposalDetail,
  useRuntimeStatus,
} from "../../api/queries";

const mockArtifact: ArtifactDetail = {
  artifact_id: "art-1",
  kind: "trace",
  path: "traces/1.json",
  digest: "sha256:1",
  created_at: "2026-05-28T00:00:00Z",
  content_type: "json",
  content: {
    prompt: "?",
    surface: "user-facing answer",
    articulation_surface: "realizer answer",
    walk_surface: "[node-1 → node-2]",
    grounding_source: "vault",
    epistemic_state: "evidenced",
    normative_clearance: "cleared",
    normative_detail: "",
    trace_hash: "abcdef0123456789abcdef0123456789",
    refusal_emitted: false,
    hedge_injected: false,
    mutation_mode: "off",
    identity_verdict: { outcome: "cleared", runtime_detail: "" },
    safety_verdict: { outcome: "cleared", runtime_detail: "" },
    ethics_verdict: { outcome: "cleared", runtime_detail: "" },
    proposal_candidates: [],
    turn_cost_ms: 1,
    checkpoint_emitted: false,
  },
};

const mockProposal: ProposalDetail = {
  proposal_id: "prop-9",
  state: "pending",
  source_kind: "vault_recall",
  replay_equivalent: true,
  created_at: "2026-05-28T01:00:00Z",
  downstream_effect: "unknown",
  proposed_chain: null,
  replay_evidence: null,
  source: null,
  evidence: [],
  artifact_refs: [],
  suggested_cli: null,
};

const mockReplay: ReplayComparison = {
  artifact_id: "art-1",
  original_hash: "0123456789abcdef0123456789abcdef",
  replay_hash: "0123456789abcdef0123456789abcdef",
  equivalent: true,
  divergences: [
    { path: "/a", original: 1, replay: 1, severity: "info" },
    { path: "/b", original: 2, replay: 3, severity: "warning" },
    { path: "/c", original: 4, replay: 5, severity: "failure" },
  ],
};

const mockStatus: RuntimeStatus = {
  backend: "numpy",
  git_revision: "deadbeef",
  engine_state_present: true,
  checkpoint_revision: "cafe",
  revision_warning: false,
  active_session_id: null,
  mutation_mode: "read_only",
};

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function withProvider(ui: React.ReactNode, initialUrl = "/") {
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <InspectorProvider>{ui}</InspectorProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Inspector store", () => {
  beforeEach(() => {
    vi.mocked(useArtifact).mockReset();
    vi.mocked(useArtifacts).mockReset();
    vi.mocked(useReplayComparison).mockReset();
    vi.mocked(useProposals).mockReset();
    vi.mocked(useProposalDetail).mockReset();
    vi.mocked(useRuntimeStatus).mockReturnValue({
      data: mockStatus,
      isLoading: false,
      isError: false,
    } as any);
  });

  describe("no-provider fallback (preview / isolated harness)", () => {
    it("useInspector returns the default no-op state outside any provider", () => {
      let captured: ReturnType<typeof useInspector> | null = null;
      function Probe() {
        captured = useInspector();
        return null;
      }
      render(<Probe />);
      expect(captured).not.toBeNull();
      expect(captured!.state.collapsed).toBe(true);
      expect(captured!.state.entity).toBeNull();
      // calling the no-ops should not throw
      captured!.setEntity({ kind: "proposal", proposalId: "x" });
      captured!.setCollapsed(false);
      captured!.toggleCollapsed();
      expect(captured!.state.collapsed).toBe(true); // unchanged: still no-op
    });
  });

  describe("toggle behavior", () => {
    it("InspectorProvider starts collapsed; toggle flips it", () => {
      function Probe() {
        const { state, toggleCollapsed } = useInspector();
        return (
          <div>
            <span data-testid="state">
              {state.collapsed ? "collapsed" : "open"}
            </span>
            <button onClick={toggleCollapsed} data-testid="toggle">
              t
            </button>
          </div>
        );
      }
      render(
        <InspectorProvider>
          <Probe />
        </InspectorProvider>,
      );
      expect(screen.getByTestId("state").textContent).toBe("collapsed");
      fireEvent.click(screen.getByTestId("toggle"));
      expect(screen.getByTestId("state").textContent).toBe("open");
      fireEvent.click(screen.getByTestId("toggle"));
      expect(screen.getByTestId("state").textContent).toBe("collapsed");
    });

    it("Shell TopBar toggle button opens the inspector pane and reflects aria-expanded", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
      } as any);
      vi.mocked(useProposals).mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
      } as any);

      render(
        <QueryClientProvider client={makeClient()}>
          <MemoryRouter initialEntries={["/chat"]}>
            <Routes>
              <Route path="/" element={<Shell />}>
                <Route path="chat" element={<div data-testid="chat-stub" />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      const toggle = screen.getByTestId("topbar-inspector-toggle");
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
      expect(screen.queryByTestId("right-inspector")).not.toBeInTheDocument();

      fireEvent.click(toggle);
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
      expect(screen.getByTestId("right-inspector")).toBeInTheDocument();
    });
  });

  describe("RightInspector rendering by entity type", () => {
    function renderInspectorWithEntity(entity: Parameters<ReturnType<typeof useInspector>["setEntity"]>[0]) {
      function Wrapper() {
        const { setEntity, setCollapsed } = useInspector();
        useEffect(() => {
          if (entity) setEntity(entity);
          setCollapsed(false);
        }, [setEntity, setCollapsed]);
        return <RightInspector />;
      }
      return render(withProvider(<Wrapper />));
    }

    it("renders nothing when collapsed", () => {
      render(
        withProvider(
          <RightInspector collapsed={true} />,
        ),
      );
      expect(screen.queryByTestId("right-inspector")).not.toBeInTheDocument();
    });

    it("renders empty state when open with no entity", async () => {
      function Wrapper() {
        const { setCollapsed } = useInspector();
        useEffect(() => {
          setCollapsed(false);
        }, [setCollapsed]);
        return <RightInspector />;
      }
      render(withProvider(<Wrapper />));
      expect(await screen.findByTestId("inspector-empty")).toBeInTheDocument();
    });

    it("renders the artifact view for kind=artifact", async () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockArtifact,
        isLoading: false,
        isError: false,
      } as any);
      renderInspectorWithEntity({ kind: "artifact", artifactId: "art-1" });
      expect(await screen.findByTestId("inspector-artifact")).toBeInTheDocument();
    });

    it("renders the proposal view for kind=proposal", async () => {
      vi.mocked(useProposalDetail).mockReturnValue({
        data: mockProposal,
        isLoading: false,
        isError: false,
      } as any);
      renderInspectorWithEntity({ kind: "proposal", proposalId: "prop-9" });
      expect(await screen.findByTestId("inspector-proposal")).toBeInTheDocument();
    });

    it("renders the trace-node view with three surface elements (addendum §2)", async () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockArtifact,
        isLoading: false,
        isError: false,
      } as any);
      renderInspectorWithEntity({ kind: "trace-node", artifactId: "art-1" });
      const surfaces = await screen.findByTestId("inspector-trace-surfaces");
      expect(within(surfaces).getByTestId("inspector-trace-surface-surface")).toBeInTheDocument();
      expect(within(surfaces).getByTestId("inspector-trace-surface-articulation")).toBeInTheDocument();
      expect(within(surfaces).getByTestId("inspector-trace-surface-walk")).toBeInTheDocument();
    });

    it("renders the replay-diff view for kind=replay-diff", async () => {
      vi.mocked(useReplayComparison).mockReturnValue({
        data: mockReplay,
        isLoading: false,
        isError: false,
      } as any);
      renderInspectorWithEntity({ kind: "replay-diff", artifactId: "art-1" });
      expect(await screen.findByTestId("inspector-replay-diff")).toBeInTheDocument();
      const counts = screen.getByTestId("inspector-replay-counts");
      expect(counts.textContent).toMatch(/breaking/);
      expect(counts.textContent).toMatch(/material/);
      expect(counts.textContent).toMatch(/low/);
    });
  });

  describe("route → store wiring (publish on URL state)", () => {
    it("RunsRoute with ?runId publishes an artifact entity", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [
          {
            artifact_id: "art-1",
            kind: "trace",
            path: "p",
            digest: null,
            created_at: null,
          } satisfies ArtifactRef,
        ],
        isLoading: false,
        isError: false,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: mockArtifact,
        isLoading: false,
        isError: false,
      } as any);

      function Probe() {
        const { state } = useInspector();
        return <div data-testid="probe">{JSON.stringify(state.entity)}</div>;
      }
      render(
        <QueryClientProvider client={makeClient()}>
          <MemoryRouter initialEntries={["/runs?runId=art-1"]}>
            <InspectorProvider>
              <Routes>
                <Route path="/runs" element={<RunsRoute />} />
              </Routes>
              <Probe />
            </InspectorProvider>
          </MemoryRouter>
        </QueryClientProvider>,
      );
      expect(screen.getByTestId("probe").textContent).toContain('"kind":"artifact"');
      expect(screen.getByTestId("probe").textContent).toContain('"artifactId":"art-1"');
    });

    it("ProposalsRoute with ?proposal_id publishes a proposal entity", () => {
      vi.mocked(useProposals).mockReturnValue({
        data: [
          {
            proposal_id: "prop-9",
            state: "pending",
            source_kind: "vault",
            replay_equivalent: null,
            created_at: null,
            downstream_effect: "unknown",
          } satisfies ProposalSummary,
        ],
        isLoading: false,
        isError: false,
      } as any);
      vi.mocked(useProposalDetail).mockReturnValue({
        data: mockProposal,
        isLoading: false,
        isError: false,
      } as any);

      function Probe() {
        const { state } = useInspector();
        return <div data-testid="probe">{JSON.stringify(state.entity)}</div>;
      }
      render(
        <QueryClientProvider client={makeClient()}>
          <MemoryRouter initialEntries={["/proposals?proposal_id=prop-9"]}>
            <InspectorProvider>
              <Routes>
                <Route path="/proposals" element={<ProposalsRoute />} />
              </Routes>
              <Probe />
            </InspectorProvider>
          </MemoryRouter>
        </QueryClientProvider>,
      );
      expect(screen.getByTestId("probe").textContent).toContain('"kind":"proposal"');
      expect(screen.getByTestId("probe").textContent).toContain('"proposalId":"prop-9"');
    });

    it("TraceRoute with ?traceId publishes a trace-node entity", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [
          {
            artifact_id: "art-1",
            kind: "trace",
            path: "p",
            digest: null,
            created_at: null,
          } satisfies ArtifactRef,
        ],
        isLoading: false,
        isError: false,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: mockArtifact,
        isLoading: false,
        isError: false,
      } as any);

      function Probe() {
        const { state } = useInspector();
        return <div data-testid="probe">{JSON.stringify(state.entity)}</div>;
      }
      render(
        <QueryClientProvider client={makeClient()}>
          <MemoryRouter initialEntries={["/trace?traceId=art-1"]}>
            <InspectorProvider>
              <Routes>
                <Route path="/trace" element={<TraceRoute />} />
              </Routes>
              <Probe />
            </InspectorProvider>
          </MemoryRouter>
        </QueryClientProvider>,
      );
      expect(screen.getByTestId("probe").textContent).toContain('"kind":"trace-node"');
      expect(screen.getByTestId("probe").textContent).toContain('"artifactId":"art-1"');
    });
  });

  describe("read-only invariant", () => {
    it("ArtifactInspectorView, ProposalInspectorView, TraceNodeInspectorView, ReplayDiffInspectorView render without mutation affordances", () => {
      // Marker test: presence checked above; the actual enforcement lives in
      // the PR validation grep block. This test exists so the intent is
      // recorded on the test surface itself.
      expect(ArtifactInspectorView).toBeDefined();
      expect(ProposalInspectorView).toBeDefined();
      expect(TraceNodeInspectorView).toBeDefined();
      expect(ReplayDiffInspectorView).toBeDefined();
    });
  });
});
