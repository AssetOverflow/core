# L10 Always-On Heartbeat Soak — Contract

**Status:** soak (falsifiable long-horizon gate) · **Not in default smoke** (run on demand / nightly).

The continuity lane (`evals/l10_continuity`) soaks the **turn loop**. This lane soaks the
**idle heartbeat** (`chat/always_on.run_continuous` — the loop the `core always-on` daemon
drives). It seeds a real continuous life (a held self + a cognitive turn to excite the
field), then runs the engine over N beats with **no user turn**, and evaluates falsifiable
predicates over the per-beat evidence. It converts the claim *"the always-on process is
built"* into *"the always-on process holds over uptime"* — the idle-path claims that the
short daemon unit tests (≤5 beats) and the turn-loop soak (disjoint from `run_continuous`)
do **not** prove at horizon.

Run: `PYTHONPATH=. .venv/bin/python -m evals.l10_always_on [n_beats] [reboot_beat]`
(pass a large `n_beats` — e.g. `100000` — for a true long-horizon soak; default `24`).

## Predicates

| ID | Proves | Fails loudly when | Mutation-verified bite |
|----|--------|-------------------|------------------------|
| **H1** closure | every OBSERVED idle beat has `versor_condition < 1e-6` (closure holds over idle uptime, READ never repaired) | the idle heartbeat drifts/corrupts the field, or the field never existed (vacuous) | a beat with `versor_condition ≥ 1e-6`; an all-`None` (no-field) soak |
| **H2** bounded idle | a `did_work=False` beat adds NOTHING to the vault (no idle resource leak) | a converged idle life keeps growing a store — invisible at 5 beats, fatal at 100k | an idle beat whose `vault_size` grew over the prior beat |
| **H3** convergence | a saturated idle life SETTLES and stays settled (no re-awakening), at rest at the end, closure intact on the tail | the life churns forever, thrashes (work-after-rest), or breaks closure once settled | a never-settling run; a rest→work re-awakening |
| **H4** reboot resume | a reboot mid-soak resumes the SAME life (strict identity guard passes, pre-reboot DERIVED learning survives, post-reboot closure holds) | a reboot forks a new life, loses learning, or breaks closure | `resumed_cleanly=False`; `learned_fact_survived=False` |

Each predicate has a `*_holds` test (real soak) **and** a `*_bites` test (mutation), per the
CLAUDE.md schema-as-proof discipline: a predicate that cannot fail under the violation it
nominally catches is decoration, not proof.

## The measured result

On a 5000-beat soak (reboot at 2500): **all gates pass.** `versor_condition` is flat at
`1.389e-07` across all 5000 beats (no drift — the idle heartbeat never perturbs the field,
no repair), the vault stays bounded at 6 entries (no idle leak), the life converges at
beat 1 and the 4999-beat tail stays at rest with closure intact, and the reboot at 2500
resumes the same life with its derived learning intact. This is the empirical resolution of
the L10 riskiest-unknown **for the idle path** (the closure-by-construction ruling covered
the field-transition walk; this covers indefinite idle uptime).

## Not covered (no silent skips)

- **H5 — learning-life resource cost.** This lane proves the **idle (converged)** life is
  resource-bounded. The cost of a continuously-**learning** life under a sustained
  new-fact stream — the full-snapshot checkpoint is O(n²) in facts, `lived_life.json` is
  per-run — is out of scope until an afferent/intake feed and incremental persistence
  exist. Recorded as `not_covered` in the report; a follow-up.

The `deterministic_digest` in the report freezes the per-beat shape (`did_work` /
`field_valid` / learning counts / vault size — all deterministic) + the verdicts, excluding
the machine-variant raw `versor_condition` float. Pin it once the lane is trusted so a
regression flips it.
