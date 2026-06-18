# Workbench Capability Mastery Implementation Plan

**Branch:** `feat/workbench-capability-mastery`
**Status:** Active development — multiple components landed and integrated

## Completed (as of 2026-06-18)

- [x] Created detailed implementation plan (this document)
- [x] Added `ExperienceFlywheelPanel.tsx` (full-featured, design-system compliant component with search, filters, summary metrics, detail inspector using StableJsonViewer + MetadataTable, honest states)
- [x] Promoted `ExperienceRecord` interface to shared `src/types/api.ts`
- [x] Integrated `ExperienceFlywheelPanel` into `EvalsRoute.tsx` (right pane, after WrongZeroLedger)
- [x] Created `CapabilityParadigmPanel.tsx` placeholder
- [x] Integrated `CapabilityParadigmPanel` into `EvalsRoute.tsx`

## Goal
Extend the CORE Workbench to fully expose the new capability-front artifacts (Experience Flywheel, capability paradigm lifts, Gate processes) for utmost mastery and auditability.

## Key Surfaces Delivered

### Experience Flywheel
- Bounded practice-memory records
- Compaction, retention gates, hazard/family blocking, promotion candidates
- Currently shows nice empty state with CLI guidance; ready for real data wiring

### Capability Paradigm
- Placeholder for lifts, Gate A* verdicts, derivation strikes, ratification evidence
- Will expand with real data from recent capability sprint work

## Remaining Work (High Priority)

- Wire real flywheel data (new query hook + backend endpoint in `workbench/api.py`)
- Flesh out `CapabilityParadigmPanel` with actual lift/gate data
- Add capability health indicators to `LivedLife` / StatusFooter
- Backend stubs for flywheel and capability ledger
- Full ADR or update to existing workbench ADRs
- Local verification + tests

## Success Criteria
- Operator can inspect flywheel records and understand retention/compaction decisions directly in Evals
- Capability paradigm progress is visible and linked to evidence
- All new surfaces follow the strict evidence-first, read-only, design-system rules of the Workbench

**Next:** Open draft PR summarizing the work.
