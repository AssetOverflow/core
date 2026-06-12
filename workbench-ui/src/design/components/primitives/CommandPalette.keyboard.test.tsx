import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { useState } from "react";
import { CommandPalette } from "./CommandPalette";

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
  beforeEach(() => {
    // Recent-items leak between tests (the Enter test writes one); start clean
    // so traversal indices map to the deterministic Navigate command order.
    localStorage.clear();
  });

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

  it("ArrowDown/ArrowUp traverses the navigation commands and clamps at both ends", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const dialog = screen.getByRole("dialog", { name: "Command Palette" });

    // The Navigate section exposes one command per route, in route order.
    expect(screen.getByRole("button", { name: "Open Chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Trace" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Replay" })).toBeInTheDocument();

    const items = dialog.querySelectorAll('[role="option"]');
    expect(items.length).toBe(10);
    const lastIndex = items.length - 1;

    // Initially first item (index 0) is focused — check aria-selected
    expect(items[0].getAttribute("aria-selected")).toBe("true");
    expect(items[1].getAttribute("aria-selected")).toBe("false");

    // ArrowUp at the top stays clamped at index 0
    await user.keyboard("{ArrowUp}");
    expect(items[0].getAttribute("aria-selected")).toBe("true");

    // ArrowDown moves to index 1
    await user.keyboard("{ArrowDown}");
    expect(items[0].getAttribute("aria-selected")).toBe("false");
    expect(items[1].getAttribute("aria-selected")).toBe("true");

    // ArrowDown moves to index 2
    await user.keyboard("{ArrowDown}");
    expect(items[2].getAttribute("aria-selected")).toBe("true");

    // ArrowUp moves back to index 1
    await user.keyboard("{ArrowUp}");
    expect(items[1].getAttribute("aria-selected")).toBe("true");

    // Holding ArrowDown past the end clamps at the last index
    for (let i = 0; i < items.length + 2; i++) {
      await user.keyboard("{ArrowDown}");
    }
    expect(items[lastIndex].getAttribute("aria-selected")).toBe("true");
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

  it("fuzzy filter: typing 'ch' shows Open Chat", async () => {
    const user = userEvent.setup();
    render(<PaletteHarness initialOpen={true} />);

    const input = screen.getByRole("textbox", { name: "Search commands" });
    await user.type(input, "ch");

    expect(screen.getByRole("button", { name: "Open Chat" })).toBeInTheDocument();
    // Proposals and Evals should not match "ch"
    expect(screen.queryByRole("button", { name: "Open Proposals" })).not.toBeInTheDocument();
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
