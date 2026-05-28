import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { TraceDrawer } from "./TraceDrawer";
import { happyChatTurn, refusalChatTurn } from "./fixtures";

describe("TraceDrawer", () => {
  it("renders all three layers from a ChatTurnResult", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Turn metadata")).toBeInTheDocument();
    expect(screen.getByText("Surfaces")).toBeInTheDocument();
    expect(screen.getByText("Grounding")).toBeInTheDocument();
    expect(screen.getByText("Verdicts")).toBeInTheDocument();
    expect(screen.getByText("Proposal candidates")).toBeInTheDocument();
    expect(screen.getByText("Trace hash + replay")).toBeInTheDocument();
    expect(screen.getByText("Stable JSON viewer")).toBeInTheDocument();
    expect(screen.getByText("Raw payload")).toBeInTheDocument();
    expect(screen.getByTestId("json-rows")).toBeInTheDocument();
  });

  it("surfaces layer-one field names", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/turn_cost_ms:/)).toBeInTheDocument();
    expect(screen.getByText(/mutation_mode:/)).toBeInTheDocument();
    expect(screen.getByText(/checkpoint_emitted:/)).toBeInTheDocument();
    expect(screen.getByText(/grounding_source:/)).toBeInTheDocument();
  });

  it("renders all three surfaces distinctly with labels", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/^surface/)).toBeInTheDocument();
    expect(screen.getByText(/^articulation_surface/)).toBeInTheDocument();
    expect(screen.getByText(/^walk_surface/)).toBeInTheDocument();
    expect(screen.getByText("(user-facing response)")).toBeInTheDocument();
    expect(screen.getByText("(realizer output)")).toBeInTheDocument();
    expect(screen.getByText("(manifold evidence)")).toBeInTheDocument();
  });

  it("renders 'not emitted' when articulation_surface or walk_surface is null", () => {
    const nullSurfaces = { ...happyChatTurn, articulation_surface: null, walk_surface: null };
    render(
      <MemoryRouter>
        <TraceDrawer result={nullSurfaces} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    const notEmitted = screen.getAllByText("not emitted");
    expect(notEmitted.length).toBe(2);
  });

  it("renders refusal panel with violated boundary detail", () => {
    render(
      <MemoryRouter>
        <TraceDrawer result={refusalChatTurn} open onOpenChange={vi.fn()} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Refusal")).toBeInTheDocument();
    expect(screen.getAllByText(/evidence_required/).length).toBeGreaterThan(0);
  });

  it("Esc closes the drawer", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <MemoryRouter>
        <TraceDrawer result={happyChatTurn} open onOpenChange={onOpenChange} />
      </MemoryRouter>,
    );

    await user.keyboard("{Escape}");

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("focuses close on open and restores focus on close", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <MemoryRouter>
          <button type="button" onClick={() => setOpen(true)}>
            Open trace drawer
          </button>
          <TraceDrawer result={happyChatTurn} open={open} onOpenChange={setOpen} />
        </MemoryRouter>
      );
    }
    const user = userEvent.setup();
    render(<Harness />);

    const trigger = screen.getByRole("button", { name: "Open trace drawer" });
    trigger.focus();
    await user.click(trigger);
    await waitFor(() => expect(screen.getByRole("button", { name: "Close trace drawer" })).toHaveFocus());
    await user.click(screen.getByRole("button", { name: "Close trace drawer" }));
    await waitFor(() => expect(trigger).toHaveFocus());
  });
});
