# CORE Workbench v1 — UI Component Map

This document maps conceptual modules to concrete UI components.

The purpose is to keep the implementation coherent and prevent uncontrolled UI
sprawl.

---

# Global Layout

```text
+---------------------------------------------------------------+
| TopBar                                                        |
+-------------+-------------------------------------------------+
| SideNav     | MainContent                                     |
|             |                                                 |
|             |                                                 |
+-------------+-------------------------------------------------+
| StatusBar                                                     |
+---------------------------------------------------------------+
```

---

# TopBar

## Responsibilities

- runtime status
- backend indicator
- replay health
- revision warning badge
- active session id
- current branch/revision

## Components

- `RuntimeBackendBadge`
- `ReplayHealthBadge`
- `RevisionWarningBadge`
- `SessionIndicator`
- `GitRevisionPill`

## Anti-goals

- giant metrics wall
- animated status spam
- streaming logs

---

# Side Navigation

## Sections

- Chat
- Replay
- Proposals
- Evals
- Artifacts
- Runtime

## Components

- `NavItem`
- `NavSection`
- `UnreadIndicator` (optional future)

Navigation should feel closer to Linear/Raycast than a cloud admin portal.

---

# Chat Screen

## Layout

```text
+------------------------------------------------+
| Conversation                                   |
|                                                |
|  Prompt                                        |
|  Response                                      |
|  Trust badges                                  |
|                                                |
+----------------------+-------------------------+
| Composer             | TraceDrawer             |
+----------------------+-------------------------+
```

## Components

### Conversation

- `ConversationTimeline`
- `PromptBubble`
- `ResponseSurface`
- `TrustBadgeRow`

### Composer

- `PromptInput`
- `SubmitButton`
- `RuntimeModeIndicator`

### Trace Drawer

Collapsed by default.

Components:

- `TraceHashCard`
- `GroundingCard`
- `ReplayDigestCard`
- `ProposalReferenceCard`
- `AdmissibilityCard`
- `RawTraceViewer`

---

# Replay Theater

## Layout

```text
+--------------------+---------------------------+
| Artifact Selector  | Replay Comparison         |
|                    |                           |
|                    | Original vs Replay        |
|                    |                           |
+--------------------+---------------------------+
```

## Components

- `ArtifactList`
- `ReplayComparisonPanel`
- `ReplayStatusBadge`
- `ReplayDiffViewer`
- `ReplayMetadataTable`

## Important

No fake “thinking” animations.

Replay evidence should feel:

- precise,
- quiet,
- inspectable.

---

# Proposal Queue

## Layout

```text
+----------------------+--------------------------+
| Proposal List        | Proposal Detail          |
|                      |                          |
| pending              | replay evidence          |
| accepted             | proposed chain           |
| rejected             | downstream effect        |
|                      | provenance               |
+----------------------+--------------------------+
```

## Components

### List

- `ProposalTable`
- `ProposalStateBadge`
- `ProposalReplayBadge`

### Detail

- `ProposalSummaryCard`
- `ReplayEvidenceCard`
- `ProposalChainViewer`
- `ProposalProvenanceViewer`
- `SuggestedCLIBox`

## Forbidden

- accept button
- reject button
- workflow trigger

---

# Eval Center

## Layout

```text
+--------------------+----------------------------+
| Eval Lane List     | Eval Result Viewer         |
|                    |                            |
| cognition          | metrics                    |
| contemplation      | failures                   |
| learning-arc       | artifacts                  |
+--------------------+----------------------------+
```

## Components

- `EvalLaneCard`
- `EvalRunButton`
- `EvalMetricGrid`
- `EvalFailureViewer`
- `EvalArtifactLink`

## UX Rule

Failures should be easier to inspect than successes.

---

# Artifact Explorer

## Layout

```text
+--------------------+----------------------------+
| Artifact Tree      | Artifact Viewer            |
+--------------------+----------------------------+
```

## Components

- `ArtifactTree`
- `ArtifactMetadataPanel`
- `ArtifactJSONViewer`
- `ArtifactTextViewer`
- `DigestBadge`

---

# Runtime Screen

## Components

- `EngineStateCard`
- `CheckpointCard`
- `RevisionMismatchAlert`
- `RebootEventTimeline`
- `BackendStatusCard`

---

# Shared Components

## Badges

- replay passed/failed
- grounded
- pending review
- refusal
- mutation state
- revision warning

## Data viewers

- `StableJsonViewer`
- `DigestValue`
- `MetadataTable`
- `Timestamp`

## UX Principle

All shared components should prefer:

- stable layout,
- low motion,
- readable density,
- deterministic ordering.

---

# Components intentionally deferred

Not allowed in v1:

- AI avatar system
- agent marketplace
- plugin panels
- node graph builders
- workflow automation canvas
- hidden background orchestration
- animated cognition theater
