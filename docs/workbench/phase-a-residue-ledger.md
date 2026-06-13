# Wave M B3.5-e — Phase A Residue Ledger

Date: 2026-06-13
Status: active consolidation ledger

| Item | Status | Reason | Next PR |
|---|---|---|---|
| Density preferences | deferred | Settings currently owns landing route and inspector-open preferences, but no density mode is wired through the shell/design tokens. | Phase A polish follow-up. |
| Command palette route drift | implemented | Navigate commands derive from `WORKBENCH_ROUTES`; Demos and Calibration are palette-visible. | None. |
| Landing route drift | implemented | Landing route ids derive from `WORKBENCH_ROUTES`; Replay and Calibration are eligible. | None. |
| Deterministic DAG consumers beyond proposal chain | deferred | Proposal chain uses the primitive; PCCP proof-promotion and entailment traces still need real reader wiring. | Phase A follow-up before Phase C visualizer expansion. |
| Calibration evidence subject | implemented | `calibration_class` is addressable via `/calibration?inspect=calibration:<className>` and renders in RightInspector/EvidenceChainRail. | None. |
| UI/UX guide | implemented | `docs/workbench/UI-UX-GUIDE.md` now records the current 12-route map, evidence grammar, route proofs, and absences. | Keep updated when route registry changes. |
| Route registry | implemented | `workbench-ui/src/app/routes.ts` is the route source for App, LeftNav, palette, shortcuts, landing prefs, and route tests. | None. |
| B4 source tuple | blocked | Full B4 producer is absent. B4a nullable `LeewayEvidence` read model now exists, but no backend path populates it yet. | B4 producer wiring from engine-owned approximation/calibration evidence. |
