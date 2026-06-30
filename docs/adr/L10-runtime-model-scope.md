# Scope: L10 — Runtime Model (Process Lifecycle for Forever-Running CORE)

**Status:** Draft v1 / scope-only (not a decision yet — prerequisite for one)
**Date:** 2026-05-24
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md) (memory)
**Companions:** [substrate-liveness-audit-scope](./substrate-liveness-audit-scope.md), [recognizer-storage-scope](./recognizer-storage-scope.md), [teaching-derived-recognition-scope](./teaching-derived-recognition-scope.md)
**Shelved-but-relevant:** [project-engine-identity-candidate](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/project-engine-identity-candidate.md) (memory) — DNA-analog `EngineIdentity` concept; may become load-bearing under this scope's decisions

---

## Why this document exists

CORE's recent scope work (recognizer-storage v2; substrate-liveness-audit
v2) repeatedly named a load-bearing prerequisite that has no scope or
ADR of its own: **the runtime model**. Several decisions are gated on
it:

- The recognizer-storage scope explicitly states: "this scope is gated
  on the runtime-model scope existing and committing to forever-running."
- The substrate-liveness-audit scope names L10 (runtime model) and L11
  (forever-running engine) as not-audit-targets because they have no
  design yet — the audit's job is to surface need for them.
