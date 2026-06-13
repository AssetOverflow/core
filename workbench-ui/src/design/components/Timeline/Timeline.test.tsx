import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TIMELINE_PREVIEW_ENTRY, Timeline, type TimelineEntry } from "./Timeline";

const entries: TimelineEntry[] = [
  TIMELINE_PREVIEW_ENTRY,
  {
    id: "mutation-1",
    timestamp: "2026-06-12T18:01:00Z",
    source: "teaching_proposal_log",
    summary: "Reviewed teaching proposal crossed a mutation boundary.",
    mutationBoundary: true,
  },
];

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("Timeline", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => 360,
    });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
      configurable: true,
      get: () => 520,
    });
  });

  afterEach(() => {
    if (offsetDescriptors.offsetHeight) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetDescriptors.offsetHeight);
    }
    if (offsetDescriptors.offsetWidth) {
      Object.defineProperty(HTMLElement.prototype, "offsetWidth", offsetDescriptors.offsetWidth);
    }
    vi.restoreAllMocks();
  });

  it("renders entries in the delivered order", () => {
    render(
      <Timeline
        ariaLabel="Audit timeline"
        entries={entries}
        height={320}
        initialRect={{ width: 520, height: 360 }}
      />,
    );

    const options = screen.getAllByRole("option");
    expect(options[0]).toHaveTextContent("Operator telemetry recorded without mutation.");
    expect(options[1]).toHaveTextContent("Reviewed teaching proposal crossed a mutation boundary.");
  });

  it("labels mutation-boundary entries with selected-token border weight", () => {
    render(
      <Timeline
        ariaLabel="Audit timeline"
        entries={entries}
        height={320}
        initialRect={{ width: 520, height: 360 }}
      />,
    );

    const boundary = screen.getByText("Mutation boundary");
    expect(boundary).toBeInTheDocument();
    expect(boundary.closest("article")).toHaveClass("border-l-[var(--color-selected-border)]");
  });

  it("selects through the virtualized keyboard spine", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <Timeline
        ariaLabel="Audit timeline"
        entries={entries}
        height={320}
        initialRect={{ width: 520, height: 360 }}
        onSelect={onSelect}
      />,
    );

    const list = screen.getByRole("listbox", { name: "Audit timeline" });
    list.focus();
    await user.keyboard("j{Enter}");

    expect(onSelect).toHaveBeenCalledWith(entries[1]);
  });
});
