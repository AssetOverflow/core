# Proposal Artifact Substrate v1

**Status:** Proposed planning substrate  
**Scope:** Workbench / teaching / proposal artifacts / future CORE-Logos Studio  
**Branch:** `docs/proposal-artifact-substrate-v1`  
**No ADR number assigned in this document.** This is a consolidation plan and implementation brief. A numbered ADR may ratify it later if the design survives review.

---

## Purpose

CORE has reached the point where `proposal` cannot remain a page-specific idea or a math-specific workflow. Proposal artifacts are the system's lawful bridge between:

```text
engine observation
→ structured hypothesis
→ evidence-bearing proposed change
→ operator review
→ ratified mutation, if and only if an admitted handler exists
→ deterministic replay / audit reconstruction
```

The current implementation has one deep corridor — math proposals — and one shallower corridor — cognition teaching proposals. CORE-Logos / pack proposals are not yet forged through this substrate at all. That split was historically reasonable: math had ratification handlers that were already proven and narrowly admitted by ADR-0173. But keeping separate proposal pipelines would now create architectural drift.

This document defines the next substrate: one universal `ProposalArtifact` envelope, with subject-specific adapters and subject-specific validators, while preserving every existing trust boundary.

The goal is not to grant new mutation power. The goal is to make every proposed change pass through the same evidence, validation, safety, replay, handler, and audit spine.

---

## Governing constraints read before this plan

This plan is constrained by the following prior doctrine.

### CORE pillars and runtime invariants

From `README.md` and `CLAUDE.md`:

- CORE is a deterministic cognitive field system, not a transformer wrapper or generic chatbot.
- The field invariant remains load-bearing: `versor_condition(F) < 1e-6` / `||F * reverse(F) - 1||_F < 1e-6`.
- Coherence is constructed, not monitored and repaired.
- Mechanical Sympathy, Semantic Rigor, and Third Door remain the design filter.
- Learning must be reviewed and auditable.
- Pack mutation is proposal-only until reviewed.
- No parallel correction or learning path.
- If a visualization is load-bearing, the underlying data must first exist as deterministic JSON/JSONL/Markdown.
- Any path touching packs, logs, dynamic imports, or filesystem paths must state its trust boundary.

### ADR-0160 — Workbench v1

- Workbench is an operator/auditor interface, not a chat clone.
- It must answer: what happened, why allowed, what evidence supports it, can it replay, did it mutate anything, who/what ratifies next.
- V1 is read-only by default.
- Proposal before mutation and replay before persuasion are product doctrine.
- Mutating proposals, corpus, packs, workflows, or engine state requires a later ADR and explicit gates.

### ADR-0161 — HITL async queue

- The HITL queue is a deterministic projection over append-only sources, not a new persistence substrate.
- Queue identity is `proposal_id`.
- Pending proposals never become active truth.
- There are no proposal-on-proposal dependencies.
- CI may stage artifacts and open PRs but may not ratify.
- Pack mutation queue remains out of scope in ADR-0161.

### ADR-0162 — Workbench design system

- Design is a trust surface, not styling.
- Stable JSON viewing must be deterministic, lossless, copyable, diffable, and large-document safe.
- Empty/error/loading states must name next action, mutation status, reproducer, and safe retry semantics.
- No animated cognition theater, no dashboard soup, no color-only state encoding.
- Proposal queue and ratification components must preserve auditability and keyboard-first operation.

### ADR-0172 — math corpus decomposition mechanism

- Proposal artifacts must carry structured reasoning traces.
- Operators review the trace, not a black-box conclusion.
- Reasoning traces are content-addressable and replayable.
- Tier 2 proposals must include self-test evidence before HITL review.
- Operator verdicts are future teaching signals; rejection/refinement rationale is part of the learning loop.

### ADR-0173 — Workbench ratification trust boundary

- The Workbench is a local keyboard accelerator over existing local ratification handlers.
- It is not a fourth ratification surface and not a new trust boundary.
- Existing admitted handlers may be driven by `POST /math-proposals/{id}/ratify` only because they already preserve the same evidence, preconditions, exceptions, and append-only JSONL effects as CLI/Python entrypoints.
- The amendment is narrow. It does not admit new mutation paths, new corpora, new pack types, remote operator auth, or unproven handlers.
- No auto-ratify. No batch ratification in v1. No bypass of handler preconditions.

