# ADR-0161 — HITL Async Queue (W-009, L11)

**Status:** Proposed
**Date:** 2026-05-26
**Author:** Shay
**Parent scope:** [L11 — HITL Async Queue Scope](./L11-hitl-async-queue-scope.md)
**Closes:** W-009 (substrate-liveness-ratchet)

---

## Context

L11 named eight sub-questions the eventual ADR must answer.  ADR-0057
already pinned proposal eligibility, replay-equivalence, the
`pending → accepted | rejected | withdrawn` state machine, and the
append-only proposal log.  ADR-0151 made `proposal_id` deterministic
over (candidate_id, chain).  ADR-0152 closed the engine-authored
proposal loop end-to-end.  ADR-0155 added a CI contemplation runner
that proposes via PR review.  `.github/workflows/ratify-proposal.yml`
exposes `accept_proposal` over `workflow_dispatch` so the operator can
ratify from a phone.

What is still missing is a queue *shape* — a named, replayable view
over those existing append-only sources, plus the minimum new
machinery needed for backpressure, mobile-feasible inspection, and
full state-transition (`reject` and `withdraw`) from the same surface
that ratifies.  This ADR answers L11's eight sub-questions by
selecting from the menu L11 listed, in every case toward the
narrowest commitment that still names a testable invariant.

The principle behind every call below is the same: the queue is **not
a new persistence substrate**.  It is a deterministic projection of
the proposal log and the contemplation-run artifacts the project
already commits to.  Anything that cannot be derived from those
sources is out of scope.

---

## Decision summary

| L11 sub-question | Decision |
|---|---|
| 1 — Persistent representation | Derived view over `teaching/proposals/proposals.jsonl` ∪ `contemplation/runs/*.json`.  Queue identity = `proposal_id`.  No new persistence file. |
| 2 — Operator interaction surface | Three surfaces, ranked: GitHub PR (mobile-primary, inspect-only), `workflow_dispatch` (mobile-primary, accept/reject/withdraw), local CLI (authoritative).  PR-merge is admission, not ratification. |
| 3 — Engine behavior while pending | Engine keeps serving turns.  Pending proposals are observable but never active truth.  No proposal-on-proposal dependencies. |
| 4 — Bounds and backpressure | Pending-count cap of **256**.  Dedup by deterministic `proposal_id`.  No wall-clock expiry.  When full, contemplation runner emits a typed `queue_full` report instead of a new proposal. |
| 5 — Trust boundary + ratification log | Only the repo owner ratifies.  Every transition appends a record carrying `ratifier_kind`, `actor`, `commit_sha`, and (for workflow path) `workflow_run_id`.  CI may stage; CI may not ratify. |

---

## Decision detail

### 1. Persistent representation

The queue is a **derived view** over two append-only sources that
already exist on disk and in git history:

- `teaching/proposals/proposals.jsonl` — the canonical proposal log
  defined by ADR-0057.  Carries `proposal`, `replay`, `transition`,
  and `accepted_corpus_append` events.
- `contemplation/runs/*.json` — CI-emitted contemplation reports
  defined by ADR-0155.  Each report carries one proposal candidate
  and its replay evidence.

No third file is introduced.

**Queue identifier.**  A queue item is identified by `proposal_id`
(deterministic SHA-256 over `(candidate_id, proposed_chain)` per
ADR-0151).  Queue items and proposals are 1:1.  A contemplation report
that has not yet been ingested by `propose_from_candidate` is a
*pre-queue artifact*; it becomes a queue item only when its
`proposal_id` appears in `proposals.jsonl`.

**Required derived fields.**  For each queue item the projection
exposes:

| Field | Source |
|---|---|
| `proposal_id` | proposals.jsonl `proposal` event |
| `source_kind` | proposals.jsonl `proposal.source.kind` |
| `source_id` | proposals.jsonl `proposal.source.source_id` |
| `proposed_chain` | proposals.jsonl `proposal.proposed_chain` |
| `replay_evidence` | proposals.jsonl `replay` event (most recent) |
| `state` | last `transition.to` for this `proposal_id`, or `"pending"` if absent |
| `review_history` | full ordered list of `transition` events |
| `contemplation_report_path` | `contemplation/runs/*.json` whose `proposal_id` matches, if any |

