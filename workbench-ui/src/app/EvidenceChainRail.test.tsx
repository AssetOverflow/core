import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceChainRail, deriveStages } from "./EvidenceChainRail";
import type { EvidenceSubject } from "./evidenceContext";
import type { ChatTurnResult, ProposalDetail } from "../types/api";

const FULL_TURN: ChatTurnResult = {
  prompt: "What is alpha?",
  surface: "alpha causes beta",
  articulation_surface: "alpha causes beta",
  walk_surface: "alpha -> beta",
  grounding_source: "teaching",
  epistemic_state: "decoded",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: "sha256:abc123",
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "runtime_turn",
  identity_verdict: null,
  safety_verdict: null,
  ethics_verdict: null,
  proposal_candidates: [],
  turn_cost_ms: 17,
  checkpoint_emitted: true,
};

function turnSubject(data: ChatTurnResult | undefined): EvidenceSubject {
  return { kind: "turn", turnId: 1, data } as EvidenceSubject;
}

function statusOf(subject: EvidenceSubject, stageId: string): string {
  const stages = deriveStages(subject);
  const found = stages?.find((s) => s.id === stageId);
  if (!found) throw new Error(`stage not derived: ${stageId}`);
  return found.status;
}

describe("EvidenceChainRail honesty contract", () => {
  it("a fully-evidenced turn lights exactly the applicable stages", () => {
    const subject = turnSubject(FULL_TURN);
    expect(statusOf(subject, "intent")).toBe("lit");
    expect(statusOf(subject, "subject")).toBe("lit");
    expect(statusOf(subject, "provenance")).toBe("lit");
    expect(statusOf(subject, "admissibility")).toBe("lit");
    expect(statusOf(subject, "replay")).toBe("lit");
    expect(statusOf(subject, "authority")).toBe("lit");
    expect(statusOf(subject, "action")).toBe("dim");
  });

  it("MEANINGFULLY FAILS: removing a single field hollows exactly its stage", () => {
    // This is the test that breaks if anyone makes the rail infer status
    // instead of deriving it from the named field.
    const noHash = turnSubject({ ...FULL_TURN, trace_hash: "" });
    expect(statusOf(noHash, "replay")).toBe("hollow");
    expect(statusOf(noHash, "provenance")).toBe("lit");

    const noGrounding = turnSubject({ ...FULL_TURN, grounding_source: "" as ChatTurnResult["grounding_source"] });
    expect(statusOf(noGrounding, "provenance")).toBe("hollow");
    expect(statusOf(noGrounding, "replay")).toBe("lit");
  });

  it("identity-only subject (detail not loaded): applicable stages are hollow, never lit", () => {
    const subject = turnSubject(undefined);
    for (const id of ["intent", "provenance", "admissibility", "replay", "authority"]) {
      expect(statusOf(subject, id)).toBe("hollow");
    }
    expect(statusOf(subject, "subject")).toBe("lit");
  });

  it("proposal: replay_equivalent=false is still recorded evidence (lit), null is hollow", () => {
    const base: ProposalDetail = {
      proposal_id: "p-1",
      state: "pending",
      source_kind: "contemplation",
      replay_equivalent: false,
      created_at: null,
      downstream_effect: "unknown",
      proposed_chain: [],
      provenance: null,
      suggested_cli: null,
    } as unknown as ProposalDetail;

    const recorded: EvidenceSubject = { kind: "proposal", proposalId: "p-1", data: base } as EvidenceSubject;
    expect(statusOf(recorded, "replay")).toBe("lit");

    const unrecorded: EvidenceSubject = {
      kind: "proposal",
      proposalId: "p-1",
      data: { ...base, replay_equivalent: null },
    } as EvidenceSubject;
    expect(statusOf(unrecorded, "replay")).toBe("hollow");
  });

  it("MEANINGFULLY FAILS run: removing checkpoint_revision hollows exactly replay", () => {
    const full: EvidenceSubject = {
      kind: "run",
      sessionId: "session-1",
      data: {
        session_id: "session-1",
        source: "engine_state_manifest",
        checkpoint_present: true,
        checkpoint_revision: "rev-1",
        evidence_gap: null,
      },
    };
    expect(statusOf(full, "provenance")).toBe("lit");
    expect(statusOf(full, "admissibility")).toBe("lit");
    expect(statusOf(full, "replay")).toBe("lit");

    const missingRevision: EvidenceSubject = {
      ...full,
      data: { ...full.data, checkpoint_revision: null },
    };
    expect(statusOf(missingRevision, "replay")).toBe("hollow");
    expect(statusOf(missingRevision, "provenance")).toBe("lit");
  });

  it("run: evidence_gap dims the replay chain instead of pretending replay is available", () => {
    const gapped: EvidenceSubject = {
      kind: "run",
      sessionId: "session-gap",
      data: {
        source: "turn_journal",
        checkpoint_present: true,
        checkpoint_revision: "rev-gap",
        evidence_gap: "checkpoint missing from manifest",
      },
    };
    expect(statusOf(gapped, "provenance")).toBe("dim");
    expect(statusOf(gapped, "admissibility")).toBe("dim");
    expect(statusOf(gapped, "replay")).toBe("dim");
  });

  it("run: identity-only subject hollows field-derived stages", () => {
    const identityOnly: EvidenceSubject = { kind: "run", sessionId: "session-identity" };
    expect(statusOf(identityOnly, "provenance")).toBe("hollow");
    expect(statusOf(identityOnly, "admissibility")).toBe("hollow");
    expect(statusOf(identityOnly, "replay")).toBe("hollow");
  });

  it("MEANINGFULLY FAILS pack: removing determinism_class hollows exactly admissibility", () => {
    const full: EvidenceSubject = {
      kind: "pack",
      packId: "en_core",
      data: {
        pack_id: "en_core",
        checksum: "sha256:pack",
        manifest_digest: "sha256:manifest",
        determinism_class: "deterministic",
      },
    };
    expect(statusOf(full, "provenance")).toBe("lit");
    expect(statusOf(full, "admissibility")).toBe("lit");

    const missingDeterminism: EvidenceSubject = {
      ...full,
      data: { ...full.data, determinism_class: null },
    };
    expect(statusOf(missingDeterminism, "admissibility")).toBe("hollow");
    expect(statusOf(missingDeterminism, "provenance")).toBe("lit");
  });

  it("MEANINGFULLY FAILS vault_entry: removing versor_digest hollows exactly provenance", () => {
    const full: EvidenceSubject = {
      kind: "vault_entry",
      entryIndex: 3,
      data: {
        entry_index: 3,
        epistemic_state: "verified",
        versor_digest: "sha256:versor",
      },
    };
    expect(statusOf(full, "provenance")).toBe("lit");
    expect(statusOf(full, "admissibility")).toBe("lit");

    const missingVersor: EvidenceSubject = {
      ...full,
      data: { ...full.data, versor_digest: null },
    };
    expect(statusOf(missingVersor, "provenance")).toBe("hollow");
    expect(statusOf(missingVersor, "admissibility")).toBe("lit");
  });

  it("MEANINGFULLY FAILS audit_event: removing payload_digest hollows exactly provenance", () => {
    const full: EvidenceSubject = {
      kind: "audit_event",
      eventId: "audit-1",
      data: {
        event_id: "audit-1",
        mutation_boundary: true,
        payload_digest: "sha256:audit",
      },
    };
    expect(statusOf(full, "provenance")).toBe("lit");
    expect(statusOf(full, "action")).toBe("lit");

    const missingPayload: EvidenceSubject = {
      ...full,
      data: { ...full.data, payload_digest: null },
    };
    expect(statusOf(missingPayload, "provenance")).toBe("hollow");
    expect(statusOf(missingPayload, "action")).toBe("lit");
  });

  it("renders no rail for kind=none", () => {
    const { container } = render(<EvidenceChainRail subject={{ kind: "none" }} />);
    expect(container.querySelector('[data-testid="evidence-chain-rail"]')).toBeNull();
  });

  it("renders all seven stages with status data attributes", () => {
    const { container } = render(<EvidenceChainRail subject={turnSubject(FULL_TURN)} />);
    const items = container.querySelectorAll("[data-stage]");
    expect(items.length).toBe(7);
    expect(container.querySelectorAll('[data-status="lit"]').length).toBe(6);
    expect(container.querySelectorAll('[data-status="dim"]').length).toBe(1);
  });
});
