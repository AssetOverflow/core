import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EvidenceStrip } from "./EvidenceStrip";
import { happyChatTurn, refusalChatTurn } from "./fixtures";

describe("EvidenceStrip", () => {
  it("renders badges for a happy-path turn", () => {
    render(<EvidenceStrip result={happyChatTurn} onOpen={vi.fn()} />);

    expect(screen.getByText("Pack")).toBeInTheDocument();
    expect(screen.getByText("Decoded")).toBeInTheDocument();
    expect(screen.getByText("Cleared")).toBeInTheDocument();
    expect(screen.getByText("Checkpoint")).toBeInTheDocument();
    expect(screen.getByText("Runtime Turn")).toBeInTheDocument();
  });

  it("renders suppressed and refusal label for a refused turn", () => {
    render(<EvidenceStrip result={refusalChatTurn} onOpen={vi.fn()} />);

    expect(screen.getByText("Suppressed")).toBeInTheDocument();
    expect(screen.getByText("Refusal")).toBeInTheDocument();
  });

  it("opens the drawer when a badge is clicked", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<EvidenceStrip result={happyChatTurn} onOpen={onOpen} />);

    await user.click(screen.getByLabelText("Open grounding evidence"));

    expect(onOpen).toHaveBeenCalledWith("grounding");
  });
});