### ADR-0015 — CORE-Logos language packs

- A language pack is not a dataset or translation table.
- It is a deterministic, checksummed, compiled linguistic manifold.
- Pack contents include manifest, lexicon, morphology, grammar attractors, cross-language resonance edges, and holonomy alignment cases.
- OOV policy, ordering, morphology, alignment, and holonomy proof cases are load-bearing.
- Unknown depth-language surfaces must not silently collapse to fallback points.

---

## Problem statement

The Workbench currently exposes proposal artifacts unevenly:

```text
math proposals      → deep artifact record + UI detail + ratification corridor
cognition proposals → queue projection + replay/provenance inspection + CLI fallback
CORE-Logos packs    → manifest/checksum inspection only, no proposal forge
future modalities   → no proposal path yet
```

This split is a historical implementation sequence, not the desired architecture.

The risk is that each subject grows its own lifecycle:

```text
math proposal lifecycle
cognition proposal lifecycle
pack proposal lifecycle
vision proposal lifecycle
```

That would violate the Workbench's evidence-manifold direction and eventually create contradictory semantics for state, review, safety, replay, and ratification.

The correct shape is:

```text
one universal proposal artifact lifecycle
+ subject-specific proposal payloads
+ subject-specific validators
+ subject-specific handlers
+ one Workbench review language
```

---

## Decision

Introduce a universal `ProposalArtifact` substrate as the single Workbench-facing envelope for all proposed changes.

The envelope standardizes identity, subject, evidence, reasoning, validation, affected artifacts, safety checks, handler routing, ratification status, and audit references.

The envelope does **not** standardize the domain payload itself. Math, cognition, CORE-Logos, vision, audio, and future subjects may each define typed payloads and validation reports. What is universal is the review spine.

---

## Core distinction: proposal artifact vs ratification handler

A proposal artifact is an evidence-bearing candidate for review.

A ratification handler is a pre-admitted local mutation path that can apply a candidate after all preconditions pass.

These must remain separate.

```text
ProposalArtifact exists → reviewable
ProposalArtifact validates → still not applied
ProposalArtifact routes to admitted handler → apply may be enabled
No admitted handler → proposal-only / CLI fallback / future ADR required
```

This distinction is the core safety boundary for CORE-Logos. A browser may help draft a Logos proposal before a handler exists. It must not apply that proposal until an admitted handler exists and tests prove the same invariants as the CLI path.

---

## Universal proposal envelope

The implementation should converge toward this shape. Field names may be refined during implementation, but the sections are load-bearing.

```text
ProposalArtifact:
  proposal_id: str
  schema_version: str
  subject: ProposalSubject
  state: pending | accepted | rejected | withdrawn | deferred | unknown
  capability_level: inspect_only | proposal_only | ratification_enabled
  source: ProposalSource
  proposed_change: ProposedChange
  reasoning_trace: ReasoningTrace | None
  evidence_pointers: tuple[EvidencePointer, ...]
  validation: ValidationReport | None
  replay_evidence: ReplayEvidence | None
  safety_report: SafetyReport | None
  affected_artifacts: tuple[AffectedArtifact, ...]
  checksum_impacts: tuple[ChecksumImpact, ...]
  handler_route: HandlerRoute | None
  suggested_cli: str | None
  audit_refs: tuple[AuditRef, ...]
  ui_disclosure: ProposalDisclosure
```

### `ProposalSubject`

```text
ProposalSubject:
  kind: math | cognition | logos_pack | pack | vision | audio | sensorimotor | runtime_policy | unknown
  subject_id: str
  partition: str
  display_name: str
```

Examples:

```text
math / shape_category=multi_quantity_composition
cognition / TeachingChainProposal
logos_pack / he_logos_micro_v1 / alignment_edge_add
logos_pack / grc_logos_micro_v1 / holonomy_case_add
```

### `capability_level`

This field prevents the UI from implying authority it does not have.

