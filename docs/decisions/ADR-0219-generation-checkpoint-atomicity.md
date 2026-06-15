# ADR-0219 — Generation-dir atomic checkpoint (L10 continuity hardening)

Status: accepted
Date: 2026-06-15
Extends: ADR-0146 (engine-state persistence), ADR-0156 (per-file atomic writes)

## Context

ADR-0156 (W-022) introduced `_atomic_write_text` to guarantee **per-file**
atomicity: each of the four checkpoint files (`recognizers.jsonl`,
`discovery_candidates.jsonl`, `session_state.json`, `manifest.json`) is
written via `temp + os.replace`, so a kill mid-write leaves the prior file
intact.

ADR-0156 §"Out of scope" explicitly excluded **cross-file atomicity**:

> "There is no cross-file consistency guarantee: recognizers and candidates
>  are written in separate atomic ops, so a kill between them leaves the
>  store in a mixed state (e.g., recognizers@N over manifest@N-1)."

The flat layout is therefore not a committed state — it is four
independently-atomic files with no shared commit boundary.  L10's telos
("one continuous life") requires that a reboot always resumes from a
**coherent, complete** checkpoint, not a mixed-generation one.

A second deficiency: `finalize_turn_trace_hash` (ADR-0153) called
`save_discovery_candidates` **outside** the main checkpoint sequence,
creating a second write path into the checkpoint directory without going
through the generation commit.

ADR-0156 also deferred the **parent-directory fsync** after `os.replace`.
POSIX strictly requires fsyncing the directory to make the rename metadata
durable.  This ADR closes that deferral.

## Decision

### Generation-dir model

The checkpoint becomes a **committed generation**: a complete, fsync-ed
`gen-NNNN/` directory pointed to by a single `current` file.  The atomic
replacement of `current` is the only commit boundary.

```
engine_state/
  gen-0041/
    recognizers.jsonl
    discovery_candidates.jsonl
    session_state.json
    manifest.json
  current                    ← one line: "gen-0041"
```

Two-phase commit protocol:
1. **`begin_generation()`** — allocate `gen-NNNN/`, return `(gen_num, gen_dir)`.
2. Write all checkpoint files into `gen_dir` via `EngineStateStore(gen_dir).save_*`.
3. **`commit_generation(gen_num)`** — fsync gen dir → `os.replace(tmp_current, current)` → fsync parent → GC old gens.

A SIGKILL before the `os.replace` in step 3 leaves the prior `current`
intact.  A SIGKILL after commits the new generation.  Incomplete `gen-NNNN/`
directories with no `current` entry are garbage, ignored by all load paths.

### `finalize_turn_trace_hash` write path closed

`finalize_turn_trace_hash` no longer calls `save_discovery_candidates`.
The in-memory candidates carry the updated `source_turn_trace`; they are
persisted atomically as part of the next `checkpoint_engine_state` call.
(If the process dies between back-stamp and next checkpoint, the trace hash
is lost from the candidate but the candidate itself survives in the prior
committed generation — acceptable: the trace hash is audit metadata, not
state-determining.)

### Legacy flat layout — explicit migration

On the first `begin_generation()` call against a flat-layout store (pre-0219
`manifest.json` at root, no `current`):
1. Flat files are copied into `gen-0000/` (fsync-ed).
2. `current` is written pointing to `gen-0000`.
3. The next generation (`gen-0001`) is allocated and returned.

Load methods fall back to the flat root when no `current` exists, so a v1
or v2 checkpoint is readable without a write (the migration only happens at
write time).

### Parent-dir fsync

`commit_generation` fsyncs both the generation directory (content durability)
and the parent directory after the `os.replace` (pointer rename metadata
durability), closing the ADR-0156 deferral.

### GC

`commit_generation` retains the last K=2 committed generations (the current
and its predecessor) and prunes older ones.  K≥2 ensures the predecessor is
available if the committed gen dir is somehow corrupted after commit.
Pruned generation names are logged at DEBUG level.

## Implementation

- `engine_state/__init__.py`: `begin_generation`, `commit_generation`,
  `_current_gen_dir`, `_resolve_dir`, `_gc_old_generations`, `_fsync_dir`.
  All `load_*` methods updated to use `_resolve_dir()`.  `exists()` checks
  both layouts.  `save_*` methods unchanged (write relative to `self.path`,
  so they naturally write into a gen dir when instantiated as
  `EngineStateStore(gen_dir)`).
- `chat/runtime.py`: `checkpoint_engine_state` uses the two-phase commit.
  `finalize_turn_trace_hash` no longer calls `save_discovery_candidates`.
- `evals/l10_continuity/runner.py`: `_inject_orphan_tmp` updated to inject
  both orphan shapes (unreferenced gen dir + torn `current` temp file).

## Acceptance gate

All of the following must hold (proven by `tests/test_adr_0219_generation_checkpoint.py`):
- Crash before pointer swap restores the prior committed generation.
- Crash after pointer swap restores the new generation.
- Incomplete gen dirs (not pointed to by `current`) are ignored on load.
- No load path mixes files across generations.
- Legacy flat layout migrates explicitly on first write; reads cleanly without migration.
- No normalization or repair on restore.
- `versor_condition < 1e-6` throughout (proven by L10 lane).

## Invariants pinned by tests

`tests/test_adr_0219_generation_checkpoint.py`:
- `test_fresh_store_writes_gen0000_and_current` — first checkpoint creates gen-0000 + current.
- `test_second_checkpoint_advances_generation` — gen-0001 replaces gen-0000.
- `test_orphan_gen_dir_ignored_before_pointer_swap` — unreferenced gen-9999 is invisible.
- `test_torn_current_tmp_ignored` — `.current.*.tmp` orphan does not affect load.
- `test_no_cross_generation_mixing` — load always reads from a single gen dir.
- `test_legacy_flat_layout_migrates_on_first_write` — flat state → gen-0000 on write.
- `test_legacy_flat_layout_readable_without_write` — load falls back to flat root.
- `test_commit_point_matches_turn_count` — recovered turn_count == committed turns.
- `test_gc_retains_last_two_generations` — GC prunes only generations outside the window.

## Related

- ADR-0146 — engine-state persistence foundation
- ADR-0156 — per-file atomic writes (extended here to cross-file)
- ADR-0157 — revision-mismatch warning on load (unaffected)
- ADR-0158 — reboot event audit (unaffected)
- L10 continuity hardening brief pack: `docs/handoff/l10-continuity-hardening-briefs-2026-06-15.md`
