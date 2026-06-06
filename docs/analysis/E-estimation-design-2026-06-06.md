# Step E — ESTIMATION: calibrated, disclosed estimation via the ADR-0206 reach bridge

**Date:** 2026-06-06
**Branch:** `feat/learned-estimation`
**Sequence:** A INSTRUMENT → B WIRE → C DEEPEN → D CLOSE → **E ESTIMATION** (last)
**Executes:** ADR-0206 §5 (cognition-path widening) — the `LICENSE` node ("built — not yet called from serving") finally called from serving.

## What E is (and is not)

E lets the engine **commit a disclosed estimate** for a class it has *measured itself
reliable on*, instead of always refusing past proof. It is **not** generic guessing,
not a probabilistic model, and it does **not** touch the sealed GSM8K serving metric
(that is a separate, riskier ADR-0206 §5 PR — `select_self_verified`).

The whole step is one wire: `govern_response` consults `reliability_gate.license_for(…,
Action.SERVE)`; a licensed class reaches `ReachLevel.APPROXIMATE`; `shape_surface`
**discloses** the estimate with an `[approximate]` prefix.

## Why it is wrong=0-safe by construction

`shape_surface(APPROXIMATE)` never commits an estimate silently — it prefixes
`[approximate]`. So an estimate that is wrong is a **disclosed**-wrong, categorically
different from the silent/asserted wrong the `wrong=0` invariant forbids. The reliability
gate (θ_SERVE=0.99 on a committed `ClassTally`) governs *when* the disclosed estimate is
even offered. Two independent guards: disclosure (honesty) + license (calibration).

## The estimator — a blind converse-guesser

Given a realized `p(a, b)` and a query `p(b, a)`, the estimator commits the **converse**
as a candidate. It is **blind** — it never reads the pack's symmetry metadata. Therefore:

- on a **symmetric** predicate (`sibling_of`, `spouse_of`, `equal_to`, `distinct_from`,
  `adjacent_to`, `overlaps_event` — `graph.edge.symmetric`) the converse is **true**;
- on a **directed** predicate (`parent_of`, `less_than`, `before_event`, … —
  `graph.edge.directed`) the converse is **false**.

The engine does not *know* which is which. It **measures** its converse-guess precision
per predicate-class over a gold lane and earns a SERVE license only where the measured
floor clears θ. That is calibrated learning (ADR-0175): reliability is commitment
precision, earned by volume. The symmetry metadata is the **gold** (the `GoldTether`'s
truth), never a serving-time shortcut.

## The committed ledger (real, sealed, HITL-ratified)

- `evals/determination_estimation/gold.py` deterministically generates the gold cases:
  657+ symmetric converse cases for the licensed class (gold=true) and a directed class
  (gold=false). 657 is the Wilson volume floor: a perfect record clears θ_SERVE=0.99 at
  `n/(n+z²) ≥ 0.99`, `z=2.576` ⇒ `n ≥ 657`. Reliability is earned by volume, never a
  lucky streak — so the gold lane is sized to that bar, not the bar to the lane.
- `core.learning_arena.run_practice` folds a `DomainSolver` (the converse-guesser) +
  `GoldTether` (symmetry-as-truth) over the cases → `dict[str, ClassTally]`.
- The resulting ledger (per-class committed counts) is frozen as a **ratified artifact**
  (`evals/determination_estimation/ratified_ledger.json`) with an expected-hash. Committing
  it via a reviewed PR **is** the HITL ratification. Ceilings stay at safe defaults
  (θ_SERVE=0.99) — no override, so the engine never raises its own bar (invariant #4).

## The wire (E-3, the delicate part)

In `chat/runtime.py`, gated by a new config flag (default OFF): when a turn is a
**converse query** (`p(b,a)` asked, `p(a,b)` realized, `p(b,a)` not directly
determinable) whose predicate-class holds a committed `license_for(SERVE).licensed`,
pass that real `LicenseDecision` into `govern_response` → it emits `APPROXIMATE` →
`shape_surface` discloses the converse estimate as `[approximate] …`. Every other turn,
and every unlicensed class, stays `STRICT` (byte-identical, wrong=0 untouched). Never a
designed-in default: absent a cleared committed tally, refuse.

## Falsification — `evals/determination_estimation`

A frozen replay asserts:
- **Discriminating gate:** the symmetric class is SERVE-licensed; the directed class is
  not (its converse-guess reliability is ~0 over the committed lane).
- **Disclosed estimate:** a licensed converse query yields an `[approximate]`-prefixed
  surface; an unlicensed one stays STRICT-refuse, byte-identical to pre-E.
- **No silent estimate:** every reach > STRICT carries the disclosure prefix.
- **wrong=0 (silent):** zero silently-committed wrong answers — every estimate is disclosed.
- **Volume floor:** below 657 committed the symmetric class is NOT licensed (the bar binds).
- **Determinism:** the ledger + verdicts reproduce byte-identically (frozen expected hash).

## Out of scope (separate PRs)
- The **math-serving seam** (`select_self_verified`) — ADR-0206 §5, touches the sealed metric.
- **SITUATE** (stakes/gravity) and the live **FEED-BACK** loop (serving outcome → ledger) —
  ADR-0206 §1 "designed, not built". E uses an offline, sealed, ratified ledger.
- `EXTRAPOLATE` / `CREATIVE` reach levels (need `VERIFIED` / novelty capabilities).
