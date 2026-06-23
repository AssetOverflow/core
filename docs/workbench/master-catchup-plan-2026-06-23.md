# Workbench/UI Master Catch-up Plan

**Date:** 2026-06-23
**Status:** Master phased plan for Workbench/UI catch-up
**Scope:** Workbench UI/UX, backend read models, proposal surfaces, eval/governance surfaces, demo readiness

## 0. North Star

CORE Workbench is the local proof cockpit for CORE. It must show what happened,
what evidence supports it, what authority allowed or refused it, whether it can
replay, what mutated, and what remains proposal-only.

The Workbench is not:

- a generic chatbot shell;
- a dashboard over invented metrics;
- a mutation console;
- an animation layer pretending to be evidence;
- a shortcut around ADR, handler, replay, or governance boundaries.

The target demo grammar is:

```text
prompt / artifact / eval input
-> deterministic trace
-> construction/proposal evidence
-> contract/refusal authority
-> replay/sealing
-> audit/governance
-> demo narrative
```

Every visible claim must be backed by a backend read model, committed artifact,
or existing allowlisted execution path.

## 1. Current baseline

The route registry in `workbench-ui/src/app/routes.ts` is the source of truth.
Current route count: 16.

| Section | Route | Path | Catch-up posture |
|---|---|---|---|
| Converse | Chat | `/chat` | usable; demo polish only |
| Cognition | Trace | `/trace` | needs Construction / ProblemFrame tab |
| Cognition | Contemplation | `/contemplation` | usable; proposal boundary copy should be checked |
| Determinism | Tour | `/tour` | needs sponsor-grade guided proof scripts |
| Determinism | Replay | `/replay` | usable; should cross-link from demo/trace |
| Determinism | Demos | `/demos` | needs proof-theater orchestration |
| Evidence | Proposals | `/proposals` | needs universal ProposalArtifact visual language |
| Evidence | Runs | `/runs` | usable; identity-continuity demo polish |
| Evidence | Lived Life | `/lived-life` | usable when persisted artifact exists; honesty copy must remain fail-closed |
| Evidence | Vault | `/vault` | usable; read-only exact-CGA recall story |
| Evidence | Audit | `/audit` | needs governance event expansion |
| Discipline | Evals | `/evals` | needs generalization audit and report-pin distinction |
| Discipline | Calibration | `/calibration` | usable; wrong/practice distinction must remain clear |
| Substrate | Packs | `/packs` | usable; cross-link CORE-Logos |
| Substrate | CORE-Logos | `/logos` | read-only viewer built; Studio explicitly deferred |
| Settings | Settings | `/settings` | usable; CLI-only runtime config boundary |

## 2. Architecture pivots Workbench must absorb

### 2.1 Proposal-first construction

The kernel now follows the authority gradient:

```text
surface/process cue
-> ConstructionProposal(status="proposed")
-> exact mention/entity/quantity bindings
-> ContractAssessment
-> diagnostic runnable/refused
```

Workbench must show that proposals are hypotheses and contracts are the runnable
or refused authority. Diagnostic families must be visibly tagged:

```text
diagnostic_only=True
serving_allowed=False
```

### 2.2 Quantity-entity foundational seam

`binding.quantity_entity` and `quantity_entity_binding_candidate.v1` are now
foundational to later rate, partition, comparison, and state-change work. The UI
must render quantity-to-entity grounding as exact local evidence, not generic NLP
entity extraction and not serving truth.

### 2.3 Residual-gated practice spine

The emerging evidence chain is:

```text
ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateOperatorResult
-> CandidateAttemptRunBinding
-> ReplayAdapterResult | ReplayAdapterRefusal
-> SealedPracticeTrace
```

This is diagnostic, inert evidence. It is not answer production, not serving
authority, not pack/policy/identity mutation, and not proof by itself.

### 2.4 Generalization audit governance

Generalization benchmarks are audit/test-only instruments. No raw sealed items
may be exposed in UI artifacts, diffs, source files, or logs. Benchmark failures
are diagnosis signals, not direct patch targets.

