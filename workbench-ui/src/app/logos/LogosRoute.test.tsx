import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type {
  LogosAlignmentRow,
  LogosPackContents,
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

function contentsFor(packId: string): LogosPackContents {
  const he = packId.includes("he");
  return {
    schema_version: "logos_pack_contents_v1",
    pack_id: packId,
    manifest: { pack_id: packId, role: he ? "depth_root" : "depth_relation", determinism_class: "D0" },
    lexicon: [
      {
        // grc's entry_id matches the warning safety report's dangling link.
        entry_id: he ? "he-001" : "logos.entry.1",
        surface: he ? "דבר" : "logos",
        lemma: he ? "דבר" : "logos",
        language: he ? "he" : "grc",
        part_of_speech: "NOUN",
        pos: "NOUN",
        morphology_id: he ? "he-morph-001" : "missing-morph",
        morphology_tags: [],
        semantic_domains: ["speech"],
        provenance_ids: ["John1:1"],
        epistemic_status: "speculative",
      },
      {
        entry_id: he ? "he-002" : "grc-002",
        surface: he ? "אמר" : "rhema",
        lemma: he ? "אמר" : "rhema",
        language: he ? "he" : "grc",
        part_of_speech: "VERB",
        pos: "VERB",
        morphology_id: null,
        morphology_tags: [],
        semantic_domains: ["cognition"],
        provenance_ids: [],
        epistemic_status: "coherent",
      },
    ],
    glosses: [
      {
        gloss_id: "gloss-1",
        lemma: he ? "דבר" : "logos",
        gloss: "word, matter, or spoken thing",
        pos: "NOUN",
        entry_ids: he ? ["he-001"] : ["logos.entry.1"],
        provenance_ids: [],
        epistemic_status: "speculative",
        raw: {},
      },
    ],
    morphology: [
      {
        morphology_id: he ? "he-morph-001" : "grc-morph-001",
        surface: he ? "דברים" : "logoi",
        lemma: he ? "דבר" : "logos",
        language: he ? "he" : "grc",
        root: he ? "דבר" : null,
        prefix_chain: [],
        stem: he ? null : "log",
        inflection: {},
        suffix_chain: he ? ["ים"] : ["oi"],
      },
    ],
    frames: [],
    compositions: [],
    alignment_edges: [],
    holonomy_cases: [],
  };
}

function alignmentFor(packId: string): LogosAlignmentRow[] {
  const he = packId.includes("he");
  return [
    {
      edge_id: "edge-1",
      source_id: he ? "he-001" : "grc-001",
      target_id: he ? "grc-001" : "en-024",
      relation: "cross_lang.logos.utterance",
      weight: 0.95,
      evidence_ids: ["John1:1", "Gen1:1"],
      target_pack_id: he ? "grc_logos_micro_v1" : "en_core_cognition_v1",
      target_resolved: true,
      invalid_target: false,
    },
    {
      edge_id: "edge-collapse",
      source_id: he ? "he-023" : "grc-023",
      target_id: "en-collapse-breath",
      relation: "cross_lang.no_english_collapse",
      weight: 0.0,
      evidence_ids: ["adr-0073c"],
      target_pack_id: null,
      target_resolved: false,
      invalid_target: true,
    },
  ];
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
    const contentsMatch = path.match(/^\/logos\/packs\/([^/]+)\/contents$/);
    if (contentsMatch) {
      const packId = decodeURIComponent(contentsMatch[1]);
      return Promise.resolve({
        json: async () => okEnvelope(contentsFor(packId)),
      });
    }
    const alignmentMatch = path.match(/^\/logos\/packs\/([^/]+)\/alignment$/);
    if (alignmentMatch) {
      const packId = decodeURIComponent(alignmentMatch[1]);
      return Promise.resolve({
        json: async () => okEnvelope({ items: alignmentFor(packId) }),
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

// happy-dom has no layout engine; the VirtualizedList virtualizer reads
// offsetWidth/offsetHeight (0x0) and renders nothing. Give elements a
// real-looking layout size so the contents-tab rows mount (same workaround
// as VirtualizedList.test.tsx).
const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get: () => 360,
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

  it("selects a pack, renders Overview, projects logos_pack evidence, and fetches contents + alignment", async () => {
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
    // LG-3 + LG-4 fetch contents and alignment eagerly on pack-select.
    expect(paths).toContain("/logos/packs/he_logos_micro_v1/contents");
    expect(paths).toContain("/logos/packs/he_logos_micro_v1/alignment");
  });

  it("renders Identity passport fields and the real pack manifest", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Identity" }));

    // Passport fields (from the overview).
    expect(await screen.findByText("manifest_digest")).toBeInTheDocument();
    expect(screen.getByText("source_manifest")).toBeInTheDocument();
    // The raw viewer now shows the actual manifest (from /contents), not a
    // projection of the overview.
    expect(screen.getByText("Raw manifest")).toBeInTheDocument();
    expect(screen.getByText(/\/determinism_class/)).toBeInTheDocument();
    expect(screen.getByText(/\/role/)).toBeInTheDocument();
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

  it("renders the Lexicon tab and projects a logos_entry evidence subject on select", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Lexicon" }));

    // Real lexicon rows from /contents, not recomputed.
    expect(await screen.findByText("דבר · דבר")).toBeInTheDocument();
    expect(screen.getByText("he-001")).toBeInTheDocument();

    await user.click(screen.getByText("דבר · דבר"));

    // Selecting an entry publishes a pack-scoped logos_entry subject + address.
    expect(await screen.findByText("CORE-Logos Entry")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "inspect=logos_entry%3Ahe_logos_micro_v1%2Fhe-001",
      ),
    );
  });

  it("flags a lexicon entry whose morphology link is dangling per the safety report", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    // grc safety reports entry logos.entry.1 -> missing-morph as dangling.
    renderRoute("/logos/grc_logos_cognition_v1");

    await user.click(await screen.findByRole("tab", { name: "Lexicon" }));

    expect(await screen.findByText("logos · logos")).toBeInTheDocument();
    expect(screen.getByText("dangling morphology")).toBeInTheDocument();
  });

  it("renders the Morphology tab chain in schema order (root then suffix)", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Morphology" }));

    expect(await screen.findByText("דברים · דבר")).toBeInTheDocument();
    // Chain renders root (√דבר) before the suffix (ים), never re-sorted.
    expect(screen.getByText("√דבר")).toBeInTheDocument();
    expect(screen.getByText("ים")).toBeInTheDocument();
    expect(screen.getByText("he-morph-001")).toBeInTheDocument();
  });

  it("renders the Glosses tab with linked entry ids", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Glosses" }));

    expect(await screen.findByText("word, matter, or spoken thing")).toBeInTheDocument();
    await user.click(screen.getByText("word, matter, or spoken thing"));
    expect(await screen.findByText("CORE-Logos Gloss")).toBeInTheDocument();
  });

  it("renders the Alignment tab, surfaces invalid targets, and projects a logos_alignment_edge subject", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Alignment" }));

    // Real edges from /alignment, deterministic graph, honest invalid-target warning.
    expect(
      await screen.findByLabelText("CORE-Logos cross-language alignment graph"),
    ).toBeInTheDocument();
    expect(screen.getByText("2 alignment edges")).toBeInTheDocument();
    expect(screen.getByText("1 invalid target")).toBeInTheDocument();
    expect(
      screen.getByText(/invalid target — en-collapse-breath resolves to no declared lexicon entry/),
    ).toBeInTheDocument();

    await user.click(screen.getByText("cross_lang.logos.utterance"));

    expect(await screen.findByText("CORE-Logos Alignment Edge")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "inspect=logos_alignment_edge%3Ahe_logos_micro_v1%2Fedge-1",
      ),
    );
  });

  it("never renders a holonomy tab or proof/success element, even with alignment present", async () => {
    stubLogosFetch();
    const user = userEvent.setup();
    renderRoute("/logos/he_logos_micro_v1");

    await user.click(await screen.findByRole("tab", { name: "Alignment" }));
    await screen.findByLabelText("CORE-Logos cross-language alignment graph");

    expect(screen.queryByRole("tab", { name: /holonomy/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/proof card/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/holonomy proof/i)).not.toBeInTheDocument();
  });
});