| Level | Meaning | UI may do |
|---|---|---|
| `inspect_only` | Artifact can be inspected but not changed from Workbench. | Read, copy evidence, navigate, show CLI fallback. |
| `proposal_only` | Workbench may draft or preview a proposal artifact, but cannot apply it. | Structured editor, validation preview, patch preview, export/copy CLI. |
| `ratification_enabled` | A handler exists and was admitted by ADR/tests. | Enable ratify/reject/defer controls subject to preconditions. |

No route may render a `Ratify` affordance unless `capability_level == ratification_enabled` and `handler_route` is present and admitted.

### `ProposedChange`

```text
ProposedChange:
  change_kind: str
  payload: object
  payload_digest: str
  human_summary: str
```

This keeps payload type open while making the envelope hashable and inspectable.

### `EvidencePointer`

```text
EvidencePointer:
  pointer_id: str
  evidence_hash: str | None
  source_path: str | None
  json_pointer: str | None
  trace_hash: str | None
  description: str | None
```

Evidence may point to audit rows, eval cases, refusal records, trace rows, pack entries, alignment edges, holonomy cases, or prior proposal verdicts.

### `ReasoningTrace`

Reuse ADR-0172's concept: a stable sequence of typed reasoning steps.

```text
ReasoningTrace:
  trace_id: str
  steps: tuple[ReasoningStep, ...]
```

The Workbench reviews the trace and the evidence, not merely the conclusion.

### `ValidationReport`

```text
ValidationReport:
  validator_id: str
  verdict: pass | warning | fail | not_run
  checks: tuple[ValidationCheck, ...]
```

Subject adapters define checks, but the envelope provides a uniform report surface.

### `SafetyReport`

```text
SafetyReport:
  verdict: clear | warning | failed | unknown
  wrong_zero_risk: none | bounded | live | unknown
  mutation_boundary: none | proposal_only | admitted_handler | forbidden
  checks: tuple[SafetyCheck, ...]
```

This is the field that prevents proposal UI from becoming persuasion theater.

### `AffectedArtifact`

```text
AffectedArtifact:
  path: str
  artifact_kind: str
  before_digest: str | None
  after_digest: str | None
  mutation_mode: proposal_only | append_only | replace | unknown
```

For proposal-only flows, `after_digest` may be predicted, not applied. The UI must label predicted digests as predicted.

### `ChecksumImpact`

```text
ChecksumImpact:
  manifest_path: str | None
  field: str
  before: str | None
  after: str | None
  status: unchanged | predicted | applied | not_applicable
```

### `HandlerRoute`

```text
HandlerRoute:
  handler_id: str
  admitted_by: str
  route: str
  required_preconditions: tuple[str, ...]
  dry_run_supported: bool
```

No `HandlerRoute` means no Workbench ratification.

---

## Universal lifecycle

Every proposal artifact moves through the same conceptual phases.

```text
drafted
→ validated
→ replayed_or_checked
→ safety_reviewed
→ routed_or_blocked
→ operator_decision
→ audit_recorded
→ replay_reconstructible
```

The stored state alphabet may remain ADR-0057-compatible where required. The Workbench can render additional transient UI dispositions, but durable state must not silently widen without a ratifying ADR.

### Drafted

A candidate exists. It may come from the engine, CLI, Workbench forge, a demo, or a future modality compiler.

### Validated

Subject-specific validators run. This may be syntax/schema validation, replay equivalence, pack checksum verification, morphology-link verification, holonomy proof status, or eval impact analysis.

### Replayed or checked

Not every subject has turn replay. The universal phase is evidence re-checking:

- math: replay equivalence / wrong=0 gate / two-arm confirmation
- cognition: teaching-chain replay equivalence
- CORE-Logos: pack compile/verify, morphology links, alignment targets, holonomy cases, checksum impacts
- modalities: deterministic compiler replay / content-addressed delta replay

### Safety reviewed

Safety report names mutation boundary, wrong=0 risk, partition risk, path safety, checksum risk, OOV/gate risk, and any missing proof obligations.

### Routed or blocked

If an admitted handler exists, the proposal may show a ratification corridor. If not, the proposal remains proposal-only with a CLI/export/follow-up path.

### Operator decision

