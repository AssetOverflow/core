# ADR-0220 — Engine identity vs. build provenance (`code_revision` in the identity hash)

Status: proposed (brief only — no code change; awaiting architect ratification)
Date: 2026-06-15
Relates: ADR-0146 (engine-state persistence), ADR-0156 (atomic checkpoint),
ADR-0157 (revision-mismatch warning), ADR-0219 (generation-dir atomic checkpoint),
L11 identity continuity (`core/engine_identity.py`, commit `f2dac1dc`),
[L10-runtime-model-scope](./L10-runtime-model-scope.md)

> This ADR **documents a contradiction between two already-ratified decisions and
> proposes how to resolve it.** It is the "PR A" of a 3-part sequence (A = this
> brief, B = safe operator ergonomics, C = the identity/provenance semantics
> change). It changes no runtime behavior. Per project doctrine (*address
> critiques, don't waive them*; *fix upstream, not beside*), the semantics change
> (C) must not ship before this decision is accepted.

## Context — the incident

`core always-on` refused to resume a 26 396-turn lived life:

```
checkpoint was written under 75f3bb75649d…
but this build computes b0f89456fe26…
```

The checkpoint (`engine_state/manifest.json`, now backed up under
`engine_state/_life_backup_c6d0e2a_f5c6914d/`) was stamped at revision
`c6d0e2a92004`; the running build is `f5c6914d0083`. Under the always-on
daemon's forced strict-continuity config the load guard raised
`IdentityContinuityError` and the daemon exited (`core/cli.py:393-401`,
exit code 2).

This was diagnosed and operationally resolved (back up the runtime files —
**not** the directory; see "Operator ergonomics" below — then start a fresh
life). The remaining question is architectural: **is the refusal correct
behavior, or a defect in how engine identity is composed?**

## The contradiction (grounded)

`EngineIdentity` is `sha256(canonical(ratified_substrate))`, where
`ratified_substrate` is the five ratified personality packs **plus the code
revision** (`core/engine_identity.py:92-99`):

```python
substrate["code_revision"] = git_revision   # engine_identity.py:99
```

But the module's own docstring states the opposite contract
(`core/engine_identity.py:9-11`):

> "It is bumped only by a ratified change to the identity substrate … NOT by
> lived learning."

A git commit is not a ratified substrate change, yet it bumps the identity.

This collides head-on with **ADR-0157**, which already ruled that a revision
mismatch on load is a **non-fatal warning**, not control flow. That decision is
live in `engine_state/__init__.py:419-433` (`load_manifest` emits an ADR-0157
`RuntimeWarning` on `written_at_revision` mismatch and loads anyway —
*"reboot is recovery, not control flow"*). So the **same git revision** drives
two opposite policies:

| Field | Where | Same-rev change ⇒ |
|---|---|---|
| `written_at_revision` (provenance) | `engine_state/__init__.py:350` | **warn**, load anyway (ADR-0157) |
| `code_revision` (inside identity hash) | `engine_identity.py:99` | **hard raise** under strict (`runtime.py:790-804`) |

The provenance field and the identity input are **the same value from the same
source** — `get_git_revision()` (`engine_state/__init__.py:121-141`) — wearing
two contradictory hats.

### Verified facts (black-box, against `f5c6914d0083`)

- The divergence is **pure code-revision.** Recomputing
  `engine_identity_for_config(RuntimeConfig(), "c6d0e2a92004")` reproduces
  `75f3bb75…637a29fee` **byte-exactly**; with `"f5c6914d0083"` it is
  `b0f89456…8bd6`. All five ratified pack SHAs are identical across the two
  revisions (the default packs — `default_general_v1`, `core_safety_axes_v1`,
  `default_general_ethics_v1`, `default_neutral_v1`, `default_unanchored_v1` —
  have identical blob hashes at both commits). Nothing about *who the engine is*
  changed; only the build did.
- The guard works as designed: identity computed at init
  (`runtime.py:749-752`), compared to the stamped value
  (`runtime.py:787`); under `strict_identity_continuity` it **raises**
  `IdentityContinuityError`, otherwise it **warns and sets the queryable
  `identity_continuity_break` flag** (`runtime.py:790-804`). The always-on
  daemon forces strict (`chat/always_on_daemon.py:45-49`).

## Why this is a defect, not just naming

It is tempting to call this an optics/naming tension. It is sharper than that:

1. **It defeats the stated telos during normal development.** Because the daemon
   forces `strict_identity_continuity=True`, **every commit between daemon
   restarts** makes the engine refuse to resume the same life — directly
   contradicting both the "one continuous life" telos and the module's own
   "bumped only by a ratified change" contract. (The failure is *fail-closed and
   safe* — it refuses rather than silently forking — but the conservatism falls
   on exactly the wrong axis.)

2. **`code_revision` is simultaneously over- and under-sensitive as an identity
   input:**
   - **Over:** flips on every commit, even a docs-only or test-only commit that
     cannot change runtime behavior (proven above — packs byte-identical).
   - **Under:** `get_git_revision()` is **HEAD-only** — an uncommitted/dirty
     working tree does **not** change the revision. You can edit operator code
     and the daemon still believes it is the same life. It is also a **12-char
     short prefix** (`--short=12`, collision-possible vs. the full SHA), and it
     returns the literal string `"unknown"` when git is unavailable — collapsing
     *all* builds in a git-less environment to one shared identity.

   A signal that is both too sensitive (every commit) and too coarse
   (ignores uncommitted edits, truncates the SHA, degrades to a constant) is a
   poor input to a "who am I" hash.

## Decision drivers

- Preserve the L11 guarantee that **distinct ratified substrate ⇒ distinct
  identity** (identity is load-bearing and falsifiable).
- Keep the guard **fail-closed**: a genuinely unsafe resume must still be
  refused, not silently accepted.
- Stop a behavior-neutral code bump from forking the engine's identity.
- Do not weaken the L10 same-life proof surface or the lineage invariants.

## Options

**O1 — Status quo (block on any revision change).** Honest about "code may have
changed → don't resume," but contradicts ADR-0157 and the docstring, and makes
continuous-life development impractical. *Rejected as the resting state.*

**O2 — Demote code_revision to a warning everywhere (drop it from the identity
hash).** Identity = ratified packs only; build revision becomes provenance only,
exactly like `written_at_revision` already is under ADR-0157. Simple and
internally consistent. **Risk:** a code change that genuinely alters
serialization/semantics of lived state would then resume silently under the same
identity (mitigated by ADR-0219's schema versioning + ADR-0157's warning, but
worth stating explicitly).

**O3 — Split the hashes (recommended).**

```
identity_substrate_hash = sha256(ratified identity/safety/ethics/register/anchor_lens packs)   # "who am I"
build_provenance_hash   = code_revision (+ optionally a content hash of the runtime)            # "which build"
```

Then the resume policy becomes an **explicit, separately-governed** question
rather than an accident of putting `code_revision` inside identity:

```
same identity_substrate_hash + different build_provenance:
    → warn + stamp provenance, resume (default; matches ADR-0157)
    → OR require an explicit operator opt-in / migration / fork (strict)
```

**O4 — Migration/fork command.** Orthogonal to O1–O3: give the operator a
first-class way to carry a life across an intended identity change
(`engine-state fork`), instead of manual file surgery. Complements whichever of
O2/O3 is chosen.

## Proposed decision (pending ratification)

Adopt **O3 (split)** as the direction, with the **resume policy defaulting to
warn-and-resume (O2 semantics) and strict-mode requiring explicit operator
intent.** Sequence the work so the doctrine change lands *after* this decision is
accepted:

- **PR A — this brief.** No code.
- **PR B — safe operator ergonomics (no identity-semantics change).** Shippable
  immediately; see below.
- **PR C — identity/provenance semantics.** Only after A is accepted. Splits the
  hash, re-points the continuity guard at `identity_substrate_hash`, adds a
  `build_provenance` manifest field (or reuses `written_at_revision`), and
  updates the proof surface.

### Honesty note on the split

The split is **not a rename.** It is the load-bearing semantics change and
touches: the continuity guard (`runtime.py:787-804`), the manifest schema
(`engine_state/__init__.py:350-353`), the lineage tests
(`tests/test_engine_identity_lineage.py`, `tests/test_identity_continuity_proof.py`,
which key off the single `engine_identity` field and assert
`engine_identity == parent_engine_identity` for a stable life), and the L10 soak
runner (`evals/l10_always_on/runner.py:113`). PR C must keep the L11
"distinct packs ⇒ distinct identity" test green and add a test that a
behavior-neutral commit no longer breaks continuity. Note that
`build_provenance`-as-a-distinct-on-disk-field **already exists**
(`written_at_revision`); what does not yet exist is an
`identity_substrate_hash` computed *without* `code_revision`.

## PR B — safe operator ergonomics (no semantics change)

Two changes, shippable before the O3 decision, that would have prevented the
incident's confusion:

1. **`core always-on --engine-state PATH`.** A trivial wire-through:
   `run_daemon` already accepts `engine_state_path: Path | None`
   (`chat/always_on_daemon.py:132,152`); `cmd_always_on` simply never passes it
   (`core/cli.py:384-390`), so it falls back to `_DEFAULT_DIR`. One
   `add_argument` + one kwarg surfaces the existing per-state-root concept so an
   operator can run a per-branch dev life without touching the package dir.
   (Note: a `CORE_ENGINE_STATE_DIR` env var already does this
   — `engine_state/__init__.py:52-56` — so the flag is a second selection path
   to keep consistent, and `--no-load-state` already provides an *ephemeral*
   fresh start. The genuinely missing piece is a *persisted* fresh life under a
   new dir while preserving the old.)

2. **A humane `IdentityContinuityError` recovery message.** Today the handler
   (`core/cli.py:393-401`) states the mismatch but gives no recovery path.

   ⚠️ **Footgun to avoid (this corrects the originally-suggested message).** Do
   **not** tell the operator to `mv engine_state …` or `rm -rf engine_state`.
   When `CORE_ENGINE_STATE_DIR` is unset, the default engine-state directory
   **is** the git-tracked `engine_state/` **Python package**
   (`_DEFAULT_DIR = parents[1] / "engine_state"`; `engine_state/__init__.py` is
   the only tracked file there, runtime data is gitignored alongside it). Moving
   or deleting it removes `engine_state/__init__.py`, breaking
   `from engine_state import …` across ~20 files — including the very
   `core always-on` command the message tells the operator to re-run
   (`core/cli.py:341`).

   The correct recovery guidance:

   ```
   This checkpoint belongs to a different engine life (the ratified substrate
   or build revision changed since it was written).

   Options:
     1. Resume the old life — run the build that wrote it:
          git checkout <checkpoint_revision>   # e.g. c6d0e2a92004
          core always-on
     2. Start a fresh persisted life under a separate state dir
        (does NOT touch the old one):
          core always-on --engine-state ./engine_state_<name>
        (or: CORE_ENGINE_STATE_DIR=./engine_state_<name> core always-on)
     3. Start fresh in place — clear ONLY the runtime state, never the package:
        back up/remove the runtime files inside the engine-state dir
        (manifest.json, the current pointer + gen-*/ dirs, recognizers.jsonl,
        discovery_candidates.jsonl, session_state.json, proposals.jsonl),
        leaving engine_state/__init__.py intact.
   ```

   The message should print the actual `<checkpoint_revision>` from the stamped
   manifest so option 1 is copy-pasteable.

### "Start fresh in place" — clear the directory, not just the manifest

Removing only `manifest.json` is sufficient **only in the legacy flat layout**
(where `EngineStateStore.exists()` keys on `manifest.json`,
`engine_state/__init__.py:456`). In the **production ADR-0219 generation-dir
layout**, `exists()` keys on the `current` pointer, so a manifest-only removal
still leaves `exists()==True` and `load_recognizers()`/
`load_discovery_candidates()` ingest the prior life's derived state. Worse,
`proposals.jsonl` is loaded independent of the `exists()` gate
(`runtime.py:761-763`). A correct in-place fresh start clears **all** runtime
files listed above. (The incident's dir was flat and was fully cleared, so its
fresh start is clean.)

## What this ADR does **not** change

- It does not modify `core/engine_identity.py`, the guard, or the manifest
  schema. PR B touches only the CLI surface (flag + message). PR C is gated on
  acceptance of O3.
- It does not weaken `strict_identity_continuity`; it proposes re-pointing what
  identity *means* so strictness lands on substrate, not build.

## Corrected non-issues (so reviewers don't chase them)

- **The stale `always_on.lock` is not a hazard.** The single-instance lock is an
  advisory `fcntl.flock` the kernel releases on process death; the lock *file* is
  intentionally never unlinked (`chat/always_on_daemon.py:55-64`). A dead
  holder's marker does not block a new daemon.
- **`engine_state/` is not scanned by the architectural-invariant suite** —
  there is no INV risk from runtime files living beside the package.

## Evidence appendix

```
# pure-code-revision proof (RuntimeConfig defaults, packs byte-identical):
engine_identity_for_config(RuntimeConfig(), "c6d0e2a92004") == 75f3bb75…637a29fee   # stamped, old life
engine_identity_for_config(RuntimeConfig(), "f5c6914d0083") == b0f89456…8bd6        # current build
git diff --stat c6d0e2a92004 f5c6914d0083 -- packs/{identity,safety,ethics,register,anchor_lens}  == (empty)

# the two-hats-on-one-value relationship:
get_git_revision()  ──▶ code_revision  (hashed into engine_identity)   engine_identity.py:99   → strict raise
                    └─▶ written_at_revision (provenance, unhashed)      __init__.py:350         → ADR-0157 warn
```
