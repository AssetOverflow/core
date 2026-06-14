import {
  EpistemicState,
  GroundingSource,
  NormativeClearance,
  ReviewState,
  SafetyVerdict,
  type BadgeMeta,
} from "./types";

export const epistemicStateMeta = {
  [EpistemicState.PERCEIVED]: { label: "Perceived", colorToken: "--color-state-perceived", meaning: "Observed at the surface but not yet independently evidenced.", adr: "ADR-0142 / ADR-0162", evidence: "A trace carries raw input evidence." },
  [EpistemicState.EVIDENCED]: { label: "Evidenced", colorToken: "--color-state-evidenced", meaning: "Supported by explicit evidence.", adr: "ADR-0142 / ADR-0162", evidence: "A proposition cites a supporting artifact." },
  [EpistemicState.EVIDENCED_INCOMPLETE]: { label: "Evidenced incomplete", colorToken: "--color-state-evidenced-muted", meaning: "Some evidence exists, but coverage is partial.", adr: "ADR-0142 / ADR-0162", evidence: "Grounding source is partial." },
  [EpistemicState.VERIFIED]: { label: "Verified", colorToken: "--color-state-verified", meaning: "Checked against an authoritative deterministic lane.", adr: "ADR-0142 / ADR-0162", evidence: "Replay hash matches original." },
  [EpistemicState.DECODED]: { label: "Decoded", colorToken: "--color-state-decoded", meaning: "Mapped through ratified semantic structure.", adr: "ADR-0142 / ADR-0162", evidence: "Grounding source is pack, teaching, or vault." },
  [EpistemicState.DECODED_UNARTICULATED]: { label: "Decoded unarticulated", colorToken: "--color-state-decoded-muted", meaning: "Structured internally but not surfaced.", adr: "ADR-0142 / ADR-0162", evidence: "Graph node exists without realized sentence." },
  [EpistemicState.INFERRED]: { label: "Inferred", colorToken: "--color-state-inferred", meaning: "Derived from available structure.", adr: "ADR-0142 / ADR-0162", evidence: "Planner derives a relation from linked propositions." },
  [EpistemicState.UNVERIFIED_POSSIBLE]: { label: "Unverified possible", colorToken: "--color-state-unverified", meaning: "Plausible but not verified.", adr: "ADR-0142 / ADR-0162", evidence: "Candidate has no ratified support yet." },
  [EpistemicState.UNVERIFIED_NOVEL]: { label: "Unverified novel", colorToken: "--color-state-unverified-warm", meaning: "New or OOV content without ratified grounding.", adr: "ADR-0142 / ADR-0162", evidence: "Grounding source is oov." },
  [EpistemicState.CONTRADICTED]: { label: "Contradicted", colorToken: "--color-state-contradicted", meaning: "Evidence conflicts with the proposition.", adr: "ADR-0142 / ADR-0162", evidence: "A boundary or claim rejects the assertion." },
  [EpistemicState.AMBIGUOUS]: { label: "Ambiguous", colorToken: "--color-state-ambiguous", meaning: "Multiple readings remain live.", adr: "ADR-0142 / ADR-0162", evidence: "Parser retains competing interpretations." },
  [EpistemicState.UNDETERMINED]: { label: "Undetermined", colorToken: "--color-state-undetermined", meaning: "No stronger epistemic state is justified.", adr: "ADR-0142 / ADR-0162", evidence: "No grounding source is present." },
  [EpistemicState.SCOPE_BOUNDARY]: { label: "Scope boundary", colorToken: "--color-state-scope", meaning: "The claim is outside the active scope.", adr: "ADR-0142 / ADR-0162", evidence: "Runtime declines to classify beyond scope." },
  [EpistemicState.COMPUTATIONALLY_BOUNDED]: { label: "Computationally bounded", colorToken: "--color-state-bounded", meaning: "The answer is limited by bounded computation.", adr: "ADR-0142 / ADR-0162", evidence: "Eval lane reports a bounded operator." },
  [EpistemicState.EPISTEMIC_STATE_NEEDED]: { label: "State needed", colorToken: "--color-state-needed", meaning: "A missing state must be assigned before trust display.", adr: "ADR-0142 / ADR-0162", evidence: "Unknown grounding source reached UI mapping." },
} satisfies BadgeMeta<EpistemicState>;