Operator may ratify, reject, defer, withdraw, or refine depending on admitted state machine for the subject. This document does not widen durable state by itself.

### Audit recorded

Every action that crosses a mutation boundary emits audit/telemetry per ADR-0173. Proposal-only draft creation should also be recordable once the substrate is implemented, but it must be labeled as non-mutating.

### Replay reconstructible

Given the artifact sources and proposal logs, the Workbench projection must be reconstructible without hidden UI state.

---

## Subject adapters

The universal envelope is consumed through adapters. Each adapter names source files, validators, safety checks, handler status, and UI affordances.

### Math adapter

Current maturity: `ratification_enabled` for admitted claim classes.

Sources:

- `teaching/math_proposals/proposals.jsonl`
- ratified math lexicon/frame/composition artifacts
- eval/audit reports

Existing strengths:

- self-contained JSONL proposal records
- evidence pointers
- reasoning trace steps
- wrong=0 assertion
- replay equivalence hash
- handler dispatch for LexicalClaim, FrameClaim, CompositionClaim
- Workbench ratify/reject/defer UI

Required migration:

- wrap existing `MathProposalDetail` into `ProposalArtifact`
- retain existing routes for compatibility during migration
- expose `capability_level=ratification_enabled` only for admitted handlers
- populate `affected_artifacts` and `checksum_impacts` after handler dry-run or predicted receipt support exists
- connect audit events back into proposal timeline

No behavior change in the migration PR. The first math adapter PR should be read-model-only.

### Cognition adapter

Current maturity: `inspect_only`, moving to `ratification_enabled` only after Surface C parity is proven.

Sources:

- `teaching/proposals/proposals.jsonl`
- contemplation reports
- replay evidence
- operator transition records

Required work:

- wrap `ProposalDetail` into `ProposalArtifact`
- populate artifact references instead of returning empty `artifact_refs`
- add review history / timeline projection
- prove Surface C parity before enabling Workbench ratification
- preserve ADR-0057 / ADR-0161 state reconstruction

### CORE-Logos adapter

Current maturity: no proposal forge yet. Target next state: `proposal_only` first, not ratification-enabled.

Sources:

- `language_packs/data/<pack_id>/manifest.json`
- `lexicon.jsonl`
- `glosses.jsonl`
- morphology files
- `alignment.jsonl`
- frame/composition files when present
- holonomy proof cases
- pack validators / compiler checks

Initial change kinds:

```text
lexicon_add
lexicon_update
lexicon_remove
gloss_add
gloss_update
morphology_add
morphology_update
alignment_edge_add
alignment_edge_update
holonomy_case_add
holonomy_case_update
frame_add
composition_add
```

Initial UI capability:

```text
structured proposal drafting
schema validation
safety report
checksum impact prediction
patch preview
suggested CLI / PR instructions
no apply button
```

Handler admission comes later, one handler family at a time.

Required safety checks:

- safe pack ID
- manifest present
- declared source file present
- checksum matches or predicted checksum is clearly labeled
- OOV policy valid for role
- depth pack fail-closed when gate engaged
- no dangling morphology links
- no invalid alignment targets
- no holonomy case with missing refs
- epistemic-status distribution visible
- known gaps carried forward
- no silent promotion from speculative to coherent

### General pack adapter

The broader `packs` route may remain an inventory view. Any pack mutation or patching path should reuse the CORE-Logos adapter where applicable and the universal proposal envelope always.

### Future modality adapters

Audio, vision, environment, and sensorimotor proposal artifacts must enter through the same envelope. Because these substrates are gated and often afferent-only, initial capability should usually be `inspect_only` or `proposal_only`.

No modality adapter may imply decode, actuation, or motor authority unless the governing ADR admits it.

---

## Workbench UX substrate

The Workbench should render proposal artifacts through shared components rather than per-domain bespoke pages.

### Shared components

```text
ProposalArtifactHeader
ProposalSubjectBadge
CapabilityLevelBadge
ProposalEvidenceRail
ReasoningTraceViewer
ValidationReportPanel
SafetyReportPanel
AffectedArtifactsPanel
ChecksumImpactPanel
HandlerRoutePanel
RatificationCorridor
ProposalTimeline
SuggestedCliPanel
PatchPreviewPanel
```

