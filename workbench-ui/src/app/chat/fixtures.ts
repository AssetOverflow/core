import type { ChatTurnResult } from "../../types/api";

export const happyChatTurn: ChatTurnResult = {
  prompt: "What is truth?",
  surface: "Truth is what is true. pack-grounded (en_core_cognition_v1).",
  articulation_surface: "Truth is what is true.",
  walk_surface: "truth -> true",
  grounding_source: "pack",
  epistemic_state: "decoded",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: "sha256:0123456789abcdef0123456789abcdef",
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "runtime_turn",
  identity_verdict: { outcome: "cleared", runtime_detail: "" },
  safety_verdict: { outcome: "cleared", runtime_detail: "" },
  ethics_verdict: { outcome: "cleared", runtime_detail: "" },
  proposal_candidates: [{ candidate_id: "cand_123", source_kind: "discovery" }],
  turn_cost_ms: 42,
  checkpoint_emitted: true,
};

export const refusalChatTurn: ChatTurnResult = {
  ...happyChatTurn,
  prompt: "Tina makes $18.00 an hour.",
  surface: "I don't know - insufficient grounding for that yet.",
  grounding_source: "none",
  epistemic_state: "undetermined",
  normative_clearance: "suppressed",
  normative_detail: "ethics:evidence_required",
  refusal_emitted: true,
  safety_verdict: { outcome: "cleared", runtime_detail: "" },
  ethics_verdict: { outcome: "violated", runtime_detail: "evidence_required" },
  proposal_candidates: [],
};