The projection is a pure function of the two source files.  Replay
of the proposal log reconstructs the queue byte-identical.

**State enumeration.**  The state set is **exactly** ADR-0057's
existing alphabet — `pending | accepted | rejected | withdrawn`.
No new states.  "Stale", "superseded", "expired", and "duplicate" are
**not** queue states; they are conditions detectable at submission or
review time (see §4) and recorded as a `rejected` transition with a
typed reason in the `note` field.

**No deletion.**  Append-only.  All historical events remain visible
under `core teaching proposals --include-history`.

---

### 2. Operator interaction surface

Three operator surfaces exist.  Each has a distinct role.  None is
optional; together they satisfy L11's "mobile-feasible" constraint
while preserving the local CLI as the audit-grade authority.

#### Surface A — GitHub PR (mobile-primary, inspect-only)

ADR-0155's contemplation workflow opens a PR whose diff is a single
`contemplation/runs/<timestamp>.json`.  The PR body now also
**embeds the queue summary**: pending count, this proposal's
`proposal_id`, replay-equivalence outcome, and the chain in
human-readable form.

The operator inspects from the GitHub mobile app.  **Merging the PR
admits the proposal to the queue.  It does not ratify.**  This
separation matters: merging is "the artifact is now part of the
audit trail"; ratifying is "this artifact mutates the corpus".

#### Surface B — workflow_dispatch (mobile-primary, transition-capable)

`.github/workflows/ratify-proposal.yml` currently exposes
`accept_proposal` only.  This ADR extends it to a single workflow
parameterized by `action ∈ {accept, reject, withdraw}`.  Invocation
from the GitHub mobile app provides a phone-feasible path to **every**
state transition, not only acceptance.

Every workflow run records, into the same `proposals.jsonl` event it
appends:

```json
{
  "event": "transition",
  "proposal_id": "...",
  "to": "accepted|rejected|withdrawn",
  "note": "<operator_note>",
  "ratifier_kind": "workflow_dispatch",
  "actor": "<github.actor>",
  "commit_sha": "<github.sha>",
  "workflow_run_id": "<github.run_id>",
  "review_date": "YYYY-MM-DD"
}
```

#### Surface C — local CLI (authoritative)

`core teaching review <proposal_id> --accept|--reject|--withdraw`
remains the audit-grade authority.  Records use
`ratifier_kind: "cli"` and carry the operator's OS username and the
local `HEAD` SHA at the moment of ratification.

Identical preconditions hold across surfaces B and C:

1. `proposal_id` exists in the log.
2. Current state is `pending`.
3. `replay_evidence.replay_equivalent` is `true`.
4. Acting actor matches the repo-owner allow-list (see §5).

A workflow that violates any precondition fails closed with a
non-zero exit and emits no transition event.  The proposal stays
`pending`.

#### New read-only surfaces

Two new CLI commands expose the queue projection:

- `core teaching queue list [--state pending|accepted|rejected|withdrawn|all]`
  — prints `proposal_id`, source kind, age (in proposals, not
  wall-clock — see §4), replay status, and current state.
- `core teaching queue show <proposal_id>` — prints the full derived
  record including `review_history` and the contemplation-report
  reference if one exists.

Both are pure projections; neither mutates state.

---

### 3. Engine behavior while pending

The engine keeps running.  ADR-0146/0150/0152 already commit to this;
this ADR makes it precise for queue semantics.

- **Live turns.**  Pending proposals do not participate in grounding,
  recall, proposition-graph admissibility, or eval scoring.  They are
  invisible to `chat.runtime.ChatRuntime.chat`.
- **Continued production.**  The engine may keep producing new
  proposals while earlier ones are pending, subject to §4 backpressure.
- **No proposal-on-proposal dependencies.**  A proposal whose
  `proposed_chain` semantically depends on another *pending* proposal's
  ratified state is rejected at submission with reason
  `dependent_on_pending`.  Dependencies between proposals create
  ratification ordering constraints that quietly couple HITL choices;
  forbidding them keeps every ratification independent.  If a chain
  genuinely depends on another, the dependent proposal is re-proposed
  *after* the dependency lands.
