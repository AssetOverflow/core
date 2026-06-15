# L10 Continuity Lane — Contract

**Status:** spike (falsifiable experiment) · **Parent:** `docs/analysis/L10-continuity-spike-design-2026-06-05.md` · **Not in default smoke** (a soak; run on demand / nightly).

This lane drives the **real** turn loop (`ChatRuntime` + `CognitiveTurnPipeline`)
over a deterministic, cyclic, in-vocabulary corpus for N turns, with optional
reboot and orphan-crash legs, and evaluates falsifiable predicates over the
recorded evidence. It is the empirical gate between the two L10 targets:

- **T-resume** — provable same-life *resume* (determinism + recovery): P1–P4.
- **T-experience** — a continuous *experiencing* field-life (content stays
  meaningful over a long horizon): P5.

Run: `PYTHONPATH=. .venv/bin/python -m evals.l10_continuity [n_turns] [reboot_turn]`

## Predicates

| ID | Proves | Fails loudly when | Mutation-verified bite |
|----|--------|-------------------|------------------------|
| **P1** closure | `versor_condition < 1e-6` every turn | a construction breaks closure (no repair allowed) | a record with `versor_condition ≥ 1e-6` trips it |
| **P2a** determinism | two independent runtimes → byte-identical `trace_hash` sequence | the pipeline is nondeterministic | a perturbed hash trips it |
| **P2b** reboot transparency | a reboot never changes turns *before* the reboot point | determinism/state leaks backward across reboot | a pre-reboot hash divergence trips it |
| **P3** bounded resources | vault grows linear-bounded/monotonic per turn | an unbounded cache/store leaks | a 10k-entry vault record trips it |
| **P4** recovery determinism | two crash-recoveries from one checkpoint converge | torn read / nondeterministic boot | divergent recovery tails trip it |
| **P4** commit point | recovered `turn_count` == committed turns (ARIES force boundary) | the checkpoint isn't the atomic commit boundary | `None`/mismatched count trips it |
| **P5a** recall precision | vault recall finds each probe entry at rank ≤ top_k, **including after a reboot** (float32 round-trip preserves `_exact_index`) | the serialisation round-trip loses precision, breaking exact-match after reboot | a `ProbeRecord` with `rank=None` or no cross-reboot probe trips it |
| **P5b** anchor stability | field anchors without **collapse** (`dist_to_anchor`↛0) or **freeze** (`turn_movement`↛0) | the field is swallowed by the attractor, or frozen | collapsing distance / zero movement trips it |
| **P5c** coherence | surfaces stay non-empty and not collapsed to one repeated output | the field wanders into noise or freezes onto one output | empty / single-surface records trip it |

Each predicate has a `*_holds` test (real soak) **and** a `*_bites` test
(mutation), per the CLAUDE.md schema-as-proof discipline: a predicate that cannot
fail under the violation it nominally catches is decoration, not proof.

## Not covered (no silent skips)

All spec predicates P1–P5c are now covered. `NOT_COVERED` is empty.

### P5a scope note — reprojection boundary

The probe is verified within two turns after the reboot, intentionally before
the vault's `null_project` auto-reproject cycle (`vault_reproject_interval=20`
stores). After reprojection, `null_project(v)` produces versors CGA-orthogonal
to the original (all inner-product scores drop to 0.0), making both exact-match
(`_exact_index`) and CGA-ranked recall useless. This is a real finding about
the vault's long-horizon recall stability, recorded here rather than silently
avoided. A dedicated follow-up increment should ratify a decision: either raise
the reproject interval for session vaults, preserve the pre-reproject versor as
a secondary recall key, or accept that long-horizon recall is intentionally
coarse.

## The headline result (P2b) — resume-as-same-life

A reboot is now **fully transparent**: `post_reboot_transparent == True`,
`first_divergence is None`. With Shape B+ persistence wired
(`SessionContext.snapshot/restore` → engine_state schema v2), the lived field /
vault / anchor / graph / referents / dialogue survive a reboot, so
`[run K → reboot → run M]` is byte-identical to the uninterrupted `[run K+M]`.
`test_p2b_reboot_is_transparent` is the load-bearing guard.

This **flipped** from the original Shape B (ADR-0146) behavior, where only
recognizers / discovery candidates / `turn_count` survived and the lived
field/vault were discarded — `post_reboot_transparent == False`, divergence at
the first post-reboot turn ("many lives sharing a checkpoint"). The spike
measured that gap, defined the persistence work, and now confirms it closed.

## Thresholds (empirical basis, not arbitrary)

All gating thresholds are set from measured real-soak data and deliberately
conservative — these are **catastrophe gates** (collapse / freeze / unbounded
leak are yes/no failures of the T-experience claim), not early-warning trend
detectors. Gradual-drift detection is a deliberate long-horizon follow-up;
tightening toward the healthy band would risk false positives on a different
corpus or longer horizon.

| Threshold | Measured healthy | Default floor/ceiling | Rationale |
|-----------|------------------|-----------------------|-----------|
| P5b `dist_to_anchor` | ~4.0–6.2 (steady) | `collapse_floor=1.0` | ~75%+ drop toward anchor = pathological collapse |
| P5b `turn_movement` | median ~1.5 | `freeze_floor=0.05` | ~1/30th of healthy = frozen field |
| P3 vault growth | ~2–3 entries/turn | `vault_per_turn_ceiling=4` | ~130–200% of as-designed writes |

**P5b vs P5c division of labour:** P5b catches the field *freezing* (movement→0)
or *collapsing onto the anchor* (distance→0); P5c catches the *output* collapsing
to a single repeated surface. The P5c real-soak test runs **over more than one
corpus cycle** so the horizon exercises repetition (a 6-turn run == the cycle
length would trivially yield 6 distinct surfaces and prove nothing).

## Freeze handle

`report.deterministic_digest` is a SHA-256 over only hardware-stable evidence
(the `trace_hash` sequence + each predicate's `(name, passed)` verdict),
excluding RSS / wall-clock / raw floats. Pin it once the lane is trusted; a
regression flips it.
