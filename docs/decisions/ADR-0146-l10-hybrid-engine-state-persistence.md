# ADR-0146: L10 Shape B Hybrid Engine-State Persistence

**Status:** Accepted
**Date:** 2026-05-25
**Scope doc:** [L10-runtime-model-scope](./L10-runtime-model-scope.md)
**Related:** ADR-0055 (inter-session memory), ADR-0040 (telemetry), ADR-0057 (proposals), W-008, W-003, W-007, W-009, W-017, W-018.

---

## Context

CORE's runtime has historically been session-bounded: every `core` CLI invocation builds a fresh `ChatRuntime` instance, loading packs and teaching corpora anew, while session-state is lost. To realize the vision of a forever-running cognitive engine that accumulates capability over its lifetime, surviving reboots as recovery rather than control flow, CORE requires a defined process and persistence model.

The [L10-runtime-model-scope](./L10-runtime-model-scope.md) evaluated three candidate process shapes:
- **Shape A (Long-lived daemon):** A single persistent daemon process running `cmd_serve`, where CLI invocations act as IPC clients.
- **Shape B (Hybrid state externalized; CLI restores it):** Engine-state is checkpointed to disk at logical action boundaries, and CLI invocations load and resume this checkpoint.
- **Shape C (One-shot CLI with audit trail reconstruction):** Every invocation builds state from scratch by replaying the entire append-only audit trail (telemetry JSONL) from inception.

### Candidate Evaluation and Rationale

- **Shape B (Selected)** is chosen because:
  - It maintains **library-session compatibility** without requiring a background daemon process to be running on the host system.
  - Startup cost is bounded to $O(\text{checkpoint size})$ rather than $O(\text{audit trail size})$, which ensures high performance as the transaction history grows.
  - Approximately 80% of the underlying persistence infrastructure (packs, telemetry, corpus) is already written to disk.
  - High-value engine-state objects, such as `DerivedRecognizer`, are already serializable (via `DerivedRecognizer.to_json() / from_json()`).
- **Shape A (Rejected)** is rejected because a background daemon process cannot survive host library-session interruptions (such as IDE reloads or parent process terminations) without complex process supervision infrastructure.
- **Shape C (Rejected)** is rejected because the $O(N)$ rebuild cost to replay the entire audit trail grows without bound over time, violating the performance and efficiency doctrines.

---

## Decision

Adopt **Shape B: Hybrid engine-state persistence**. 

At every logical-action boundary (specifically, at the turn boundary in `ChatRuntime.chat()`), the current engine-state is serialized and checkpointed to an `engine_state/` directory in the repository root (or the path specified by the `CORE_ENGINE_STATE_DIR` environment variable). Any subsequent CLI invocation loads this checkpoint, restoring `RecognizerRegistry` and the `DiscoveryCandidate` working set, and continues. 

Session-state remains ephemeral and is discarded upon turn completion or process exit.

---

## State Class Assignments

The runtime state is partitioned into four distinct classes:

| State class | Objects | Persistence |
| :--- | :--- | :--- |
| **Session-state** | `session_thread`, current intent, field excitation | Ephemeral — lost on reboot / process exit, no concern. |
| **Engine-state** | `RecognizerRegistry`, `DiscoveryCandidate` working set | Persistent — written to `engine_state/recognizers.jsonl` and `engine_state/discovery_candidates.jsonl` on turn boundaries. |
| **Substrate-state** | Ratified packs, teaching corpus, telemetry JSONL, proposal log | Persistent — already on disk; append-only and immutable without operator intervention. |
| **T1 vault** | `VaultStore` (in-memory deque) | Ephemeral — intentionally ephemeral per ADR-0055 T1; promoted to T3 via HITL. |

---

## `engine_state/` Directory Specification

The checkpoint directory is structured as follows:

```text
engine_state/
  ├── manifest.json
  ├── recognizers.jsonl
  └── discovery_candidates.jsonl
```

