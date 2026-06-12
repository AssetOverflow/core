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

export type EvidenceSubject =
  | { kind: "turn"; turnId: number; data: ChatTurnResult }
  | { kind: "proposal"; proposalId: string; data: ProposalDetail }
  | { kind: "artifact"; artifactId: string; data: ArtifactDetail }
  | { kind: "eval_result"; lane: string; data: EvalRunResult }
  | { kind: "none" };

interface EvidenceContextValue {
  subject: EvidenceSubject;
  setSubject: (subject: EvidenceSubject) => void;
  clearSubject: () => void;
  inspectorOpen: boolean;
  setInspectorOpen: (open: boolean) => void;
  toggleInspector: () => void;
}

const NONE_SUBJECT: EvidenceSubject = { kind: "none" };

const EvidenceContext = createContext<EvidenceContextValue | null>(null);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [subject, setSubjectState] = useState<EvidenceSubject>(NONE_SUBJECT);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  const setSubject = useCallback((s: EvidenceSubject) => {
    setSubjectState(s);
  }, []);

  const clearSubject = useCallback(() => {
    setSubjectState(NONE_SUBJECT);
  }, []);

  const toggleInspector = useCallback(() => {
    setInspectorOpen((prev) => !prev);
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
