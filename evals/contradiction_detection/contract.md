# contradiction-detection eval lane

## What it measures

When CORE is taught two corrections that directly contradict each
other (e.g. *"truth is coherence"* then *"truth is not coherence"*),
the second event should be flagged as conflicting with the first —
either via a coherence judgment that transitions one or both to
`EpistemicStatus.CONTESTED`, or via a versor-condition spike that
makes the conflict structurally visible.

## Why it matters (structural win, eventually)

Frontier LLMs absorb contradictory training data silently. A
fine-tuning corpus that says "X is Y" in one shard and "X is not Y"
in another produces a model whose answer depends on sampling, not on
which claim is correct. There is no mechanism to surface the
disagreement to a reviewer.

CORE's stored-relation substrate and exact CGA recall make
contradiction a *detectable* event in principle: two triples
`(truth, IS, coherence)` and `(truth, IS_NOT, coherence)` in the
same teaching store are inconsistent on inspection, and a coherence
judgment can transition the conflicting pair to CONTESTED before
they pollute downstream inference.

## Current state — honest

The detection mechanism is **not implemented at v1**.

The teaching review path today admits both members of a contradictory
pair at `EpistemicStatus.SPECULATIVE`. There is no coherence judgment
that compares newly-admitted triples against existing store contents,
and no automatic CONTESTED transition on conflict. The pipeline does
not raise the versor-condition signal on the second teaching event.

This lane exists *now* so the gap is visible and tracked. It will not
pass until one of the following is built:

1. A coherence checker invoked at `TeachingStore.add` that detects
   `(S, R, O)` ↔ `(S, R_negated, O)` pairs and transitions both to
   CONTESTED.
2. A geometric contradiction signal derived from versor-condition
   delta when conflicting teachings are applied.

ADR-0021 reserves `CONTESTED` and `FALSIFIED` precisely for this; the
machinery to *enter* those states is not yet wired.

## Pass criteria

| Metric | Definition | v1 threshold | Honest current expectation |
|--------|-----------|--------------|----------------------------|
| `contradiction_flag_rate` | Fraction of paired-contradiction cases where the second event surfaces a CONTESTED transition or versor spike | 0.90 | 0.00 |
| `false_flag_rate` | Fraction of paired-consistent cases that are incorrectly flagged as contradictory | 0.00 | 0.00 (no flagger exists) |
| `overall_pass` | flag_rate ≥ 0.90 AND false_flag_rate == 0 | true | false at v1 |

## Cases

Each case is a *pair* of corrections delivered sequentially against
the same prior. The lane runner applies them in order and inspects
the second event's `pack_mutation_proposal.epistemic_status` and the
versor-condition delta between the two events.

- **Paired contradiction** — corrections that negate each other.
- **Paired consistent** — control pairs that elaborate without
  contradicting, to keep the flagger honest if/when one is built.

## Runner

`runner.py` in this directory.
