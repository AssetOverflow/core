import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { CalibrationClass, ServingMetrics } from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { EvidenceUrlSync } from "../evidenceUrlSync";
import { RightInspector } from "../RightInspector";
import { CalibrationRoute } from "./CalibrationRoute";

const classes: CalibrationClass[] = [
  {
    class_name: "unearned",
    correct: 0,
    wrong: 0,
    refused: 9,
    committed: 0,
    reliability_floor: 0.0,
    coverage: 0.0,
    propose_required: 0.85,
    propose_licensed: false,
    serve_required: 0.99,
    serve_licensed: false,
    source_path: "evals/gsm8k_math/practice/v1/report.json",
    source_digest: "sha256:practice",
  },
  {
    class_name: "additive",
    correct: 95,
    wrong: 5,
    refused: 50,
    committed: 100,
    reliability_floor: 0.860842,
    coverage: 0.66,
    propose_required: 0.85,
    propose_licensed: true,
    serve_required: 0.99,
    serve_licensed: false,
    source_path: "evals/gsm8k_math/practice/v1/report.json",
    source_digest: "sha256:practice",
  },
];

const metrics: ServingMetrics[] = [
  {
    lane: "train_sample",
    correct: 4,
    refused: 46,
    wrong: 0,
    sample_count: 50,
    source_path: "evals/gsm8k_math/train_sample/v1/report.json",
    source_digest: "sha256:aaaaaaaaaaaaaaaa",
  },
];

function renderRoute(initialEntry = "/calibration", withInspector = false) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <EvidenceUrlSync />
          <CalibrationRoute />
          {withInspector ? <RightInspector /> : null}
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function okBody(data: unknown) {
  return { ok: true, generated_at: "now", data };
}

function stub({ classesAvailable = true }: { classesAvailable?: boolean } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: unknown) => {
      const path = new URL(String(input)).pathname;
      if (path === "/calibration/classes") {
        return classesAvailable
          ? Promise.resolve({ json: () => Promise.resolve(okBody({ items: classes })) })
          : Promise.resolve({
              json: () =>
                Promise.resolve({
                  ok: false,
                  generated_at: "now",
                  error: { code: "evidence_unavailable", message: "no practice report" },
                }),
            });
      }
      if (path === "/serving/metrics") {
        return Promise.resolve({ json: () => Promise.resolve(okBody({ items: metrics })) });
      }
      return Promise.resolve({
        json: () =>
          Promise.resolve({ ok: false, generated_at: "now", error: { code: "not_found", message: path } }),
      });
    }),
  );
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("CalibrationRoute", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 560 });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: () => 520 });
  });

  afterEach(() => {
    if (offsetDescriptors.offsetHeight) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetDescriptors.offsetHeight);
    }
    if (offsetDescriptors.offsetWidth) {
      Object.defineProperty(HTMLElement.prototype, "offsetWidth", offsetDescriptors.offsetWidth);
    }
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders the gold-tether classes with their earned verdicts", async () => {
    stub();
    renderRoute();
    expect(await screen.findByText("additive")).toBeInTheDocument();
    expect(screen.getByText("unearned")).toBeInTheDocument();
    expect(screen.getByText("earned PROPOSE")).toBeInTheDocument();
    expect(screen.getByText("not yet licensed")).toBeInTheDocument();
  });

  it("surfaces the live serving outcome with wrong=0", async () => {
    stub();
    renderRoute();
    expect(await screen.findByText("train_sample")).toBeInTheDocument();
    // the discipline's result is present
    expect(screen.getByText("Live serving outcome — the discipline's result")).toBeInTheDocument();
    expect(screen.getAllByText("0 wrong").length).toBeGreaterThan(0);
  });

  it("shows the honest license math (measured vs θ) for a selected class", async () => {
    stub();
    const user = userEvent.setup();
    renderRoute();
    await user.click(await screen.findByText("additive"));
    await user.click(screen.getByRole("tab", { name: "License math" }));
    // PROPOSE licensed (>= 0.85), SERVE not (< 0.99)
    expect(screen.getAllByText(/licensed/).length).toBeGreaterThan(0);
    expect(screen.getByText(/core\.reliability_gate/)).toBeInTheDocument();
  });

  it("publishes the selected class as calibration evidence for the inspector", async () => {
    stub();
    const user = userEvent.setup();
    renderRoute("/calibration", true);
    await user.click(await screen.findByText("additive"));
    expect(screen.getByText("Calibration Class")).toBeInTheDocument();
    expect(screen.getByText(/licensed at θ 85\.0%/)).toBeInTheDocument();
    expect(screen.getAllByText("sha256:practice").length).toBeGreaterThan(0);
  });

  it("restores a selected calibration class from a deep link", async () => {
    stub();
    renderRoute("/calibration?inspect=calibration:additive", true);
    expect(await screen.findByText("Calibration Class")).toBeInTheDocument();
    expect(await screen.findByText(/licensed at θ 85\.0%/)).toBeInTheDocument();
  });

  it("fail-closed: an empty arena ledger renders the honest absence card, not an error", async () => {
    stub({ classesAvailable: false });
    renderRoute();
    expect(await screen.findByText(/No calibration evidence yet\./)).toBeInTheDocument();
    expect(screen.queryByText("What failed")).not.toBeInTheDocument();
  });

  it("moves the class list focus with j/k through the VirtualizedList spine", async () => {
    stub();
    const user = userEvent.setup();
    renderRoute();
    const list = await screen.findByRole("listbox", { name: "Calibration classes" });
    list.focus();
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");
  });
});
