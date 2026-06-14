import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { LivedLifeRoute, LIVED_LIFE_ABSENCE_STATEMENT } from "./LivedLifeRoute";
import type { LivedLife } from "../../types/api";

/**
 * The Lived Life surface must render the continuous life HONESTLY: it shows the
 * heartbeat-over-uptime facts when a life is recorded, and it can NEVER paint a
 * breached field as valid. These assert the rendered content, not just that the
 * route mounts (the frontend analogue of the backend's non-vacuous tamper tests).
 */

const GENERATED_AT = "2026-06-14T00:00:00Z";

function stubFetch(life: LivedLife) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        json: async () => ({ ok: true, generated_at: GENERATED_AT, data: life }),
      }),
    ),
  );
}

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/lived-life"]}>
        <LivedLifeRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const HEALTHY: LivedLife = {
  schema_version: "lived_life_v1",
  status: "recorded",
  missing_reason: null,
  identity: "sha256:abcdef0123456789",
  heartbeats: 3,
  closure_observed: true,
  closure_held: true,
  closure_ceiling: 1e-6,
  final_checkpoint_ok: true,
  converged: true,
  total_facts_consolidated: 2,
  total_proposals_created: 0,
  current_identity: "sha256:abcdef0123456789", // matches identity -> would_resume
  resume_status: "would_resume",
  resume_summary:
    "a reboot resumes this life — its identity matches the current substrate",
  records: [
    {
      tick: 0,
      versor_condition: 8.2e-13,
      field_valid: true,
      facts_consolidated: 2,
      proposals_created: 0,
      pending_proposals: 0,
      did_work: true,
    },
    {
      tick: 1,
      versor_condition: 8.2e-13,
      field_valid: true,
      facts_consolidated: 0,
      proposals_created: 0,
      pending_proposals: 0,
      did_work: false,
    },
    {
      tick: 2,
      versor_condition: 8.2e-13,
      field_valid: true,
      facts_consolidated: 0,
      proposals_created: 0,
      pending_proposals: 0,
      did_work: false,
    },
  ],
  artifact: {
    artifact_id: "engine_state/lived_life.json",
    kind: "lived_life",
    path: "engine_state/lived_life.json",
    digest: "sha256:deadbeefcafe",
    created_at: null,
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LivedLifeRoute", () => {
  it("renders the continuous life: heartbeats, closure held, learned-while-idle, beats", async () => {
    stubFetch(HEALTHY);
    renderRoute();

    expect(await screen.findByText("One continuous life")).toBeInTheDocument();
    // Learned while idle (non-zero, from the records).
    expect(screen.getByText("2 learned while idle")).toBeInTheDocument();
    // Closure held below the ceiling (never claimed without observation).
    expect(screen.getAllByText(/closure held/i).length).toBeGreaterThan(0);
    // The heartbeat over uptime: each beat is shown.
    expect(screen.getByText("beat 0")).toBeInTheDocument();
    expect(screen.getByText("beat 2")).toBeInTheDocument();
    // A saturated life is at rest.
    expect(screen.getAllByText(/at rest/i).length).toBeGreaterThan(0);
    // The resume-as-same-life verdict is made felt: this life wakes up as itself.
    expect(screen.getByText(/resumes as same life/i)).toBeInTheDocument();
    expect(
      screen.getByText(/its identity matches the current substrate/i),
    ).toBeInTheDocument();
    // The per-reboot lineage chain is honestly cross-linked to Runs.
    expect(screen.getByRole("link", { name: /Runs/ })).toBeInTheDocument();
  });

  it("a breached beat surfaces the closure warning, never a false 'held'", async () => {
    const breached: LivedLife = {
      ...HEALTHY,
      heartbeats: 1,
      closure_held: false,
      converged: true,
      records: [
        {
          tick: 0,
          versor_condition: 5e-3, // breaches the 1e-6 ceiling
          field_valid: false,
          facts_consolidated: 0,
          proposals_created: 0,
          pending_proposals: 0,
          did_work: false,
        },
      ],
    };
    stubFetch(breached);
    renderRoute();

    expect(await screen.findByText(/closure BREACHED/i)).toBeInTheDocument();
    // The breached beat is marked INVALID, never painted valid.
    expect(screen.getByText("INVALID")).toBeInTheDocument();
    expect(screen.queryByText(/closure held/i)).not.toBeInTheDocument();
  });

  it("a changed substrate surfaces the would-refuse warning, never a false resume", async () => {
    const changed: LivedLife = {
      ...HEALTHY,
      current_identity: "sha256:0000different0000",
      resume_status: "substrate_changed",
      resume_summary:
        "the substrate changed — a reboot would refuse (IdentityContinuityError)",
    };
    stubFetch(changed);
    renderRoute();

    expect(
      (await screen.findAllByText(/substrate changed/i)).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText(/a reboot would refuse/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/resumes as same life/i)).not.toBeInTheDocument();
  });

  it("an absent artifact shows honest absence, never a fabricated life", async () => {
    const absent: LivedLife = {
      ...HEALTHY,
      status: "missing_evidence",
      missing_reason: "no always-on run has been persisted yet",
      identity: null,
      heartbeats: 0,
      closure_observed: false,
      closure_held: false,
      converged: false,
      total_facts_consolidated: 0,
      total_proposals_created: 0,
      current_identity: null,
      resume_status: "unknown",
      resume_summary:
        "resume verdict unavailable — the current substrate identity could not be recomputed",
      records: [],
      artifact: null,
    };
    stubFetch(absent);
    renderRoute();

    expect(
      await screen.findByText(LIVED_LIFE_ABSENCE_STATEMENT),
    ).toBeInTheDocument();
    // No fabricated heartbeat content.
    expect(screen.queryByText("One continuous life")).not.toBeInTheDocument();
    expect(screen.queryByText("beat 0")).not.toBeInTheDocument();
  });
});
