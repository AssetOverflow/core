import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactElement } from "react";
import { createTestQueryClient } from "../test/createTestQueryClient";
import { EvidenceProvider } from "./evidenceContext";
import { ChatRoute } from "../routes/ChatRoute";
import { ProposalsRoute } from "./proposals/ProposalsRoute";
import { TraceRoute } from "./trace/TraceRoute";
import { AuditRoute } from "./audit/AuditRoute";
import { EvalsRoute } from "./evals/EvalsRoute";
import { ReplayRoute } from "./replay/ReplayRoute";
import { DemoTheaterRoute } from "./demos/DemoTheaterRoute";
import { RunsRoute } from "./runs/RunsRoute";
import { PacksRoute } from "./packs/PacksRoute";
import { VaultRoute } from "./vault/VaultRoute";
import { SettingsRoute } from "./settings/SettingsRoute";

/**
 * ADR-0162 §6 route conformance — executable, not aspirational.
 *
 * Every implemented route must ship all three states:
 *  - empty:   a one-line absence statement + a next action
 *  - error:   what failed + mutation status + reproducer + retry safety
 *  - loading: a specific label (never "Thinking...")
 *
 * New routes (Wave R2+) add themselves to the tables below; a route that
 * cannot pass this test does not ship.
 */

const GENERATED_AT = "2026-06-12T00:00:00Z";

function okEnvelope(data: unknown) {
  return { ok: true, generated_at: GENERATED_AT, data };
}

const ERROR_ENVELOPE = {
  ok: false,
  generated_at: GENERATED_AT,
  error: { code: "read_error", message: "synthetic read failure" },
};

function emptyDataFor(path: string): unknown {
  if (path === "/evals") return { lanes: [] };
  return { items: [] };
}

type FetchPlan = "pending" | "error" | "empty";

function installFetch(plan: FetchPlan) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: unknown) => {
      if (plan === "pending") {
        return new Promise<never>(() => {});
      }
      const path = new URL(String(input)).pathname;
      const body = plan === "error" ? ERROR_ENVELOPE : okEnvelope(emptyDataFor(path));
      return Promise.resolve({ json: async () => body });
    }),
  );
}

// Routes mount the way App.tsx declares them: under their (param) path and
// inside EvidenceProvider, since routes publish their selection as the
// evidence subject (R0c).
function renderRoute(element: ReactElement, path = "/", initialEntry = "/") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route path={path} element={element} />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// Routes may render a contract-bearing state in more than one pane
// (list + detail), so assert "at least one", never "exactly one".
async function expectErrorContract() {
  expect((await screen.findAllByText("What failed")).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Mutation status").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Reproducer").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Retry safety").length).toBeGreaterThan(0);
  // The mutation-status line is load-bearing (ADR-0162 §6 / CLAUDE.md).
  expect(screen.getAllByText(/No .*mutation occurred\./).length).toBeGreaterThan(0);
}

