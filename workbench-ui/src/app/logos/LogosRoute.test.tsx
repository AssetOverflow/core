import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type {
  LogosPackOverview,
  LogosPackSummary,
  LogosSafetyReport,
  SafetyVerdict,
} from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { RightInspector } from "../RightInspector";
import { LogosRoute } from "./LogosRoute";

const summaries: LogosPackSummary[] = [
  {
    pack_id: "he_logos_micro_v1",
    language: "he",
    role: "depth_root",
    script: "Hebrew",
    version: "1.0.0",
    determinism_class: "D0",
    gate_engaged: true,
    oov_policy: "fail_closed",
    lexicon_count: 3,
    gloss_count: 2,
    morphology_count: 3,
    frame_count: 0,
    composition_count: 0,
    alignment_edge_count: 4,
    holonomy_case_count: 0,
    safety_status: "unknown",
    manifest_digest: "sha256:aaaaaaaaaaaaaaaa",
    manifest_path: "language_packs/data/he_logos_micro_v1/manifest.json",
  },
  {
    pack_id: "grc_logos_cognition_v1",
    language: "grc",
    role: "depth_relation",
    script: "Greek",
    version: "1.0.0",
    determinism_class: "D0",
    gate_engaged: true,
    oov_policy: "fail_closed",
    lexicon_count: 5,
    gloss_count: 5,
    morphology_count: 5,
    frame_count: 0,
    composition_count: 0,
    alignment_edge_count: 8,
    holonomy_case_count: 0,
    safety_status: "warning",
    manifest_digest: "sha256:bbbbbbbbbbbbbbbb",
    manifest_path: "language_packs/data/grc_logos_cognition_v1/manifest.json",
  },
];

function overviewFor(packId: string): LogosPackOverview {
  const summary = summaries.find((item) => item.pack_id === packId) ?? summaries[0];
  return {
    ...summary,
    schema_version: "logos_pack_overview_v1",
    normalization_policy: "NFC",
    source_manifest: "logos-source-manifest.json",
    known_gaps: packId.includes("grc") ? ["undeclared English collapse anchors"] : [],
  };
}

function safetyFor(
  packId: string,
  verdict: SafetyVerdict = packId.includes("grc") ? "warning" : "unknown",
): LogosSafetyReport {
  return {
    schema_version: "logos_safety_report_v1",
    pack_id: packId,
    checksum_status: verdict === "warning" ? "warning" : "unknown",
    checksum_errors: verdict === "warning" ? ["alignment checksum pending review"] : [],
    domain_contract: { valid: verdict !== "failed", domain_id: "hebrew_greek_textual_reasoning" },
    domain_contract_status: verdict === "failed" ? "failed" : "unknown",
    oov_policy_ok: true,
    gate_policy_ok: true,
    path_safety_ok: true,
    dangling_morphology_links: verdict === "warning"
      ? [{ entry_id: "logos.entry.1", morphology_id: "missing-morph" }]
      : [],
    invalid_alignment_targets: verdict === "warning"
      ? [
          {
            edge_id: "edge-warning-1",
            source_id: "grc-logos",
            target_id: "en-collapse-logos",
            relation: "logos-collapse",
            target_pack_id: "en_core_cognition_v1",
          },
        ]
      : [],
    missing_holonomy_refs: "unknown",
    epistemic_status_counts: { speculative: 5, contested: verdict === "warning" ? 1 : 0 },
    speculative_entries: ["logos.entry.1", "logos.entry.2"],
    contested_entries: verdict === "warning" ? ["logos.entry.3"] : [],
    falsified_entries: [],
    known_gaps: verdict === "warning" ? ["no holonomy refs"] : [],
    verdict,
  };
}

function okEnvelope(data: unknown) {
  return { ok: true, generated_at: "2026-06-14T00:00:00Z", data };
}

