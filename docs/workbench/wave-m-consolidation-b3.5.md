# Wave M Consolidation / B3.5 — Workbench Mastery Before Next Complexity

**Status:** Proposed planning slice  
**Scope:** Workbench UI/UX architecture, route substrate, evidence subjects, calibration discipline, B4 readiness  
**Branch:** `docs/proposal-artifact-substrate-v1`  
**No code changes in this document.**

---

## Purpose

Before Workbench Phase B4 or Phase C adds more visible complexity, the existing Workbench substrate must be metabolized into one coherent product architecture.

Recent Workbench waves successfully made determinism, replay, demos, calibration, and wrong=0 discipline visible. But the surface has outgrown parts of its original route, command, evidence-subject, and documentation substrate. This document captures the consolidation plan discussed after Wave M B3.

The intent is not to slow momentum. The intent is to prevent Workbench from becoming a set of individually-good screens that contradict each other at the navigation, evidence, or authority layer.

---

## Governing doctrine

This slice inherits:

- ADR-0160: Workbench is an operator/auditor interface, not a chat clone.
- ADR-0162: design is a trust surface; every route must honor empty/error/loading contracts.
- ADR-0173: ratification authority is narrow and handler-bound.
- `CLAUDE.md`: no hidden mutation, no visualization as proof without deterministic artifact, no parallel learning path.
- Wave M worthiness plan: make calibration/serving discipline and cognition substrate visible without reimplementing engine math in the frontend.

---

## Current diagnosis

### 1. The route substrate has drifted

The Workbench now has more routes than the original route/navigation assumptions. The UI has grown to include Demos and Calibration, but command-palette entries, landing-route preferences, keyboard assumptions, docs, and route conformance lists can drift unless there is a single source of truth.

This is not only a convenience bug. In Workbench, navigation is evidence access. If a route exists in LeftNav but not in command search, or exists in App routing but not in docs, the product is teaching operators an inconsistent map of its own evidence manifold.

### 2. Calibration is visible, but not yet fully evidence-native

Calibration classes and serving metrics are visible, and wrong=0 is now a felt global presence. But calibration class selection is not yet a first-class evidence subject with a URL-addressable inspector projection.

That means calibration is still partly a page-local experience, not fully part of the Evidence Chain Rail.

### 3. B4 is conceptually right but data-shape risky

B4 wants the Replay/Proposals evidence rails to explain why approximation/leeway was granted: class, license, theta, disclosure, and relation to HITL ratification.

That is the right product idea. But the UI must not invent the tuple. If turn/proposal schemas do not carry those fields in typed form, B4 needs a backend/schema/read-model slice first.

### 4. Documentation is behind the product

A UI/UX guide was discussed as necessary for external evaluators and new operators. It must reflect the current route count and current capabilities, including what is absent.

Old documentation that says eleven routes while the app has twelve is worse than missing documentation: it trains reviewers to distrust the map.

### 5. Phase A residue should be either finished or explicitly deferred

Some design-mastery items remain partially open, such as density preferences, broader deterministic-DAG consumers, and route/keyboard command truth. These should be resolved or named before moving into the next layer.

---

## Decision

Insert a consolidation slice before building more complexity:

```text
Wave M B3.5 — Workbench Consolidation
```

This slice standardizes route truth, evidence-subject truth, calibration evidence integration, B4 feasibility, and operator documentation.

It must be small enough to review, but serious enough to prevent architectural drift.

---

## Deliverable 1 — Route registry unification

Create one route registry that can be consumed by:

- `App` route declarations
- `LeftNav`
- `CommandPalette`
- global keyboard help
- landing route preferences
- route conformance tests
- UI/UX guide route table

The registry should identify:

```text
id
path
label
description
left_nav_visible
command_palette_visible
landing_route_allowed
keyboard_shortcut
route_conformance_required
```

### Critical rule

If there are more routes than single-digit keyboard shortcuts, the UI must say so honestly.

Good:

```text
Pinned route shortcuts: Chat through Settings
All routes searchable in Command Palette
```

Bad:

```text
Navigate to every route with 1–10
```

when there are more than ten routes.

### Acceptance

- Command palette contains every command-visible route.
- Landing route dropdown includes every landing-eligible route.
- Demos and Calibration cannot silently fall out of command/search surfaces.
- Route conformance fixtures derive from or assert against the registry.
- Tests fail if a route is added to App without updating the registry.

