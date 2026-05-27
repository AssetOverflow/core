import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, fetchProposalDetail, fetchProposals, WorkbenchApiError } from "./client";
import { proposalDetail, proposalSummaries } from "./__fixtures__/proposals";

describe("apiFetch", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses ok:true envelope and returns data", async () => {
    const mockData = { backend: "numpy", git_revision: "abc123" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({ ok: true, generated_at: "2026-01-01T00:00:00Z", data: mockData }),
      }),
    );

    const result = await apiFetch("/runtime/status");
    expect(result).toEqual(mockData);
  });

  it("throws WorkbenchApiError on ok:false envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({
          ok: false,
          generated_at: "2026-01-01T00:00:00Z",
          error: { code: "runtime_unavailable", message: "Server is offline" },
        }),
      }),
    );

    await expect(apiFetch("/runtime/status")).rejects.toThrow(WorkbenchApiError);
    await expect(apiFetch("/runtime/status")).rejects.toMatchObject({
      code: "runtime_unavailable",
      message: "Server is offline",
    });
  });

  it("AbortController fires on timeout (never-resolving fetch)", async () => {
    vi.useFakeTimers();

    const abortMock = vi.fn();
    const originalAbortController = global.AbortController;

    // Replace AbortController to track abort calls
    const mockController = {
      signal: { aborted: false } as AbortSignal,
      abort: abortMock,
    };
    vi.stubGlobal("AbortController", vi.fn(() => mockController));

    // fetch never resolves
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));

    const fetchPromise = apiFetch("/runtime/status");

    // Advance past the 5s timeout
    await vi.advanceTimersByTimeAsync(6000);

    expect(abortMock).toHaveBeenCalled();

    // Clean up
    global.AbortController = originalAbortController;
    vi.useRealTimers();
    // fetchPromise will never resolve but that's expected
    fetchPromise.catch(() => {});
  });
});

describe("proposal fetchers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("unwraps the /proposals items envelope and applies a state filter locally", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({
          ok: true,
          generated_at: "now",
          data: { items: proposalSummaries },
        }),
      }),
    );

    await expect(fetchProposals("accepted")).resolves.toEqual([proposalSummaries[1]]);
  });

  it("fetches proposal detail without mutating the proposal log", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({ ok: true, generated_at: "now", data: proposalDetail }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchProposalDetail("proposal/detail id")).resolves.toEqual(proposalDetail);
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8765/proposals/proposal%2Fdetail%20id");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBeUndefined();
  });
});
