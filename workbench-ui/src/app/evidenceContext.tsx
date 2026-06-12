import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type {
  ChatTurnResult,
  ProposalDetail,
  ArtifactDetail,
  EvalRunResult,
} from "../types/api";

// `data` is optional: a subject restored from a URL carries identity only
// until the owning route's query loads its detail.  Inspectors must render
// an honest "detail not loaded" state when data is absent.
export type EvidenceSubject =
  | { kind: "turn"; turnId: number; data?: ChatTurnResult }
  | { kind: "proposal"; proposalId: string; data?: ProposalDetail }
  | { kind: "artifact"; artifactId: string; data?: ArtifactDetail }
  | { kind: "eval_result"; lane: string; data?: EvalRunResult }
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
  const [inspectorOpen, setInspectorOpen] = useState(false);
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
