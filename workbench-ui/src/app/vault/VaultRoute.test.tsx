import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { VaultEntry, VaultSummary } from "../../types/api";
import { EvidenceProvider, useEvidenceSubject } from "../evidenceContext";
import { VaultRoute } from "./VaultRoute";

const summary: VaultSummary = {
  source_path: "engine_state/session_state.json",
  entry_count: 2,
  store_count: 1,
  reproject_interval: 64,
  max_entries: 4096,
  persisted: true,
};

const entries: VaultEntry[] = [
  {
    entry_index: 0,
    epistemic_status: "coherent",
    epistemic_state: "verified",
    metadata: { concept: "truth", propositional_form: "alpha causes beta" },
    versor_digest: "sha256:aaaaaaaaaaaaaaaaaaaa",
  },
  {
    entry_index: 1,
    epistemic_status: "speculative",
    epistemic_state: "inferred",
    metadata: { concept: "beauty", promotion_certificate_digest: "sha256:certcert" },
    versor_digest: "sha256:bbbbbbbbbbbbbbbbbbbb",
  },
];

function SubjectProbe() {
  const { subject } = useEvidenceSubject();
  return (
    <span data-testid="subject">
      {subject.kind === "vault_entry" ? `vault_entry:${subject.entryIndex}` : subject.kind}
    </span>
  );
}

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/vault"]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/vault"
              element={
                <>
                  <VaultRoute />
                  <SubjectProbe />
                </>
              }
            />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function okBody(data: unknown) {
  return { ok: true, generated_at: "now", data };
}

function evidenceUnavailable(message: string) {
  return { ok: false, generated_at: "now", error: { code: "evidence_unavailable", message } };
}

function stubVault({ persisted = true }: { persisted?: boolean } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: unknown) => {
      const path = new URL(String(input)).pathname;
      if (path === "/vault/summary") {
        return persisted
          ? Promise.resolve({ json: () => Promise.resolve(okBody(summary)) })
          : Promise.resolve({
              json: () =>
                Promise.resolve(evidenceUnavailable("vault evidence unavailable: not persisted")),
            });
      }
      if (path === "/vault/entries") {
        return Promise.resolve({ json: () => Promise.resolve(okBody({ items: entries })) });
      }
      return Promise.resolve({
        json: () => Promise.resolve(evidenceUnavailable(`unexpected ${path}`)),
      });
    }),
  );
}

