import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import {
  AppleUmaReportRoute,
  APPLE_UMA_LOADING,
  APPLE_UMA_ABSENCE_STATEMENT,
  APPLE_UMA_ABSENCE_ACTION,
} from "./AppleUmaReportRoute";

const GENERATED_AT = "2026-06-14T00:00:00Z";

function stubFetch(data: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        json: async () => ({ ok: true, generated_at: GENERATED_AT, data }),
      }),
    ),
  );
}

function stubFetchPending() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<never>(() => {})),
  );
}

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/apple-uma"]}>
        <AppleUmaReportRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const STALE_REPORT = {
  read_only: true,
  report_id: "apple_uma_mechanical_sympathy_latest",
  source_path: "reports/apple_uma.json",
  source_digest: "sha256:1234567890abcdef",
  benchmark_name: "Apple Silicon UMA Mechanical Sympathy",
  benchmark_version: "1.0.0",
  metadata: {},
  backend_status: { native_status: false, using_rust: true },
  tracks: {
    available: ["rust"],
    required: ["mlx_exact_cga_recall"],
    missing_required: ["mlx_exact_cga_recall"],
    mlx_exact_cga_recall: {
      present: false,
      skipped: true,
      reason: "No MLX semantic-backend claim.",
      serving_authorized: false,
      case_count: 0,
      all_cases_parity_pass: false,
      cases: [],
    },
  },
  copy_boundaries: [],
  non_claims: ["No MLX semantic-backend claim."],
  claim_safety: {
    safe_claims: [],
    rust_backend_notes: [],
    known_copy_paths: [],
    known_zero_copy_input_paths: [],
    future_work: [],
  },
};

const MLX_PRESENT_REPORT = {
  read_only: true,
  report_id: "apple_uma_mechanical_sympathy_latest",
  source_path: "reports/apple_uma.json",
  source_digest: "sha256:1234567890abcdef",
  benchmark_name: "Apple Silicon UMA Mechanical Sympathy",
  benchmark_version: "1.0.0",
  metadata: {},
  backend_status: { native_status: true, using_rust: true },
  tracks: {
    available: ["rust", "mlx_exact_cga_recall"],
    required: ["mlx_exact_cga_recall"],
    missing_required: [],
    mlx_exact_cga_recall: {
      present: true,
      skipped: false,
      reason: null,
      serving_authorized: true,
      case_count: 1,
      all_cases_parity_pass: true,
      cases: [
        {
          N: 128,
          top_k: 5,
          p50_ms: 0.977,
          p95_ms: 1.2,
          mean_ms: 1.0,
          rows_per_sec: 1024,
          parity: { parity_pass: true },
          copy_in_boundary: "copy-in zero borrow",
          copy_out_boundary: "copy-out zero borrow",
        },
      ],
    },
  },
  copy_boundaries: [
    {
      path: "test-path",
      input: true,
      output: true,
      zero_copy_input: true,
    },
  ],
  non_claims: ["No MLX semantic-backend claim."],
  claim_safety: {
    safe_claims: [],
    rust_backend_notes: [],
    known_copy_paths: [],
    known_zero_copy_input_paths: [],
    future_work: [],
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AppleUmaReportRoute", () => {
  it("loading state shows APPLE_UMA_LOADING and never 'Thinking'", async () => {
    stubFetchPending();
    renderRoute();
    expect(await screen.findByText(APPLE_UMA_LOADING)).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("malformed/empty API shape renders APPLE_UMA_ABSENCE_STATEMENT and APPLE_UMA_ABSENCE_ACTION", async () => {
    stubFetch({});
    renderRoute();
    expect(await screen.findByText(APPLE_UMA_ABSENCE_STATEMENT)).toBeInTheDocument();
    expect(screen.getByText(APPLE_UMA_ABSENCE_ACTION)).toBeInTheDocument();
  });

  it("stale committed-report shape renders expected labels", async () => {
    stubFetch(STALE_REPORT);
    renderRoute();

    expect(await screen.findByText("Report artifact needs refresh")).toBeInTheDocument();
    expect(screen.getByText(/No MLX success is being inferred/)).toBeInTheDocument();
    expect(screen.getByText("track absent")).toBeInTheDocument();
    expect(screen.getByText("parity false")).toBeInTheDocument();
    expect(screen.getByText("serving authorized false")).toBeInTheDocument();
    expect(screen.getAllByText("No MLX semantic-backend claim.").length).toBeGreaterThan(0);
  });

  it("MLX-present shape renders expected metrics and copy boundaries", async () => {
    stubFetch(MLX_PRESENT_REPORT);
    renderRoute();

    expect(await screen.findByText("track present")).toBeInTheDocument();
    expect(screen.getByText("executed")).toBeInTheDocument();
    expect(screen.getByText("parity true")).toBeInTheDocument();
    expect(screen.getByText("serving authorized true")).toBeInTheDocument();
    expect(screen.getByText("128")).toBeInTheDocument();
    expect(screen.getByText("0.977")).toBeInTheDocument();
    expect(screen.getByText("copy-in zero borrow")).toBeInTheDocument();
    expect(screen.getByText("copy-out zero borrow")).toBeInTheDocument();
  });
});
