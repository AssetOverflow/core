import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";

describe("state components", () => {
  it("requires empty-state statement and next action", () => {
    render(<EmptyState statement="No trace selected." nextAction="Select a trace." />);
    expect(screen.getByText("No trace selected.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Select a trace." })).toBeInTheDocument();
  });

  it("renders cli-form nextAction as mono command row with copy button", async () => {
    // navigator.clipboard is configured in setup.ts — spy on the existing mock
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);

    render(
      <EmptyState
        statement="Chat — no data loaded yet."
        nextAction={{ kind: "cli", command: "core chat" }}
      />,
    );

    expect(screen.getByText("Chat — no data loaded yet.")).toBeInTheDocument();
    // command shown in mono row
    expect(screen.getByText("core chat")).toBeInTheDocument();
    // copy button present
    const copyBtn = screen.getByRole("button", { name: /copy/i });
    expect(copyBtn).toBeInTheDocument();
    // clicking it writes to clipboard
    await userEvent.click(copyBtn);
    expect(writeText).toHaveBeenCalledWith("core chat");

    writeText.mockRestore();
  });

  it("renders every error-state contract field", () => {
    render(
      <ErrorState
        whatFailed="Preview fixture failed to parse."
        mutationStatus="No mutation attempted."
        reproducer="pnpm test"
        retrySafety="Retry is read-only."
      />,
    );
    expect(screen.getByText("What failed")).toBeInTheDocument();
    expect(screen.getByText("Mutation status")).toBeInTheDocument();
    expect(screen.getByText("Reproducer")).toBeInTheDocument();
    expect(screen.getByText("Retry safety")).toBeInTheDocument();
  });

  it("requires a specific loading label and caps shimmer cycles", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<LoadingState label="Thinking..." />)).toThrow();
    consoleError.mockRestore();
    render(<LoadingState label="Loading trace fixture." />);
    expect(screen.getByText("Loading trace fixture.")).toBeInTheDocument();
    expect(document.querySelector("[data-shimmer-cycles='2']")).toBeInTheDocument();
  });
});
