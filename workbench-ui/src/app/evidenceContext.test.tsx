import { render, screen, fireEvent } from "@testing-library/react";
import { EvidenceProvider, useEvidenceSubject } from "./evidenceContext";
import type { ChatTurnResult } from "../types/api";

const MOCK_TURN: ChatTurnResult = {
  prompt: "test",
  surface: "answer",
  articulation_surface: "answer",
  walk_surface: "walk",
  grounding_source: "teaching",
  epistemic_state: "decoded",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: "sha256:abc",
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "runtime_turn",
  identity_verdict: null,
  safety_verdict: null,
  ethics_verdict: null,
  proposal_candidates: [],
  turn_cost_ms: 10,
  checkpoint_emitted: false,
};

function TestConsumer() {
  const { subject, setSubject, clearSubject, inspectorOpen, toggleInspector } =
    useEvidenceSubject();
  return (
    <div>
      <span data-testid="kind">{subject.kind}</span>
      <span data-testid="inspector">{inspectorOpen ? "open" : "closed"}</span>
      <button
        type="button"
        onClick={() => setSubject({ kind: "turn", turnId: 1, data: MOCK_TURN })}
      >
        set-turn
      </button>
      <button type="button" onClick={clearSubject}>
        clear
      </button>
      <button type="button" onClick={toggleInspector}>
        toggle
      </button>
    </div>
  );
}

describe("EvidenceContext", () => {
  it("starts with kind=none and inspector closed", () => {
    render(
      <EvidenceProvider>
        <TestConsumer />
      </EvidenceProvider>,
    );
    expect(screen.getByTestId("kind")).toHaveTextContent("none");
    expect(screen.getByTestId("inspector")).toHaveTextContent("closed");
  });

  it("setSubject updates kind", () => {
    render(
      <EvidenceProvider>
        <TestConsumer />
      </EvidenceProvider>,
    );
    fireEvent.click(screen.getByText("set-turn"));
    expect(screen.getByTestId("kind")).toHaveTextContent("turn");
  });

  it("clearSubject resets to none", () => {
    render(
      <EvidenceProvider>
        <TestConsumer />
      </EvidenceProvider>,
    );
    fireEvent.click(screen.getByText("set-turn"));
    expect(screen.getByTestId("kind")).toHaveTextContent("turn");
    fireEvent.click(screen.getByText("clear"));
    expect(screen.getByTestId("kind")).toHaveTextContent("none");
  });

  it("toggleInspector toggles open state", () => {
    render(
      <EvidenceProvider>
        <TestConsumer />
      </EvidenceProvider>,
    );
    expect(screen.getByTestId("inspector")).toHaveTextContent("closed");
    fireEvent.click(screen.getByText("toggle"));
    expect(screen.getByTestId("inspector")).toHaveTextContent("open");
    fireEvent.click(screen.getByText("toggle"));
    expect(screen.getByTestId("inspector")).toHaveTextContent("closed");
  });

  it("throws if used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      "useEvidenceSubject must be used within EvidenceProvider",
    );
    spy.mockRestore();
  });
});
