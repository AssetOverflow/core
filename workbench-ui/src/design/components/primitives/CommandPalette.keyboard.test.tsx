import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { useState } from "react";
import { CommandPalette } from "./CommandPalette";

vi.mock("../../../api/queries", () => ({
  useEvalLanes: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
}));

function PaletteHarness({ initialOpen = false }: { initialOpen?: boolean }) {
  const [open, setOpen] = useState(initialOpen);
  return (
    <MemoryRouter>
      <button type="button" onClick={() => setOpen(true)} aria-label="Open palette">
        Open
      </button>
      <CommandPalette open={open} onOpenChange={setOpen} />
    </MemoryRouter>
  );
}

describe("CommandPalette keyboard contract", () => {
  it("⌘K still opens the palette (regression)", async () => {
    const user = userEvent.setup();
    // We test the open prop directly — ⌘K is handled by the host (TopBar/PreviewPage)
    render(<PaletteHarness initialOpen={false} />);
    // Open via button
    await user.click(screen.getByRole("button", { name: "Open palette" }));
    expect(screen.getByRole("dialog", { name: "Command Palette" })).toBeInTheDocument();
  });

  it("Escape closes the palette (regression)", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);
    expect(screen.getByRole("dialog", { name: "Command Palette" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Command Palette" })).not.toBeInTheDocument();
  });

  it("ArrowDown/ArrowUp traverses all commands", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const dialog = screen.getByRole("dialog", { name: "Command Palette" });

    const items = dialog.querySelectorAll('[role="option"]');
    const lastIdx = items.length - 1;
    expect(items[0].getAttribute("aria-selected")).toBe("true");
    expect(items[1].getAttribute("aria-selected")).toBe("false");

    // ArrowDown moves to index 1
    await user.keyboard("{ArrowDown}");
    expect(items[0].getAttribute("aria-selected")).toBe("false");
    expect(items[1].getAttribute("aria-selected")).toBe("true");

    // ArrowDown to last
    for (let i = 1; i < lastIdx; i++) {
      await user.keyboard("{ArrowDown}");
    }
    expect(items[lastIdx].getAttribute("aria-selected")).toBe("true");

    // ArrowDown at end stays clamped
    await user.keyboard("{ArrowDown}");
    expect(items[lastIdx].getAttribute("aria-selected")).toBe("true");

    // ArrowUp moves back
    await user.keyboard("{ArrowUp}");
    expect(items[lastIdx - 1].getAttribute("aria-selected")).toBe("true");
  });

  it("Enter activates the focused command and closes the palette", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    // Focus is on index 0 = "Open Chat"
    // Press Enter to activate
    await user.keyboard("{Enter}");

    // Palette should close
    expect(screen.queryByRole("dialog", { name: "Command Palette" })).not.toBeInTheDocument();
  });

  it("fuzzy filter: typing 'ch' shows chat commands", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const input = screen.getByRole("textbox", { name: "Search commands" });
    await user.type(input, "ch");

    expect(screen.getByRole("button", { name: "Open Chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New chat session" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open Evals" })).not.toBeInTheDocument();
  });

  it("fuzzy filter: typing 'eval' shows Open Evals", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const input = screen.getByRole("textbox", { name: "Search commands" });
    await user.type(input, "eval");

    expect(screen.getByRole("button", { name: "Open Evals" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open Chat" })).not.toBeInTheDocument();
  });

  it("shows 'No commands match' when filter matches nothing", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const input = screen.getByRole("textbox", { name: "Search commands" });
    await user.type(input, "zzznomatch");

    expect(screen.getByText("No commands match.")).toBeInTheDocument();
  });
});