---

## Deliverable 2 — Calibration evidence subject

Add calibration to the evidence model.

Suggested subject:

```text
calibration_class
```

Possible address:

```text
calibration:<class_name>
```

or, if using URL path semantics:

```text
/calibration?inspect=calibration:<class_name>
```

The selected class should publish an evidence subject and render in the RightInspector / EvidenceChainRail.

### Inspector projection

Show only fields carried by the backend read model:

- class name
- correct / wrong / refused / committed counts
- Wilson floor / reliability floor
- propose threshold and license
- serve threshold and license
- coverage
- source digest / report path if available
- explicit absence for unavailable proof

### Acceptance

- Selecting a calibration class updates evidence subject.
- Deep link restores selected calibration evidence subject.
- RightInspector handles the subject without falling to raw unknown.
- Evidence Chain Rail names calibration as serving-discipline evidence, not runtime truth.
- Missing data renders as missing/unknown, not as green.

---

## Deliverable 3 — B4 leeway feasibility gate

Before implementing B4 UI annotations, prove the source tuple exists in typed data.

Required tuple:

```text
class_name
license: PROPOSE | SERVE | blocked | unknown
theta / threshold context
claim/disclosure: approximate | verified | proposal_only | none
source digest / calibration evidence reference
```

If this tuple is not present in `ChatTurnResult`, `TurnJournalEntry`, `ProposalDetail`, `MathProposalDetail`, or a lawful backend join, create B4a first.

### B4a — backend/schema/read-model first

B4a should add only the read model needed to explain leeway honestly.

No frontend card should explain what the data model cannot prove.

### Acceptance

- A served-with-leeway fixture renders class + threshold + license + disclosure.
- A fully verified turn renders no leeway annotation.
- If any tuple field is absent, UI renders explicit absence.
- No frontend-only inference of class/license/theta.

---

## Deliverable 4 — UI/UX guide

Create or update:

```text
docs/workbench/UI-UX-GUIDE.md
```

This guide should be accurate enough for:

- a new operator,
- an external evaluator,
- an implementation agent,
- a design reviewer,
- or a sponsor doing due diligence.

Required sections:

1. What Workbench is and is not.
2. How to run it.
3. The evidence model.
4. Current route map from the route registry.
5. What each route proves.
6. What each route does not prove.
7. Evidence subjects and address grammar.
8. Command palette and keyboard model.
9. Empty/error/loading doctrine.
10. Proposal vs ratification boundary.
11. Calibration / wrong=0 discipline.
12. CORE-Logos / packs current state and next state.
13. Known absences and follow-up items.

### Acceptance

- Route count matches code.
- Calibration and Demos are included.
- The guide distinguishes visible checks from actionable engineering flows.
- Missing features are named, not implied.

---

## Deliverable 5 — Phase A residue ledger

Before Phase C, create a small checklist ledger that says whether each residue item is implemented, deferred, or superseded.

Known residue:

- density preferences
- command palette route drift
- landing route drift
- deterministic DAG consumers beyond proposal chain
- calibration evidence subject
- UI/UX guide
- route registry
- B4 source tuple

### Acceptance

Each item has:

```text
status: implemented | deferred | superseded | blocked
reason
next PR if any
```

This avoids rediscovering the same gaps after each wave.

---

## No-go list

- No visual-only B4 leeway card.
- No frontend inference of calibration license.
- No route added in one place only.
- No command help that advertises shortcuts that do not exist.
- No hidden mutation or apply affordance.
- No vague “soon” docs; every absence must be named as absent.
- No Workbench route that cannot answer at least one ADR-0160 audit question.

---

## Implementation order

Recommended small PR sequence:

1. **B3.5-a — route registry**
2. **B3.5-b — calibration evidence subject**
3. **B3.5-c — B4 feasibility / schema audit**
4. **B3.5-d — UI/UX guide**
5. **B3.5-e — Phase A residue ledger**

B4 should not start until B3.5-c says the tuple exists or B4a creates it.

---

## Final design sentence

Workbench must not merely have many powerful screens. It must have one coherent evidence grammar.

B3.5 is the slice that makes the grammar true before the next layer speaks through it.
