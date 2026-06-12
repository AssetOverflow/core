import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { AuditEvent } from "../../types/api";
import { AuditRoute } from "./AuditRoute";

const events: AuditEvent[] = [
  {
    event_id: "audit-1",
    source: "operator_telemetry",
    source_path: "engine_state/telemetry.jsonl",
    timestamp: "2026-06-12T18:00:00Z",
    event_type: "telemetry_recorded",
    mutation_boundary: false,
    summary: "Operator telemetry recorded.",
    ref_id: "telemetry-1",
    payload_digest: "sha256:111111111111abcdef",
    payload: { value: 1 },
  },
  {
    event_id: "audit-2",
    source: "teaching_proposal_log",
    source_path: "teaching/proposals.jsonl",
    timestamp: "2026-06-12T18:01:00Z",
    event_type: "teaching_reviewed",
    mutation_boundary: true,
    summary: "Reviewed teaching proposal reached mutation boundary.",
    ref_id: "proposal-1",
    payload_digest: "sha256:222222222222abcdef",
    payload: { value: 2 },
  },
];

const nextPage: AuditEvent[] = [
  {
    event_id: "audit-next-1",
    source: "math_proposal_log",
    source_path: "math/proposals.jsonl",
    timestamp: "2026-06-12T18:02:00Z",
    event_type: "math_proposal_recorded",
    mutation_boundary: false,
    summary: "Math proposal recorded for review.",
    ref_id: "math-1",
    payload_digest: "sha256:333333333333abcdef",
    payload: { value: 3 },
  },
];

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

function okEnvelope(items: AuditEvent[]) {
  return {
    ok: true,
    generated_at: "2026-06-12T18:00:00Z",
    data: { items, limit: 50, offset: 0 },
  };
}

function stubAuditFetch(pages: Record<string, AuditEvent[]> = { "0": events }) {
  const fetchMock = vi.fn((input: unknown) => {
    const url = new URL(String(input));
    const offset = url.searchParams.get("offset") ?? "0";
    return Promise.resolve({
      json: () => Promise.resolve(okEnvelope(pages[offset] ?? [])),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <AuditRoute />
    </QueryClientProvider>,
  );
}

describe("AuditRoute", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => 560,
    });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
      configurable: true,
      get: () => 720,
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

  it("renders audit events in API order", async () => {
    stubAuditFetch();
    renderRoute();

    expect(await screen.findByText("Operator telemetry recorded.")).toBeInTheDocument();
    const options = screen.getAllByRole("option");
    expect(options[0]).toHaveTextContent("Operator telemetry recorded.");
    expect(options[1]).toHaveTextContent("Reviewed teaching proposal reached mutation boundary.");
  });

  it("filters by source or summary", async () => {
    stubAuditFetch();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("Operator telemetry recorded.");
    await user.type(screen.getByLabelText("Filter by source or summary"), "teaching");

    await waitFor(() => {
      expect(screen.queryByText("Operator telemetry recorded.")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Reviewed teaching proposal reached mutation boundary.")).toBeInTheDocument();
  });

  it("weights mutation-boundary events with a visible label", async () => {
    stubAuditFetch();
    renderRoute();

    const label = await screen.findByText("Mutation boundary");
    expect(label.closest("article")).toHaveClass("border-l-[var(--color-selected-border)]");
  });

  it("loads another API page without re-sorting existing events", async () => {
    const firstPage = Array.from({ length: 50 }, (_, index): AuditEvent => ({
      ...events[index % events.length],
      event_id: `audit-${index}`,
      summary: `Event ${index}`,
    }));
    const fetchMock = stubAuditFetch({ "0": firstPage, "50": nextPage });
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByRole("button", { name: "Load more" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[1][0])).toContain("offset=50");
    await waitFor(() => expect(screen.getByText(/51 events/)).toBeInTheDocument());
    expect(screen.getAllByRole("option")[0]).toHaveTextContent("Event 0");
  });

  it("renders the empty next action", async () => {
    stubAuditFetch({ "0": [] });
    renderRoute();

    expect(await screen.findByText("No audit events recorded.")).toBeInTheDocument();
    expect(screen.getByText("core audit events")).toBeInTheDocument();
  });

  it("renders the error contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          json: () =>
            Promise.resolve({
              ok: false,
              generated_at: "now",
              error: { code: "read_error", message: "synthetic audit failure" },
            }),
        }),
      ),
    );
    renderRoute();

    expect(await screen.findByText("What failed")).toBeInTheDocument();
    expect(screen.getByText("No audit mutation occurred.")).toBeInTheDocument();
    expect(screen.getByText("curl /audit/events")).toBeInTheDocument();
  });

  it("renders the specific loading state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<never>(() => {})));
    renderRoute();

    expect(await screen.findByText("Loading audit events...")).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });
});
