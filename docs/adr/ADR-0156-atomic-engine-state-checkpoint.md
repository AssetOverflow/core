# ADR-0156 — Atomic engine-state checkpoint writes (W-022 / L10b.1)

Status: accepted
Date: 2026-05-25

## Context

ADR-0146 §"File Operations and Invariants" specified:

> "Checkpointing must be atomic (e.g., write to temporary file and
> rename) to prevent corruption if the process is terminated
> mid-write."

The W-008 implementation used `Path.write_text` directly on all three
checkpoint files (`manifest.json`, `recognizers.jsonl`,
`discovery_candidates.jsonl`). `write_text` opens the target with
`O_TRUNC`, so the existing file is truncated **before** the new
content is written. SIGINT, SIGKILL, hardware reset, or even an
exception in serialization between truncate and write leaves a
partial / empty file on disk. The next process's load then either
fails or — worse — silently restores from a half-written checkpoint.

L10's "reboot is recovery, not control flow" invariant requires that
reboot find a consistent prior state. Mid-write corruption violates
that invariant.

## Decision

Introduce `engine_state._atomic_write_text(target, content)`:

1. `tempfile.NamedTemporaryFile(dir=target.parent, delete=False)` —
   keeps the temp on the same filesystem as the target so
   `os.replace` is atomic.
2. Write content, `fh.flush()`, `os.fsync(fh.fileno())` — content
   is on the disk's write queue before rename.
3. `os.replace(tmp_path, target)` — atomic same-directory rename.
4. On any exception before or during rename, unlink the temp file
   (best-effort) and re-raise.

All three `EngineStateStore.save_*` methods route through this
helper. The directory-create step moves from each caller into the
helper.

## Invariants pinned by tests

`tests/test_adr_0156_atomic_checkpoint.py` (9 tests):

- Atomic write creates target / overwrites existing / creates parent dir
- `os.replace` failure preserves the prior target file byte-identically
- `os.replace` failure cleans up the temp file
- Temp file lives in the target's directory (same-FS requirement)
- Store-level: `save_manifest`, `save_recognizers` failure preserves prior
- Round-trip content unchanged after the atomic refactor (regression guard)

## Determinism

No payload bytes change. The on-disk content is byte-identical to
pre-W-022 for the same input. Only the failure-mode contract
improves: prior valid checkpoint stays visible, never a partial new one.

## Out of scope

- **`reboot_event` audit trail entry** (L10 scope §Sub-question 3) —
  L10b.3 / W-024.
- **Revision-mismatch warning on load** (ADR-0146 §Risks line 127) —
  L10b.2 / W-023.
- **fsync of the parent directory** after rename. POSIX strictly
  requires this for crash-safety of the rename metadata itself.
  Defers to a future ADR if a real-world corruption is observed; the
  same-FS rename + content fsync we ship today is sufficient for
  the SIGINT/SIGKILL failure modes ADR-0146 specifically named.
- **Cross-process locking.** Shape B is single-process per ADR-0146;
  concurrent writers are out of scope.

## Validation

- `tests/test_adr_0156_atomic_checkpoint.py` (9 passed)
- `tests/test_adr_0146_engine_state.py` (8 passed — round-trip regression guard)
- `core test --suite smoke` (67 passed)
- `core test --suite cognition` (120 passed, 1 skipped)

## Closure

L10b.1 closes the highest-leverage Shape-B correctness gap: a
checkpoint is now either fully-prior or fully-new on disk, never
partial. Reboot recovery is no longer one signal away from silent
corruption.
