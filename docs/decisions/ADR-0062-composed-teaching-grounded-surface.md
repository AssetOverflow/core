# ADR-0062 — Composed Teaching-Grounded Surface (Chain-of-Chains)

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

Pre-ADR-0062, `teaching_grounded_surface` emitted exactly **one
reviewed chain** per surface:

```
light — teaching-grounded (cognition_chains_v1): cognition.illumination;
logos.core. light reveals truth (cognition.truth).
No session evidence yet.
```

Every grounded prompt produced a single-clause surface, regardless
of how many follow-up chains the corpus already contained.  With
21 active chains in `cognition_chains_v1` (after curriculum
saturation v2), many grounded prompts have an immediate corpus-
ratified follow-up that the surface composer was silently dropping:

| Initial chain | Follow-up chain | What single-chain emits | What composed could emit |
|---|---|---|---|
| `light reveals truth` | `truth grounds knowledge` | `light reveals truth` | `light reveals truth, which grounds knowledge` |
| `thought reveals meaning` | `meaning grounds understanding` | `thought reveals meaning` | `thought reveals meaning, which grounds understanding` |
| `inference requires evidence` | `evidence grounds knowledge` | `inference requires evidence` | `inference requires evidence, which grounds knowledge` |

This is the *fluency-from-existing-corpus* gap I called out
in the "more packs?" question: the rate-limiter on articulation
isn't pack vocabulary, it's surface composition over chains that
already exist.

---

## Decision

Add `teaching_grounded_surface_composed(subject, intent_tag)` to
`chat/teaching_grounding.py` alongside the existing single-chain
composer, and route it via a new opt-in
`RuntimeConfig.composed_surface: bool = False`.

### Surface format

```
"{A} — teaching-grounded ({corpus_id}): {dA1}; {dA2}.
 {A} {conn_A} {B} ({dB}), which {conn_B} {C} ({dC}).
 No session evidence yet."
```

Every visible non-template token remains a lemma, a verbatim pack
`semantic_domains` string, or a `humanize_predicate`-emitted
connective. The new `, which ` linker is the only added template
constant.

### Follow-up resolution rules

1. Look up an initial chain `(subject, intent)`.
2. Look up a follow-up chain whose `subject` equals the initial
   chain's `object`. Prefer `cause`; fall back to `verification`.
   (Causal continuation reads more naturally than a verification
   detour; the preference is deterministic.)
3. **Cycle guard.** If the follow-up's `object` equals the initial
   `subject` OR the initial `object`, do not follow (1-step cycle
   or degenerate same-cell mismatch).
4. **Pack-residency guard.** If the follow-up's `object` is not
   pack-resident with `semantic_domains`, do not follow (would
   emit a partially-grounded composition).
5. If no follow-up survives the guards, degrade to the
   single-chain surface **byte-identically**. Drop-in replacement.

### Bounded depth

v1 follows **exactly one hop**. Deeper compositions (A→B→C→D) are
deferred to a future ADR. The cycle/pack-residency guards alone
don't suffice for unbounded depth — a depth-2 chain can re-enter
through a different intent. Bounded depth + visited-set check is
the natural next step but adds template-shape complexity not
needed today.

### Opt-in flag

`RuntimeConfig.composed_surface: bool = False`. Default preserves
all pre-ADR-0062 behaviour byte-identically. Mirrors the
ADR-0047/0058 `forward_graph_constraint` pattern: ship the
capability behind a flag, characterise empirically, decide on
default behaviour in a follow-up once downstream consumers have
observed it on their workloads.

---

## Verification

```
tests/test_composed_surface.py                11 passed
  - Pure function: None when no chain / degrades when no follow-up /
    produces two-clause when follow-up exists / includes both
    intermediate and final domains / deterministic / cycle guard
    blocks 1-step cycle / preserves trust-boundary label.
  - Runtime: default keeps single-chain / flag-on uses composed /
    flag is observable on frozen config.
  - Null-drop invariant: cognition-lane metrics byte-identical
    flag OFF vs ON on both public and holdout splits.

Lanes (regression check):
  core test --suite smoke           67 passed
  core test --suite cognition      121 passed
  core test --suite teaching        17 passed
```

