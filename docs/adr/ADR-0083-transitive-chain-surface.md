# ADR-0083 — Transitive Chain Surface (Bounded Multi-Hop Composition)

**Status:** Accepted
**Date:** 2026-05-20
**Author:** Shay

---

## Context

ADR-0062 introduced depth-1 chain-of-chains composition
(`teaching_grounded_surface_composed`): given a ratified chain
`(A, intent_A, conn_A, B)` and a follow-up `(B, intent_B, conn_B, C)`,
emit a two-clause surface

```
A {conn_A} B (dB), which {conn_B} C (dC).
```

The composer is opt-in (`RuntimeConfig.composed_surface=False`),
cycle-guarded, pack-residency-guarded, and degrades byte-identically
to the single-chain surface when no follow-up exists. On the 21-chain
saturation-v2 cognition corpus, follow-up resolution succeeds for
~12 chains.

### What's still missing

ADR-0062 explicitly defers deeper composition:

> v1 follows **exactly one hop**. Deeper compositions (A→B→C→D) are
> deferred to a future ADR.

Inspection of the holdout misses (memory:
`dev-holdout-generalization-2026-05-18`, `adr-0053-cognition-lane-closure`)
and the cognition saturation corpus shows several latent depth-2 paths
that today's composer cannot reach:

| Hop 1 | Hop 2 | Hop 3 |
|---|---|---|
| `inference requires evidence` | `evidence grounds knowledge` | `knowledge requires evidence` (cycle — stops at hop 2) |
| `thought reveals meaning` | `meaning grounds understanding` | `understanding requires knowledge` |
| `light reveals truth` | `truth grounds knowledge` | `knowledge requires evidence` |
| `definition grounds concept` | `concept requires definition` (cycle — stops at hop 1) | — |

Three of these would emit a three-clause surface today if the
composer could follow a second hop with cycle tracking; the fourth
demonstrates the cycle guard already does its job at depth 1 and
must extend to depth N.

### Why this is the next architectural step

The repo's φ separation probe (memory: `phi separation falsified`)
made it explicit that semantic "stress" or "contradiction" cannot
currently be encoded geometrically — the working semantic engine is
**pack-grounded chain composition over ratified teaching corpora**.
That engine is the cognition surface. Its depth ceiling is therefore
the cognition surface's depth ceiling.

ADR-0083 raises that ceiling by one constant per release: depth-2
now, with the visited-set machinery to support depth-N later under
the same flag.

---

## Decision

Add `teaching_grounded_surface_transitive(subject, intent_tag, *, max_depth)`
to `chat/teaching_grounding.py` alongside the existing single-chain
and composed (depth-1) composers. Route it via a new opt-in
`RuntimeConfig.transitive_surface: bool = False` and a separate
`RuntimeConfig.transitive_max_depth: int = 2`.

### Surface format

```
"{A} — teaching-grounded ({corpus_id}): {dA1}; {dA2}.
 {A} {conn_A} {B} ({dB1}), which {conn_B} {C} ({dC1}), which {conn_C} {D} ({dD1}).
 No session evidence yet."
```

Each additional hop adds one `", which {conn_k} {X_k} ({dX_k1})"`
clause before the trailing period. The `, which ` linker is reused
from ADR-0062; no new template constants.

### Follow-up resolution rules

Reuse ADR-0062's per-hop rules, applied iteratively:

1. Resolve the initial chain `(subject, intent)`. If absent, return `None`.
2. For each hop `k ∈ {1, ..., max_depth - 1}`:
   a. Look up `(X_k.object, "cause")`; fall back to
      `(X_k.object, "verification")`.
   b. **Visited-set guard.** Maintain `visited = {subject, X_1.object, ..., X_k.object}`.
      Refuse a candidate whose `object` is in `visited` (closes the
      ADR-0062 cycle guard at every depth).
   c. **Pack-residency guard.** Refuse a candidate whose `object` is
      not pack-resident with `semantic_domains` in the candidate's
      resolving corpus's pack.
   d. **Cross-corpus guard.** v1 requires all hops to resolve in the
      **same** corpus (`spec.corpus_id == initial.corpus_id`). ADR-0064
      cross-corpus chains exist, but transitive composition across
      corpora needs its own audit — deferred.
   e. If no candidate survives, stop and emit whatever depth has
      accumulated so far.
