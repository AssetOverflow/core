# CORE Workbench UI/UX Guide

Date: 2026-06-14
Status: Wave M B3.5 guide (post-Wave-M reconciliation: Lived Life, CORE-Logos
reader, trace Field reader, and the truncated-cell reveal)

## 1. What Workbench Is And Is Not

CORE Workbench is a local operator/auditor surface for deterministic CORE
evidence. It is a cognition observatory, replay debugger, proposal review
station, eval console, calibration reader, and audit surface.

It is not a generic chatbot shell, not a dashboard over invented metrics, not a
mutation console, and not a visualization proof. Every visible claim should
trace to a backend read model, committed artifact, or existing allowlisted
execution path.

## 2. How To Run It

Backend:

```bash
core workbench api
```

Frontend:

```bash
cd workbench-ui
pnpm dev
```

Default API health check:

```bash
curl http://127.0.0.1:8765/health
```

## 3. Evidence Model

The workbench has one evidence grammar. A selected item publishes an
`EvidenceSubject`; the RightInspector and Evidence Chain Rail render only fields
that subject actually carries.

Evidence subject kinds:

- `turn`
- `proposal`
- `eval_result`
- `artifact`
- `run`
- `pack`
- `vault_entry`
- `audit_event`
- `calibration_class`

Missing detail is rendered as "detail not loaded" or "not recorded", never as a
successful proof.

## 4. Current Route Map

The route registry in `workbench-ui/src/app/routes.ts` is the source of truth.
Current route count: 17.

| Section | Route | Path | Shortcut | Purpose |
|---|---|---|---|---|
| Converse | Chat | `/chat` | `⌘1` | Execute a normal CORE turn and journal evidence. |
| Cognition | Trace | `/trace` | `⌘2` | Inspect turn surfaces, grounding, verdicts, and trace hashes. |
| Cognition | Contemplation | `/contemplation` | Palette | Inspect persisted contemplation process traces. |
| Determinism | Tour | `/tour` | Palette | Guided determinism tour: a curated narrative over the real demos with "what this proves / does not prove" honesty cards. |
| Determinism | Replay | `/replay` | `⌘3` | Re-execute journaled turns in a sealed fresh runtime and compare envelopes. |
| Determinism | Demos | `/demos` | Palette | Run registered determinism demos. |
| Evidence | Proposals | `/proposals` | `⌘4` | Review cognition and math proposal evidence. |
| Evidence | Runs | `/runs` | `⌘6` | Browse recorded run/session evidence. |
| Evidence | Lived Life | `/lived-life` | Palette | Watch the always-on heartbeat hold one continuous life (closure read-not-repaired over uptime + learned-while-idle). |
| Evidence | Vault | `/vault` | `⌘8` | Inspect persisted vault entries when persistence exists — entry-inspector depth, status/facet/text filters, evidence rail, and opt-in exact-CGA recall evidence. Read-only (no runtime controls). |
| Evidence | Audit | `/audit` | `⌘9` | Read deterministic audit events. |
| Discipline | Evals | `/evals` | `⌘5` | Run/read allowlisted eval lanes and wrong=0 ledgers. |
| Discipline | Calibration | `/calibration` | Palette | Inspect practice-class reliability and license verdicts. |
| Substrate | Packs | `/packs` | `⌘7` | Browse language/runtime pack metadata. |
| Substrate | CORE-Logos | `/logos` | Palette | Inspect CORE-Logos pack identity and safety. |
| Substrate | Apple UMA | `/apple-uma` | Palette | Inspect the Apple Silicon mechanical-sympathy benchmark report. |
| Settings | Settings | `/settings` | `⌘0` | Manage local UI preferences; engine config remains CLI-only. |

Pinned route shortcuts cover Chat through Settings. All routes are searchable in
the command palette.

## 5. What Each Route Proves

| Route | Proves |
|---|---|
| Chat | The local runtime can produce a typed turn envelope and journal it. |
| Trace | The journal carries user, articulation, walk, grounding, verdict, and hash evidence. |
| Contemplation | Persisted contemplation process reports expose cold attempt, checkpoint enrichment, proposal boundary, and grounded-after scenes. |
| Replay | A selected journaled prompt can be replayed through the sealed replay comparator; equivalence is leaf-based. |
| Demos | Registered demo scenarios pass or fail with recorded scenario evidence and proof/entailment DAGs where the demo emits them. |
| Proposals | Proposal evidence, replay facts, and ratification commands are inspectable without applying mutation. |
| Runs | Recorded run/session references, checkpoint gaps, and identity-continuity verdicts are discoverable. |
| Lived Life | A persisted always-on run (produced by the `core always-on` daemon) shows the engine living + learning over uptime, with closure (`versor_condition < 1e-6`) read as evidence each beat (never repaired); the surface's `closure_held` is consistency-checked against the per-beat measurements, so it can never paint a breached field as valid, and its resume verdict shows whether a reboot resumes this life. |
| Vault | Persisted vault metadata is inspectable when persistence is configured. |
| Audit | Audit events are readable with payload digests and mutation-boundary flags. |
| Evals | Allowlisted eval lanes and wrong/correct/refused metrics are visible. |
| Calibration | Practice classes show engine-owned Wilson floor and PROPOSE/SERVE license verdicts. |
| Packs | Pack manifests, checksums, and determinism metadata are visible. |
| Apple UMA | Committed mechanical-sympathy benchmark reports, track execution/parity status, and copy boundaries are visible. |
| Settings | UI preferences are local-only; density mode is consumed by shell/design tokens; runtime status is read-only. |