### Design rules

- Every proposal screen names mutation status.
- Every disabled ratification affordance names the failed precondition.
- Every unknown or missing proof renders as unknown/missing, not as green.
- Draft/preview/predicted/applied must be visibly distinct in text, not color only.
- `StableJsonViewer` remains the raw artifact trust surface.
- No auto-ratify, no batch ratification, no hidden background jobs.
- No direct pack editing UI.
- No route-specific proposal semantics that contradict the shared envelope.

---

## Backend API direction

The future API should converge toward generic proposal endpoints while preserving old endpoints during migration.

Read-only / projection:

```text
GET /proposal-artifacts
GET /proposal-artifacts/{proposal_id}
GET /proposal-artifacts/{proposal_id}/timeline
GET /proposal-artifacts/{proposal_id}/artifacts
```

Subject-specific draft endpoints may exist when they do not mutate substrate artifacts:

```text
POST /logos/packs/{pack_id}/proposals/draft
POST /proposal-artifacts/{proposal_id}/validate
```

Ratification remains subject to admitted handler routes:

```text
POST /proposal-artifacts/{proposal_id}/ratify
```

But this generic route must refuse unless `handler_route` is admitted for the proposal subject and all preconditions pass. The route may initially be omitted entirely until generic routing is proven.

During migration, existing math routes remain valid:

```text
GET /math-proposals
GET /math-proposals/{id}
POST /math-proposals/{id}/ratify
POST /math-proposals/{id}/reject
POST /math-proposals/{id}/defer
```

The adapter layer can translate those into the universal envelope without changing behavior.

---

## Trust boundary matrix

| Subject | Initial capability | May draft in UI? | May apply in UI? | Gate to enable apply |
|---|---:|---:|---:|---|
| Math / admitted handlers | `ratification_enabled` | No new drafting in this slice | Yes, existing narrow path | Existing ADR-0173 + handler tests |
| Math / unsupported change kind | `proposal_only` or `inspect_only` | Later | No | New handler ADR/tests |
| Cognition teaching proposal | `inspect_only` | No | Not yet | Surface C parity tests + implementation |
| CORE-Logos pack proposal | `proposal_only` | Yes, after forge PR | No | New handler family ADR/tests |
| General pack mutation | `proposal_only` | Later | No | Reviewed handler path |
| Vision/audio modality proposal | `inspect_only` first | Later | No | Dedicated modality ADR/tests |
| Runtime policy / identity | `inspect_only` unless separately ratified | No by default | No | Dedicated governance ADR |

---

## Implementation sequence

### S0 — This plan

Create this document. No code. No schema changes. No mutation path.

### S1 — Universal envelope schemas, read-only only

Add Python and TypeScript read-model schemas for `ProposalArtifact`, `ProposalSubject`, `SafetyReport`, `ValidationReport`, `AffectedArtifact`, `ChecksumImpact`, and `HandlerRoute`.

No endpoints apply anything.

Acceptance:

- schema drift tests cover TS/Python mirrors
- no new mutation routes
- existing math/cognition endpoints unchanged

### S2 — Proposal artifact projection endpoint

Add a read-only endpoint that projects existing math and cognition proposals into the universal envelope.

```text
GET /proposal-artifacts
GET /proposal-artifacts/{id}
```

Acceptance:

- math proposal count matches `/math-proposals`
- cognition proposal count matches `/proposals`
- unsupported handlers render `capability_level != ratification_enabled`
- missing artifacts render absence explicitly

### S3 — Shared UI components

Build the shared proposal artifact components and render them behind a feature flag or route-internal experiment.

Acceptance:

- no existing ProposalsRoute behavior removed
- every component has empty/error/loading state where applicable
- no color-only status
- keyboard focus works
- raw JSON still available

### S4 — Math adapter migration

Render math proposals through the universal proposal artifact components while preserving existing ratification behavior.

Acceptance:

- existing math ratify/reject/defer tests still pass
- `RatificationCorridor` remains gated by pending + replay equivalent + admitted handler
- no unsupported handler becomes enabled
- target path/evidence hash after apply is surfaced in timeline or result panel

### S5 — Cognition adapter depth

