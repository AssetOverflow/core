import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { TraceDrawer } from "./TraceDrawer";
import { happyChatTurn } from "./fixtures";

describe("trace_hash stability", () => {
  it("mounting, navigating panels, and unmounting the trace drawer does not mutate trace_hash", async () => {
    const hashBefore = happyChatTurn.trace_hash;
    const resultRef = { ...happyChatTurn };

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <MemoryRouter>
          <button type="button" data-testid="trigger" onClick={() => setOpen(true)}>
            open
          </button>
          <TraceDrawer result={resultRef} open={open} focus="metadata" onOpenChange={setOpen} />
        </MemoryRouter>
      );
    }

    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByTestId("trigger"));
    await waitFor(() => expect(screen.getByText("Turn metadata")).toBeInTheDocument());

    expect(screen.getByText("Surfaces")).toBeInTheDocument();
    expect(screen.getByText("Grounding")).toBeInTheDocument();
    expect(screen.getByText("Verdicts")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByText("Turn metadata")).not.toBeInTheDocument());

    await user.click(screen.getByTestId("trigger"));
    await waitFor(() => expect(screen.getByText("Turn metadata")).toBeInTheDocument());

    expect(resultRef.trace_hash).toBe(hashBefore);

    await user.keyboard("{Escape}");
    expect(resultRef.trace_hash).toBe(hashBefore);
  });

  it("trace_hash value displayed in drawer matches the result object", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open focus="trace" onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    expect(
      screen.getByLabelText(`trace_hash: ${happyChatTurn.trace_hash}`),
    ).toBeInTheDocument();
  });
});
