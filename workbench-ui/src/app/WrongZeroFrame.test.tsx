import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../test/createTestQueryClient";
import type { ServingMetrics } from "../types/api";
import { WrongZeroFrame } from "./WrongZeroFrame";

function renderFrame() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <WrongZeroFrame />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stub(metrics: ServingMetrics[] | "error") {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      metrics === "error"
        ? Promise.resolve({
            json: () =>
              Promise.resolve({
                ok: false,
                generated_at: "now",
                error: { code: "read_error", message: "boom" },
              }),
          })
        : Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: metrics } }),
          }),
    ),
  );
}

function lane(correct: number, refused: number, wrong: number, name: string): ServingMetrics {
  return {
    lane: name,
    correct,
    refused,
    wrong,
    sample_count: correct + refused + wrong,
    source_path: `evals/${name}/report.json`,
    source_digest: "sha256:x",
  };
}

describe("WrongZeroFrame", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("aggregates the live serving triplet across lanes with wrong load-bearing", async () => {
    stub([lane(4, 46, 0, "train_sample"), lane(5, 495, 0, "holdout_dev")]);
    renderFrame();
    // 9 correct · 541 refused · 0 wrong
    expect(await screen.findByText(/9 correct · 541 refused ·/)).toBeInTheDocument();
    expect(screen.getByText("0 wrong")).toBeInTheDocument();
    // it links to the discipline behind it
    expect(screen.getByRole("link")).toHaveAttribute("href", "/calibration");
  });

  it("is a mirror — renders a non-zero wrong honestly, not a hard-coded zero", async () => {
    stub([lane(90, 5, 5, "drifted")]);
    renderFrame();
    expect(await screen.findByText("5 wrong")).toBeInTheDocument();
    expect(screen.queryByText("0 wrong")).not.toBeInTheDocument();
  });

  it("renders an honest 'metrics unavailable', never a fake zero, on error", async () => {
    stub("error");
    renderFrame();
    expect(await screen.findByText(/metrics unavailable/)).toBeInTheDocument();
    expect(screen.queryByText("0 wrong")).not.toBeInTheDocument();
  });
});
