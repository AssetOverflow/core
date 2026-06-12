import { render, screen } from "@testing-library/react";
import { EvidenceProvider, useEvidenceSubject } from "./evidenceContext";
import { RightInspector } from "./RightInspector";
import type { ChatTurnResult, ProposalDetail } from "../types/api";

const MOCK_TURN: ChatTurnResult = {
  prompt: "What is alpha?",
  surface: "alpha causes beta",
  articulation_surface: "alpha causes beta",
  walk_surface: "alpha -> beta",
  grounding_source: "teaching",
  epistemic_state: "decoded",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: "sha256:abc123def456",
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "runtime_turn",
  identity_verdict: null,
  safety_verdict: null,
  ethics_verdict: null,
  proposal_candidates: [],
  turn_cost_ms: 17,
  checkpoint_emitted: true,
};

function SetSubjectAndRender({
  kind,
}: {
  kind: "turn" | "none";
}) {
  const { setSubject } = useEvidenceSubject();
  if (kind === "turn") {
    setSubject({ kind: "turn", turnId: 1, data: MOCK_TURN });
  }
  return <RightInspector />;
}

function renderInspector(kind: "turn" | "none" = "none") {
  return render(
    <EvidenceProvider>
      <SetSubjectAndRender kind={kind} />
    </EvidenceProvider>,
  );
}

describe("RightInspector", () => {
  it("renders inspector region", () => {
    renderInspector();
    expect(document.querySelector('[data-region="inspector"]')).toBeInTheDocument();
  });

  it("shows empty hint when no subject selected", () => {
    renderInspector("none");
    expect(screen.getByText("Select an item to inspect its evidence.")).toBeInTheDocument();
  });

  it("shows turn data when turn subject is set", () => {
    renderInspector("turn");
    expect(screen.getByText("Turn #1")).toBeInTheDocument();
    expect(screen.getByText("17ms")).toBeInTheDocument();
  });

  it("shows keyboard shortcut hint", () => {
    renderInspector();
    expect(screen.getByText("⌘I")).toBeInTheDocument();
  });
});
