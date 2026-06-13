import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { PackDetail, PackSummary } from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { PacksRoute } from "./PacksRoute";

const summaries: PackSummary[] = [
  {
    pack_id: "en_core_cognition_v1",
    source: "language_pack",
    manifest_path: "language_packs/data/en_core_cognition_v1/manifest.json",
    version: "1",
    language: "en",
    modality: "text",
    determinism_class: "deterministic",
    checksum: "sha256:declared0000000000000000",
    checksums: {},
  },
  {
    pack_id: "safety_core_v1",
    source: "runtime_pack",
    manifest_path: "packs/runtime/safety_core_v1/manifest.json",
    version: "1",
    language: null,
    modality: null,
    determinism_class: "pinned",
    checksum: null,
    checksums: {},
  },
];

function detailFor(packId: string): PackDetail {
  const summary = summaries.find((s) => s.pack_id === packId) ?? summaries[0];
  return {
    ...summary,
    checksums: {
      lexicon_sha256: "sha256:aaaaaaaaaaaaaaaaaaaaaaaa",
      manifest_checksum: "sha256:bbbbbbbbbbbbbbbbbbbbbbbb",
    },
    manifest_digest: "sha256:cccccccccccccccccccccccc",
    manifest: {
      pack_id: packId,
      version: "1",
      lexicon: { entries: 128, sealed: true },
    },
  };
}

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return (
    <>
      <span data-testid="location">{`${location.pathname}${location.search}`}</span>
      <span data-testid="nav-type">{navigationType}</span>
    </>
  );
}

function renderRoute(initialEntry = "/packs") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/packs/:packId?"
              element={
                <>
                  <PacksRoute />
                  <LocationProbe />
                </>
              }
            />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubPacksFetch(items: PackSummary[] = summaries) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/packs") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    const match = path.match(/^\/packs\/(.+)$/);
    if (match) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            ok: true,
            generated_at: "now",
            data: detailFor(decodeURIComponent(match[1])),
          }),
      });
    }
    return Promise.resolve({
      json: () =>
        Promise.resolve({
          ok: false,
          generated_at: "now",
          error: { code: "not_found", message: `unexpected path ${path}` },
        }),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("PacksRoute", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => 560,
    });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
      configurable: true,
      get: () => 480,
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
    localStorage.clear();
  });

  it("renders packs with source, version, and determinism class", async () => {
    stubPacksFetch();
    renderRoute();

    expect(await screen.findByText("en_core_cognition_v1")).toBeInTheDocument();
    expect(screen.getByText("safety_core_v1")).toBeInTheDocument();
    expect(screen.getAllByText("Language pack").length).toBeGreaterThan(0);
    expect(screen.getByText("deterministic")).toBeInTheDocument();
    expect(screen.getByText("pinned")).toBeInTheDocument();
  });

  it("selecting a pack writes /packs/<packId> with replace and shows the manifest tree", async () => {
    stubPacksFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("en_core_cognition_v1"));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/packs/en_core_cognition_v1"),
    );
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    // manifest tree is the default tab — top-level keys render as treeitems
    const tree = await screen.findByRole("tree");
    expect(tree).toBeInTheDocument();
    expect(screen.getByText("lexicon")).toBeInTheDocument();
  });

  it("surfaces the manifest checksums as the verify affordance", async () => {
    stubPacksFetch();
    const user = userEvent.setup();
    renderRoute("/packs/en_core_cognition_v1");

    await user.click(await screen.findByRole("tab", { name: "Checksums" }));

    expect(await screen.findByText("manifest_digest")).toBeInTheDocument();
    expect(screen.getByText("lexicon_sha256")).toBeInTheDocument();
    expect(screen.getByText("manifest_checksum")).toBeInTheDocument();
    // the manifest_digest renders as a sha256 digest badge (full value in aria-label)
    expect(
      screen.getByLabelText(/Digest sha256:cccccccccccccccccccccccc/),
    ).toBeInTheDocument();
    // per-field checksum digests are present as the verify affordance
    expect(
      screen.getByLabelText(/Digest sha256:aaaaaaaaaaaaaaaaaaaaaaaa/),
    ).toBeInTheDocument();
  });

  it("moves the pack list focus with j/k through the VirtualizedList spine", async () => {
    stubPacksFetch();
    const user = userEvent.setup();
    renderRoute();

    const list = await screen.findByRole("listbox", { name: "Packs" });
    list.focus();
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("k");
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
  });
});
