# ADR-0076 — Confirmation-Tag Normalization (C2)

**Status:** Accepted  
**Date:** 2026-05-20  
**Series:** C2 — Confirmation-tag intent normalization  
**Builds on:** [ADR-0075](ADR-0075-realizer-slot-type-guard.md)

## Context

ADR-0075 established the coherence floor: illegal realizer candidates
must not escape.  Its holdout cluster deliberately preserved the observed
failure class:

```text
Light reveals truth, right? -> Right does not thought.
```

C1 routed those candidates to bounded disclosure.  C2 moves the fix
upstream by preserving the proposition before the realizer sees it.

## Decision

The intent classifier strips terminal confirmation tags only when they
are punctuation-bound after content:

```text
X reveals Y, right?
X reveals Y. ok?
```

Bare or content uses are not stripped:

```text
yes?
Is right an axis?
```

After stripping, a closed declarative relation form is classified as a
`VERIFICATION` proposition carrying:

```text
subject
relation
object
negated
```

The runtime adds a deterministic pack-grounded relation-confirmation
surface for these claims.  It emits only when both endpoint lemmas
resolve in mounted packs and the relation is in the closed relation
display table.

## Invariants

The ADR-0075 guard remains active.  The holdout gate becomes hybrid:

1. Synthetic illegal candidates are checked directly with
   `generate.realizer_guard.check_surface()` to prove the guard still
   fires.
2. Runtime confirmation prompts now assert accepted propositional
   surfaces with `realizer_guard_status="ok"`.

The old `walk_surface` grep for `"does not thought"` is retired for C2
runtime prompts because the rejected candidate is no longer produced.

Trace-hash values for the C2 holdout-cluster prompts change as a
deliberate consequence of the substantive lift.  Register-invariance and
lens-distinctness invariants are unaffected because they are stated
per-prompt, not against frozen hash values.

## Non-Goals

- No broad English parser.
- No stochastic repair.
- No relaxation of ADR-0075 guard rules.
- No corpus mutation; relation-confirmation surfaces are reconstructed
  from mounted pack lemmas and semantic domains.