export const normativeClearanceMeta = {
  [NormativeClearance.CLEARED]: { label: "Cleared", colorToken: "--color-clearance-cleared", meaning: "Runtime-checkable normative gates passed.", adr: "ADR-0142 / ADR-0162", evidence: "Safety and ethics verdicts upheld." },
  [NormativeClearance.VIOLATED]: { label: "Violated", colorToken: "--color-clearance-violated", meaning: "A runtime-checkable boundary failed.", adr: "ADR-0142 / ADR-0162", evidence: "Boundary id appears in normative detail." },
  [NormativeClearance.UNASSESSABLE]: { label: "Unassessable", colorToken: "--color-clearance-unassessable", meaning: "No positive clearance can be asserted.", adr: "ADR-0142 / ADR-0162", evidence: "No runtime-checkable verdict exists." },
  [NormativeClearance.SUPPRESSED]: { label: "Suppressed", colorToken: "--color-clearance-suppressed", meaning: "A refusal surface replaced unsafe output.", adr: "ADR-0142 / ADR-0162", evidence: "refusal_emitted is true." },
} satisfies BadgeMeta<NormativeClearance>;

export const reviewStateMeta = {
  [ReviewState.PENDING]: { label: "Pending", colorToken: "--color-review-pending", meaning: "Proposal awaits operator review.", adr: "ADR-0057 / ADR-0161 / ADR-0162", evidence: "No terminal transition exists." },
  [ReviewState.ACCEPTED]: { label: "Accepted", colorToken: "--color-review-accepted", meaning: "Operator ratified the proposal.", adr: "ADR-0057 / ADR-0161 / ADR-0162", evidence: "transition.to is accepted." },
  [ReviewState.REJECTED]: { label: "Rejected", colorToken: "--color-review-rejected", meaning: "Operator rejected the proposal.", adr: "ADR-0057 / ADR-0161 / ADR-0162", evidence: "transition.to is rejected." },
  [ReviewState.WITHDRAWN]: { label: "Withdrawn", colorToken: "--color-review-withdrawn", meaning: "Proposal was withdrawn without ratification.", adr: "ADR-0057 / ADR-0161 / ADR-0162", evidence: "transition.to is withdrawn." },
} satisfies BadgeMeta<ReviewState>;

export const groundingSourceMeta = {
  [GroundingSource.PACK]: { label: "Pack", colorToken: "--color-grounding-pack", meaning: "Grounded in a curated semantic pack.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is pack." },
  [GroundingSource.TEACHING]: { label: "Teaching", colorToken: "--color-grounding-teaching", meaning: "Grounded in reviewed teaching memory.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is teaching." },
  [GroundingSource.VAULT]: { label: "Vault", colorToken: "--color-grounding-vault", meaning: "Grounded in deterministic vault recall.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is vault." },
  [GroundingSource.PARTIAL]: { label: "Partial", colorToken: "--color-grounding-partial", meaning: "Only partial grounding was available.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is partial." },
  [GroundingSource.OOV]: { label: "OOV", colorToken: "--color-grounding-oov", meaning: "Out-of-vocabulary grounding was encountered.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is oov." },
  [GroundingSource.NONE]: { label: "None", colorToken: "--color-grounding-none", meaning: "No grounding source was present.", adr: "ADR-0160 / ADR-0162", evidence: "grounding_source is none." },
} satisfies BadgeMeta<GroundingSource>;

export const safetyVerdictMeta = {
  [SafetyVerdict.CLEAR]: { label: "Clear", colorToken: "--color-state-verified", meaning: "The reported Logos safety check has no recorded warning or failure.", adr: "ADR-0162 / CORE-Logos LG-2", evidence: "SafetyVerdict is clear." },
  [SafetyVerdict.WARNING]: { label: "Warning", colorToken: "--color-state-warning-text", meaning: "The reported Logos safety check found reviewable gaps or link issues; this is not clear.", adr: "ADR-0162 / CORE-Logos LG-2", evidence: "SafetyVerdict is warning." },
  [SafetyVerdict.FAILED]: { label: "Failed", colorToken: "--color-state-danger-text", meaning: "The reported Logos safety check failed a blocking contract.", adr: "ADR-0162 / CORE-Logos LG-2", evidence: "SafetyVerdict is failed." },
  [SafetyVerdict.UNKNOWN]: { label: "Unknown", colorToken: "--color-state-undetermined", meaning: "The reported Logos safety check lacks proof evidence; this is not clear.", adr: "ADR-0162 / CORE-Logos LG-2", evidence: "SafetyVerdict is unknown." },
} satisfies BadgeMeta<SafetyVerdict>;