- **Replay across ratification.**  Work produced before a
  ratification replays under the pre-ratification corpus.  Work
  produced after replays under the post-ratification corpus.  The
  proposal log preserves the order so this remains deterministic.

---

### 4. Bounds and backpressure

The queue has a hard cap on **pending** items.  Accepted, rejected,
and withdrawn items do not count toward the cap.

#### Pending cap

**Cap: 256 pending proposals.**

Rationale: contemplation can run nightly; replay equivalence is the
expensive part of producing a proposal, but human review is the
expensive part of clearing one.  256 ≈ a year of nightly proposals if
the operator clears one per day on average.  Any higher and the
operator's mental model of "what is pending" stops fitting in human
attention; any lower and a short CI burst could refuse work the
operator would have wanted to see.  This is the only magic number in
the ADR; it is operator-tunable via repo variable
`CORE_HITL_PENDING_CAP` and defaults to 256 when the variable is
absent.  The default change is itself a reviewed change (this ADR);
the variable is for *raising* the cap, not lowering it below default.

#### Dedup

A proposal whose `proposal_id` already exists in the log is rejected
at submission as `duplicate`.  Because `proposal_id` is deterministic
over content (ADR-0151), this is a content-based dedup, not a
timestamp dedup.  Replay of the same candidate produces the same
`proposal_id` and is silently coalesced.

#### Expiry

**There is no wall-clock expiry.**  Pending proposals stay pending
until the operator transitions them.  Wall-clock expiry would couple
queue state to runner time and break deterministic replay.  Operator
withdrawal is the only path out of `pending` other than accept/reject.

#### Full-queue behavior

When `pending_count >= cap`, the contemplation runner emits a typed
`queue_full` report instead of a new proposal:

```json
{
  "report_kind": "queue_full",
  "pending_count": <N>,
  "cap": <C>,
  "candidates_skipped": [{"candidate_id": "...", "reason": "queue_full"}, ...]
}
```

This is written to `contemplation/runs/<timestamp>.json` and opened
as a PR exactly like a normal contemplation report.  The PR body
makes the full state visible to the operator on their phone.  No
proposal is silently dropped: the `candidate_id` of every skipped
candidate is recorded so a future run (after the operator clears
queue space) can re-emit it.

#### Age (in proposals, not wall-clock)

Queue listing exposes an `age_proposals` integer — the number of
*subsequent* proposals appended to the log after this one entered
`pending`.  This is a replayable, deterministic notion of staleness.
Wall-clock time is recorded in events but never load-bearing for
queue ordering or backpressure.

---

### 5. Trust boundary and ratification log

#### Who may ratify

Only the repo owner.  Enforcement:

- **Surface B (workflow_dispatch).**  The workflow's `if:` guard
  rejects any `github.actor` not in the repo's `CORE_RATIFIERS`
  variable (comma-separated GitHub logins).  When the variable is
  unset, the default ratifier set is `${{ github.repository_owner }}`
  alone.  The job fails closed with a clear log message if the actor
  is unauthorized.
- **Surface C (local CLI).**  No additional check beyond the existing
  local filesystem authority.  The CLI cannot be exercised remotely;
  possession of a local working copy is the trust boundary.

CI workflows (contemplation runner, lane-SHA verifier, smoke gate,
etc.) **cannot ratify**.  They have no path to `accept_proposal`.
They may stage artifacts and open PRs, nothing more.

#### Ratification record

Every transition appends a single JSONL event to `proposals.jsonl`:

```json
{
  "event": "transition",
  "proposal_id": "<sha256>",
  "to": "accepted|rejected|withdrawn",
  "note": "<free-text>",
  "ratifier_kind": "cli|workflow_dispatch",
  "actor": "<github.actor | os.user>",
  "commit_sha": "<HEAD at transition>",
  "workflow_run_id": "<github.run_id or null>",
  "review_date": "YYYY-MM-DD"
}
```

`actor`, `commit_sha`, and `workflow_run_id` are recorded for audit
but are **not load-bearing for state reconstruction**.  Replay of the
log requires only `proposal_id` and `to`.  This keeps the replay
substrate small while making audit forensics complete.

#### Replay invariants

