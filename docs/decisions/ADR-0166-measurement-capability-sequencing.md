# ADR-0166 — Measurement-Capability Sequencing Discipline

**Status:** Proposed
**Date:** 2026-05-27
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Companions:** [ADR-0114a — Anti-overfitting proof obligations](./ADR-0114a-anti-overfitting-proof-obligations.md), [ADR-0165 — Regex Scope Rule](./ADR-0165-regex-scope-rule.md), [ADR-0164 — Incremental Comprehension Reader](./ADR-0164-incremental-comprehension-reader.md)

---

## Context — why the order matters

CORE accrues two distinct kinds of artifact over time:

1. **Capability artifacts** — the operators, recognizers, registries, and
   composition rules that make the engine *able to* admit a class of
   problems (e.g. the comprehension reader, the binding-graph
   admissibility check, the deterministic solver).

2. **Measurement artifacts** — the eval lanes, runners, scoring rules,
   and baselines that quantify *whether* the engine handles a class of
   problems (e.g. `evals/gsm8k_math/`, `evals/cross_domain_transfer/`,
   the capability-axis lanes G1–G5).

Both are load-bearing. Both must exist for an honest claim of capability
to be made. But they only produce signal when they are sequenced
correctly: a measurement artifact that runs against a non-existent
capability produces refusals — and refusals at 100% generate noise, not
data.

The session that produced this ADR identified a concrete instance:
a strategic plan proposed authoring `spatial_geometry_ood`,
`historical_sequence_ood`, and other new eval lanes ahead of the
operators that those lanes would test. The recommended "single most
impactful next commit" was to populate the Tier 3 TBD rows by running
existing lanes — a step that is legitimate but is in fact a snapshot,
not advancement. Meanwhile the engine's actual capability bottleneck
(`gsm8k_math` train_sample at 3/47/0) was treated as adjacent rather
than as the gating concern.

That kind of sequencing inversion is what this ADR prevents. It is in
the same family of structural invariants as the field-state versor
condition (CLAUDE.md §"Non-Negotiable Field Invariant"), ADR-0165's
regex scope rule, and ADR-0114a's anti-overfitting obligations: a
typed boundary the project enforces by convention, not a guideline.

---

## Rule

> **Capability lands before the measurement that depends on it.**
> An eval lane may only be authored when the operators it probes exist
> on main and at least one case admits end-to-end through those
> operators. An OOD lane for a domain may only be authored when the
> in-domain capability it probes has a non-trivial baseline.
>
> An existing TBD measurement row may be populated at any time by
> running the lane; this is a snapshot of current capability and is
> permitted independently. But "populating TBD rows" is **not** a
> substitute for the capability work that would make those numbers
> rise.
>
> Expanding the eval surface ahead of the capability that produces
> signal on it is rejected at PR review.

---

## Three-question test (apply to every new eval lane PR)

When reviewing or proposing a new eval lane, answer three questions:

1. **Does the capability this lane probes exist on main today?**
   Name the modules. If you cannot point to specific code that
   implements the operator, recognizer, or composition rule the lane
   would exercise, the lane is being authored ahead of its capability.

2. **Has at least one case admitted end-to-end through that
   capability?** "Admitted" means produced a non-refused output that
   passed admissibility. A lane whose every case will predictably
   refuse generates no signal — it just stamps the same refusal mode
   N times.

3. **Will running this lane distinguish capability-presence from
   capability-absence?** A lane that returns 0/N at capability=absent
   and 0/N at capability=partial is not measuring; it is decorating
   the data debt.

A lane that fails any of these three is being authored ahead of its
capability and must wait. The waiting period is not arbitrary: it
ends when the answers shift to (1) yes, (2) yes, (3) yes — at which
point the lane lands and immediately produces signal.

---

## Legitimate work (capability-before-lane)

These are the canonical examples of correct sequencing.

