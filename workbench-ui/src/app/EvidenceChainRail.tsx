import type { CSSProperties } from "react";
import type { EvidenceSubject } from "./evidenceContext";

/**
 * EvidenceChainRail — the spine's seven stages rendered for the selected
 * subject (Wave R brief R1):
 *
 *   intent -> subject -> provenance -> admissibility -> replay -> authority -> action
 *
 * HONESTY CONTRACT: a stage's status derives ONLY from fields the subject
 * actually carries. `lit` = the named field holds evidence. `hollow` = the
 * stage applies to this subject kind but no evidence is recorded/loaded.
 * `dim` = the stage does not apply to this kind. Nothing is ever inferred:
 * a recorded trace hash lights "replay" as "trace hash recorded" — it does
 * NOT claim replay was verified.
 */

export type StageStatus = "lit" | "hollow" | "dim";

export interface RailStage {
  id: string;
  label: string;
  status: StageStatus;
  /** What the status derives from — shown in the tooltip, audit-honest. */
  derivation: string;
}

const STAGE_IDS = [
  "intent",
  "subject",
  "provenance",
  "admissibility",
  "replay",
  "authority",
  "action",
] as const;

function stage(
  id: (typeof STAGE_IDS)[number],
  status: StageStatus,
  derivation: string,
): RailStage {
  return { id, label: id, status, derivation };
}

function evidenceOf(value: unknown): "lit" | "hollow" {
  if (value === null || value === undefined || value === "") return "hollow";
  return "lit";
}

function evidenceAny(...values: unknown[]): "lit" | "hollow" {
  return values.some((value) => evidenceOf(value) === "lit") ? "lit" : "hollow";
}

