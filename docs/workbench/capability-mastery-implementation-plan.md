# Workbench Capability Mastery Implementation Plan

**Branch:** `feat/workbench-capability-mastery`
**Created:** 2026-06-18
**Context:** Post Wave M UI work (June 14-15) and recent capability paradigm / GSM8K experience flywheel / Gate lifts (June 16-18 PRs #815, #816, etc.).

## Goal
Extend the CORE Workbench (v1 + design system) to fully expose and make auditable the new capability-front artifacts and processes, enabling operators to achieve utmost mastery over the deterministic geometric cognitive architecture. All changes must be read-only where possible, evidence-first, deep-linkable, replayable, design-system compliant (ADR-0162), and use honest states.

## Key New Concepts to Surface
- **Experience Flywheel** (`ExperienceRecord` from evals/gsm8k_math/.../experience.py): Compacted practice memory with retention gates, hazard/family blocking, provenance, promotion candidates.
- **Capability Paradigm / Derivation Lifts**: Question-bound product aggregates, Gate A1/A2a/A2b injections, strike batches, specific case lifts while preserving wrong=0.
- **Gate Processes & Verdicts**: Unit partitions, compositions, peer-pick, etc.
- Supporting: Sealed attempt scouts, frontier analysis, ratification evidence for capabilities.

## Prioritized Deliverables (Phased for Incremental PRs / Reconciliation)

### Phase 1: Foundation & Planning (Low risk, additive)
1. This plan document (done).
2. Infer and document `ExperienceRecord` and related schemas (from PR descriptions and code).
3. Create/update ADR or section for Workbench capability extensions.

### Phase 2: Types & Backend Stubs
- Extend `workbench-ui/src/types/api.ts` with new interfaces (ExperienceRecord, FlywheelSummary, CapabilityLift, GateVerdict, etc.).
- Add Python stubs or extensions in `workbench/` (e.g., new reader in schemas.py or dedicated flywheel.py, api endpoints in api.py for /flywheel, /capabilities).
- Update schema snapshots if needed.

### Phase 3: Core UI Components (New Files — Safe to Add)
**Primary: Evals Route Extensions**
- New: `workbench-ui/src/app/evals/ExperienceFlywheelPanel.tsx` (or subdir)
  - Uses: Panel, StableJsonViewer, MetadataTable, TruncatedCell, SearchInput, VirtualizedList or existing table patterns, EmptyState/ErrorState/LoadingState, badges (extend mappings if new enums).
  - Features: Filterable list of records (status, family, hazard_tags, promotion_candidate), compaction summary, detail drawer/inspector with provenance and retention rationale, links to source runs/reports.
  - States: Honest empty ("Run the flywheel CLI..."), error with reproducer.
- New or extended: `EvalWrongZeroLedger.tsx` or new tab/panel for capability sprint metrics and lift history.

**Secondary: Capability Surfaces**
- New: `workbench-ui/src/app/evals/CapabilityParadigmPanel.tsx` or integrated section showing active capabilities, recent lifts (e.g., product aggregates), gate status overview, with links to traces/derivations.
- Reuse/extend existing: TraceRoute or Contemplation for deeper gate/derivation inspection.

**Vault Integration**
- Enhance or add support in `VaultRoute.tsx` / related for new record types (facets, inspectors). May require minor edits + new helper components.

### Phase 4: Integration & Polish
- Edit `workbench-ui/src/app/routes.ts` and `LeftNav.tsx` or EvalsRoute to wire new panels/tabs (use existing patterns from Calibration, Logos tabs).
- Update `StatusFooter` or `LivedLifeRoute` for capability health indicators (wrong=0 pulse, flywheel size, recent lifts) — read-only.
- Command palette / shortcut extensions if useful.
- Full design system compliance: semantic tokens, enum-bound badges (tie to existing EpistemicState or new normative ones), no cognitive motion.
- Deep linking, evidence bundles support for flywheel artifacts.
- Test stubs or updates to conformance tests.

### Phase 5: Backend API & Data Serving
- Extend `workbench/api.py` and `schemas.py` to serve flywheel data, capability ledger snapshots, gate states (read-only).
- Ensure TanStack Query integration in UI (`src/api/queries.ts`).

## Exact File Touchpoints (from current tree on main)
**New files (preferred for clean branch):**
- docs/workbench/capability-mastery-implementation-plan.md (this)
- workbench-ui/src/app/evals/ExperienceFlywheelPanel.tsx
- workbench-ui/src/app/evals/CapabilityParadigmPanel.tsx (or similar)
- Possibly workbench/flywheel_reader.py or extensions in existing.

**Edits (use with SHA from tree or Copilot):**
- workbench-ui/src/app/evals/EvalsRoute.tsx (embed panels)
- workbench-ui/src/app/routes.ts
- workbench-ui/src/types/api.ts
- workbench-ui/src/app/LeftNav.tsx or commandRegistry.ts (if new nav)
- workbench/api.py, schemas.py
- Potentially docs/decisions/ new ADR or update to ADR-0160/0162

## Design Constraints (Non-negotiable)
- Read-only by default (per ADR-0160).
- Every panel answers: What happened? Evidence? Replayable? Why allowed? Ratified?
- Use StableJsonViewer for all complex records.
- Honest Empty/Error/Loading states with next-action guidance and reproducers.
- Keyboard-first, reduced motion.
- Semantic color badges only via existing mappings or safe extensions.
- No serving mutation, no corpus changes.

## How to Reconcile / Next Steps
- This branch can be used for incremental commits.
- Use GitHub Copilot coding agent (via tool) for implementing specific components or integrations.
- Local clone recommended for: pnpm dev, type checking, e2e tests (Playwright in e2e/), Python backend validation, visual review in /preview.
- PR can be opened as draft once initial components land; team reviews and reconciles with main as sections complete.

## Success Criteria for "Utmost Mastery"
- Operator can inspect any ExperienceRecord from the flywheel, understand compaction/retention decisions, and link to source evidence.
- Capability paradigm lifts and gate processes are visible and auditable without leaving the Workbench.
- New evidence types feel native to the existing Vault/Trace/Evals experience.
- Invariants (wrong=0, algebraic coherence) are surfaced prominently.

**Status:** Branch created. Ready for file additions and scoped implementation via connector or Copilot delegation.