- **`engine_state/recognizers.jsonl`**: One JSON line per registered recognizer, serialized using `DerivedRecognizer.to_json()`.
- **`engine_state/discovery_candidates.jsonl`**: One JSON line per pending candidate, serialized using `DiscoveryCandidate.as_dict()`. Note that while `as_dict()` is already implemented, a corresponding `from_dict()` (or load path) will be implemented to deserialize candidates.
- **`engine_state/manifest.json`**: Metadata schema pinning correctness:
  ```json
  {
    "schema_version": 1,
    "written_at_revision": "<git-sha>",
    "turn_count": N
  }
  ```

### File Operations and Invariants:
- The `engine_state/` directory is created on the first checkpoint. A missing directory represents a clean-slate start and must not raise an error.
- Unlike substrate-state (which is append-only), **engine-state files are mutable and overwritten** during each checkpoint to reflect the current active working state.
- Checkpointing must be atomic (e.g., write to temporary file and rename) to prevent corruption if the process is terminated mid-write.

---

## Checkpoint Protocol

The `ChatRuntime` class manages the lifecycle of the engine-state checkpoint:

1. **`ChatRuntime.checkpoint_engine_state(path: Path)`**: Called at the turn boundary after a turn completes, but *before* the response is returned to the caller. This serializes and overwrites the files in the target directory.
2. **`ChatRuntime.load_engine_state(path: Path)`**: Called within `ChatRuntime.__init__` at startup if the `engine_state/` directory exists and the `--no-load-state` CLI flag is not set.
3. **`--no-load-state` CLI Flag**: An opt-out flag for debugging, testing, or executing clean-slate runs. When set, `load_engine_state` is bypassed.

---

## Determinism Guarantee

To preserve the non-negotiable byte-identical replay contract:
- Engine state files must be written using canonical JSON serialization: `sort_keys=True`, and tight separators `separators=(",", ":")` with `ensure_ascii=False`.
- **Round-Trip Invariant:** Loading a checkpoint and immediately re-saving it must produce byte-identical files on disk. Unit and integration tests must pin this round-trip invariant to prevent serialization drift.

---

## What is NOT in Scope

To maintain a narrow and robust focus, the following items are explicitly excluded from this design:
- **VaultStore persistence:** `VaultStore` remains an ephemeral T1 memory layer per ADR-0055. Permanent memory resides in the T3 teaching corpus and is promoted only via HITL.
- **Concurrency control:** Since Shape B is single-process and synchronous, cross-process file locking, daemon synchronization, and signal handling are out of scope.
- **Network surfaces:** The engine remains strictly local-only; no TCP/HTTP servers or sockets are added to support persistence.
- **Multi-tenancy/multi-instance:** A single repository supports exactly one active engine state checkpoint.
- **Re-architecting `ChatRuntime`:** The unit of execution is unchanged; `ChatRuntime` merely gains load/save hook methods.

---

## Unlocks

Establishing this hybrid persistence model directly unlocks the following ratchet tasks:
- **W-003 (`VaultPromotionPolicy` wiring):** The timing for when the active field state crystallizes and promotes candidates is now defined by the turn-boundary checkpoint.
- **W-007 (DerivedRecognizer integration):** Provides the persistent `RecognizerRegistry` slot that preserves active recognizers across turns.
- **W-009 (HITL async queue):** The pending `DiscoveryCandidate` working set on disk acts as the async queue state, allowing the operator to review candidates asynchronously.
- **W-017 / W-018:** Enables autonomous contemplation and automated memory promotion pipelines to check and update persistence boundaries safely.

---

## Risks and Mitigations

- **Serialization Drift:** A stale serializer or added fields on `DerivedRecognizer` or `DiscoveryCandidate` could break reload compatibility.
  - *Mitigation:* Pin round-trip serialization in unit tests. Verify that schema updates include migrations or clear-slate fallbacks.
- **Stale Checkpoint after Pack Mutation:** If a user checks out a different git revision or modifies packs, the loaded checkpoint might refer to invalid types or mismatching revisions.
  - *Mitigation:* Compare `written_at_revision` in `manifest.json` with the current git SHA. If they mismatch, log a warning but continue startup (do not refuse to start, as a reboot is recovery, not control flow).
