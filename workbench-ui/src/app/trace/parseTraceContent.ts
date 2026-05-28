import type { ChatTurnResult } from "../../types/api";

function asString(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

function asNumber(v: unknown): number {
  return typeof v === "number" ? v : 0;
}

function asBool(v: unknown): boolean {
  return typeof v === "boolean" ? v : false;
}

function asVerdict(v: unknown): ChatTurnResult["identity_verdict"] {
  if (!v || typeof v !== "object") return null;
  const obj = v as Record<string, unknown>;
  const outcome = obj.outcome;
  if (outcome !== "cleared" && outcome !== "violated" && outcome !== "unassessable") {
    return null;
  }
  return {
    outcome,
    runtime_detail:
      typeof obj.runtime_detail === "string" ? obj.runtime_detail : "",
  };
}

function asProposals(v: unknown): ChatTurnResult["proposal_candidates"] {
  if (!Array.isArray(v)) return [];
  return v
    .map((c) => {
      if (!c || typeof c !== "object") return null;
      const obj = c as Record<string, unknown>;
      const id = asString(obj.candidate_id);
      const kind = asString(obj.source_kind);
      if (!id || !kind) return null;
      return { candidate_id: id, source_kind: kind };
    })
    .filter((c): c is { candidate_id: string; source_kind: string } => c !== null);
}

/**
 * Runtime-safe decode of an artifact's `content` field into a ChatTurnResult.
 * Returns null when the content cannot be reasonably interpreted as a trace.
 * Read-only; performs no mutation on the input.
 */
export function parseTraceContent(content: unknown): ChatTurnResult | null {
  if (!content || typeof content !== "object") return null;
  const obj = content as Record<string, unknown>;

  // surface is required — without it, this is not a trace
  const surface = asString(obj.surface);
  if (surface === null) return null;

  return {
    prompt: asString(obj.prompt) ?? "",
    surface,
    articulation_surface: asString(obj.articulation_surface),
    walk_surface: asString(obj.walk_surface),
    grounding_source: (asString(obj.grounding_source) ?? "unknown") as ChatTurnResult["grounding_source"],
    epistemic_state: (asString(obj.epistemic_state) ?? "unknown") as ChatTurnResult["epistemic_state"],
    normative_clearance: (asString(obj.normative_clearance) ?? "unknown") as ChatTurnResult["normative_clearance"],
    normative_detail: asString(obj.normative_detail) ?? "",
    trace_hash: asString(obj.trace_hash),
    refusal_emitted: asBool(obj.refusal_emitted),
    hedge_injected: asBool(obj.hedge_injected),
    mutation_mode: (asString(obj.mutation_mode) ?? "off") as ChatTurnResult["mutation_mode"],
    identity_verdict: asVerdict(obj.identity_verdict),
    safety_verdict: asVerdict(obj.safety_verdict),
    ethics_verdict: asVerdict(obj.ethics_verdict),
    proposal_candidates: asProposals(obj.proposal_candidates),
    turn_cost_ms: asNumber(obj.turn_cost_ms),
    checkpoint_emitted: asBool(obj.checkpoint_emitted),
  };
}