| Sequence | Example |
|---|---|
| Operator lands → lane authored that probes it → measure | ADR-0118 stepped realizer landed → `evals/articulation_of_status` authored → real metrics emerged |
| Reader landed → coexistence wiring → measurement lane updated to use it | ADR-0164 Phase 1 reader landed → coexistence wiring (#331) → `reader_phase1_delta.json` produced |
| Solver landed → capability axis lane → byte-stable baseline | ADR-0116 deterministic solver → capability-axis lanes G1–G5, S1 each at 100% on controlled cases |
| Pack landed → pack-test landed → enum-coverage gate | `en_core_math_v1` (#322) → `tests/test_en_core_math_v1_pack.py` → manifest-checksum + lemma-count regression net |

In each case, the measurement artifact was authored *after* there was
something for it to measure, and produced signal the moment it ran.

## Forbidden work (lane-before-capability)

These are the patterns this ADR rejects.

```
# FORBIDDEN — authoring an OOD lane without the operator:

mkdir evals/spatial_geometry_ood
# But CGA-field → spatial-inference operators do not exist.
# Every case will refuse. The lane will register 0/N pass for
# however long the operators take to land, generating no signal
# in the interim.
```

```
# FORBIDDEN — authoring an external benchmark integration without
# the prerequisite capability:

mkdir evals/arc_easy
# But the comprehension reader is currently math-specific in its
# composition rules. ARC reasoning prose requires narrative-frame
# composition rules that do not exist. The lane will refuse on
# every case until that capability lands.
```

```
# FORBIDDEN — adding TBD rows to the Tier 3 table as if they were
# work:

# tier3:
#   multi_step_reasoning:   TBD
#   symbolic_logic:         TBD
#   cross_domain_transfer:  TBD
#   spatial_geometry_ood:   TBD   <-- new row, capability missing
```

```
# FORBIDDEN — substituting measurement work for capability work:

# "The most impactful next commit is to run all Tier 3 lanes and fill
#  the TBD rows."
#
# Wrong, when GSM8K-math is at 3/47/0 and the reader scope that
# would lift it has not landed. The numbers Tier 3 would produce
# are dominated by the unbuilt-reader noise floor. Populate the
# rows AFTER the reader work clears the floor, not before.
```

---

## Population — how the eval surface grows

The closed sequencing rule is not static; it advances as capability
advances. New lanes enter the surface through a specific pathway:

1. **A capability commits to main.** Operator / recognizer /
   composition rule lands with tests and a non-trivial admission case.

2. **The contemplation corridor (ADR-0150 / 0152 / 0155 / 0161)
   identifies measurement gaps the new capability now makes
   testable.** This is the same corridor that grows the lexicon and
   the primitive registry under ADR-0164 / 0165 — but it now also
   surfaces "this capability admits but has no lane that measures it"
   as a proposal type.

3. **A new lane is authored.** Its first run produces real numbers
   (not zeros), satisfying the three-question test from the moment
   of landing.

4. **The lane is added to the Tier 3 table or domain ledger as a
   real row** with a real baseline — never as TBD.

A TBD row exists *only* for lanes that were already authored under a
prior capability and have not been re-run since. TBD is a re-run
debt, not a placeholder for unbuilt lanes.

---

## Consequences

### Positive

1. **Signal-to-noise ratio of the eval surface stays high.** Every
   lane that exists produces interpretable numbers. The number of
   lanes that consistently report 0/N is bounded.
2. **Strategic prioritization becomes legible.** When someone proposes
   "what should we do next?" the answer is constrained by current
   capability rather than by aspirational lane authoring. The order
   "Brief 10 (Phase 2 reader) before any new OOD lane" is mechanical
   under this rule.
3. **Data debt has a fixed retirement path.** Run the lane → number
   appears → no debt. There's no slow accrual of zeros that hides
   whether progress is real.
4. **The eval surface stays a *measurement* of CORE rather than a
   *wishlist* for CORE.**

### Negative / tradeoffs

1. **Some lane authoring is deferred that an enthusiastic operator
   might want to do "for completeness."** This is intentional; the
   completeness gain is illusory if the lanes refuse uniformly.
2. **The rule requires PR reviewers to verify the three-question test
   — slight review overhead per new-lane PR.** The test is fast (one
   grep + one trial run).
3. **A new operator and a new lane cannot land in the same PR**
   unless the operator's admission case is demonstrated *first*,
   before the lane is added. (Allowed: operator + admission test in
   PR N, lane in PR N+1. Forbidden: operator + lane in same PR with
   no demonstrated admission.)

---

## Boundaries — what this ADR does **not** say

1. **It does not forbid measurement.** Running existing lanes to
   snapshot current numbers is always permitted and often
   diagnostically valuable. The ADR governs *authoring*, not
   *running*.

2. **It does not require all lanes to pass at 100%.** A lane that
   reports e.g. `correct=3 refused=47 wrong=0` is producing signal —
   the refusals are themselves interpretable when wrong=0 is intact.
   The ADR's "0/N pattern" forbidding refers to lanes that refuse
   uniformly because their capability is wholly absent.

3. **It does not constrain experimental probes.** A throwaway
   measurement script under `scratch/` or `evals/_lab/` exploring
   whether a capability would admit a class of input is fine. The
   constraint applies to lanes that enter the canonical Tier 3 /
   domain-ledger / capability-axis surfaces.

4. **It does not specify ordering among capabilities.** Whether to
   build Phase 2 statement reader before geometric-inference
   operators is a separate strategic decision (see
   `SESSION-2026-05-27-tier3-sequencing.md`). The ADR only says: in
   whichever order capability is built, the lane that measures it
   follows, not leads.

5. **It does not constrain the contemplation corridor.** The
   corridor's proposals (lexicon entries, primitives, recognizer
   candidates) are not eval lanes; they ride a separate pathway
   under ADR-0057 / 0150 / 0152 / 0161.

---

## Cross-references

- **Sibling structural invariants** (same family, different domain):
  - [ADR-0114a](./ADR-0114a-anti-overfitting-proof-obligations.md) —
    Anti-overfitting proof obligations
  - [ADR-0165](./ADR-0165-regex-scope-rule.md) — Regex scope rule
  - CLAUDE.md §"Non-Negotiable Field Invariant" —
    `versor_condition(F) < 1e-6`
  - CLAUDE.md §"Normalization Rules" — allowed sites only
- **The capability path that motivates this ADR**:
  - [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) — the
    architectural pivot that, mid-build, makes the "run all Tier 3
    lanes" framing premature
  - [ADR-0114](./ADR-0114-expert-capability-roadmap-gsm8k-first.md) —
    the roadmap that established GSM8K as the first capability gate
- **Narrative record**:
  - `SESSION-2026-05-27-tier3-sequencing.md` — how this rule was
    reached, the prior analysis it amends, the honest re-sequence
- **Population mechanism**:
  - [ADR-0150](./ADR-0150-autonomous-inter-session-contemplation.md),
    [ADR-0152](./ADR-0152-learning-arc-demo.md),
    [ADR-0155](./ADR-0155-ci-contemplation-runner.md),
    [ADR-0161](./ADR-0161-hitl-async-queue.md) — the corridor that
    surfaces measurement gaps as proposals
- **Anchor**: `[[thesis-decoding-not-generating]]` — measurement that
  precedes capability is not decoding the engine's state; it is
  generating a wishlist of states the engine has not yet entered.
  The ADR keeps the eval surface aligned with what the engine
  actually does.
