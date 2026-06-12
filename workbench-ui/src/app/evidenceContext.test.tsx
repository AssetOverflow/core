import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  MemoryRouter,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { EvidenceProvider, useEvidenceSubject } from "./evidenceContext";
import { EvidenceUrlSync } from "./evidenceUrlSync";
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
  const {
    subject,
    setSubject,
    clearSubject,
    inspectorOpen,
    toggleInspector,
    addressCopyCount,
    notifyAddressCopied,
  } = useEvidenceSubject();
  return (
    <div>
      <span data-testid="kind">{subject.kind}</span>
      <span data-testid="subject-id">
        {subject.kind === "proposal" ? subject.proposalId : ""}
      </span>
      <span data-testid="inspector">{inspectorOpen ? "open" : "closed"}</span>
      <span data-testid="copy-count">{addressCopyCount}</span>
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
      <button type="button" onClick={notifyAddressCopied}>
        notify-copied
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

  it("notifyAddressCopied increments the copy signal", () => {
    render(
      <EvidenceProvider>
        <TestConsumer />
      </EvidenceProvider>,
    );
    expect(screen.getByTestId("copy-count")).toHaveTextContent("0");
    fireEvent.click(screen.getByText("notify-copied"));
    fireEvent.click(screen.getByText("notify-copied"));
    expect(screen.getByTestId("copy-count")).toHaveTextContent("2");
  });
});

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return (
    <>
      <span data-testid="search">{location.search}</span>
      <span data-testid="nav-type">{navigationType}</span>
    </>
  );
}

function renderWithUrl(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <EvidenceProvider>
        <EvidenceUrlSync />
        <TestConsumer />
        <LocationProbe />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

describe("EvidenceUrlSync", () => {
  it("restores the inspector subject and open state from ?inspect=", () => {
    renderWithUrl("/proposals/abc?inspect=proposal:abc");
    expect(screen.getByTestId("kind")).toHaveTextContent("proposal");
    expect(screen.getByTestId("subject-id")).toHaveTextContent("abc");
    expect(screen.getByTestId("inspector")).toHaveTextContent("open");
  });

  it("drops a malformed ?inspect= from the URL and stays closed", async () => {
    renderWithUrl("/proposals?inspect=garbage");
    expect(screen.getByTestId("kind")).toHaveTextContent("none");
    expect(screen.getByTestId("inspector")).toHaveTextContent("closed");
    await waitFor(() =>
      expect(screen.getByTestId("search")).toHaveTextContent(/^$/),
    );
  });

  it("writes ?inspect= when the inspector opens on a subject, using replace", async () => {
    renderWithUrl("/chat");
    fireEvent.click(screen.getByText("set-turn"));
    fireEvent.click(screen.getByText("toggle"));
    await waitFor(() =>
      expect(screen.getByTestId("search")).toHaveTextContent("?inspect=turn%3A1"),
    );
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
  });

  it("removes ?inspect= when the inspector closes", async () => {
    renderWithUrl("/trace/1?inspect=turn:1");
    expect(screen.getByTestId("inspector")).toHaveTextContent("open");
    fireEvent.click(screen.getByText("toggle"));
    await waitFor(() =>
      expect(screen.getByTestId("search")).toHaveTextContent(/^$/),
    );
  });

  it("does not write ?inspect= while the inspector stays closed", async () => {
    renderWithUrl("/chat");
    fireEvent.click(screen.getByText("set-turn"));
    await waitFor(() =>
      expect(screen.getByTestId("kind")).toHaveTextContent("turn"),
    );
    expect(screen.getByTestId("search")).toHaveTextContent(/^$/);
  });
});
