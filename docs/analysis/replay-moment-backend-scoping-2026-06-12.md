# Replay Moment Backend — Scoping (Wave R3, `GET /replay/{turn_id}`)

Date: 2026-06-12
Plan: `docs/workbench/wave-R-mastery-revamp.md` § Wave R3 (first item).
Status: implemented — with one design correction recorded below.

## Amendment (implementation PR, same day)

The "sealed genesis-prefix replay" decision below was **wrong** and was
corrected before any code shipped.  This doc was written before reading the
chat handler; implementation began by reading it, which surfaced the
decisive fact: `workbench/api.py::_run_chat_turn` constructs a **fresh
`ChatRuntime()` per turn**.  The journaled turns were never one continuous
session, so feeding prompts `1..N` through a single runtime would
accumulate session state the original turns never had — prefix replay
would manufacture spurious divergence by construction.

What shipped instead: **sealed fresh-runtime single-turn replay**
(`comparison_basis: "sealed_fresh_runtime_single_turn"`), which matches
the original per-turn execution shape and is O(1) instead of O(N).  The
honesty consequence is unchanged in kind but renamed: the unknown is not
prefix completeness but whether the original turn's fresh runtime loaded
an engine-state checkpoint present at the time (`origin_state:
"unrecorded"` — the journal does not record it).  `refused:
prefix_too_long` is obsolete (no prefix); the contract section in
`docs/workbench/api-contract-v1.md` § Replay is authoritative for the
shipped shape.  The five proof obligations below survive, re-aimed at the
single-turn model, and all execute in `tests/test_workbench_replay.py`.

The original analysis is preserved unedited below as the decision record.

## What exists today

- `workbench/api.py:257` — `GET /replay/...` returns 501 (`deferred beyond
  W-026`).
- `workbench/schemas.py` — `ReplayComparison` / `ReplayDivergence` already
  exist (W-026 vintage, keyed by `artifact_id`).
- `docs/workbench/api-contract-v1.md` § Replay — standing honesty rule:
  the API must not claim `"equivalent": true` unless a real replay/compare
  path ran; digest-to-itself comparison is not replay evidence.
- `workbench/journal.py` — entries carry the full `prompt` plus the full
  recorded envelope (`surface`, `articulation_surface`, `walk_surface`,
  `trace_hash`, `verdicts`, `epistemic_state`, …), monotonic `turn_id`.

## The constraint that shapes the design

A turn's output depends on the lived engine state at that turn.  The engine
keeps ONE rolling checkpoint, written **after** turns (`chat/runtime.py::
checkpoint_engine_state`) — there is no per-turn checkpoint history, so the
pre-turn state of an arbitrary historical turn is **not recoverable** from
checkpoints.

And the journal is **not a provably complete input history**: it is appended
only by the workbench chat handler (`workbench/api.py:390`).  Turns via
`core chat` CLI, `idle_tick` learning, teaching ratifications, and
checkpoint-restored prior state all advance the engine without journal
entries.

## Decided v1 semantics: sealed genesis-prefix replay

`GET /replay/{turn_id}` re-runs journal entries `1..N` (prompts only, in
order) in a **sealed transient runtime** — fresh genesis state, current
default identity/pack configuration, `persist_session_state=False`, no
journal appends, no checkpoint writes — and compares the resulting envelope
at turn N against the recorded entry, leaf by leaf.

The claim this demonstrates is exactly the architectural one: **same input
sequence → bit-identical envelope** (determinism), NOT "the live engine's
full history is captured here."  The response must carry that envelope
explicitly:

- `comparison_basis: "genesis_prefix_replay"` — names the method;
- `history_complete: "unknown"` — the journal cannot prove the original
  turns ran from genesis with no interleaved non-journaled inputs (no
  per-entry config/lineage fields exist today);
- divergences therefore mean *either* nondeterminism *or* unjournaled
  state influence — the UI honesty card states both, and the frontend
  never renders a divergent replay as a determinism failure verdict.

Rejected alternatives (record for the ADR/PR):

- **Checkpoint-restore replay** — unimplementable for historical turns
  (no per-turn checkpoints); sound only for "the next turn", which is not
  yet a journaled subject.
- **Replay against current live state** — compares different states;
  dishonest as "replay".
- **Claiming completeness** — would violate the contract's honesty rule;
  completeness becomes provable only via an additive journal field
  (genesis marker + config digest), which is a sanctioned follow-up,
  same pattern as the `versor_condition` journal note in the plan.

## Response shape (supersedes the W-026 `artifact_id` placeholder)

`ReplayComparison` is re-keyed to `turn_id` (the W-026 placeholder was
never wired; `artifact_id` had no consumer).  Fields: `turn_id`,
`comparison_basis`, `history_complete`, `original_hash` / `replay_hash`
(trace hashes), `equivalent` (true only on zero critical divergences),
`divergences: list[ReplayDivergence]`, `replayed_prefix_length`.

Leaf comparison over the recorded entry vs the re-run envelope, with
severity classes:

- **critical** — `trace_hash`, `surface`, `articulation_surface`,
  `walk_surface`, `verdicts`, `epistemic_state`, `grounding_source`,
  `refusal_emitted`, `hedge_injected`, `proposal_candidates`;
- **informational** — wall-clock fields (`timestamp`, `turn_cost_ms`) and
  `journal_digest` (recomputed over different timestamps by construction);
  never affect `equivalent`.

Refusal vocabulary (typed, fail-closed — never a 500, never a fabricated
comparison): `refused:turn_not_found`, `refused:prefix_too_long` (bound
N at a documented cap; replay cost is O(N) turns), `refused:runtime_error`
(replay runtime failed to construct — reason echoed, no comparison
claimed).

## Trust boundary

Journaled prompts are user-controlled text re-entering the runtime: the
replay runtime is constructed sealed (transient, no persistence, no
teaching ratification, no pack mutation — proposal-only paths stay
proposal-only), and the endpoint is GET/read-only.  No new write surface.

## Proof obligations (MEANINGFULLY-FAILS tests, per CLAUDE.md schema rule)

1. Mutating one recorded prompt in a fixture journal flips `equivalent`
   to false with a critical divergence at the right leaf path.
2. Mutating one recorded envelope leaf (e.g. `surface`) does the same —
   the comparison reads the RECORDED entry, not a re-derivation.
3. A digest-to-itself shortcut (no re-execution) cannot pass: test asserts
   the replay runtime actually ran N turns (e.g. via prefix-length
   evidence on the response).
4. Replay leaves no trace: journal byte-identical, no checkpoint written,
   `engine_state/` untouched (asserted on disk).
5. Wall-clock fields differing does NOT break equivalence.

## Same-PR documentation obligations

- Amend `docs/workbench/api-contract-v1.md` § Replay (turn-keyed shape,
  honesty fields, refusal vocabulary).
- The frontend Replay Moment (separate R3 PR) renders `comparison_basis`
  and `history_complete` on the honesty card; hash-to-hash equality is the
  hero only when `equivalent` is true.