function stubLogosFetch() {
  const paths: string[] = [];
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    paths.push(path);
    if (path === "/logos/packs") {
      return Promise.resolve({
        json: async () => okEnvelope({ items: summaries }),
      });
    }
    const safetyMatch = path.match(/^\/logos\/packs\/([^/]+)\/safety$/);
    if (safetyMatch) {
      const packId = decodeURIComponent(safetyMatch[1]);
      return Promise.resolve({
        json: async () => okEnvelope(safetyFor(packId)),
      });
    }
    const overviewMatch = path.match(/^\/logos\/packs\/([^/]+)$/);
    if (overviewMatch) {
      const packId = decodeURIComponent(overviewMatch[1]);
      return Promise.resolve({
        json: async () => okEnvelope(overviewFor(packId)),
      });
    }
    return Promise.resolve({
      json: async () => ({
        ok: false,
        generated_at: "2026-06-14T00:00:00Z",
        error: { code: "not_found", message: `unexpected path ${path}` },
      }),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { paths, fetchMock };
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{`${location.pathname}${location.search}`}</span>;
}

function renderRoute(initialEntry = "/logos") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/logos/:logosPackId?"
              element={
                <div className="grid grid-cols-[1fr_20rem]">
                  <div>
                    <LogosRoute />
                    <LocationProbe />
                  </div>
                  <RightInspector />
                </div>
              }
            />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("LogosRoute", () => {
  it("renders the grouped Pack Universe and persistent read-only status", async () => {
    stubLogosFetch();
    renderRoute();

    expect(await screen.findByText("Pack Universe")).toBeInTheDocument();
    expect(screen.getAllByText("Depth root").length).toBeGreaterThan(0);
    expect(screen.getByText("Logos cognition")).toBeInTheDocument();
    expect(screen.getByText("he_logos_micro_v1")).toBeInTheDocument();
    expect(screen.getByText("grc_logos_cognition_v1")).toBeInTheDocument();
    expect(screen.getByText("proposal mode: none — read-only")).toBeInTheDocument();
    expect(screen.getByText("no pack selected")).toBeInTheDocument();
    expect(screen.queryByText(/Draft proposal/i)).not.toBeInTheDocument();
  });

  it("selects a pack, renders Overview, projects logos_pack evidence, and avoids deferred endpoints", async () => {
    const { paths } = stubLogosFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("he_logos_micro_v1"));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/logos/he_logos_micro_v1"),
    );
    expect(await screen.findByText("depth-root compression")).toBeInTheDocument();
    expect(screen.getByText("operational articulation")).toBeInTheDocument();
    expect(screen.getByText("depth-relation precision")).toBeInTheDocument();
    expect(screen.getByText("holonomy_cases · missing_evidence")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /holonomy/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/proof card/i)).not.toBeInTheDocument();
    expect(screen.getByText("CORE-Logos Pack")).toBeInTheDocument();
    expect(screen.getByText("0 / missing_evidence")).toBeInTheDocument();
    expect(paths).not.toContain("/logos/packs/he_logos_micro_v1/contents");
    expect(paths).not.toContain("/logos/packs/he_logos_micro_v1/alignment");
  });

  it("renders Identity passport fields and the raw live overview projection", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Identity" }));

    expect(await screen.findByText("manifest_digest")).toBeInTheDocument();
    expect(screen.getByText("source_manifest")).toBeInTheDocument();
    expect(screen.getByText("Raw overview projection")).toBeInTheDocument();
    expect(screen.getByText(/\/manifest_digest/)).toBeInTheDocument();
    expect(screen.getByText(/\/schema_version/)).toBeInTheDocument();
  });

  it("renders Safety warnings and unknown holonomy without mapping either to clear", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/grc_logos_cognition_v1");

    await user.click(await screen.findByRole("tab", { name: "Safety" }));

    expect(await screen.findByText("Invalid alignment targets")).toBeInTheDocument();
    expect(screen.getByText("en-collapse-logos")).toBeInTheDocument();
    expect(screen.getByText("Dangling morphology links")).toBeInTheDocument();
    expect(screen.getByText("missing-morph")).toBeInTheDocument();
    expect(screen.getByText("missing_holonomy_refs")).toBeInTheDocument();
    expect(screen.getAllByText("Warning").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unknown").length).toBeGreaterThan(0);
    expect(screen.queryByText("Clear")).not.toBeInTheDocument();
  });
});
