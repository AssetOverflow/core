import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { getWorkbenchPrefs } from "./workbenchPrefs";
import type {
  ChatTurnResult,
  TurnJournalEntry,
  ProposalDetail,
  MathProposalDetail,
  ArtifactDetail,
  EvalRunResult,
  CalibrationClass,
  LogosPackOverview,
  LogosLexiconRow,
  LogosGlossRow,
  LogosMorphologyRow,
  SafetyVerdict,
} from "../types/api";

export type ProposalSubjectDomain = "cognition" | "math";

export interface RunSubjectData {
  session_id?: string;
  source?: string;
  checkpoint_present?: boolean;
  checkpoint_revision?: string | null;
  evidence_gap?: string | null;
}

export interface PackSubjectData {
  pack_id?: string;
  checksum?: string | null;
  manifest_digest?: string | null;
  determinism_class?: string | null;
}

export interface LogosPackSubjectData
  extends Partial<
    Pick<
      LogosPackOverview,
      | "pack_id"
      | "language"
      | "role"
      | "script"
      | "version"
      | "determinism_class"
      | "gate_engaged"
      | "oov_policy"
      | "safety_status"
      | "manifest_digest"
      | "manifest_path"
      | "holonomy_case_count"
    >
  > {
  checksum_status?: SafetyVerdict | null;
}

export interface VaultEntrySubjectData {
  entry_index?: number;
  epistemic_state?: string;
  versor_digest?: string | null;
}

export interface AuditEventSubjectData {
  event_id?: string;
  mutation_boundary?: boolean;
  payload_digest?: string | null;
}

// `data` is optional: a subject restored from a URL carries identity only
// until the owning route's query loads its detail.  Inspectors must render
// an honest "detail not loaded" state when data is absent.
export type EvidenceSubject =
  | { kind: "turn"; turnId: number; data?: ChatTurnResult | TurnJournalEntry }
  | {
      kind: "proposal";
      proposalId: string;
      domain?: ProposalSubjectDomain;
      data?: ProposalDetail | MathProposalDetail;
    }
  | { kind: "artifact"; artifactId: string; data?: ArtifactDetail }
  | { kind: "eval_result"; lane: string; data?: EvalRunResult }
  | { kind: "run"; sessionId: string; data?: RunSubjectData }
  | { kind: "pack"; packId: string; data?: PackSubjectData }
  | { kind: "logos_pack"; packId: string; data?: LogosPackSubjectData }
  | {
      kind: "logos_entry";
      packId: string;
      entryId: string;
      data?: LogosLexiconRow;
    }
  | {
      kind: "logos_gloss";
      packId: string;
      glossId: string;
      data?: LogosGlossRow;
    }
  | {
      kind: "logos_morphology";
      packId: string;
      morphologyId: string;
      data?: LogosMorphologyRow;
    }
  | { kind: "vault_entry"; entryIndex: number; data?: VaultEntrySubjectData }
  | { kind: "audit_event"; eventId: string; data?: AuditEventSubjectData }
  | { kind: "calibration_class"; className: string; data?: CalibrationClass }
  | { kind: "none" };

interface EvidenceContextValue {
  subject: EvidenceSubject;
  setSubject: (subject: EvidenceSubject) => void;
  clearSubject: () => void;
  inspectorOpen: boolean;
  setInspectorOpen: (open: boolean) => void;
  toggleInspector: () => void;
  addressCopyCount: number;
  notifyAddressCopied: () => void;
}

const NONE_SUBJECT: EvidenceSubject = { kind: "none" };

const EvidenceContext = createContext<EvidenceContextValue | null>(null);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [subject, setSubjectState] = useState<EvidenceSubject>(NONE_SUBJECT);
  // Initial visibility follows the workbench pref; EvidenceUrlSync still
  // force-opens on a `?inspect=` deep link.
  const [inspectorOpen, setInspectorOpen] = useState(
    () => getWorkbenchPrefs().inspectorDefaultOpen,
  );
  const [addressCopyCount, setAddressCopyCount] = useState(0);

  const setSubject = useCallback((s: EvidenceSubject) => {
    setSubjectState(s);
  }, []);

  const clearSubject = useCallback(() => {
    setSubjectState(NONE_SUBJECT);
  }, []);

  const toggleInspector = useCallback(() => {
    setInspectorOpen((prev) => !prev);
  }, []);

  const notifyAddressCopied = useCallback(() => {
    setAddressCopyCount((prev) => prev + 1);
  }, []);

  return (
    <EvidenceContext.Provider
      value={{
        subject,
        setSubject,
        clearSubject,
        inspectorOpen,
        setInspectorOpen,
        toggleInspector,
        addressCopyCount,
        notifyAddressCopied,
      }}
    >
      {children}
    </EvidenceContext.Provider>
  );
}

export function useEvidenceSubject(): EvidenceContextValue {
  const ctx = useContext(EvidenceContext);
  if (!ctx) {
    throw new Error("useEvidenceSubject must be used within EvidenceProvider");
  }
  return ctx;
}