3. If no hop survived past the initial chain, degrade byte-identically
   to the ADR-0062 composed surface (which itself degrades to the
   single-chain surface).

### Bounded depth

`transitive_max_depth: int = 2` is the v1 default — equivalent to one
additional hop beyond ADR-0062's composed surface. The config field
is exposed so operators can characterise depth-3 / depth-4 on their
workloads before any default change is proposed. The runtime clamps
to `max(1, transitive_max_depth)` so a misconfigured 0 degrades
gracefully to single-chain.

### Opt-in flag

`RuntimeConfig.transitive_surface: bool = False`. Default preserves
all pre-ADR-0083 behaviour byte-identically. Mirrors the
ADR-0047/0058/0062 pattern: ship the capability behind a flag,
characterise empirically, decide on default behaviour in a follow-up.

The flag composes with `composed_surface`:

| `composed_surface` | `transitive_surface` | Behaviour |
|---|---|---|
| False | False | single-chain (pre-ADR-0062) |
| True  | False | depth-1 composed (ADR-0062) |
| *     | True  | depth-N transitive (ADR-0083, overrides composed) |

`transitive_max_depth` is the number of follow-up hops to append
beyond the initial chain. At `max_depth=0` transitive degrades
byte-identically to single-chain; at `max_depth=1` byte-identical
to ADR-0062's composed surface; at `max_depth=2` byte-identical to
ADR-0062 when no second hop survives the guards, strict superset
when one does.

---

## Verification

### Required tests (new file: `tests/test_transitive_surface.py`)

- **Pure function**:
  - returns `None` when no chain / initial-only / depth-1 / depth-2;
  - emits an N-clause surface (N ≤ `max_depth`) when chains chain;
  - includes every intermediate object as a clause subject;
  - includes every intermediate `semantic_domains` head;
  - deterministic across two calls;
  - visited-set guard blocks a depth-N cycle at every depth from 2 to `max_depth`;
  - pack-residency guard blocks at any depth (not just depth-1);
  - cross-corpus guard refuses to traverse a cross-corpus follow-up.
- **Runtime**:
  - default keeps single-chain;
  - `composed_surface=True, transitive_surface=False` matches ADR-0062;
  - `transitive_surface=True, max_depth=1` matches single-chain;
  - `transitive_surface=True, max_depth=2` matches ADR-0062 when no
    second hop exists, **strict superset** when one does;
  - flags observable on frozen config.
- **Null-drop invariant**:
  - cognition-lane public + holdout metrics byte-identical
    `transitive_surface` OFF vs ON at `max_depth=2`. The composer is
    a strict-superset emitter (every token in the depth-1 surface is
    preserved; new tokens append) so `expected_term` and
    `expected_surface_contains` assertions must hold flag-on.

### Lanes (regression check)

```
core test --suite smoke
core test --suite cognition
core test --suite teaching
core eval cognition
```

### Live-prompt observable lift (expected)

```
composed_surface=True (ADR-0062):
  "Why does light exist?"
  → light — teaching-grounded (cognition_chains_v1):
    cognition.illumination; logos.core. light reveals truth
    (cognition.truth), which grounds knowledge (cognition.knowledge).
    No session evidence yet.

transitive_surface=True, max_depth=2 (ADR-0083):
  "Why does light exist?"
  → light — teaching-grounded (cognition_chains_v1):
    cognition.illumination; logos.core. light reveals truth
    (cognition.truth), which grounds knowledge (cognition.knowledge),
    which requires evidence (cognition.evidence). No session evidence yet.
```

The third clause is **already in the ratified corpus**
(`knowledge requires evidence`). ADR-0083 doesn't introduce content;
it surfaces content the realizer was silently dropping.

