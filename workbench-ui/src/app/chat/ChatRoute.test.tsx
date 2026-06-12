import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatRoute } from "../../routes/ChatRoute";
import { happyChatTurn } from "./fixtures";

function renderRoute() {
  const client = createTestQueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ChatRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChatRoute", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders composer and empty state initially", () => {
    renderRoute();

    expect(screen.getByPlaceholderText("Ask CORE a question...")).toBeInTheDocument();
    expect(screen.getByText("Ask CORE a question.")).toBeInTheDocument();
  });

  it("submits the typed prompt to useChatTurn", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({ ok: true, generated_at: "now", data: happyChatTurn }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByPlaceholderText("Ask CORE a question..."), "What is truth?");
    await user.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1].body).toBe(JSON.stringify({ prompt: "What is truth?" }));
  });

  it("disables composer and renders Awaiting turn while pending", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    const user = userEvent.setup();
    renderRoute();

    const textarea = screen.getByPlaceholderText("Ask CORE a question...");
    await user.type(textarea, "What is truth?");
    await user.click(screen.getByRole("button", { name: /submit/i }));

    expect(screen.getByText("Awaiting turn...")).toBeInTheDocument();
    expect(textarea).toBeDisabled();
  });

  it("renders response and evidence badges on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({ ok: true, generated_at: "now", data: happyChatTurn }),
      }),
    );
    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByPlaceholderText("Ask CORE a question..."), "What is truth?");
    await user.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText(happyChatTurn.surface)).toBeInTheDocument();
    expect(screen.getByText("Pack")).toBeInTheDocument();
    expect(screen.getByText("Cleared")).toBeInTheDocument();
  });

  it("renders ErrorState fields on WorkbenchApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({
          ok: false,
          generated_at: "now",
          error: { code: "bad_request", message: "prompt must be non-empty" },
        }),
      }),
    );
    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByPlaceholderText("Ask CORE a question..."), "x");
    await user.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByText("What failed")).toBeInTheDocument();
    expect(screen.getByText("Mutation status")).toBeInTheDocument();
    expect(screen.getByText("Reproducer")).toBeInTheDocument();
    expect(screen.getByText("Retry safety")).toBeInTheDocument();
  });
});