// A persisted snapshot that holds zero entries — distinct from absence. The
// entries query stays disabled (entry_count === 0), so /vault/entries is never
// hit; an unexpected hit fails the stub loudly.
function stubVaultPersistedEmpty() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: unknown) => {
      const path = new URL(String(input)).pathname;
      if (path === "/vault/summary") {
        return Promise.resolve({
          json: () => Promise.resolve(okBody({ ...summary, entry_count: 0 })),
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve(evidenceUnavailable(`unexpected ${path}`)),
      });
    }),
  );
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("VaultRoute", () => {
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

  it("fail-closed: an absent vault renders the honest absence card inside Vault chrome, not an error", async () => {
    stubVault({ persisted: false });
    renderRoute();

    expect(
      await screen.findByText(/No persisted vault snapshot is available\./),
    ).toBeInTheDocument();
    // framed as the Vault route, not a context-free card floating in a blank
    // surface (the "nothing comes up" symptom)
    expect(screen.getByRole("heading", { name: "Vault" })).toBeInTheDocument();
    // the statement still names the opt-in flag
    expect(screen.getByText(/RuntimeConfig\.persist_session_state/)).toBeInTheDocument();
    // the next action is a real, runnable command (copyable), not a dead button
    expect(screen.getByText("core always-on")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    // it is NOT the generic error contract
    expect(screen.queryByText("What failed")).not.toBeInTheDocument();
  });

  it("persisted-but-empty: distinguishes 'no entries yet' from absence, still framed as Vault", async () => {
    stubVaultPersistedEmpty();
    renderRoute();

    expect(
      await screen.findByText(/Vault snapshot exists, but no entries have been stored yet\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vault" })).toBeInTheDocument();
    // it is a DIFFERENT statement from absence, and not the generic error
    expect(
      screen.queryByText(/No persisted vault snapshot is available\./),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("What failed")).not.toBeInTheDocument();
  });

  it("renders the summary strip and entries when persisted", async () => {
    stubVault();
    renderRoute();

    expect(await screen.findByText("entry_count")).toBeInTheDocument();
    expect(screen.getByText("reproject_interval")).toBeInTheDocument();
    // Scope row pills to the listbox — the status <select> also renders
    // "coherent"/"speculative" as <option> text.
    const list = screen.getByRole("listbox", { name: "Vault entries" });
    expect(within(list).getByText("coherent")).toBeInTheDocument();
    expect(within(list).getByText("verified")).toBeInTheDocument();
    expect(within(list).getByText("speculative")).toBeInTheDocument();
  });

  it("never invents a similarity / relevance score (exact-recall doctrine)", async () => {
    stubVault();
    renderRoute();

    await screen.findByText("entry_count");
    expect(screen.queryByText(/similarity|relevance|score/i)).not.toBeInTheDocument();
  });

  it("selecting an entry publishes the vault_entry subject", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    // Click entry 1's state pill ("inferred") — unambiguous; "speculative"
    // now also appears as a status <select> option.
    await user.click(await screen.findByText("inferred"));

    await waitFor(() =>
      expect(screen.getByTestId("subject")).toHaveTextContent("vault_entry:1"),
    );
  });

  it("moves entry focus with j/k through the VirtualizedList spine", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    const list = await screen.findByRole("listbox", { name: "Vault entries" });
    list.focus();
    // Scope to the listbox: the status <select> also owns role="option" nodes.
    expect(within(list).getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(within(list).getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");
  });

  // Scope row counting to the listbox — the status <select> also owns options.
  function visibleRows() {
    return within(
      screen.getByRole("listbox", { name: "Vault entries" }),
    ).getAllByRole("option");
  }

  it("status facet narrows entries to the chosen epistemic_status", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("entry_count");
    expect(visibleRows()).toHaveLength(2);

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Filter by epistemic status" }),
      "coherent",
    );
    const rows = visibleRows();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("verified"); // entry 0 (coherent/verified)
  });

  it("'Has proposition' facet keeps only entries carrying propositional_form", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("entry_count");
    await user.click(screen.getByRole("switch", { name: "Has proposition" }));

    const rows = visibleRows();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("verified"); // entry 0 has propositional_form
  });

  it("'Has promotion digest' facet keeps only certified entries", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("entry_count");
    await user.click(screen.getByRole("switch", { name: "Has promotion digest" }));

    const rows = visibleRows();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("inferred"); // entry 1 (speculative/inferred) has the digest
  });

  it("text search reaches metadata values, not just epistemic labels", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("entry_count");
    await user.type(
      screen.getByPlaceholderText("Filter by status, state, index, or metadata"),
      "beauty",
    );

    // SearchInput debounces ~150ms before it propagates onChange.
    await waitFor(() => expect(visibleRows()).toHaveLength(1));
    expect(visibleRows()[0]).toHaveTextContent("inferred"); // entry 1 metadata.concept = "beauty"
  });

  it("a filter that matches nothing stays filter-empty, not persistence guidance", async () => {
    stubVault();
    const user = userEvent.setup();
    renderRoute();

    await screen.findByText("entry_count");
    await user.type(
      screen.getByPlaceholderText("Filter by status, state, index, or metadata"),
      "no-such-entry",
    );

    // SearchInput debounces ~150ms before it propagates onChange.
    await waitFor(() =>
      expect(screen.getByText("No vault entries match this filter.")).toBeInTheDocument(),
    );
    // NOT the absence/persistence guidance
    expect(
      screen.queryByText(/No persisted vault snapshot is available\./),
    ).not.toBeInTheDocument();
  });
});
