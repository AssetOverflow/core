import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";

describe("state components", () => {
  it("requires empty-state statement and next action", () => {
    render(<EmptyState statement="No trace selected." nextAction="Select a trace." />);
    expect(screen.getByText("No trace selected.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Select a trace." })).toBeInTheDocument();
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
