import type { ProposalDetail, ProposalSummary } from "../../types/api";

export const proposalSummaries: ProposalSummary[] = [
  {
    proposal_id: "proposal-pending-001abcdef",
    state: "pending",
    source_kind: "contemplation",
    replay_equivalent: true,
    created_at: "2026-05-26T00:00:00Z",
    downstream_effect: "observed",
  },
  {
    proposal_id: "proposal-accepted-002abcdef",
    state: "accepted",
    source_kind: "corpus",
    replay_equivalent: true,
    created_at: "2026-05-26T00:01:00Z",
    downstream_effect: "none",
  },
  {
    proposal_id: "proposal-rejected-003abcdef",
    state: "rejected",
    source_kind: "contemplation",
    replay_equivalent: false,
    created_at: "2026-05-26T00:02:00Z",
    downstream_effect: "unknown",
  },
];

export const proposalDetail: ProposalDetail = {
  ...proposalSummaries[0],
  proposed_chain: {
    chain_records: [
      {
        subject: "truth",
        predicate: "requires",
        object: "coherence",
        provenance: "cognition_chains_v1",
      },
    ],
  },
  replay_evidence: {
    original_digest: "11111111111111111111111111111111",
    replay_digest: "11111111111111111111111111111111",
    divergences: [],
  },
  source: {
    source_id: "contemplation-run-001",
    corpus_id: "cognition_chains_v1",
    summary: "Contemplation proposed a coherence relation.",
  },
  evidence: [{ artifact_id: "trace-001", trail: ["turn", "proposal"] }],
  artifact_refs: [
    {
      artifact_id: "artifact-001",
      kind: "proposal",
      path: "teaching/proposals/proposals.jsonl",
      digest: "sha256:1111",
      created_at: "2026-05-26T00:00:00Z",
    },
  ],
  suggested_cli: null,
};