/** Pure derivation — exported for the meaningfully-fail tests. */
export function deriveStages(subject: EvidenceSubject): RailStage[] | null {
  switch (subject.kind) {
    case "none":
      return null;
    case "turn": {
      const d = subject.data;
      return [
        stage("intent", d ? evidenceOf(d.prompt) : "hollow", "prompt"),
        stage("subject", "lit", "selected turn"),
        stage("provenance", d ? evidenceOf(d.grounding_source) : "hollow", "grounding_source"),
        stage(
          "admissibility",
          d ? evidenceOf(d.epistemic_state) : "hollow",
          "epistemic_state + normative_clearance",
        ),
        stage("replay", d ? evidenceOf(d.trace_hash) : "hollow", "trace_hash recorded (not a verification claim)"),
        stage(
          "authority",
          d
            ? evidenceOf("mutation_mode" in d ? d.mutation_mode : d.checkpoint_emitted)
            : "hollow",
          "mutation_mode / checkpoint_emitted",
        ),
        stage("action", "dim", "not applicable to a completed turn"),
      ];
    }
    case "proposal": {
      const d = subject.data;
      const provenance = d
        ? "source_kind" in d
          ? d.source_kind
          : d.proposed_change_kind
        : undefined;
      const replayEvidence = d
        ? "replay_equivalent" in d
          ? d.replay_equivalent
          : d.replay_equivalence_hash
        : undefined;
      const authority = d ? ("state" in d ? d.state : d.handler_name) : undefined;
      const action = d
        ? "suggested_cli" in d
          ? d.suggested_cli
          : d.suggested_ratify_cli
        : undefined;
      return [
        stage("intent", "dim", "not applicable — proposals originate in contemplation"),
        stage("subject", "lit", "selected proposal"),
        stage("provenance", evidenceOf(provenance), "source_kind / proposed_change_kind"),
        stage(
          "admissibility",
          replayEvidence === null ? "hollow" : evidenceOf(replayEvidence),
          "replay_equivalent / replay_equivalence_hash recorded",
        ),
        stage(
          "replay",
          replayEvidence === null ? "hollow" : evidenceOf(replayEvidence),
          "replay evidence value (false is recorded evidence)",
        ),
        stage("authority", evidenceOf(authority), "review state / handler_name"),
        stage("action", evidenceOf(action), "suggested_cli / suggested_ratify_cli"),
      ];
    }
    case "run": {
      const d = subject.data;
      const hasGapField = !!d && Object.prototype.hasOwnProperty.call(d, "evidence_gap");
      const gapped = evidenceOf(d?.evidence_gap) === "lit";
      return [
        stage("intent", "dim", "not applicable to recorded runs"),
        stage("subject", "lit", "selected run"),
        stage("provenance", gapped ? "dim" : d ? evidenceOf(d.source) : "hollow", "source / evidence_gap"),
        stage(
          "admissibility",
          !d || !hasGapField ? "hollow" : gapped ? "dim" : "lit",
          "evidence_gap absent means no gap recorded",
        ),
        stage(
          "replay",
          !d
            ? "hollow"
            : gapped
            ? "dim"
            : d?.checkpoint_present
              ? evidenceOf(d.checkpoint_revision)
              : "hollow",
          "checkpoint_present + checkpoint_revision",
        ),
        stage("authority", "dim", "not applicable to read-only run evidence"),
        stage("action", "dim", "not applicable to recorded runs"),
      ];
    }
    case "pack": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to semantic packs"),
        stage("subject", "lit", "selected pack"),
        stage(
          "provenance",
          d ? evidenceAny(d.checksum, d.manifest_digest) : "hollow",
          "checksum / manifest_digest",
        ),
        stage("admissibility", d ? evidenceOf(d.determinism_class) : "hollow", "determinism_class"),
        stage("replay", "dim", "not applicable to pack metadata"),
        stage("authority", "dim", "not applicable to pack metadata"),
        stage("action", "dim", "not applicable to pack metadata"),
      ];
    }
    case "logos_pack": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to read-only Logos pack inspection"),
        stage("subject", "lit", "selected CORE-Logos pack"),
        stage(
          "provenance",
          d ? evidenceAny(d.manifest_digest, d.manifest_path) : "hollow",
          "manifest_digest / manifest_path",
        ),
        stage(
          "admissibility",
          d ? evidenceAny(d.safety_status, d.checksum_status) : "hollow",
          "safety_status / checksum_status",
        ),
        stage(
          "replay",
          d && d.holonomy_case_count && d.holonomy_case_count > 0 ? "lit" : "hollow",
          "holonomy_case_count (0 means missing_evidence)",
        ),
        stage("authority", "dim", "read-only Logos Studio has no mutation authority"),
        stage("action", "dim", "proposal mode none"),
      ];
    }
    case "logos_entry": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to read-only Logos entry inspection"),
        stage("subject", "lit", "selected CORE-Logos lexical entry"),
        stage(
          "provenance",
          d ? evidenceAny(...d.provenance_ids) : "hollow",
          "provenance_ids",
        ),
        stage(
          "admissibility",
          d ? evidenceOf(d.epistemic_status) : "hollow",
          "epistemic_status (ADR-0021 revision position)",
        ),
        stage("replay", "dim", "not applicable to a static lexicon row"),
        stage("authority", "dim", "read-only Logos Studio has no mutation authority"),
        stage("action", "dim", "proposal mode none"),
      ];
    }
    case "logos_gloss": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to read-only Logos gloss inspection"),
        stage("subject", "lit", "selected CORE-Logos gloss"),
        stage(
          "provenance",
          d ? evidenceAny(...d.provenance_ids) : "hollow",
          "provenance_ids",
        ),
        stage(
          "admissibility",
          d ? evidenceOf(d.epistemic_status) : "hollow",
          "epistemic_status",
        ),
        stage(
          "replay",
          d ? evidenceAny(...d.entry_ids) : "hollow",
          "linked entry_ids",
        ),
        stage("authority", "dim", "read-only Logos Studio has no mutation authority"),
        stage("action", "dim", "proposal mode none"),
      ];
    }
    case "logos_morphology": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to read-only Logos morphology inspection"),
        stage("subject", "lit", "selected CORE-Logos morphology record"),
        stage(
          "provenance",
          d ? evidenceAny(d.root, d.stem) : "hollow",
          "root / stem",
        ),
        stage(
          "admissibility",
          d ? evidenceOf(d.morphology_id) : "hollow",
          "morphology_id (lexicon link target)",
        ),
        stage("replay", "dim", "not applicable to a static morphology row"),
        stage("authority", "dim", "read-only Logos Studio has no mutation authority"),
        stage("action", "dim", "proposal mode none"),
      ];
    }
    case "vault_entry": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to vault entries"),
        stage("subject", "lit", "selected vault entry"),
        stage("provenance", d ? evidenceOf(d.versor_digest) : "hollow", "versor_digest"),
        stage("admissibility", d ? evidenceOf(d.epistemic_state) : "hollow", "epistemic_state"),
        stage("replay", "dim", "not applicable to vault entries"),
        stage("authority", "dim", "not applicable to vault entries"),
        stage("action", "dim", "not applicable to vault entries"),
      ];
    }
    case "audit_event": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to audit events"),
        stage("subject", "lit", "selected audit event"),
        stage("provenance", d ? evidenceOf(d.payload_digest) : "hollow", "payload_digest"),
        stage("admissibility", "dim", "not applicable to audit events"),
        stage("replay", "dim", "not applicable to audit events"),
        stage("authority", "dim", "not applicable to audit events"),
        stage("action", d ? evidenceOf(d.mutation_boundary) : "hollow", "mutation_boundary"),
      ];
    }
    case "calibration_class": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable — calibration is serving-discipline evidence, not runtime truth"),
        stage("subject", "lit", "selected calibration class"),
        stage(
          "provenance",
          d ? evidenceAny(d.source_digest, d.source_path) : "hollow",
          "practice report source_digest / source_path",
        ),
        stage(
          "admissibility",
          d ? evidenceOf(d.reliability_floor) : "hollow",
          "Wilson floor + theta gate from core.reliability_gate",
        ),
        stage("replay", "dim", "not a runtime replay claim"),
        stage(
          "authority",
          d ? evidenceAny(d.propose_licensed, d.serve_licensed) : "hollow",
          "PROPOSE/SERVE license verdict; read-only, not mutation authority",
        ),
        stage("action", "dim", "calibration view is read-only"),
      ];
    }
    case "artifact": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to stored artifacts"),
        stage("subject", "lit", "selected artifact"),
        stage("provenance", d ? evidenceOf(d.path) : "hollow", "path"),
        stage("admissibility", "dim", "not applicable to stored artifacts"),
        stage("replay", d ? evidenceOf(d.digest) : "hollow", "digest"),
        stage("authority", "dim", "not applicable to stored artifacts"),
        stage("action", "dim", "not applicable to stored artifacts"),
      ];
    }
    case "eval_result": {
      const d = subject.data;
      return [
        stage("intent", "dim", "not applicable to eval runs"),
        stage("subject", "lit", "selected eval result"),
        stage("provenance", d ? evidenceOf(d.lane) : "hollow", "lane + version"),
        stage("admissibility", d ? evidenceOf(d.split) : "hollow", "split (lane discipline)"),
        stage("replay", d ? evidenceOf(d.source_digest) : "hollow", "source_digest"),
        stage("authority", "dim", "not applicable to read-only lanes"),
        stage("action", d ? (d.passed === null ? "hollow" : "lit") : "hollow", "pass/fail recorded"),
      ];
    }
  }
}

