import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useChatTurn } from "./queries";
import { WorkbenchApiError } from "./client";
import { happyChatTurn } from "../app/chat/fixtures";

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
      {children}
    </QueryClientProvider>
  );
}

describe("useChatTurn", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts /chat/turn with the prompt body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({ ok: true, generated_at: "now", data: happyChatTurn }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useChatTurn(), { wrapper });

    result.current.mutate({ prompt: "What is truth?" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/chat/turn",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ prompt: "What is truth?" }),
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it.each([
    [400, "bad_request"],
    [413, "read_error"],
  ])("%s surfaces as WorkbenchApiError %s", async (_status, code) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({
          ok: false,
          generated_at: "now",
          error: { code, message: "failed" },
        }),
      }),
    );
    const { result } = renderHook(() => useChatTurn(), { wrapper });

    result.current.mutate({ prompt: "" });
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(WorkbenchApiError);
    expect(result.current.error).toMatchObject({ code });
  });
});