Given `proposals.jsonl` and `contemplation/runs/*.json`, the queue
state at any historical point is reconstructible byte-identical by
folding events in order.  The new fields (`ratifier_kind`, `actor`,
`commit_sha`, `workflow_run_id`) appear in audit projections but not
in the trace hash inputs.  Existing trace_hash invariants from
ADR-0153 are preserved.

---

## Out of scope (deferred)

This ADR scopes only the HITL async queue.  It does not commit to:

- a Workbench API or UI surface (ADR-0160 W-026..W-031);
- engine-identity continuity (`project-engine-identity-candidate`,
  shelved — un-shelve only if cross-reboot ratifier identity becomes
  load-bearing);
- recognizer-storage durability (separate ADR);
- pack mutation queue (packs remain reviewed-ratify-only outside this
  queue);
- safety / ethics ratification semantics;
- a queue prioritization heuristic (queue is FIFO by log order);
- automatic dependency-chasing across pending proposals;
- Slack / email / push-notification delivery;
- a daemon or background worker;
- a database-backed queue.

The queue presented here is the **minimum** structure that satisfies
L11.  Each deferred item can become its own ADR without disturbing
this one.

---

## Implementation plan

Five small PRs, each a self-contained step, none of which mutate
existing recorded queue history:

### Step 1 — `core teaching queue` read commands

- New module `teaching/queue.py` exposing a pure `derive_queue(log)`
  function that returns the projection in §1.
- New CLI subcommand `core teaching queue list|show` wired in
  `core/cli.py`.
- Tests: pure derivation over fixture proposals.jsonl; states match
  ADR-0057's alphabet; replay-equivalence in derivation.
- **No mutation paths.**

### Step 2 — Backpressure (pending-count cap)

- `propose_from_candidate` consults pending count via
  `teaching/queue.derive_queue` and emits a `queue_full` report
  instead of a new proposal when the cap is reached.
- `contemplation/runs/<timestamp>.json` schema extended with
  `report_kind ∈ {"learning_arc", "queue_full"}` (default
  `"learning_arc"` for back-compat).
- Repo variable `CORE_HITL_PENDING_CAP` honored; default 256.
- Tests: synthetic full-queue triggers `queue_full` report;
  candidate_id of every skipped item is recorded; replay still
  byte-identical.

### Step 3 — Submission-time invariants

- `propose_from_candidate` rejects duplicate `proposal_id` with reason
  `duplicate` (already enforced; this step adds the explicit recorded
  reason).
- `propose_from_candidate` rejects `dependent_on_pending` proposals.
  Heuristic: chain whose `subject` or `object` lemma is a substring
  of any pending proposal's `proposed_chain` is considered dependent;
  the conservative check fails loud and the proposal is re-emitted
  after the dependency lands.
- Tests for both rejection paths.

### Step 4 — Extend ratification workflow to reject/withdraw

- `.github/workflows/ratify-proposal.yml` gains an `action` input
  (`accept | reject | withdraw`) and dispatches to the corresponding
  CLI subcommand.
- Workflow guard enforces `actor ∈ CORE_RATIFIERS` (defaults to repo
  owner if variable is unset).
- Transition record includes `ratifier_kind: "workflow_dispatch"`,
  `actor`, `commit_sha`, `workflow_run_id`, `review_date`.
- Mirror updates to `core teaching review` so CLI records
  `ratifier_kind: "cli"` symmetrically.
- Tests: precondition failures emit no transition event; unauthorized
  actor fails closed.

### Step 5 — Embed queue summary in contemplation PR body

- The contemplation workflow's PR body now includes the queue summary
  (pending count, cap, this proposal_id, replay outcome,
  human-readable chain).
- Operator inspecting from mobile sees full queue context without
  opening the JSON.
- No corpus or ratification effect.

Each PR ships with its own ADR-compatibility statement, lane tests,
and read-only invariant assertion (no mutation outside
`proposals.jsonl` and `contemplation/runs/`).

---

## Acceptance criteria

This ADR is ratifiable when:

1. The queue projection is a pure function of the two source files,
   with a test that proves the projection is byte-identical across a
   randomized event-order replay (the source files are append-only,
   so order is fixed in practice — the test confirms the projection
   does not depend on hidden state).
