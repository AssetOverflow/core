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

## Current state — graduated 2026-05-17

Lane now passes overall: `contradiction_flag_rate=1.00`,
`false_flag_rate=0.00`. `TeachingStore.add` runs a coherence checker
on every new proposal:

- **Typed path** — when the new proposal and a prior parse to triples
  with the same relation, compare tails for negation/opposition
  differential AND shared content tokens.
- **Text fallback** — when one side fails to parse a triple (relation
  predicate not in the cognition pack yet), compare raw correction
  texts for polarity differential AND ≥2 shared non-discourse content
  tokens. The ≥2 threshold prevents single-shared-subject false
  positives.

On detection, BOTH the new proposal and the conflicting prior
transition to `EpistemicStatus.CONTESTED` — neither is admissible as
evidence until a coherence judgment ratifies one direction or
falsifies the other.

The v1 versor-spike heuristic was retired in the same commit; the
runner now reads the CONTESTED transition directly.

## Pass criteria

| Metric | Definition | v1 threshold | Current |
|--------|-----------|--------------|---------|
| `contradiction_flag_rate` | Fraction of paired-contradiction cases where the second event surfaces a CONTESTED transition | 0.90 | **1.00** |
| `false_flag_rate` | Fraction of paired-consistent cases that are incorrectly flagged as contradictory | 0.00 | **0.00** |
| `overall_pass` | flag_rate ≥ 0.90 AND false_flag_rate == 0 | true | **true** |

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
