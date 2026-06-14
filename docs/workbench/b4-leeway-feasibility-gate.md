# Wave M B3.5-c — B4 Leeway Feasibility Gate

Date: 2026-06-13
Status: **GATE CLEARED (2026-06-13)** — the engine-side producer now exists.
`core/cognition/leeway.py::build_leeway_record` turns the reach-policy +
`LicenseDecision` the response path already computes into an observational
`LeewayRecord` on `CognitiveTurnResult`; `workbench/api.py::_leeway_evidence_from_result`
maps it to `LeewayEvidence` (no `reliability_gate` import — firewall intact);
the journal persists it and the existing B4a UI (Replay / Proposals /
RightInspector) renders it. Every turn now carries an honest record (STRICT →
"no latitude"; a licensed SERVE widening → the real class/θ/`[approximate]`).
Scope + design: `b4-leeway-producer-scope-2026-06-13.md`. Original gate text
below, kept for provenance.

## Finding

B4 needs a tuple that explains why approximation or leeway was granted:

- `class_name`
- `license`: `PROPOSE | SERVE | blocked | unknown`
- `theta`
- `claim_disclosure`: `approximate | verified | proposal_only | none`
- `source_digest`
- `calibration_evidence_ref`

Before this slice, that tuple was not present in `ChatTurnResult`,
`TurnJournalEntry`, `ProposalDetail`, or `MathProposalDetail`. Any UI card that
named class/license/theta would have had to infer calibration state in the
frontend.

## B4a Read Model

`workbench/schemas.py::LeewayEvidence` is now the only lawful tuple shape for
B4 explanations. It is nullable on:

- `ChatTurnResult`
- `TurnJournalEntrySchema`
- `TurnReplayComparison`
- `ProposalDetail`
- `MathProposalDetail`

Frontend mirrors live in `workbench-ui/src/types/api.ts`. The shared
`LeewayEvidenceCard` renders the tuple when present and renders explicit absence
when it is null or missing.

## Gate Result

B4 UI annotations may start only when a backend producer populates
`LeewayEvidence` from engine-owned calibration evidence or a lawful backend join.
Until then, Proposals and Replay can show "No leeway evidence recorded."; they
must not explain leeway from frontend-only class/license inference.

## Follow-Up

Next PR: B4 producer wiring. Candidate sources are the turn/proposal creation
paths that already know whether a claim is approximate, plus the calibration
reader's `calibration:<class_name>` evidence subject.
