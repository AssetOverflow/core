/**
 * Documented GSM8K capability milestones — sourced from committed lookback
 * analyses on main through PR 824. These are NOT live API values; labels must
 * stay honest (ADR-0160 / ADR-0162).
 */

export type DocumentedScore = {
  correct: number;
  refused: number;
  wrong: number;
};

export type GateMilestone = {
  gate: string;
  organ: string;
  sprint: string;
  pr: string;
  newlySolved: string[];
  scoreAfter: DocumentedScore;
  lookbackDoc: string;
};

export type BlockedFamily = {
  family: string;
  cases: string[];
  reason: string;
};

/** Serving baseline after PR 824 (Sprint 11), from lookback evidence. */
export const DOCUMENTED_TRAIN_SAMPLE_BASELINE: DocumentedScore = {
  correct: 24,
  refused: 26,
  wrong: 0,
};

export const DOCUMENTED_BASELINE_LABEL =
  "Documented baseline (train_sample after PR 824 — not a live API read)";

export const GATE_LADDER_A2E_A2Q: GateMilestone[] = [
  {
    gate: "A2e",
    organ: "goal_residual",
    sprint: "Strike batch 4 (PR 814)",
    pr: "PR 814",
    newlySolved: [],
    scoreAfter: { correct: 10, refused: 40, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint5-lookback-2026-06-17.md",
  },
  {
    gate: "A2g",
    organ: "duration_segment_total",
    sprint: "Sprint 6 (PR 817)",
    pr: "PR 817",
    newlySolved: ["0015"],
    scoreAfter: { correct: 14, refused: 36, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint6-lookback-2026-06-17.md",
  },
  {
    gate: "A2h",
    organ: "survey_rate_earnings",
    sprint: "Sprint 6 (PR 817)",
    pr: "PR 817",
    newlySolved: ["0045"],
    scoreAfter: { correct: 14, refused: 36, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint6-lookback-2026-06-17.md",
  },
  {
    gate: "A2i",
    organ: "round_trip_trip_duration",
    sprint: "Sprint 7 (PR 818)",
    pr: "PR 818",
    newlySolved: ["0030"],
    scoreAfter: { correct: 16, refused: 34, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint7-lookback-2026-06-17.md",
  },
  {
    gate: "A2j",
    organ: "giveaway_target_residual",
    sprint: "Sprint 7 (PR 818)",
    pr: "PR 818",
    newlySolved: ["0035"],
    scoreAfter: { correct: 16, refused: 34, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint7-lookback-2026-06-17.md",
  },
  {
    gate: "A2k",
    organ: "fraction_decrease",
    sprint: "Sprint 8 (PR 819)",
    pr: "PR 819",
    newlySolved: ["0005"],
    scoreAfter: { correct: 18, refused: 32, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint8-lookback-2026-06-17.md",
  },
  {
    gate: "A2l",
    organ: "percent_partition",
    sprint: "Sprint 8 (PR 819)",
    pr: "PR 819",
    newlySolved: ["0046"],
    scoreAfter: { correct: 18, refused: 32, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint8-lookback-2026-06-17.md",
  },
  {
    gate: "A2m",
    organ: "temporal_tariff",
    sprint: "Sprint 9 (PR 820/PR 822)",
    pr: "PR 820",
    newlySolved: ["0001"],
    scoreAfter: { correct: 21, refused: 29, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint9-lookback-2026-06-17.md",
  },
  {
    gate: "A2n",
    organ: "affine_fraction_delta",
    sprint: "Sprint 9 (PR 820/PR 822)",
    pr: "PR 820",
    newlySolved: ["0010", "0017"],
    scoreAfter: { correct: 21, refused: 29, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint9-lookback-2026-06-17.md",
  },
  {
    gate: "A2o",
    organ: "affine_comparative_inversion_total",
    sprint: "Sprint 10 (PR 823)",
    pr: "PR 823",
    newlySolved: ["0006"],
    scoreAfter: { correct: 23, refused: 27, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint10-lookback-2026-06-17.md",
  },
  {
    gate: "A2p",
    organ: "sequential_comparative_scale",
    sprint: "Sprint 10 (PR 823)",
    pr: "PR 823",
    newlySolved: ["0009"],
    scoreAfter: { correct: 23, refused: 27, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint10-lookback-2026-06-17.md",
  },
  {
    gate: "A2q",
    organ: "calendar_grounded_piecewise_daily_hours_total",
    sprint: "Sprint 11 (PR 824)",
    pr: "PR 824",
    newlySolved: ["0013"],
    scoreAfter: { correct: 24, refused: 26, wrong: 0 },
    lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint11-lookback-2026-06-17.md",
  },
];

export const BLOCKED_FAMILIES: BlockedFamily[] = [
  {
    family: "DCS / relation_hypothesis",
    cases: ["0032", "0047"],
    reason: "Sealed-wrong neighbors; divisive/count surfaces blocked until typed chain clears wrong-risk.",
  },
  {
    family: "currency_amount",
    cases: ["0019", "0028"],
    reason: "Currency grounding not ratified for serving; conservative refusal preserved.",
  },
  {
    family: "sealed_elimination",
    cases: ["0011", "0026"],
    reason: "Sealed practice elimination surfaces; serving admission blocked.",
  },
  {
    family: "multiplicative_aggregate (wholesale)",
    cases: ["0006", "0013", "0025", "0047"],
    reason: "Rejected broad MA promotion — 0025/0047 sealed-wrong share MA surface; end-to-end chain not safe.",
  },
];

export const CLUSTER_CONTRACT_SPRINT11 = {
  familyId: "calendar_grounded_piecewise_daily_hours_total",
  organs: ["piecewise_daily_hours_total (Gate A2q)", "calendar_grounding (civil_month_day_count_table)"],
  includedCase: "gsm8k-train-sample-v1-0013",
  provenance: "calendar_table:{month_name}",
  lookbackDoc: "docs/analysis/gsm8k-capability-paradigm-sprint11-lookback-2026-06-17.md",
};

export const EXPERIENCE_FLYWHEEL_CLI =
  "scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience.json";

export const EXPERIENCE_RECORD_FIELDS: { key: string; value: string }[] = [
  { key: "record_id", value: "SHA-256 of load-bearing fields" },
  { key: "case_id / serving_status / sealed_status", value: "Per-case diagnostic posture" },
  { key: "candidate_family / first_missing_primitive", value: "Typed lift hypothesis" },
  { key: "hazard_tags / promotion_status", value: "Retention and promotion gates" },
  { key: "source_report_hash", value: "Read-only report digest — report.json never mutated" },
];