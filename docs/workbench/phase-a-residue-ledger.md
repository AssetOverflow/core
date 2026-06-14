# Wave M B3.5-e — Phase A Residue Ledger

Date: 2026-06-13
Status: active consolidation ledger

| Item | Status | Reason | Next PR |
|---|---|---|---|
| Density preferences | implemented | Settings owns a `comfortable` / `compact` mode; Shell publishes `data-density`, and shared chrome/primitives consume density variables for shell, panel, row, nav, footer, metadata, and button spacing. | None. |
| Command palette route drift | implemented | Navigate commands derive from `WORKBENCH_ROUTES`; Demos and Calibration are palette-visible. | None. |
| Landing route drift | implemented | Landing route ids derive from `WORKBENCH_ROUTES`; Replay and Calibration are eligible. | None. |
| Deterministic DAG consumers beyond proposal chain | implemented | Demo runs now expose backend-projected `DemoEvidenceDag` records for all PCCP proof-promotion scenarios and deductive-entailment traces, rendered by Demo Theater with the shared deterministic DAG primitive. | None. |
| Calibration evidence subject | implemented | `calibration_class` is addressable via `/calibration?inspect=calibration:<className>` and renders in RightInspector/EvidenceChainRail. | None. |
| UI/UX guide | implemented | `docs/workbench/UI-UX-GUIDE.md` now records the current 12-route map, evidence grammar, route proofs, and absences. | Keep updated when route registry changes. |
| Route registry | implemented | `workbench-ui/src/app/routes.ts` is the route source for App, LeftNav, palette, shortcuts, landing prefs, and route tests. | None. |
| B4 source tuple | implemented | Engine producer landed (2026-06-13): `core/cognition/leeway.py` emits an observational `LeewayRecord` on the turn result from the reach-policy + `LicenseDecision` the response path already computes; `workbench/api.py` maps it to `LeewayEvidence` across the read-only firewall. Every turn now carries an honest record; the existing B4a UI renders it. | — (follow-up: a SERVE-licensed fixture to exercise the earned-`APPROXIMATE` path end-to-end). |