## 6. What Each Route Does Not Prove

| Route | Does not prove |
|---|---|
| Chat | Does not prove replay equivalence until Replay verifies a journaled turn. |
| Trace | Does not prove correctness; it exposes recorded state. |
| Contemplation | Does not ratify findings or prove open-ended learning; it reads committed reports only. |
| Replay | Does not distinguish nondeterminism from unrecorded origin-state influence. |
| Demos | Does not generalize beyond registered scenarios. |
| Proposals | Does not ratify unless an admitted handler path is explicitly invoked. |
| Runs | Does not reconstruct missing checkpoints or synthesize identity continuity when manifest evidence is absent. |
| Vault | Does not expose live in-process memory. |
| Audit | Does not create a new event store. |
| Evals | Does not run unsafe or sealed holdout lanes from the UI. |
| Calibration | Does not mutate a license and does not claim serving wrong=0 from practice data. |
| Packs | Does not apply pack mutation. |
| Apple UMA | Does not execute benchmarks, mutate reports, or authorize serving. |
| Settings | Does not edit engine configuration. |

## 7. Evidence Subjects And Address Grammar

Canonical addresses:

- `turn` -> `/trace/<turnId>`
- `proposal` -> `/proposals/<proposalId>`
- `eval_result` -> `/evals/<laneId>`
- `artifact` -> `/replay/<artifactId>`
- `run` -> `/runs/<sessionId>`
- `pack` -> `/packs/<packId>`
- `vault_entry` -> `/vault?inspect=vault:<entryIndex>`
- `audit_event` -> `/audit?inspect=audit:<eventId>`
- `calibration_class` -> `/calibration?inspect=calibration:<className>`

`?inspect=` means the RightInspector is open on that subject. Malformed inspect
values are dropped rather than interpreted.

## 8. Command Palette And Keyboard Model

`⌘K` opens the command palette. Route commands derive from the route registry;
Demos and Calibration are palette-visible even though they do not have digit
shortcuts.

Keyboard help is live-registry driven. It shows only shortcuts currently bound
by mounted components. It must not advertise unreachable commands.

## 9. Empty/Error/Loading Doctrine

Every route with remote evidence must provide:

- a specific loading label,
- an empty state that names what is absent and gives a next action,
- an error state with failure, mutation status, reproducer, and retry safety.

No route should use vague "thinking" text or imply mutation happened when it did
not.

## 10. Proposal Vs Ratification Boundary

Proposal views are read-only unless a narrow admitted handler explicitly exists.
Suggested CLI commands are copyable operator affordances, not UI execution.
Pack mutation and general corpus mutation remain proposal-only until reviewed.

## 11. Calibration / Wrong=0 Discipline

Calibration reads committed practice artifacts and applies engine-owned
`core.reliability_gate` functions. It shows how a class earns PROPOSE or SERVE
license. Practice can contain wrong attempts; those wrong attempts are the
learning signal.

The global wrong=0 frame reads serving metrics from committed serving reports.
It mirrors counts honestly; if a report says wrong is non-zero, the UI must show
non-zero wrong.

## 12. CORE-Logos / Packs Current And Next State

Today, Packs exposes manifest/checksum/determinism metadata. It is the current
Substrate neighborhood for language/runtime pack inspection.

A read-only **CORE-Logos** route (`/logos`) is now built: Overview, Identity,
Lexicon, Glosses, Morphology, Alignment, and Safety tabs over CORE-Logos pack
evidence. The fuller CORE-Logos *Studio* — proposal-only draft artifacts and a
patch-forge / holonomy handler family — is not built; it must enter as
proposal-only drafts before any ratification-enabled handler family is admitted.

## 13. Known Absences And Follow-Up Items

- Full B4 leeway annotations are not admitted; B4a nullable
  `LeewayEvidence` read models exist first.
- The CORE-Logos *Studio* (proposal-only draft + patch-forge / holonomy
  handlers) is not built; only the read-only `/logos` reader exists.
- Universal proposal artifact envelope is designed, not implemented as a UI
  substrate.
- Phase E (robustness; continuous) is ongoing.

Reconciled (previously listed as absent, now shipped):

- Cognitive pipeline visualizer — the Trace **Pipeline** tab renders the stage
  rail, propagation edges, and per-stage detail.
- Field substrate / `versor_condition` reader — the Trace **Field** tab and the
  **Lived Life** surface read per-beat closure as evidence (never repaired).
- Identity continuity — the **Lived Life** route plus Runs identity-continuity
  verdicts.

## 14. Table / Rail Cell Full-Content Reveal

Every cell that truncates a dense value (ids, digests, sources, paths, prompts,
stage names) uses the shared `TruncatedCell` component. It keeps the compact
display but attaches one hover/focus-revealed trigger that opens an accessible
popover with the full value (selectable) plus one-click copy; long/multiline
values also offer "Open full view" into a modal. The trigger calls
`stopPropagation`, so revealing a value never selects the surrounding row.

Applies across the proposal queue, eval wrong=0 case ledger, CORE-Logos
contents, proposal artifacts, trace propagation edges, and the single-column
selection rails. Digests keep `DigestBadge` (already copy + full-value `title`).
A row that is an `<a>`/`<Link>` (e.g. Runs `TurnRefRow`) keeps its anchor
semantics and is reached by navigation rather than nesting an interactive
trigger. See `../handoff/workbench-truncated-cell-visual-evidence-2026-06-14.md`
for captured evidence.