Populate artifact refs, review history, and proposal timeline for cognition proposals. Do not enable Workbench ratification until Surface C parity is proven.

Acceptance:

- artifact_refs no longer always empty when source artifacts exist
- review_history is visible
- CLI fallback remains available
- Workbench ratify button absent or disabled with clear reason

### S6 — CORE-Logos proposal forge, proposal-only

Add proposal-only drafting for CORE-Logos changes.

Acceptance:

- structured editor produces proposal artifact only
- no language pack file is mutated
- safety report includes pack-specific checks
- checksum impacts are predicted and labeled predicted
- patch preview is visible
- suggested CLI/PR instructions are visible
- no `Ratify` affordance exists

### S7 — CORE-Logos handler families, one at a time

Admit one handler family per ADR/brief/PR sequence.

Suggested order:

1. `gloss_add` / `gloss_update`
2. `lexicon_add` with speculative status only
3. morphology link attach/update
4. alignment edge add/update
5. holonomy case add/update
6. coherent/admissible status promotion only after a stricter review path exists

Each family must prove:

- append-only or deterministic file rewrite discipline
- checksum update correctness
- pack compile/verify pass
- no depth-language OOV collapse
- no silent epistemic promotion
- rollback/replay reconstruction
- audit event emission

---

## Acceptance gates for this substrate

This substrate is ready to implement when reviewers agree the following are true:

1. The universal envelope does not widen durable proposal state without ADR review.
2. The universal envelope does not grant new mutation authority.
3. Math remains behavior-identical after adapter projection.
4. Cognition remains inspect-only until Surface C parity tests exist.
5. CORE-Logos begins proposal-only, not ratification-enabled.
6. Every proposal artifact can name evidence, validation, safety, affected artifacts, and handler status.
7. Missing evidence renders as missing, not as success.
8. Every route using the substrate preserves ADR-0162 empty/error/loading doctrine.
9. Every mutation-capable route names the handler, preconditions, target artifact, audit event, and replay boundary.
10. No UI path can apply a subject whose handler is not admitted.

---

## Explicit no-go list

- No direct pack editor.
- No generic `apply_patch` endpoint.
- No browser write to `language_packs/data/*`.
- No ratification affordance for proposal-only subjects.
- No auto-ratify.
- No batch ratification.
- No hidden background validation that changes files.
- No new durable proposal state names without ADR review.
- No pack checksum rewrite from UI until a handler family admits it.
- No using `ratifier_kind` as permission logic.
- No treating Workbench as remote operator auth.
- No proposal-on-proposal dependency chain.
- No visualization as proof without deterministic underlying artifact.

---

## CORE-Logos implication

CORE-Logos Studio should be the first major consumer after math/cognition are projected into the envelope.

The Studio should not create a separate Logos proposal system. It should create Logos proposal artifacts using this universal envelope:

```text
CORE-Logos proposed change
→ subject = logos_pack
→ change_kind = lexicon_add | morphology_add | alignment_edge_add | holonomy_case_add | ...
→ evidence pointers
→ safety report
→ checksum impact
→ patch preview
→ handler route absent
→ capability_level = proposal_only
```

Only after a specific Logos handler family is admitted may that family become `ratification_enabled`.

This keeps CORE-Logos functional for active engineering and development while preserving the safety boundary that made math ratification lawful.

---

## Open questions

1. Should universal `deferred` be a durable state, or remain a Workbench UI disposition backed by existing state/log semantics?
2. Should proposal draft artifacts live under a new `proposal_artifacts/` tree, or remain subject-owned until ratified?
3. Should `POST /proposal-artifacts/{id}/validate` be read-only by contract, or should validation always be a fresh read endpoint with query parameters?
4. What is the smallest CORE-Logos handler family safe enough to ratify first: gloss updates, lexicon additions as speculative, or holonomy case additions?
5. Should operator rejection/refinement attach to reasoning-trace step IDs universally, not just math Tier 2?

None of these open questions block S1/S2 read-only projection.

---

## Final design sentence

A proposal artifact is CORE's lawful way to say:

> “The engine has seen enough to suggest a change, but not enough to become the change.”

The Workbench's job is to make that distinction impossible to miss.