The UI must distinguish:

- committed report pins;
- ephemeral local outputs;
- governed rebaseline candidates;
- unratified artifacts.

### 2.5 Universal ProposalArtifact substrate

Proposal cannot remain math-specific or page-specific. Workbench should converge
on one proposal visual grammar:

```text
ProposalArtifact
  subject
  state
  capability_level
  source
  proposed_change
  reasoning_trace
  evidence_pointers
  validation
  replay_evidence
  safety_report
  affected_artifacts
  handler_route
  suggested_cli
  audit_refs
  ui_disclosure
```

Capability levels:

| Level | Meaning | UI may do |
|---|---|---|
| `inspect_only` | artifact can be inspected only | read/copy/navigate |
| `proposal_only` | draft or preview may exist | validate/export/copy, no apply |
| `ratification_enabled` | admitted handler exists | ratify/reject/defer through handler only |

No `Ratify` affordance may render unless `capability_level ==
ratification_enabled` and an admitted handler route exists.

## 3. Phased execution plan

### Phase 0 — Truth baseline and docs reconciliation

Deliverables:

- refresh `workbench-ui/README.md` route inventory;
- update `docs/workbench/UI-UX-GUIDE.md` with post-Wave-M pivots;
- add this master plan;
- add implementation briefs for the first code-bearing phases.

Acceptance:

```bash
cd workbench-ui
pnpm test
pnpm build
```

### Phase 1 — Trace Construction read model

Add read-only backend endpoint:

```text
GET /trace/<turn_id>/construction
```

Target schemas:

```text
ConstructionEvidence
ConstructionProposalView
SourceSpanView
RoleObligationView
MentionView
MentionBindingView
BoundRelationView
ContractAssessmentView
ConstructionFamilyView
```

Rules:

- read-only;
- no candidate generation;
- no replay execution;
- no mutation;
- no serving authority;
- exact spans only;
- missing evidence returns `missing_evidence`.

### Phase 2 — Trace Construction tab

Add Trace tab:

```text
Pipeline | Construction | Field | Bundle | Surfaces | Grounding | Verdicts | Metadata | Raw
```

Components:

```text
ConstructionTab
SourceTextWithSpans
ConstructionProposalCard
RoleObligationTable
MentionBindingTable
ContractAssessmentPanel
ConstructionAuthorityBanner
```

Required copy/badges:

```text
Proposal != Runnable
Contract Determines
Diagnostic Only
Serving Disallowed
Exact Span Required
```

### Phase 3 — Residual-gated practice visibility

Expose read-only practice/candidate/sealed-trace projections. Prefer adding the
surface under Trace/Evals/Audit before creating a new route.

Cards:

```text
Residual Card
Search Gate Card
Compute Budget Card
Candidate Operator Card
Run Binding Card
Replay Adapter Card
Sealed Practice Trace Card
```

Every card must say whether mutation happened. In the current spine, the answer
should be no.

### Phase 4 — Universal ProposalArtifact UI frame

Build shared proposal review components and adapt existing math/cognition
proposals into them before adding new proposal domains.

Components:

```text
ProposalArtifactFrame
ProposalCapabilityBadge
ProposalSubjectHeader
ProposalEvidencePointerList
ProposalReasoningTraceViewer
ProposalValidationReport
ProposalSafetyReport
ProposalHandlerDisclosure
ProposalAuditRefs
```

### Phase 5 — Generalization audit governance in Evals

Add read-only endpoints:

```text
GET /generalization/manifests
GET /generalization/cache
GET /generalization/reports
GET /generalization/reports/<dataset>/<split>
```

Add `/evals` internal tabs:

```text
Lanes
Generalization Audits
Report Pins
```

Required banner:

```text
Audit-only. No raw sealed items are exposed here. Benchmark failures are diagnosis signals, not direct mutation targets.
```

### Phase 6 — Audit governance expansion

Expand audit sources for:

