# Workbench UI Continuation — CORE-Doctrine Addendum

> **Status:** binding addendum to `docs/plans/workbench-ui-continuation.md`
> **Applies to:** all Phase 5+ work; back-applies to Phases 1–4 where noted
> **Authority:** CLAUDE.md (§Security, §Teaching Safety, §Runtime Surface Contract, §PR Checklist, §Schema-Defined Proof Obligations), `docs/runtime_contracts.md`, ADR-0051

The parent plan is sound as frontend hygiene. This addendum supplies the
trust-boundary, determinism, and proof-obligation language CORE requires before
any route that touches packs, vault, audit, settings, or trace can ship.

---

## 1. Per-route trust classification

Every route must declare one classification before its first implementation PR.
The classification gates what the UI is allowed to do.

| Route       | Classification   | Allowed UI operations                                                       | Forbidden                                                                                  |
|-------------|------------------|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Chat        | read + turn-submit | Submit turn; render `surface`; expose `walk_surface` / `articulation_surface` distinctly | Mutating identity axes, runtime policy, or operator code from user text                    |
| Proposals   | proposal-only    | View queue/detail; accept/reject through existing proposal API              | Bypassing review; direct pack/vault mutation                                                |
| Replay      | read-only        | Compare artifacts; render divergence                                        | Writing artifacts; rewriting trace_hash; "fix" buttons                                      |
| Evals       | read-only        | Browse lanes/runs/metrics                                                   | Mutating lane definitions; suppressing failing cases from view                              |
| Runs        | read-only        | List/filter artifacts; deep-link to Replay                                  | Deletion; metadata edits                                                                    |
| Trace       | read-only        | Render three surfaces distinctly; node-by-node walk                         | Surface conflation; any write path                                                          |
| Inspector   | read-only        | Display selected entity by type                                             | Inline edits; cross-route mutation                                                          |
| Vault       | read-only        | Hierarchical browse; grounding-source coloring                              | Entry creation/edit/delete; recall-semantic changes                                         |
| Packs       | proposal-only    | List; inspect contents; **propose** re-ingestion via existing CLI/proposal path | Direct re-ingestion buttons; pack_id strings reaching the filesystem without `_validate_pack_id` |
| Audit       | read-only        | Browse `TurnVerdicts`; filter by clearance state; paginate                  | Aggregating/suppressing per-turn verdicts; "mark resolved"                                  |
| Settings    | mutating (allowlisted) | Read/write only fields on the allowlist below                          | Any setting that affects closure thresholds, normalization sites, recall semantics, or identity packs |

### Settings allowlist (initial)

The Settings route may read **and** write only these fields. Anything outside
this list is read-only or absent from the UI entirely.

- API endpoint override (UI ↔ backend wiring only)
- Operator display preferences (theme, density, default route)
- Telemetry sink toggles already exposed by `chat/telemetry.py`
- Eval lane selection / default suite

Out of scope for the UI (operator CLI only):

- `versor_condition` threshold (1e-6, non-negotiable)
- Algebra backend selection
- Identity pack selection / `DEFAULT_IDENTITY_PACK`
- Safety/ethics pack mounting
- Vault recall thresholds and indexing parameters
- Any normalization site (`ingest/gate.py`, `language_packs/compiler.py`, `algebra/versor.py`)

Adding a field to the allowlist requires an ADR.

---

## 2. Runtime Surface Contract obligations (Phase 3 — Trace route)

The Trace route is the surface where doctrine violations are easiest to commit
silently. Three obligations:

1. **Distinct rendering.** `surface`, `walk_surface`, and `articulation_surface`
   are visually and semantically distinct in the UI. They are not collapsed into
   a single "response" pane.
2. **Read-only.** No node, no edge, no turn is editable in v1. Drill-down to
   evidence is fine; mutation is not.
3. **Trace-hash stability.** Rendering must not depend on or alter values that
   feed `trace_hash`. The Trace route PR must include a contract test asserting
   `trace_hash` is byte-identical before and after the route fetches and renders
   a session.

Reference: `docs/runtime_contracts.md`. Any change to the surface contract lands
the doc update and contract test in the same PR (per CLAUDE.md §Runtime Surface
Contract).

---

## 3. Audit fidelity guarantee (Phase 6 — Audit route)

The Audit route is the operator's window into `SafetyCheck` / `EthicsCheck`
verdicts. It is load-bearing for catching regressions in fail-closed safety
behavior. Therefore:

- Per-turn verdict cardinality is preserved. Pagination is allowed; aggregation
  that hides individual verdicts is not.
- Clearance state coloring uses the existing tokens (`cleared`, `violated`,
  `unassessable`, `suppressed`) without remapping or merging.
- No UI affordance "resolves," "suppresses," or "dismisses" a verdict. Operator
  response to verdicts happens in the engine, not the workbench.
- Search/filter is permitted; saved views are permitted; mutation is not.

Reference: `audit-completeness`, `TurnVerdicts`, CLAUDE.md §Teaching Safety.

---

## 4. Pack route discipline (Phase 6 — Packs)

`language_packs/compiler.py` is one of three allowed normalization sites and is
guarded by `_validate_pack_id` (ADR-0051) against path traversal.

- Pack re-ingestion is **proposal-only** in the UI. The UI may surface a
  "propose re-ingestion" affordance; it may not invoke the compiler directly.
- Any `pack_id` displayed in the UI is treated as untrusted display data:
  centralized safe-display path, no filesystem operations driven by UI input.
- Pack mutation proposals follow the existing reviewed-teaching pipeline.
  No parallel correction/learning path (CLAUDE.md §Teaching Safety).

---

## 5. Backend contract documentation

"Confirm with backend" (parent plan, Phase 5) is replaced by:

- Every new endpoint consumed by a workbench route is documented in
  `docs/runtime_contracts.md` (or a named sibling under `docs/contracts/`) in
  the same PR that introduces the TypeScript mirror in `src/types/api.ts`.
- The Python handler and the TS mirror cite the same contract section.
- Contract drift between Python and TS is a CI failure, not a code-review
  catch — add a parity test if one does not exist.

---

## 6. CLI-lane requirement

Any PR that adds or modifies a backend endpoint to support a workbench route
must include the CLI lane that exercises it:

- Runtime-touching: `core test --suite runtime`
- Cognition-touching: `core eval cognition`
- Pack-touching: `core test --suite packs`
- Teaching-touching: `core test --suite teaching`

UI-only PRs (no backend change) are exempt — `pnpm test` is sufficient.

---

## 7. Per-PR checklist (replaces the parent plan's "Validation checklist" for Phase 5+)

```text
[ ] Route trust classification matches §1 of this addendum
[ ] If Settings: every writable field is on the §1 allowlist (or an ADR adds it)
[ ] If Trace: trace_hash stability test included; three surfaces rendered distinctly
[ ] If Audit: no aggregation/suppression of per-turn verdicts
[ ] If Packs: re-ingestion is proposal-only; pack_id flows through safe display
[ ] New backend endpoints documented in docs/runtime_contracts.md (or sibling)
[ ] TS mirror in src/types/api.ts cites the same contract section
[ ] Relevant CLI lane added or extended (§6); pnpm test green
[ ] PR description answers the four CLAUDE.md §PR Checklist questions:
      - What capability/property/boundary did this add/protect?
      - Which invariant proves the field remains valid?
      - Which CLI suite/eval proves the lane?
      - What trust boundary was enforced?
```

---

## 8. Proof-obligation discipline (CLAUDE.md §Schema-Defined Proof Obligations)

Schemas and types added to `src/types/api.ts` that nominally guarantee a
structural property (e.g. a discriminated union for verdict states, a typed
proposal lifecycle) carry the same obligation as backend schemas: an executing
test must fail under the violations the type is written to catch.

If no such test exists, the type is decoration. Record the gap in the PR
description rather than treating the type as load-bearing.

---

## 9. Phase applicability

| Phase                                | Addendum sections that apply        |
|--------------------------------------|-------------------------------------|
| 1 — Polish existing routes           | §2 (Chat surface distinction), §7   |
| 2 — Runs                             | §1 (read-only), §7                  |
| 3 — Trace                            | §1, §2, §7                          |
| 4 — Inspector                        | §1 (read-only), §7                  |
| 5 — Contracts for placeholders       | §1, §5, §7                          |
| 6 — Packs / Vault / Audit / Settings | §1, §3, §4, §5, §6, §7, §8          |
| 7 — Command palette                  | §1 (no command bypasses §1 rules)   |

---

## 10. Delete-when-done

This addendum is deleted together with the parent plan, after all phases merge
and its rules have been folded into:

- `docs/runtime_contracts.md` (surface contract additions)
- ADRs for any Settings-allowlist extensions
- Workbench-specific contributing notes if needed

Until then, both files travel together.