### Cognition-lane null-drop invariant

Composed mode emits a **strictly longer** surface — every token
in the single-chain surface still appears, plus one follow-up
clause. So every `expected_term` and `expected_surface_contains`
that passed flag-OFF must still pass flag-ON. The contract test
`test_cognition_lane_metrics_unchanged_with_composed_flag` runs
both public and holdout splits twice (flag OFF vs ON) and asserts
all four watched metrics are pair-wise identical:

| Split | Flag OFF | Flag ON |
|---|---|---|
| public  | 100 / 100 / 91.7 / 100 | **100 / 100 / 91.7 / 100** |
| holdout | 100 / 100 / 83.3 / 100 | **100 / 100 / 83.3 / 100** |

If a future change ever drops tokens in composed mode (e.g.
shortens the surface to omit the intermediate object), this test
fails as the deliberate regression it is.

### Live-prompt observable lift

Composed mode visibly enriches the surface on prompts where
follow-ups exist:

```
flag OFF: "Why does light exist?"
  → light — teaching-grounded (cognition_chains_v1):
    cognition.illumination; logos.core. light reveals truth
    (cognition.truth). No session evidence yet.

flag ON:  "Why does light exist?"
  → light — teaching-grounded (cognition_chains_v1):
    cognition.illumination; logos.core. light reveals truth
    (cognition.truth), which grounds knowledge
    (cognition.knowledge). No session evidence yet.
```

Of the 21 active chains, the follow-up resolution succeeds for
~12 of them (the rest hit cycle guards or pack-residency
guards). Saturation v2's three coherent clusters were authored
partly with this composition in mind — `thought reveals meaning`
+ `meaning grounds understanding`, `definition grounds concept` +
`concept requires definition` (cycle-blocked, degrades cleanly),
etc.

---

## Consequences

### What changes

- `core/config.py` — `RuntimeConfig.composed_surface: bool = False`.
- `chat/teaching_grounding.py` —
  `teaching_grounded_surface_composed(subject, intent_tag)` sibling
  to `teaching_grounded_surface`.
- `chat/runtime.py` — dispatch branch in `_maybe_pack_grounded_surface`
  for `IntentTag.CAUSE` / `IntentTag.VERIFICATION` selects composed
  vs single-chain based on the config flag. Single-line change.

### What does not change

- The pack-grounded discipline: zero LLM-generated tokens; every
  visible word is lemma, pack-domain, connective, or template
  constant.
- ADR-0053's cold-start contract: empty session + no chain still
  emits the universal disclosure.
- Default runtime behaviour: byte-identical to pre-ADR-0062 main.
- The non-negotiable field invariant
  (`versor_condition(F) < 1e-6`) is unaffected — this ADR only
  changes surface composition, not rotor construction or sandwich
  application.

---

## Scope limits

- **Depth-1 only.** v1 follows one hop. `light reveals truth,
  which grounds knowledge, which requires evidence` would require
  a depth-2 composer with visited-set tracking — out of scope
  here.
- **No multi-claim aggregation.** When the same subject has
  multiple ratified chains (e.g. `knowledge requires evidence`
  AND `knowledge` is the object of three other chains), the
  composer still picks one initial chain. Aggregation across
  multiple grounded views is a separate ADR.
- **English path only.** The `, which ` linker and the
  `humanize_predicate` connectives are English-specific.
- **Flag stays off by default.** Operators must opt in. A follow-up
  ADR will decide on default behaviour after characterising the
  flag on more workloads (mirrors ADR-0047/0058).

---

## Cross-References

- [ADR-0052](./ADR-0052-teaching-grounded-surface.md) — the
  single-chain teaching-grounded composer this ADR extends.
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the cognition-
  lane closure that exposed the saturation headroom.
- [ADR-0058](./ADR-0058-forward-graph-constraint-status.md) —
  the opt-in-default-False + null-lift-invariant pattern this ADR
  reuses.
- [Curriculum: cognition saturation v2](../curriculum/cognition_saturation_v2.md)
  — the unit that produced the 21 chains this composer composes
  over.