```text
generalization_manifest
generalization_report
report_rebaseline
startup_guard
construction_evidence
candidate_operator
practice_trace
sealed_practice_trace
proposal_artifact
logos_pack_safety
```

Cards must answer:

```text
What happened?
Was mutation possible?
Was mutation performed?
What digest proves it?
What route inspects it?
What command reproduces it?
```

### Phase 7 — Demo Theater proof tour

Upgrade `/tour` and `/demos` into guided proof narratives over the real routes.

Flagship demo paths:

1. Deterministic turn evidence: Chat -> Trace -> Field -> Bundle -> Replay.
2. Proposal-first construction: Trace -> Construction -> Contract blockers.
3. Residual-gated practice: Evals/Trace -> Candidate -> Replay -> Sealed trace -> Audit.
4. Generalization audit governance: Evals -> Generalization -> Report Pins -> Audit.

Every demo step must include:

```text
Claim
What this proves
What this does not prove
Evidence route
Artifact/digest
Reproducer
Failure mode
```

### Phase 8 — CORE-Logos read-only excellence

Polish the existing `/logos` viewer without adding Studio semantics.

Allowed:

- overview cards;
- safety verdict explanation;
- alignment graph/table polish;
- known gaps card;
- holonomy case viewer;
- manifest digest prominence;
- Packs <-> CORE-Logos cross-links.

Forbidden until later ADR/ProposalArtifact substrate:

- pack editing;
- patch forge;
- holonomy handler UI;
- draft mutation UI;
- Studio route.

### Phase 9 — Visual and capture hardening

Run a demo-readiness pass over density, layout, keyboard flow, empty/error/loading
contracts, copy buttons, truncation, and partner screenshots.

Capture targets:

```text
/chat
/trace/<turn_id>
/trace/<turn_id> Construction tab
/replay/<turn_id>
/proposals
/evals Generalization Audits
/audit Governance filters
/logos
/tour
/demos
```

## 4. Master PR ladder

| PR | Title | Scope |
|---:|---|---|
| 1 | `docs(workbench): reconcile catch-up baseline` | README/UI guide/master plan |
| 2 | `feat(workbench): expose construction evidence read model` | schemas + `/trace/:id/construction` |
| 3 | `feat(workbench-ui): add Trace construction tab` | frontend tab/components/tests |
| 4 | `feat(workbench): expose practice evidence read models` | candidate/practice/sealed trace readers |
| 5 | `feat(workbench-ui): render residual practice evidence` | Trace/Evals/Audit cards |
| 6 | `feat(workbench-ui): add proposal artifact frame` | shared proposal visual substrate |
| 7 | `feat(workbench): expose generalization audit summaries` | manifest/cache/report readers |
| 8 | `feat(workbench-ui): add generalization audit view` | Evals tabs/cards/tests |
| 9 | `feat(workbench): expand audit governance sources` | audit source/schema readers |
| 10 | `feat(workbench-ui): upgrade audit governance surface` | filters/cards/cross-links |
| 11 | `feat(workbench-ui): upgrade demo theater proof tour` | demo scripts/evidence links |
| 12 | `polish(workbench-ui): demo readiness hardening` | visual/copy/accessibility/capture |
| 13 | `docs(demos): add partner demo package` | scripts/reproducers/screenshots |

## 5. Critical success criteria

Workbench is caught up when:

1. every major backend capability has a truthful read surface;
2. Trace shows construction/proposal-first evidence;
3. Evals show generalization audit governance without raw data leakage;
4. Audit shows mutation and governance boundaries clearly;
5. Proposal review uses one visual language across domains;
6. Demo Theater can tell the whole CORE story without manual explanation;
7. CORE-Logos is beautiful but still read-only;
8. no UI route implies authority the backend has not admitted;
9. every claim has evidence or explicitly says it does not;
10. a sponsor can understand why CORE is not another chatbot wrapper.

## 6. Operating rule

```text
Make the truth visible.
Do not beautify absence into evidence.
Do not promote hypothesis into authority.
Do not let UI convenience outrun governance.
```
