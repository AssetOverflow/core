export enum EpistemicState {
  PERCEIVED = "perceived",
  EVIDENCED = "evidenced",
  EVIDENCED_INCOMPLETE = "evidenced_incomplete",
  VERIFIED = "verified",
  DECODED = "decoded",
  DECODED_UNARTICULATED = "decoded_unarticulated",
  INFERRED = "inferred",
  UNVERIFIED_POSSIBLE = "unverified_possible",
  UNVERIFIED_NOVEL = "unverified_novel",
  CONTRADICTED = "contradicted",
  AMBIGUOUS = "ambiguous",
  UNDETERMINED = "undetermined",
  SCOPE_BOUNDARY = "scope_boundary",
  COMPUTATIONALLY_BOUNDED = "computationally_bounded",
  EPISTEMIC_STATE_NEEDED = "epistemic_state_needed",
}

export enum NormativeClearance {
  CLEARED = "cleared",
  VIOLATED = "violated",
  UNASSESSABLE = "unassessable",
  SUPPRESSED = "suppressed",
}

export enum ReviewState {
  PENDING = "pending",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  WITHDRAWN = "withdrawn",
}

export enum GroundingSource {
  PACK = "pack",
  TEACHING = "teaching",
  VAULT = "vault",
  PARTIAL = "partial",
  OOV = "oov",
  NONE = "none",
}

export enum SafetyVerdict {
  CLEAR = "clear",
  WARNING = "warning",
  FAILED = "failed",
  UNKNOWN = "unknown",
}

export type BadgeMeta<T extends string> = Record<
  T,
  {
    label: string;
    colorToken: string;
    meaning: string;
    adr: string;
    evidence: string;
  }
>;
