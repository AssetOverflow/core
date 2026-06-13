import { act, fireEvent, render, screen } from "@testing-library/react";
import { useEffect } from "react";
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
  // Render-phase setSubject created an infinite synchronous render loop
  // (new subject object every pass) — the 100%-CPU spin previously
  // misdiagnosed as a teardown hang. State updates belong in effects.
  useEffect(() => {
    if (kind === "turn") {
      setSubject({ kind: "turn", turnId: 1, data: MOCK_TURN });
    }
  }, [kind, setSubject]);
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

  it("renders an honest not-loaded state for an identity-only subject", () => {
    function SetIdentityOnly() {
      const { setSubject } = useEvidenceSubject();
      useEffect(() => {
        setSubject({ kind: "proposal", proposalId: "proposal-xyz" });
      }, [setSubject]);
      return <RightInspector />;
    }
    render(
      <EvidenceProvider>
        <SetIdentityOnly />
      </EvidenceProvider>,
    );
    expect(screen.getByText("proposal-xyz")).toBeInTheDocument();
    expect(screen.getByText(/Detail not loaded in this session/)).toBeInTheDocument();
  });

  it("renders calibration class evidence instead of raw unknown", () => {
    function SetCalibrationClass() {
      const { setSubject } = useEvidenceSubject();
      useEffect(() => {
        setSubject({
          kind: "calibration_class",
          className: "additive",
          data: {
            class_name: "additive",
            correct: 95,
            wrong: 5,
            refused: 50,
            committed: 100,
            reliability_floor: 0.86084162,
            coverage: 0.666666667,
            propose_required: 0.85,
            propose_licensed: true,
            serve_required: 0.99,
            serve_licensed: false,
            source_path: "evals/gsm8k_math/practice/v1/report.json",
            source_digest: "sha256:practice",
          },
        });
      }, [setSubject]);
      return <RightInspector />;
    }
    render(
      <EvidenceProvider>
        <SetCalibrationClass />
      </EvidenceProvider>,
    );
    expect(screen.getByText("Calibration Class")).toBeInTheDocument();
    expect(screen.getByText("additive")).toBeInTheDocument();
    expect(screen.getByText(/licensed at θ 85\.0%/)).toBeInTheDocument();
    expect(screen.getByText("sha256:practice")).toBeInTheDocument();
  });

  it("shows a transient Copied confirmation after an address copy", () => {
    vi.useFakeTimers();
    try {
      function CopySignal() {
        const { notifyAddressCopied } = useEvidenceSubject();
        return (
          <>
            <button type="button" onClick={notifyAddressCopied}>
              signal-copy
            </button>
            <RightInspector />
          </>
        );
      }
      render(
        <EvidenceProvider>
          <CopySignal />
        </EvidenceProvider>,
      );

      expect(screen.queryByTestId("address-copied")).not.toBeInTheDocument();
      fireEvent.click(screen.getByText("signal-copy"));
      expect(screen.getByTestId("address-copied")).toHaveTextContent("Copied");

      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(screen.queryByTestId("address-copied")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
