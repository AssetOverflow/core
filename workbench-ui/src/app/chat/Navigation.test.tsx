import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { EvidenceStrip } from "./EvidenceStrip";
import { TraceDrawer } from "./TraceDrawer";
import { happyChatTurn } from "./fixtures";

describe("navigation hardening", () => {
  it("clicking trace_hash in EvidenceStrip fires onOpen('trace')", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<EvidenceStrip result={happyChatTurn} onOpen={onOpen} />);

    await user.click(screen.getByLabelText("Open trace evidence"));
    expect(onOpen).toHaveBeenCalledWith("trace");
  });

  it("proposal candidates in TraceDrawer link to /proposals/:id", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    const link = screen.getByText(`/proposals/${happyChatTurn.proposal_candidates[0].candidate_id}`);
    expect(link.closest("a")).toHaveAttribute(
      "href",
      `/proposals/${happyChatTurn.proposal_candidates[0].candidate_id}`,
    );
  });

  it("trace_hash region is focusable and activatable via keyboard", () => {
    const onOpen = vi.fn();
    render(<EvidenceStrip result={happyChatTurn} onOpen={onOpen} />);

    const region = screen.getByLabelText("Open trace evidence");
    expect(region).toHaveAttribute("tabIndex", "0");
    expect(region).toHaveAttribute("role", "button");
    fireEvent.keyDown(region, { key: "Enter" });
    expect(onOpen).toHaveBeenCalledWith("trace");
  });
});
