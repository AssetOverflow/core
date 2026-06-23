export type DemoStepKind = "intro" | "evidence" | "replay" | "proposal" | "audit" | "payoff";

export interface DemoEvidenceLink {
  label: string;
  route: string;
  artifact_id: string | null;
  digest: string | null;
  reproducer: string | null;
}

export interface DemoNarrativeStep {
  step_id: string;
  order: number;
  kind: DemoStepKind;
  title: string;
  claim: string;
  what_this_proves: string;
  what_this_does_not_prove: string;
  evidence_links: DemoEvidenceLink[];
  failure_mode: string | null;
}

export interface DemoNarrative {
  narrative_id: string;
  title: string;
  summary: string;
  steps: DemoNarrativeStep[];
}