- The forever-running engine vision ("listen, comprehend, recall, think,
  articulate, learn from reviewed correction, replay deterministically
  — with capability compounding across turns and surviving reboot as
  recovery, not as control flow") is the destination CORE is being built
  toward, but the *process shape* in which that vision is realized is
  unspecified.

CORE today is session-bounded: every `core` CLI invocation builds a
fresh `ChatRuntime`, packs are loaded fresh, the engine has no
long-lived process. The thesis demands the engine *accumulate
capability over its lifetime*; the current process shape doesn't have
a lifetime in any meaningful sense.

This scope defines the question. The answer belongs to the ADR that
follows, and to the substrate-liveness-audit findings that will
inform what's actually load-bearing.

---

## Cross-reference audit (applying the discipline up front)

Per [[feedback-adr-cross-reference-discipline]], the runtime-model
question must be drafted *against* the existing ADRs and code that
already touch lifecycle, persistence, and process shape — not in a
vacuum.

### Existing ADRs touching lifecycle / persistence / process shape

| ADR | Subject | Relevance |
|---|---|---|
| ADR-0040 | Telemetry sink (JSONL) | Persistent turn-event audit trail; survives across sessions; load-bearing for any audit-based "what happened" recovery. |
| ADR-0041 | CLI verdicts + fan-out | Operator readout surface; relevant to HITL entry shape. |
| ADR-0042 | Audit-tour demo | Four-scene reproducibility tour; demonstrates that telemetry IS the cross-session record. |
| ADR-0055 | Inter-session memory | **Most directly relevant.** Defines four-tier memory: T1 session vault (ephemeral-ish), T2 turn-event JSONL (audit trail, persistent), T3 reviewed teaching corpus (persistent, append-only), T4 ratified packs (long-term substrate). Explicitly names "what survives across all sessions and reboots." |
| ADR-0056 / ADR-0080 | Contemplation loop | Async-feeling work (enriching discovery candidates) — needs a process model to know when/where it runs. |
| ADR-0057 | Teaching-chain proposal review | Append-only proposal log; HITL review surface; the existing HITL machinery this scope must build on. |
| ADR-0014 | Train/learning loop (`VaultPromotionPolicy`) | Promotion gate, currently dormant; L2 audit will verify. Live promotion is part of "live mode." |
| ADR-0027 | Identity packs | Loaded at startup; mutation = restart today. Persistent identity continuity is open. |
| ADR-0029 | Safety packs | Same — startup-loaded, fail-closed; mutation = restart. |
| ADR-0033 | Ethics packs | Same shape. |

### Existing code shape (session-bounded reality today)

- **All entrypoints are `argparse`-based CLI commands in `core/cli.py`.**
  `cmd_chat`, `cmd_test`, `cmd_check`, `cmd_trace`, `cmd_oov`,
  `cmd_capability_*` (many), `cmd_pack_*`, `cmd_teaching_*`. Every
  command is one-shot; the process exits when the command returns.
- **No `cmd_serve` / `cmd_daemon` / long-lived process exists.** There
  is no current "forever" entrypoint.
- **`ChatRuntime` (`chat/runtime.py:418`)** is per-invocation. State
  on it (manifold, session thread, contemplation state, recognizer
  registry) does not survive process exit.
- **Persistent state today:** vault store (on-disk, reloaded each
  invocation), teaching corpus (append-only JSONL on disk), telemetry
  sink (JSONL on disk, ADR-0040), packs (on-disk with manifests),
  proposal log (when written, append-only, ADR-0057).
- **Ephemeral state today:** ChatRuntime instance, field manifold,
  session_thread context, contemplation working state, recognizer
  registry (no persistence layer yet), HITL queue (no in-memory
  representation yet).
- **HITL today** is operator-runs-CLI-commands. There is no async
  queue the operator reviews while the engine continues running —
  because the engine doesn't continue running.

### Existing HITL machinery this scope must build on

Per [[feedback-adr-cross-reference-discipline]] and the recognizer-
storage v2 self-review (which previously missed this): the HITL path
is *not* greenfield. ADR-0057 establishes the shape:

- **`teaching/review.py`** — `ReviewOutcome` enum, `review_correction()`
- **`teaching/store.py`** — `PackMutationProposal`, `TeachingStore`,
  append-only proposal log discipline
- **Automated gate:** replay-equivalence (ADR-0057's load-bearing
  innovation)
- **Operator review surface:** today, CLI commands (`cmd_teaching_*`)
- **Append-only proposal log:** persistent across sessions

L10 must reuse this machinery; the *new* concern is making it
asynchronous (operator reviews while engine runs) rather than
synchronous (operator review is a CLI command between engine
invocations).

---

## The runtime-model question

> **What process shape allows CORE to accumulate capability over its
> lifetime, survive reboot as recovery rather than as control flow,
> and present a narrow async HITL ratification entrypoint that is
> never bypassed and never required for runtime continuation?**

Four sub-questions, each load-bearing:

### Sub-question 1 — Process shape

Three candidates, evaluated against current state:

- **A. Long-lived daemon (`cmd_serve`).** One process; CLI commands
  become clients of the daemon via local IPC. Most thesis-aligned
  (engine has a lifetime). Largest delta from today's code shape;
  requires concurrency model decisions, signal handling, supervision.
- **B. Hybrid (engine state externalized; CLI commands restore it).**
  Engine state serialized to disk on every "logical action" boundary;
  any CLI invocation can restore the latest state and continue. No
  long-lived process needed; lifetime is the lifetime of the
  serialized state on disk. Smaller code delta; serialization
  discipline becomes load-bearing.
- **C. Continue with one-shot CLI; teach the audit/recovery layer
  to be the lifetime.** Every invocation is a fresh process, but
  every turn appends to a deterministic audit trail (ADR-0040 +
  ADR-0055 T2) from which the *next* invocation reconstructs
  capability. The audit trail IS the engine's lifetime. Smallest
  delta; pushes the cost of "always on" into "always rebuild from
  audit."

Honest assessment of trade-offs is the spike/ADR's job, not the
scope's. Scope names the three candidates.

### Sub-question 2 — State partitioning

Three state classes the runtime-model must distinguish:

- **Session-state (ephemeral, per-turn-window):** anaphora context,
  current intent, immediate field excitation. May be lost on reboot
  without architectural concern.
- **Engine-state (live, persistent across reboot):** the recognizer
  registry, the contemplation working set, the HITL ratification
  queue. *Expensive to rebuild from primitives;* MUST persist; reboot
  reloads, does not re-derive.
- **Substrate-state (cold, persistent across reboot):** ratified packs,
  ratified teaching corpus, vault store, telemetry JSONL, proposal
  log. Already on disk today; the discipline question is when each
  is updated and how reboot validates consistency.

The scope's commitment is to **naming the three classes**; the ADR
decides what concrete state objects fall in which class.

### Sub-question 3 — Reboot recovery

Three questions reboot recovery must answer:

- **What does reboot verify?** Pack manifest checksums (already do);
  vault integrity (does); reviewed corpus consistency (does); engine-
  state integrity (does NOT today — engine state doesn't survive). If
  any verification fails, what happens? (Refuse to start, fall back,
  surface to HITL?)
- **What does reboot reload vs. rederive?** Substrate-state reloads;
  engine-state reloads if Process Shape A or B, or rederives from
  audit if C; session-state is always rederived (it's per-turn).
- **What does reboot record?** A `reboot_event` analog of `TurnEvent`,
  written to the audit trail, that lets future audit reconstruct the
  fact that this engine instance lost and regained its lifetime here.

The shelved [[project-engine-identity-candidate]] (`EngineIdentity`
content-derived hash) is one candidate mechanism for verifying engine
identity continuity across reboot — explicitly NOT committed by this
scope; flagged here so the ADR knows the candidate exists.

### Sub-question 4 — HITL async entrypoint

Today: operator runs CLI commands. There is no async queue. ADR-0057
establishes the proposal-log shape but the operator interacts with it
through `cmd_teaching_*` commands.

For forever-running, the HITL queue is async by definition:

- **What is the queue's persistent representation?** Likely an
  extension of the ADR-0057 append-only proposal log, possibly with a
  "review state" axis (pending / under-review / accepted / rejected /
  expired).
- **How does the operator interact with it?** Continued CLI commands
  (Process Shape A/B/C compatible) vs. a TUI / web surface (larger
  delta; out of scope for this ADR most likely).
- **What does the engine do while a proposal is pending HITL?**
  Continue serving turns normally; the proposal is not blocking. This
  matches the [[feedback-adr-cross-reference-discipline]] commitment
  ("HITL is the narrow entrypoint, never bypassed, never required for
  runtime continuation").
- **How are proposal queues bounded?** Already named in recognizer-
  storage v2 as a load-bearing constraint: backpressure (queue cap?
  rate limit? operator alert?). The drop-off sibling ADR will specify
  for deprecation; this scope must specify the *generic* shape that
  drop-off and discovery-promotion and pack-mutation all share.

---

## Constraints (non-negotiable)

From CLAUDE.md and the existing thesis:

1. **Deterministic replay.** Whatever the runtime model, given the
   same teaching corpus + same input stream + same ratified substrate,
   the engine must produce the same turn outputs and the same
   trace_hashes. Process shape MUST NOT introduce non-determinism
   (no wall-clock timestamps in deterministic payloads, no parallelism
   without explicit ordering, no race-condition surface in the turn
   loop).
2. **No hidden state.** Engine-state that persists across reboot MUST
   be auditable: serialized in a human-and-machine-readable form,
   checksummable, reproducible from the audit trail when possible.
3. **HITL is the narrow entrypoint.** No autonomous mutation of
   ratified state. No path that lets the engine modify packs,
   teaching corpus, or recognizer registry without operator
   ratification. The forever-running engine's autonomy ends at
   "propose"; ratification is always operator.
4. **Reboot is recovery, not control flow.** No CLI command, no test,
   no operator action should require a reboot. Reboot is a hardware-
   event analog; the engine survives it but does not depend on it.
5. **Existing append-only artifacts stay append-only.** Telemetry
   JSONL, teaching corpus, proposal log — these are audit substrate
   and must remain append-only across this scope's decisions.
6. **No drift repair, no hot-path normalization in the new code.**
   Per CLAUDE.md normalization rules — runtime-model code is a
   forbidden site for these patterns.

---

## What this scope explicitly rejects

- **A runtime-model that requires re-architecting `ChatRuntime`.**
  The session-bounded `ChatRuntime` is the unit of work; whatever
  shape the runtime model takes, `ChatRuntime` should remain
  recognizable.
- **Database persistence for engine state.** Per ADR-0055 north-star:
  "not in a database/embedding store." Engine state persists as files
  (JSONL, pack manifest, vault store), not in a DBMS.
- **Network surface as a primary entrypoint.** This scope assumes
  local-only operation (the user's circumstances make
  always-on-internet unsafe to assume; per [[user-circumstances]]).
  A network surface may come later but is not in scope.
- **Multi-tenant or multi-instance concerns.** Single engine instance
  on a single machine. Sharing substrate across instances is a
  separate scope (or a feature of [[project-engine-identity-candidate]]
  if it ever un-shelves).

---

## What this scope does NOT commit

- **Process Shape A vs. B vs. C.** Spike/ADR decides. The audit (L4-L9
  findings, especially L7/L8) will inform which is least disruptive.
- **HITL surface beyond CLI.** A TUI or web surface may eventually
  exist; this scope doesn't decide.
- **EngineIdentity adoption.** Shelved candidate; ADR may un-shelve
  it if reboot-recovery sub-question demands it.
- **Concurrency model.** If Shape A wins, the daemon's concurrency
  model (threads? async? per-turn process?) is an implementation
  detail of the ADR, not the scope.
- **Specific persistence format for engine-state.** JSONL extension?
  Custom binary? Pack-style? Implementation detail.
- **Migration path from current session-bounded shape.** ADR
  specifies; scope notes that migration MUST be incremental (no big-
  bang switchover that breaks `core chat`).

---

## Determinism requirements (non-negotiable)

The runtime model must preserve:

1. **Byte-identical replay.** Same substrate + same input stream ⇒
   same turn outputs. Process shape MUST NOT introduce wall-clock,
   PID, or other process-bound entropy into deterministic payloads.
2. **Reboot-equivalent state.** State after `(boot, run N turns,
   reboot, reload)` is byte-identical to state after `(boot, run N
   turns)` minus process-memory artifacts. (Reboot loses
   session-state; engine-state and substrate-state are restored.)
3. **HITL ratification trace.** Every ratification produces an
   append-only log entry with deterministic content; the log is the
   audit trail for engine-state mutations.

---

## Risks the spike / first ADR must surface

- **Shape-A concurrency complexity.** A long-lived daemon introduces
  signal handling, supervision, possibly inter-process concurrency.
  CLAUDE.md's "Do not add hidden background execution" is at risk;
  daemon design must make all concurrency explicit and auditable.
- **Shape-B serialization correctness.** Every engine-state object
  must round-trip serialization byte-identically. One drifted
  serializer breaks reboot recovery silently.
- **Shape-C rebuild cost.** If the audit trail grows to N turns,
  rebuilding capability on every CLI invocation is O(N). May be fine
  for small N, untenable for large.
- **HITL queue starvation.** If the operator goes offline for an
  extended period, proposals accumulate. The recognizer-storage v2
  scope flagged this as load-bearing for drop-off; it's load-bearing
  for every proposal kind. The ADR must specify backpressure
  generically.
- **Pack-mutation during running engine.** If Shape A or B is chosen,
  a ratified pack mutation while the engine is running raises
  questions: hot-reload? Refuse-and-restart? Queue-until-quiescent?
  Each option has different operator-experience implications.
- **Audit-trail compaction.** If telemetry JSONL grows unbounded,
  reboot recovery (under Shape C) becomes slower over time. Compaction
  / snapshotting is the natural answer but introduces a new mutation
  axis on append-only state. ADR specifies or defers.
- **State-class boundary mistakes.** Putting engine-state in
  session-state's bucket loses learning on reboot; putting session-
  state in engine-state's bucket bloats persistence and breaks
  determinism. The state-partitioning sub-question is high-leverage.

---

## Open questions for the audit and follow-up scopes to inform

- **What does the substrate-liveness audit (L4-L9) find about state
  that wants to be persistent but currently isn't?** Each closure gap
  the audit surfaces is potential engine-state for this scope to
  classify. Specifically:
  - L4 (Recognition) — recognizer registry persistence (already
    scoped in recognizer-storage; cross-references here).
  - L7 (Teaching loop) — proposal log liveness; HITL queue persistence.
  - L8 (Inter-session memory + contemplation) — Tier 1/2/3 transitions;
    contemplation working set.
- **Should the runtime-model ADR un-shelve `EngineIdentity`?** If
  Sub-question 3 (reboot recovery) commits to verifying engine
  identity continuity across reboot, the shelved candidate likely
  becomes the right primitive. Trigger: sub-question 3 commits to
  cross-reboot identity verification.
- **Does Process Shape A require a new top-level package
  (`core/server/` or `core/daemon/`)?** Implementation-detail
  question, but if yes, the substrate-liveness audit will need to
  add a layer (L10b? a daemon layer?) to its map.
- **How does the runtime model interact with the audit's "live mode"
  framing?** The substrate-liveness-audit scope frames "live mode" as
  the destination state; the runtime model is the mechanism. They
  must be drafted together as the ADR cluster lands.

---

## Summary

L10 — the runtime model — is the missing prerequisite for forever-
running CORE. Several recent scopes (recognizer-storage,
substrate-liveness-audit) flagged it as gated work without it
existing.

This scope frames the question against four sub-questions: process
shape (daemon / hybrid / one-shot-with-replay), state partitioning
(session / engine / substrate), reboot recovery (verify what, reload
vs. rederive, record what), and HITL async entrypoint (queue shape
+ backpressure). It explicitly cross-references the ADR-0040/0041/
0042/0055/0056/0057 cluster that already implements parts of the
answer, and the recognizer-storage scope that depends on this scope's
decisions.

It rejects database persistence, network primary entrypoints,
multi-tenant concerns, and re-architecting `ChatRuntime`. It commits
no specific shape; the spike/ADR decides, informed by audit findings.

The scope's commitment is to **the question framed against existing
machinery**. Answers belong to the spike and the ADR that follows.
Audit findings (L4-L9) refine the question over time.
