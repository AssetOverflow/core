import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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
    metadata: { concept: "truth" },
    versor_digest: "sha256:aaaaaaaaaaaaaaaaaaaa",
  },
  {
    entry_index: 1,
    epistemic_status: "speculative",
    epistemic_state: "inferred",
    metadata: { concept: "beauty" },
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
    expect(screen.getByText("coherent")).toBeInTheDocument();
    expect(screen.getByText("verified")).toBeInTheDocument();
    expect(screen.getByText("speculative")).toBeInTheDocument();
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

    await user.click(await screen.findByText("speculative"));

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
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");
  });
});