function expectEmptyContract(statement: string, command: string) {
  expect(screen.getAllByText(statement).length).toBeGreaterThan(0);
  expect(screen.getAllByText(command).length).toBeGreaterThan(0);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

interface MountRouteSpec {
  name: string;
  element: ReactElement;
  path: string;
  initialEntry: string;
  loadingLabel: string;
  emptyStatement: string;
  emptyCommand: string;
}

const MOUNT_ROUTES: MountRouteSpec[] = [
  {
    name: "Audit",
    element: <AuditRoute />,
    path: "/audit",
    initialEntry: "/audit",
    loadingLabel: "Loading audit events...",
    emptyStatement: "No audit events recorded.",
    emptyCommand: "core audit events",
  },
  {
    name: "Trace",
    element: <TraceRoute />,
    path: "/trace/:turnId?",
    initialEntry: "/trace",
    loadingLabel: "Loading trace...",
    emptyStatement: "No turns recorded yet. Use Chat to create evidence.",
    emptyCommand: "core chat",
  },
  {
    name: "Proposals",
    element: <ProposalsRoute />,
    path: "/proposals/:proposalId?",
    initialEntry: "/proposals",
    loadingLabel: "Loading proposal queue...",
    emptyStatement: "No proposals match this queue view.",
    emptyCommand: "core teaching proposals --state pending",
  },
  {
    name: "Evals",
    element: <EvalsRoute />,
    path: "/evals/:laneId?",
    initialEntry: "/evals",
    loadingLabel: "Loading eval lanes...",
    emptyStatement: "No eval lanes discovered.",
    emptyCommand: "core eval --list",
  },
  {
    name: "Runs",
    element: <RunsRoute />,
    path: "/runs/:sessionId?",
    initialEntry: "/runs",
    loadingLabel: "Loading runs...",
    emptyStatement: "No runs recorded yet. Use Chat to create evidence.",
    emptyCommand: "core chat",
  },
  {
    name: "Replay",
    element: <ReplayRoute />,
    path: "/replay/:turnId?",
    initialEntry: "/replay",
    loadingLabel: "Loading turns...",
    emptyStatement: "No turns recorded yet. Use Chat to create evidence.",
    emptyCommand: "core chat",
  },
  {
    name: "Demos",
    element: <DemoTheaterRoute />,
    path: "/demos/:demoId?",
    initialEntry: "/demos",
    loadingLabel: "Loading demos...",
    emptyStatement: "No demos registered.",
    emptyCommand: "core demo --list",
  },
  {
    name: "Packs",
    element: <PacksRoute />,
    path: "/packs/:packId?",
    initialEntry: "/packs",
    loadingLabel: "Loading packs...",
    emptyStatement: "No packs discovered.",
    emptyCommand: "core pack validate <path>",
  },
  {
    name: "Vault",
    element: <VaultRoute />,
    path: "/vault",
    initialEntry: "/vault",
    loadingLabel: "Loading vault...",
    // Fail-closed: absence of a persisted vault is the primary contract.
    emptyStatement:
      "No persisted vault. Session memory is held in-process and discarded on exit; persistence is opt-in via RuntimeConfig.persist_session_state.",
    emptyCommand: "Set RuntimeConfig.persist_session_state = true",
  },
];

describe.each(MOUNT_ROUTES)("route conformance: $name", (spec) => {
  it("loading: shows a specific label, never 'Thinking...'", async () => {
    installFetch("pending");
    renderRoute(spec.element, spec.path, spec.initialEntry);
    expect(await screen.findByText(spec.loadingLabel)).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("error: surfaces what failed, mutation status, reproducer, retry safety", async () => {
    installFetch("error");
    renderRoute(spec.element, spec.path, spec.initialEntry);
    await expectErrorContract();
  });

  it("empty: states what is absent and offers a next action", async () => {
    installFetch("empty");
    renderRoute(spec.element, spec.path, spec.initialEntry);
    expect((await screen.findAllByText(spec.emptyStatement)).length).toBeGreaterThan(0);
    expectEmptyContract(spec.emptyStatement, spec.emptyCommand);
  });
});

describe("route conformance: Chat (interaction-driven states)", () => {
  async function submitPrompt() {
    const user = userEvent.setup();
    await user.type(
      screen.getByPlaceholderText("Ask CORE a question..."),
      "hello",
    );
    await user.click(screen.getByRole("button", { name: /submit/i }));
    return user;
  }

  it("empty (initial): states what is absent and offers a next action", () => {
    installFetch("empty");
    renderRoute(<ChatRoute />);
    expectEmptyContract("Ask CORE a question.", "core chat");
  });

  it("loading: shows a specific label after submit, never 'Thinking...'", async () => {
    installFetch("pending");
    renderRoute(<ChatRoute />);
    await submitPrompt();
    expect(await screen.findByText("Awaiting turn...")).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("error: surfaces what failed, mutation status, reproducer, retry safety", async () => {
    installFetch("error");
    renderRoute(<ChatRoute />);
    await submitPrompt();
    await expectErrorContract();
  });
});

// Settings has no empty state — the preferences panel always renders — so it
// carries a bespoke loading/error contract over its read-only status fetch.
describe("route conformance: Settings (no empty state — prefs always render)", () => {
  it("loading: shows a specific label and the CLI-only statement, never 'Thinking...'", async () => {
    installFetch("pending");
    renderRoute(<SettingsRoute />);
    expect(await screen.findByText("Loading runtime status...")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Engine configuration is CLI-only. This page mutates nothing on the server.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("error: surfaces what failed, mutation status, reproducer, retry safety", async () => {
    installFetch("error");
    renderRoute(<SettingsRoute />);
    await expectErrorContract();
  });
});
