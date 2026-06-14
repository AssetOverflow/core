# CORE Workbench — Evaluator Quickstart

For a technical evaluator with ~10 minutes who wants to *test the claims*, not
read the pitch. CORE is a deterministic cognitive engine; the Workbench is its
audit-native UI. The thesis you're here to check: **this engine refuses rather
than guesses wrong, replays bit-for-bit, and its geometry can't fake coherence.**

This document is written to be **falsifiable** — every claim below points at a
surface you can poke or a file you can read. Verify, don't trust.

## Run it (one command)

```bash
scripts/workbench            # preflight → install → start API + UI, health-gated
```

Prereqs (the preflight checks them and prints the exact fix if missing):
[`uv`](https://docs.astral.sh/uv/), Node ≥ 20, `pnpm` (`corepack enable pnpm`).
**No Rust build required** — the backend runs on the pure-Python numpy backend.
It prints one URL (**http://127.0.0.1:5173**); `Ctrl+C` stops both servers.
Everything binds to localhost only; the UI is read-only by construction.

## The 10-minute path

Each stop says what it proves — and what it does **not**.

1. **`/tour` — the determinism narrative.** A provider-agnostic, ordered walk:
   the engine *decides* a claim, *refuses* a wrong one, and *replays* it to the
   same hash. Each card pulls its "what this proves / does not prove" text from
   the real demo spec — not marketing copy.
   *Proves:* the spine is honest by construction. *Not:* general capability.

2. **`/trace` + Replay.** Pick a turn; read its pipeline stages, grounding,
   epistemic state, and trace hash. Hit **Replay** — it re-executes in a sealed
   fresh runtime and shows **hash == hash**.
   *Proves:* determinism is real and verifiable, not asserted. *Not:* that the
   answer is *correct* — only that it's *reproducible*.

3. **`/evals` — the `wrong=0` ledger.** The serving discipline made constant:
   N correct · N refused · **0 wrong**. The zero is load-bearing.
   *Proves:* the engine declines rather than emits an unverified answer.
   *Not:* high coverage — refusal rate is high *on purpose* (see scope below).

4. **`/calibration` — the gold-tether arena.** Per class: coverage vs the
   one-sided Wilson floor, the θ ceiling, and a plain "earned PROPOSE / SERVE /
   neither" verdict. This is *where the engine earns the right to guess*.
   *Proves:* "guessing" is gated by a calibrated statistical floor, not vibes.

5. **`/logos` — Alignment tab (the geometry).** The tri-language resonance graph
   (Hebrew → Greek → English). Open `grc_logos_cognition_v1`: the Safety tab and
   edge list flag **invalid alignment targets**. That is **not a bug** — the tool
   is honestly surfacing a real, latent cross-pack data inconsistency that a
   less-honest UI would have hidden. The geometry telling the truth, live.
   *Proves:* the audit surface exposes its own substrate's gaps. *Not:* that the
   field is "reasoning" — see scope.

## Honest scope (read before you judge capability)

CORE is deliberately narrow and says so. The Workbench is built to *prevent*
overclaiming — let it.

- **Verified flagship: propositional entailment.** The strongest *proven*
  capability is sound + complete deductive entailment, checked against an
  **independent** decision procedure. Read `CLAIMS.md` and the deductive-logic
  eval lane for the exact, pinned numbers — don't take a README's word.
- **GSM8K math is a *diagnostic*, not the headline.** The serving reader refuses
  most problems rather than risk a wrong answer; that's the `wrong=0` discipline,
  not a capability flex.
- **The CL(4,1) field is a coherence-gate, not the reasoner.** It localizes and
  coherence-gates, then hands off to symbolic structure. Anyone pitching it as
  "geometric reasoning" is overreaching; it is geometric *coherence-checking*.
- **Holonomy proof cards are roadmap.** The `/logos` Holonomy state reads
  `missing_evidence` by design — the tri-language "meaning survived the path"
  proof is authored but not yet computed end-to-end. It is honestly absent, not
  faked.

## Verify, don't trust

- **Determinism:** Replay any turn; the trace hash must match. Re-run
  `scripts/workbench` — same inputs, same hashes.
- **`wrong=0` is gated, not hoped:** `scripts/verify_lane_shas.py` pins the
  eval-lane SHAs; `scripts/generate_claims.py --check` guards `CLAIMS.md`.
- **No hidden mutation:** the UI is read-only (`proposal mode: none — read-only`
  in every footer); the only write paths are explicit, allowlisted, and
  human-ratified (`/proposals`).
- **The architecture's invariants are tested:** `tests/test_architectural_invariants.py`
  and the field invariant (`versor_condition < 1e-6`) fail loudly when violated.

## Where to go deeper

- `docs/workbench/` — design system, route map, mastery roadmap.
- `CLAUDE.md` — the engine's non-negotiable invariants and doctrine.
- `docs/runtime_contracts.md` — response/telemetry/identity/replay contracts.
