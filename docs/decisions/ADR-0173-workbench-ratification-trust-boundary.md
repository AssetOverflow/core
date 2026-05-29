# ADR-0173 — Workbench Ratification Trust Boundary

**Status:** Accepted (W0 of the workbench-UI wave; doctrine only — UI
implementation gated to the W1..W4 acceptance gates below)
**Date:** 2026-05-27 (proposed); 2026-05-29 (accepted)
**Author:** Shay
**Parent:** [ADR-0160](./ADR-0160-core-workbench-v1.md), [ADR-0161](./ADR-0161-hitl-async-queue.md), [ADR-0162](./ADR-0162-workbench-design-system.md)
**Related:** ADR-0146 (checkpoints), ADR-0150 (engine_state durability), ADR-0152 (replay), ADR-0167 (audit-as-evidence), ADR-0168 / 0168.1 (FrameClaim), ADR-0169 / 0169.1 (CompositionClaim), ADR-0172 (math contemplation corridor), `docs/handoff/WORKBENCH-UI-WAVE-SCOPING.md`

---

## Context

The workbench UI wave (`WORKBENCH-UI-WAVE-SCOPING.md`) requires a
trust-boundary update before any frontend code lands. The relevant
prior doctrine:

- **ADR-0160 §"Trust boundary"** declared workbench v1 **read-only by
  default**. Forbidden in v1: "accepting proposals", "rejecting
  proposals as durable state", "mutating teaching corpus", "mutating
  packs", "writing engine_state except through normal runtime
  checkpoint path".
- **ADR-0161 §5** pinned three ratification surfaces and explicitly
  stated CI workflows **cannot ratify**:
  - Surface A — GitHub PR (mobile-primary, inspect-only)
  - Surface B — `workflow_dispatch` (mobile-primary, transition-capable)
  - Surface C — local CLI (`core teaching review …`, audit-grade)

Both ADRs pre-date the Tier 1.5 math ratification handlers that now
exist on `origin/main`:

- `teaching/math_lexical_ratification.py::apply_lexical_claim` (W2-D of ADR-0167)
- `teaching/math_frame_ratification.py::apply_frame_claim` (PR #389 / ADR-0168)
- `teaching/math_composition_ratification.py::apply_composition_claim` (PR-β of ADR-0169, in flight)

Each handler is:

- replay-gated
- hazard-pinned (case 0050 mandatory pin)
- partition-tested (math/cognition isolation)
- idempotent (`AlreadyRatified` on duplicate)
- append-only on a reviewed JSONL artifact under
  `language_packs/data/en_core_math_v1/{lexicon,frames,compositions}/*.jsonl`
- accessible only via local Python entrypoints

The original ADR-0160 prohibition was a safety stance against
mutation paths that did not yet have proper gates. Those gates now
exist. The question is therefore not whether ratification can land
through the workbench — it is **how** without inventing a new trust
boundary.

The current operator-burden cost (named in the scoping brief's five
pain points) is the gating constraint on the teaching corridor's
compounding loop. Every audit refusal we cannot ratify quickly is a
learning event the engine never gets.

---

## Prior ADR compatibility audit

This ADR is not final until it remains compatible with prior ADR
doctrine. The following audit was performed before opening
implementation work.

| Prior ADR | Load-bearing rule | ADR-0173 compatibility result |
|---|---|---|
| ADR-0146 | engine_state durability via checkpoint path | Compatible. ADR-0173 explicitly forbids workbench writes to `engine_state/*` outside the existing checkpoint path. |
| ADR-0150 | engine_state schema discipline | Compatible. No new engine_state shapes from this ADR. |
| ADR-0152 | replay invariants | Compatible. Workbench-driven ratifications produce byte-identical replay outcomes to CLI-driven ratifications. |
| ADR-0160 | Workbench v1 read-only by default | **Amended**, narrowly. The "read-only" stance is preserved for corpus/packs/engine_state; mutation is admitted only through the existing reviewed handlers, with the workbench acting as a local keyboard accelerator (see Decision). |
| ADR-0161 | Three ratification surfaces (A/B/C); CI workflows cannot ratify | **Compatible without amendment** to the surface set. The workbench is *not* a fourth surface — it is a local keyboard accelerator for Surface C. Every UI ratification action invokes the same Python entrypoint as the CLI. The ratification record gains a new `ratifier_kind: "workbench"` discriminant for audit-forensic clarity, but `proposal_id` and `to` remain the only load-bearing fields for replay. |
| ADR-0162 | Workbench design system; v1 must-ship; no-go list | Compatible. ADR-0173 pins the keyboard contract referenced in ADR-0162 §7 and resolves the `RatificationCommandPanel` semantics that ADR-0162 §9 named as must-ship without pinning. |
| ADR-0167 | Audit rows become teaching evidence; LexicalClaim-first; partition guarantees | Compatible. ADR-0173 does not alter evidence-floor semantics, partition tests, or sub-type discipline. |
| ADR-0168 / 0168.1 | FrameClaim doctrine + math-domain proposal adapter | Compatible. ADR-0173 admits driving `apply_frame_claim()` from the UI; preconditions, hazards, and partition tests are unchanged. |
| ADR-0169 / 0169.1 | CompositionClaim doctrine + math-domain proposal adapter | Compatible. ADR-0173 admits driving `apply_composition_claim()` from the UI subject to the same scope as ADR-0169 (SAFE_COMPOSITION_CATEGORIES allowlist; case 0050 pin). |
| ADR-0172 | Math contemplation corridor (Tier 1.5) | Compatible. The workbench-driven ratification corridor is the operator-facing throughput pair to ADR-0172's mechanism. |

### Resolved tension: ADR-0161 surface set

ADR-0161 §5 says "CI workflows cannot ratify". This ADR honors that:

- The workbench backend (`workbench/api.py`) runs **locally only** —
  bound to `127.0.0.1` per ADR-0160. It is not a CI workflow and
  cannot be reached remotely.
- The workbench is **not** a fourth ratification surface in ADR-0161's
  taxonomy. It is a keyboard accelerator over Surface C (local CLI).
- The ratification record gains a `ratifier_kind: "workbench"`
  discriminant **for audit forensic clarity only** — not because the
  workbench has different trust authority than Surface C. Replay
  remains driven by `proposal_id` and `to` alone (ADR-0161 §5
  "Replay invariants").

What is forbidden:

- exposing the workbench backend on a non-loopback interface
- introducing a CI workflow that drives `apply_*_claim()` via the
  workbench API
- adding a "remote operator" authentication path
- treating `ratifier_kind: "workbench"` as a permission discriminant
  rather than an audit field

This section is the compatibility trip-wire for any implementation PR.

---

## Decision

> The workbench is a **local keyboard accelerator for the existing
> local ratification handlers**. It is not a new trust boundary, not
> a fourth ratification surface, and not a new mutation path.
>
> Every workbench-driven ratification action invokes the same Python
> entrypoint — `apply_lexical_claim()`, `apply_frame_claim()`,
> `apply_composition_claim()`, `core teaching review …` — with the
> same evidence, the same preconditions, the same exceptions, and the
> same append-only JSONL effect as a direct CLI invocation.

This ADR therefore:

1. amends ADR-0160's v1 read-only stance narrowly to admit the three
   existing handlers as UI-driven ratification targets;
2. honors ADR-0161's surface set unchanged (A/B/C — workbench is C);
3. extends the ratification record with a `ratifier_kind: "workbench"`
   discriminant for audit forensics;
4. pins the keyboard contract referenced by ADR-0162 §7;
5. resolves the five open questions named in
   `WORKBENCH-UI-WAVE-SCOPING.md`.

The ADR does **not** approve any new mutation paths, any new corpora,
any new pack types, any remote operator authentication, or any
handler the implementation PRs have not already proven on the server
side.

---

## Five resolved open questions

The scoping brief deferred these to W0. Each is pinned below.

### Q1 — In-process ratification vs out-of-process dispatch

**Decision: in-process.**

The workbench API (`workbench/api.py`) imports and calls the existing
`apply_*_claim()` Python entrypoints directly. The UI sends a
`POST /math-proposals/{id}/ratify` (existing route) and the API
invokes the corresponding handler in the same process.

Rationale:

- Out-of-process dispatch (subprocess of `core teaching review`)
  would add operator latency for no audit gain — both paths execute
  the same code.
- In-process keeps the exception surface usable: the handler raises
  `AlreadyRatified`, `WrongClaimSubType`, `WrongCompositionCategory`,
  etc., and the API translates them into structured JSON errors the
  UI renders verbatim.
- Replay invariants are unaffected — both paths produce identical
  `proposals.jsonl` / JSONL-artifact appends.

What this does **not** admit:

- Hidden background ratification (no auto-ratify, no "approve all
  replay-passed").
- Dispatching anything beyond the three existing handlers. A new
  handler requires its own scoping ADR (the ADR-0168 / 0169 pattern).

### Q2 — Single-operator vs multi-operator concurrency

**Decision: single-operator.**

v1 of the workbench UI assumes one operator at a time. There is no
proposal locking, no review-state contention, no operator presence
indicator, no real-time collaboration.

Rationale:

- The existing handlers are idempotent (`AlreadyRatified` on
  duplicate) — multi-operator is *safe*, just not *ergonomic*.
- A second operator browsing the same queue would see stale state
  until the next backend poll; this is acceptable for v1 because the
  primary deployment is one operator on one laptop.
- Multi-operator features (proposal claim, presence cursors, conflict
  banners) are explicitly deferred to a follow-up ADR if the need is
  ever proven.

### Q3 — Telemetry path for operator-action events

**Decision: same JSONL sink as `chat/telemetry.py`, new event kinds.**

The workbench backend emits operator-action events to the existing
telemetry sink (the one configured by `chat/telemetry.py`) using new
discriminant kinds:

```json
{"event": "operator_ratify",   "proposal_id": "...", "handler": "...", "outcome": "applied|rejected_precondition", ...}
{"event": "operator_reject",   "proposal_id": "...", "handler": "...", "note": "...", ...}
{"event": "operator_defer",    "proposal_id": "...", ...}
{"event": "operator_navigate", "proposal_id_from": "...", "proposal_id_to": "...", "kind": "j|k|search|click", ...}
```

Rationale:

- A single sink keeps audit reconstruction simple: one log to fold.
- Discriminant `event` kinds keep workbench events isolable without a
  parallel file.
- `redact-by-default` discipline from the existing sink applies: no
  surface text or token content in workbench events unless the sink
  is explicitly opted into `include_content=True`.

Forbidden:

- a parallel "workbench-only" log file
- emitting operator-action events that include corpus or evidence
  text content
- emitting an event before the handler has actually attempted the
  ratification (no "intent-to-ratify" telemetry — only outcomes)

### Q4 — Font and icon bundling

**Decision: bundled locally.**

ADR-0162 pins typography but did not commit on remote vs bundled.
ADR-0173 commits to **bundled**: fonts and icon glyphs ship in
`workbench-ui/dist/` and the running UI loads them from
`127.0.0.1:<port>`.

Rationale:

- ADR-0160 forbids "remote network dependencies for cognition" — the
  same posture applies to the operator-facing UI, even though the UI
  is not itself cognition.
- A CDN font fetch creates a determinism asymmetry (font renders
  differently with/without network) that the workbench's read-only
  invariants must not depend on.
- Local-first is the workbench's defining property; bundling fonts
  preserves it under offline development (and offline operators —
  see [[user-circumstances]]).

License compliance for bundled fonts is the responsibility of the
W1 PR.

### Q5 — Build artifact location

**Decision: gitignored; CI verifies the build is green but does not
commit `dist/`.**

`workbench-ui/dist/` is added to `.gitignore` in the W1 PR. The
local `core workbench serve` command builds (or uses a previously-
built) `dist/` and serves it as static assets through the existing
stdlib HTTP server.

Rationale:

- Committing build artifacts pollutes the diff with regenerated
  bundle bytes that are not load-bearing for replay.
- A CI job (`workbench-ui-build`) builds `dist/` to verify the source
  compiles, then discards the artifact. This is enough audit signal
  without bloating the repo.
- Operators run `npm ci && npm run build` once after `git clone`;
  the brief acceptance criterion ("a new operator can run `core
  workbench serve` and open the UI") covers this in its setup step.

---

## Keyboard contract (pinned)

ADR-0162 §7 named "Keyboard contract" but did not commit specific
bindings for the ratification corridor. ADR-0173 pins them.

**Global (every view):**

| Key | Action |
|---|---|
| `?` | Show keyboard help overlay |
| `:` | Focus command palette |
| `g p` | Go to proposal queue |
| `g e` | Go to eval center |
| `g t` | Go to trace drawer (last viewed) |
| `Esc` | Dismiss overlay / blur input |

**Proposal queue + detail panel:**

| Key | Action |
|---|---|
| `j` / `↓` | Focus next proposal |
| `k` / `↑` | Focus previous proposal |
| `Enter` | Open detail panel for focused proposal |
| `Esc` | Close detail panel, return to queue |
| `/` | Search/filter the queue |

**Ratification command panel (only when proposal is focused AND replay-passed):**

| Key | Action |
|---|---|
| `r` | Ratify (apply handler) |
| `x` | Reject with note |
| `d` | Defer (mark as deferred-by-operator; remains pending) |
| `y` | Copy `suggested_ratify_cli` to clipboard (operator audit fallback) |
| `?` | Show panel-specific help |

Bindings that ratify (`r`) MUST require the proposal to be in
`pending` state AND `replay_evidence.replay_equivalent == true` AND
the handler to be one of the admitted set. If any precondition
fails, the key is a no-op and a status-footer message names the
failing precondition. No silent failures.

Bindings MUST NOT chord with `Cmd`/`Ctrl` to avoid colliding with
browser-level shortcuts (`Cmd+R` reload, etc.).

The W1 PR ships the keyboard help overlay (`?`) populated from this
table; W3 wires the ratify/reject/defer keys.

---

## What the workbench MAY do

The narrow amendments to ADR-0160's read-only stance.

- **Read everything** the existing API routes expose (proposals,
  math-proposals, artifacts, evals, replays, traces).
- **Drive `apply_lexical_claim()`** on a `LexicalClaim` proposal via
  `POST /math-proposals/{id}/ratify`.
- **Drive `apply_frame_claim()`** on a `FrameClaim` proposal via the
  same route.
- **Drive `apply_composition_claim()`** on a `CompositionClaim`
  proposal once ADR-0169's CC-2 lands.
- **Drive `core teaching review --accept|--reject|--withdraw`** on
  cognition `TeachingChainProposal` records via the existing
  `/proposals/{id}` ratification route once Surface C parity is
  proven in tests (this is the cognition analog; see Sequencing).
- **Emit operator-action telemetry** to the existing JSONL sink per
  Q3 above.
- **Render** the `suggested_ratify_cli` field for audit fallback
  (operator may copy and run via shell if they prefer).

---

## What the workbench MUST NOT do

The non-negotiable forbidden surface.

- **No new mutation paths.** The workbench does not edit corpus,
  packs, lexicon, frame registries, or composition registries
  *except* via the admitted handlers above.
- **No bypass of handler preconditions.** UI cannot ratify a
  proposal that fails `replay_evidence.replay_equivalent` or that
  the handler would reject. The UI's `r` keybind calls the handler;
  the handler's exception path is the UI's failure path.
- **No remote operator.** The backend binds to `127.0.0.1` only.
  CORS is restrictive. No "operator login" endpoint, no token-
  bearer auth, no remote workflow_dispatch trigger.
- **No engine_state writes** outside the existing checkpoint path
  (ADR-0146 / 0150).
- **No silent ratification.** Every ratification produces an
  append-only telemetry event AND a JSONL artifact append. UI must
  surface both to the operator visually before transitioning the
  proposal off the queue.
- **No auto-ratify** under any condition. Replay-passed proposals
  remain `pending` until an explicit keypress (`r`) from a focused,
  expanded proposal detail.
- **No batch ratification** in v1. Each ratification is one
  keypress on one focused proposal. ("Select multiple, ratify all"
  is explicitly deferred — see Non-goals.)
- **No mutation of cognition `TeachingChainProposal` flow** that
  ADR-0161 has not already admitted. The workbench wraps Surface C;
  it does not create a fourth surface.
- **No emission of cognition-domain artifacts from math handlers
  and vice versa.** Partition guarantees from ADR-0167 / 0168 / 0169
  hold unchanged.

---

## Ratification record extension

ADR-0161 §5 defines the ratification record schema. ADR-0173 extends
the `ratifier_kind` enum by one value:

```text
ratifier_kind ∈ {"cli", "workflow_dispatch", "workbench"}
```

A workbench-driven ratification appends a record whose only
divergence from a CLI ratification is `ratifier_kind: "workbench"`.
`actor` carries the OS username of the process running the workbench
server (same as Surface C). `workflow_run_id` is `null`.

**`ratifier_kind` is not a permission discriminant.** It is an
audit-forensic discriminant only. Any code path treating it as a
permission gate is a bug.

**`proposal_id` and `to` remain the only load-bearing fields for
replay** (ADR-0161 §5 "Replay invariants" unchanged).

---

## Sequencing

Per ADR-0166:

### Q1 — Capability

Adds **zero** new capabilities. The workbench ratification corridor
is an ergonomics layer over capabilities that already exist on
`origin/main`:

- `apply_lexical_claim()` — merged
- `apply_frame_claim()` — merged
- `apply_composition_claim()` — pending (PR-β of CompositionClaim wave)
- `core teaching review` — merged

Cognition `TeachingChainProposal` driving is admitted by this ADR but
implementation is deferred until Surface C parity tests are in place
(see Acceptance gates).

### Q2 — Lane

**No new eval lane.** Existing lanes remain the proof surface.

### Q3 — Invariant

Must preserve:

- `wrong == 0` on `core eval gsm8k_math`
- replay equivalence (ADR-0161 §5)
- deterministic claim hashing (ADR-0167 / 0168.1 / 0169.1)
- refusal-first semantics
- handler-side hazard pins (especially case 0050)
- partition (math vs cognition)
- ADR-0160 forbidden-set minus the narrow handler-driving amendment

The implementation PRs (W1..W4 in `WORKBENCH-UI-WAVE-SCOPING.md`)
pass only when all seven are mechanically proven.

---

## Acceptance gates for W1..W4

Each subsequent wave PR must provide:

### W1 (scaffold)

- `workbench-ui/` directory created at repo root per ADR-0162
  Branch 1.
- `dist/` is gitignored.
- A CI job builds the UI green; no `dist/` committed.
- No remote font/icon fetches.
- Backend binds to `127.0.0.1` only (existing); UI verified to
  refuse cross-origin requests.

### W2 (read surfaces)

- Reads only through existing API routes.
- No new backend routes introduced.
- Cognition and math proposal surfaces remain partitioned in the
  UI (separate routes, separate components, separate stores).
- `StableJsonViewer` does not alter bytes — render is canonical.

### W3 (ratification corridor)

- Every `r` keypress executes the same Python entrypoint as the
  corresponding CLI invocation.
- Equivalent ratification (CLI vs workbench) produces byte-equal
  JSONL artifact appends except for `ratifier_kind`.
- Case 0050 hazard pin remains green end-to-end (ratifying any
  admitted handler via the UI does not cause case 0050 to admit).
- `AlreadyRatified` / `WrongClaimSubType` /
  `WrongCompositionCategory` exceptions surface verbatim in the UI
  status footer.
- `r` keypress is a no-op (with named status footer message) on any
  proposal not in `pending` state OR without `replay_equivalent == true`.
- Operator-action telemetry emits per Q3.
- Cross-process replay equivalence test: ratify via UI, fold the
  proposals log, replay — outcome identical to CLI ratification.
- Partition tests: math UI ratifications do not produce cognition
  artifacts and vice versa.

### W4 (verify surfaces)

- Trace and replay surfaces are read-only.
- Eval lanes run via existing read-only routes (`/evals`, `/evals/run`).
- No new eval lane introduced.

### All waves

- `core test --suite teaching -q` green.
- `core test --suite runtime -q` green.
- `core eval gsm8k_math` green.
- No new files under `engine_state/*` in the diff.
- No CDN/remote runtime dependencies.

---

## Non-goals

This ADR does NOT approve:

- A fourth ADR-0161 ratification surface (workbench is part of Surface C).
- Remote operators, operator login, or any authentication beyond
  local filesystem authority.
- Multi-operator concurrency (Q2).
- Batch / multi-select ratification.
- Auto-ratify on replay pass (operator keypress is mandatory).
- Mutation of any handler not enumerated above.
- New corpus families.
- New pack types.
- A workbench-events parallel log (Q3).
- CDN-loaded assets (Q4).
- Committed `dist/` artifacts (Q5).
- ADR-0162 follow-up components (PackInspector, CorpusInspector,
  VaultRecallInspector, MetricGateTable, RegressionDiffPanel, etc.).
- A node-graph builder, workflow canvas, or "approve all"
  affordance (ADR-0162 no-go list).
- Toast notifications that auto-dismiss audit events
  (ADR-0162 no-go list).
- Mobile / responsive form factors (workbench is laptop-class only;
  mobile ratification stays on Surfaces A + B per ADR-0161).

---

## Decision summary

> The CORE workbench may extend ADR-0160 v1's read-only posture
> narrowly to admit operator-driven invocation of the three Tier 1.5
> ratification handlers (`apply_lexical_claim`, `apply_frame_claim`,
> `apply_composition_claim`) and the existing cognition
> `core teaching review` path, provided:
>
> - the workbench backend remains local-only (127.0.0.1, no CORS
>   relaxation, no remote auth)
> - every ratification action invokes the same Python entrypoint as
>   the corresponding CLI invocation, with identical preconditions,
>   exceptions, and append-only artifacts
> - the workbench is treated as a keyboard accelerator over ADR-0161
>   Surface C, not as a fourth ratification surface
> - the ratification record gains a `ratifier_kind: "workbench"`
>   discriminant for audit forensics only — not as a permission gate
> - case 0050, partition, and handler hazard pins remain mechanically
>   green end-to-end
> - all engine_state writes remain on the existing checkpoint path
> - no new mutation paths, corpora, packs, or handlers are admitted
>
> The operator burden is the bottleneck on the teaching corridor's
> compounding loop. This ADR makes ergonomics a first-class concern
> while keeping the trust boundary unchanged in substance.

Reopening this ADR requires evidence that:

1. the keyboard contract (above) is the wrong default and a
   different contract would materially improve operator throughput;
2. multi-operator concurrency has become load-bearing for the
   project's actual operator population; or
3. a new mutation path needs admittance that the existing
   handler-handler discipline cannot express.

Reopening is not required to admit additional handlers as they ship
— each new handler is admitted automatically once its server-side
scoping ADR (the ADR-0168 / 0169 pattern) lands and its acceptance
gates are mechanically pinned.