---

## Consequences

### What changes

- `core/config.py` —
  `RuntimeConfig.transitive_surface: bool = False`,
  `RuntimeConfig.transitive_max_depth: int = 2`.
- `chat/teaching_grounding.py` —
  `teaching_grounded_surface_transitive(subject, intent_tag, *, register, max_depth)`
  sibling to the depth-1 composer; shared follow-up-resolution helper
  refactored out of ADR-0062's body so both composers consult one
  function (no behavioural change to the depth-1 path).
- `chat/runtime.py` — dispatch branch in `_maybe_pack_grounded_surface`
  for `IntentTag.CAUSE` / `IntentTag.VERIFICATION` picks
  transitive > composed > single based on the two flags.

### What does not change

- The pack-grounded discipline: every visible token remains lemma,
  pack-domain, connective, or template constant. No LLM. No synthesis.
- ADR-0053's cold-start contract: empty session + no chain → universal
  disclosure.
- ADR-0062's null-drop invariant: still enforced; ADR-0083 adds its
  own equivalent at depth-2.
- Default runtime behaviour: byte-identical to pre-ADR-0083 main.
- The non-negotiable field invariant
  (`versor_condition(F) < 1e-6`) is unaffected — this ADR composes
  surface text from ratified chains; no algebra is touched.
- Trust-boundary labels: every emitted surface continues to carry the
  `teaching:{corpus_id}` tag.

---

## Scope limits

- **Depth-2 default.** v1 ships at `max_depth=2`. Depth-3 and beyond
  are reachable by raising the config field, but the default holds
  until a follow-up ADR characterises lift and readability.
- **Single-corpus traversal.** Cross-corpus transitive chains (e.g.
  cognition → relations) are deferred. ADR-0064 already allows
  cross-corpus single-chain emission; transitive cross-corpus adds an
  audit surface (`teaching:{cognition_chains_v1, relations_chains_v1}`)
  that needs its own ADR.
- **No multi-claim aggregation.** When a subject has multiple
  initial chains, the composer still picks one — same selection as
  ADR-0062.
- **English path only.** Linker `, which ` and `humanize_predicate`
  connectives are English-specific. Anchor-lens lifts of transitive
  surfaces will need their own per-pack linkers — out of scope.
- **Flag stays off by default.** Operators must opt in. A follow-up
  ADR decides on default behaviour after measuring on holdout cases
  and on the cognition eval.

---

## Why now (and why not the alternatives)

The three other candidate next-steps:

1. **A learned φ embedding** (replace hash-derived φ with one trained
   on chain co-occurrence). Real research, could be wrong, lives in
   `evals/lab/`.
2. **Greek/Hebrew content phase II** (lift the cognition-tier grc/he
   packs from 9+3 lemmas to ~50+). Content grind, not architecture.
3. **Teaching corpus epistemology v2 / kinship v2**. Also content grind.

ADR-0083 is the only one that:

- exercises only existing primitives (PropositionGraph, chains,
  pack-grounded surfaces, the ADR-0062 composer pattern),
- ships behind the established opt-in-flag + null-drop-invariant
  pattern,
- has measurable lift on the existing holdout corpus without any
  new content,
- and lands inside one ADR.

It is the smallest design step that moves the substantive ceiling.

---

## Cross-References

- [ADR-0062](./ADR-0062-composed-teaching-grounded-surface.md) — the
  depth-1 composer this ADR extends.
- [ADR-0058](./ADR-0058-forward-graph-constraint-status.md) — the
  opt-in-default-False + null-lift-invariant pattern reused here.
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the cognition-
  lane closure that frames "term_capture is the next ceiling."
- [ADR-0064](./ADR-0064-cross-pack-teaching-chains.md) — defines the
  cross-corpus chain model that the cross-corpus-traversal scope
  limit defers to a future ADR.
- Memory: `phi separation falsified` — establishes that semantic
  capability lives in chain composition, not in φ geometry, framing
  why deepening the composer is the load-bearing next step.
