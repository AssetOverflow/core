import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TruncatedCell } from "./TruncatedCell";

const LONG = "x".repeat(200);

describe("TruncatedCell", () => {
  it("shows the compact display and keeps the full value in title", () => {
    render(
      <TruncatedCell value="6ea18d4e5e9f1c2a3b4c" display="6ea18d4e5e…" label="proposal_id" />,
    );
    const display = screen.getByText("6ea18d4e5e…");
    expect(display).toBeInTheDocument();
    expect(display).toHaveAttribute("title", "6ea18d4e5e9f1c2a3b4c");
  });

  it("reveals the full value in a popover and copies it", async () => {
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);

    render(
      <TruncatedCell value="6ea18d4e5e9f1c2a3b4c" display="6ea18d4e5e…" label="proposal_id" />,
    );

    await userEvent.click(screen.getByRole("button", { name: /show full proposal_id/i }));
    // full value now visible in the revealed popover
    expect(screen.getByText("6ea18d4e5e9f1c2a3b4c")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /copy proposal_id/i }));
    expect(writeText).toHaveBeenCalledWith("6ea18d4e5e9f1c2a3b4c");

    writeText.mockRestore();
  });

  it("does not offer a modal for short values", async () => {
    render(<TruncatedCell value="short" label="source" />);
    await userEvent.click(screen.getByRole("button", { name: /show full source/i }));
    expect(screen.queryByRole("button", { name: /open full view/i })).not.toBeInTheDocument();
  });

  it("opens a modal with the full value for long values", async () => {
    render(<TruncatedCell value={LONG} label="source" />);
    await userEvent.click(screen.getByRole("button", { name: /show full source/i }));
    await userEvent.click(screen.getByRole("button", { name: /open full view/i }));
    expect(screen.getByRole("dialog", { name: "source" })).toBeInTheDocument();
  });

  it("does not bubble clicks to a surrounding row handler", async () => {
    const onRowClick = vi.fn();
    render(
      <div role="button" tabIndex={0} onClick={onRowClick}>
        <TruncatedCell value="6ea18d4e5e9f1c2a3b4c" label="proposal_id" />
      </div>,
    );
    await userEvent.click(screen.getByRole("button", { name: /show full proposal_id/i }));
    expect(onRowClick).not.toHaveBeenCalled();
  });
});