const STATUS_STYLE: Record<StageStatus, { dot: CSSProperties; text: string }> = {
  lit: {
    dot: {
      background: "var(--color-state-evidenced)",
      border: "1px solid var(--color-state-evidenced)",
    },
    text: "text-[var(--color-text-secondary)]",
  },
  hollow: {
    dot: {
      background: "transparent",
      border: "1px solid var(--color-border-strong)",
    },
    text: "text-[var(--color-text-muted)]",
  },
  dim: {
    dot: {
      background: "var(--color-border-subtle)",
      border: "1px solid var(--color-border-subtle)",
      opacity: 0.5,
    },
    text: "text-[var(--color-text-muted)] opacity-60",
  },
};

const STATUS_WORD: Record<StageStatus, string> = {
  lit: "evidence present",
  hollow: "not recorded",
  dim: "not applicable",
};

export function EvidenceChainRail({ subject }: { subject: EvidenceSubject }) {
  const stages = deriveStages(subject);
  if (!stages) return null;

  return (
    <ol
      className="m-0 flex list-none flex-wrap items-center gap-x-1 gap-y-1 border-b p-0 pb-2"
      style={{ borderColor: "var(--color-border-subtle)" }}
      aria-label="Evidence chain"
      data-testid="evidence-chain-rail"
    >
      {stages.map((s, i) => (
        <li
          key={s.id}
          className="flex items-center gap-1"
          title={`${s.label}: ${STATUS_WORD[s.status]} — ${s.derivation}`}
          data-stage={s.id}
          data-status={s.status}
        >
          <span
            aria-hidden
            className="inline-block h-2 w-2 shrink-0 rounded-full"
            style={STATUS_STYLE[s.status].dot}
          />
          <span className={`text-[10px] ${STATUS_STYLE[s.status].text}`}>
            {s.label}
          </span>
          {i < stages.length - 1 && (
            <span aria-hidden className="text-[10px] text-[var(--color-text-muted)]">
              →
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