2. The pending-count cap fires deterministically in a synthetic test
   that pre-populates `proposals.jsonl` with 256 pending entries; the
   257th submission produces a `queue_full` report and no proposal.
3. Every transition event records `ratifier_kind`, `actor`, and
   `commit_sha`, asserted by tests against both CLI and workflow
   surfaces.
4. The workflow's actor guard fails closed in a CI test that fakes a
   non-allowlisted `github.actor`.
5. `core teaching queue list` and `... show` succeed against the
   current `teaching/proposals/proposals.jsonl` on `main` without
   mutating any file (snapshot assertion).

---

## Consequences

### Positive

- Closes W-009, the last open substrate-liveness ratchet item.
- The queue exists without introducing a new persistence file.
- Mobile ratification path covers all three transitions, not just
  accept.
- Backpressure is bounded and deterministic — no silent drops, no
  unbounded growth.
- Audit forensics gain `actor` / `commit_sha` / `workflow_run_id`
  without changing replay semantics or trace_hash inputs.

### Negative

- The pending cap is a single magic number; raising it remotely
  requires the operator to change a repo variable from a phone.  This
  is an accepted trade for keeping the queue projection a pure
  function of two files.
- Forbidding proposal-on-proposal dependencies will occasionally
  force a re-emission of a chain after its dependency lands.  This
  is intentional: dependent ratification ordering is the wrong
  failure mode to bake in.
- Symmetry between CLI and workflow surfaces enlarges the surface
  area for `accept_proposal`'s preconditions; tests must enforce
  identical precondition behavior across both paths.

### Risks

- `ratifier_kind` and `actor` are recorded but not used for
  authorization beyond the workflow's `if:` guard.  Local CLI trust
  remains "possession of the working copy".  If the threat model
  later admits multi-operator scenarios, a follow-up ADR must add a
  CLI-side identity check; this ADR explicitly does not.
- `dependent_on_pending` detection uses lemma-substring heuristics.
  False positives reject genuinely independent chains.  False
  negatives admit dependent chains that ratification ordering will
  surface later.  The conservative choice is to err toward false
  positives (over-reject), since rejected proposals can be
  re-emitted; the alternative silently couples ratifications.

---

## Cross-references

- [L11 — HITL Async Queue Scope](./L11-hitl-async-queue-scope.md)
- [L10 — Runtime Model Scope](./L10-runtime-model-scope.md)
- [ADR-0057 — Teaching-Chain Proposal + Review + Replay-Equivalence Gate](./ADR-0057-teaching-chain-proposal-review.md)
- [ADR-0151 — Load-time auto-proposal pipeline](./ADR-0151-auto-proposal-pipeline.md)
- [ADR-0152 — Learning-arc demo (proof corridor)](./ADR-0152-learning-arc-demo.md)
- [ADR-0153 — TurnEvent.trace_hash back-stamp](./ADR-0153-turn-event-trace-hash-backstamp.md)
- [ADR-0155 — CI contemplation runner](./ADR-0155-ci-contemplation-runner.md)
- [ADR-0156 — Atomic engine-state checkpoint](./ADR-0156-atomic-engine-state-checkpoint.md)
- [ADR-0157 — Revision-mismatch warning](./ADR-0157-revision-mismatch-warning.md)
- [ADR-0158 — Reboot-event audit trail](./ADR-0158-reboot-event-audit.md)
- [`.github/workflows/ratify-proposal.yml`](../../.github/workflows/ratify-proposal.yml)
- [CLAUDE.md](../../CLAUDE.md) — deterministic replay, exact recall, proposal-only learning, no hidden state.

### Memory cross-references

- [[thesis-decoding-not-generating]] — the queue must teach the
  engine *to find* better-ratified evidence, not just store another
  found thing.  Backpressure-as-`queue_full`-report rather than
  silent-drop honors this.
- [[feedback-adr-cross-reference-discipline]] — every decision above
  selects from existing ADRs and workflows; no parallel mechanism is
  introduced.
- [[feedback-address-critiques-dont-waive]] — L11's eight sub-questions
  are answered in order, not deferred.
- [[project-engine-identity-candidate]] — remains shelved; the
  `actor` field in transition records covers the audit need without
  un-shelving engine-identity work.
