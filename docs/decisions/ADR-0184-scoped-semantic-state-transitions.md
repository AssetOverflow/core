# ADR-0184 — Scoped Semantic State Transitions for English Multi-Step Reasoning

**Status:** Proposed  
**Date:** 2026-05-29  
**Author:** ChatGPT / Josh direction  
**Blueprint:** [`docs/handoff/SEMANTIC-STATE-TRANSITION-BLUEPRINT.md`](../handoff/SEMANTIC-STATE-TRANSITION-BLUEPRINT.md)  
**Anchor:** [[thesis-decoding-not-generating]]  
**Builds on:** ADR-0165, ADR-0174, ADR-0176, ADR-0177, ADR-0178, ADR-0179, ADR-0182  
**Supersedes:** no runtime path yet; this is a scope-setting ADR for the next implementation sequence.

---

## 1. Decision

CORE will introduce a sealed derivation-lane semantic-state substrate for English multi-step math reasoning.

The substrate reads word problems into scoped, entity-owned state transitions before arithmetic derivation:

```text
text
  -> lexeme extraction + clause segmentation
  -> semantic frames
  -> entity-bound state transitions
  -> semantic ledger / world candidates
  -> GroundedDerivation replay
  -> existing self-verification / classification
  -> cross-composer pooling
  -> answer or refusal
```

This ADR does **not** authorize a serving-path change. The first implementation must remain sealed under `generate/derivation/**` and must emit ordinary `GroundedDerivation` candidates for the existing verifier/pool to judge.

The immediate implementation target is to promote the proven accumulation logic in `generate/derivation/accumulate.py` into a reusable semantic-state package before adding transfer, comparison, rate/container, temporal replay, or DAG logic.

---

## 2. Why this is needed

CORE's arithmetic verification layer is stronger than its semantic reading layer.

The current derivation lane can verify candidate arithmetic traces using grounding, cue evidence, unit consistency, completeness, uniqueness, and commit eligibility. That is the right final judge. But hard English word problems fail earlier: the system often lacks a scoped representation of the situation the text describes.

The missing layer is not more arithmetic. It is a typed world-state reading:

```text
Sam has 14 apples.
He buys 9 more.
How many apples does Sam have now?
```

should first become:

```text
SET_STATE(Sam.apples, 14)
GAIN(Sam.apples, 9)
TARGET(final Sam.apples)
```

and only then replay to:

```text
14 + 9 = 23
```

Without this layer, future work will keep reimplementing the same semantic logic inside local composers:

- subject / referent binding;
- gain/loss polarity;
- question target scope;
- temporal scope;
- foreign distractor classification;
- transfer handling;
- comparison direction;
- rate/container binding;
- branch/DAG quantity reuse.

That is the path to composer spaghetti and wrong=0 hazards.

---

## 3. What already exists

The new substrate should use the existing system rather than bypass it.

### Existing pieces to preserve

- `generate/derivation/extract.py` — lexeme-level quantity/unit/source-token extraction.
- `generate/derivation/clauses.py` — deterministic clause segmentation and local clause results.
- `generate/derivation/accumulate.py` — first working state-transition composer: single-referent gain/loss accumulation.
- `generate/derivation/target.py` — target extraction and prior-state question guard.
- `generate/derivation/verify.py` — final proof gate: grounding, cue, unit, completeness, classification, uniqueness.
- `generate/derivation/pool.py` — cross-composer candidate pooling, disagreement refusal, commit eligibility.
- `generate/comprehension/state.py` — immutable state, entity/quantity/question/refusal/hypothesis concepts and canonical hashing; useful as design precedent, not automatically the active scoring path.

### Existing pieces to avoid misusing

- Do **not** resurrect the old broad comprehension lifecycle as the active scoring reader unless a separate audit proves it is now load-bearing.
- Do **not** revive gender-blind most-recent antecedent pronoun resolution.
- Do **not** make semantic worlds commit directly.
- Do **not** replace `verify.py`.
- Do **not** let any composer pick first non-`None` when multiple competing readings exist; use pooling.

---

## 4. Where this fits

Add a new sealed derivation-lane package:

```text
generate/derivation/state/
  __init__.py
  model.py
  bind.py
  change.py
  ledger.py
  target.py
  replay.py
  refusals.py
```

Later phases may add:

```text
generate/derivation/state/transfer.py
generate/derivation/state/compare.py
generate/derivation/state/rate.py
generate/derivation/state/time.py
generate/derivation/state/world.py
generate/derivation/state/dag.py
```

The initial integration path is deliberately conservative:

```text
accumulate.py public functions
  -> semantic-state helper modules
  -> semantic ledger
  -> replay to GroundedDerivation
  -> existing verify/select/classify
```

`pool.py` continues to arbitrate final candidates.

---

## 5. Initial object language

The first version should model only what accumulation already needs.

Suggested minimal types:

```python
@dataclass(frozen=True, slots=True)
class EntityMention:
    surface: str
    canonical: str
    clause_index: int
    token_index: int
    kind: str  # proper | pronoun | implicit | unknown

@dataclass(frozen=True, slots=True)
class QuantityMention:
    value: float
    unit: str
    source_token: str
    clause_index: int
    role: str  # state | delta | scalar | rate | target | unknown

@dataclass(frozen=True, slots=True)
class CueMention:
    surface: str
    cue_kind: str  # gain | loss | aggregate | multiplicative | temporal | ...
    clause_index: int

@dataclass(frozen=True, slots=True)
class StateKey:
    entity: str
    unit: str

@dataclass(frozen=True, slots=True)
class StateTransition:
    key: StateKey
    op: str  # set | gain | loss
    quantity: QuantityMention
    cue: CueMention
    clause_index: int

@dataclass(frozen=True, slots=True)
class SemanticLedger:
    transitions: tuple[StateTransition, ...]
```

The first replay target is a standard `GroundedDerivation`.

This ADR intentionally does not require all final types up front. It requires that types be frozen, deterministic, and covered by tests before they are used for candidate generation.

---

## 6. Wrong=0 obligations

Every implementation phase must preserve the following.

### 6.1 Semantic worlds do not commit directly

A semantic world may only produce a candidate. It cannot answer by itself.

Commit path remains:

```text
SemanticWorld / SemanticLedger
  -> GroundedDerivation
  -> self_verifies / classify_derivation
  -> resolve_pooled
```

A test must fail if a semantic-world-only answer bypasses `verify.py` or `pool.py`.

### 6.2 Existing complete-commit rules remain intact

`complete` remains the only commit-eligible classification. Exempt/distractor readings may enter the pool only to force disagreement/refusal, never as sole committable answers.

### 6.3 Ambiguous referents refuse

If a state transition needs an entity and the entity cannot be safely bound, the semantic world refuses or is not emitted.

Required tests:

```text
Sam has 14 apples. He buys 9 more. -> same referent, candidate allowed
Sam has 14 apples. Tom buys 9 more. -> new actor, candidate refused
Alice has 5. Bob has 3. She buys 2. -> ambiguous, refused unless explicitly resolved by a future safe rule
```

### 6.4 Ambiguous polarity refuses

A gain/loss event may be emitted only when polarity is unambiguous and cue-grounded.

Required tests:

```text
gets 4 more -> gain
loses 4 -> loss
owns 4 -> no change cue, refused
mixed gain/loss cue in same change frame -> refused
```

### 6.5 Unsupported temporal target refuses

Until temporal replay exists, prior-state questions remain refused.

Required tests:

```text
How much did Lisa have before lunch? -> refuse until time replay exists
How much does Lisa have left? -> forward/net target allowed
before in body narrative does not trip prior-state refusal
used to make does not trip prior-state refusal
```

### 6.6 Determinism

All emitted candidates must be deterministic:

- no random ordering;
- no unordered set/dict iteration in outputs;
- stable candidate ordering;
- frozen dataclasses or canonical bytes for replay-critical state.

---

## 7. Implementation sequence

### S1 — Extract proven accumulation helpers

Create:

```text
generate/derivation/state/bind.py
generate/derivation/state/change.py
```

Move behavior-equivalent helpers from `accumulate.py`:

```text
_subject_token -> leading_subject_token
_same_referent -> continues_anchor_referent
_polarity -> classify_change_polarity
_cue -> select_change_cue
```

Acceptance:

- accumulation tests unchanged and green;
- pool tests unchanged and green;
- new helper tests prove non-vacuous referent and polarity guards;
- no serving imports;
- no runner changes;
- no behavior change.

### S2 — Add accumulation semantic ledger

Create:

```text
generate/derivation/state/model.py
generate/derivation/state/ledger.py
generate/derivation/state/replay.py
```

Represent:

```text
SET_STATE(entity, unit, value)
GAIN(entity, unit, value)
LOSS(entity, unit, value)
```

Then replay the ledger into `GroundedDerivation`.

Acceptance:

- `compose_accumulation()` output unchanged;
- `accumulation_candidates()` output unchanged or explicitly equivalent by candidate answer/key tests;
- direct manual construction of accumulation chains in `accumulate.py` is minimized or removed;
- replay tests prove ledger -> `GroundedDerivation` correctness.

### S3 — Add semantic target wrapper

Create:

```text
generate/derivation/state/target.py
```

Wrap current target extraction with semantic fields:

```text
entity: optional
unit: optional
time_scope: final | prior | unknown
relation: count | difference | aggregate | unknown
```

Acceptance:

- current prior-state guard behavior preserved;
- forward/net questions still resolve;
- target wrapper is conservative and refuses unsupported scope.

### S4 — Add semantic candidate source to pool

Create public surface:

```python
def semantic_state_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]: ...
```

Initially it delegates to accumulation-backed worlds.

Then update `pool.py` from:

```text
accumulation_candidates, multiplicative_candidates, candidate_chains
```

to:

```text
semantic_state_candidates, multiplicative_candidates, candidate_chains
```

Acceptance:

- all ADR-0182 pool tests remain green;
- clean accumulation still commits;
- distractor cases still refuse;
- exempt-only still never commits;
- direct `pool.py` import of `accumulation_candidates` can be removed.

### S5 — Transfer events

Add source/target entity transitions:

```text
Sam gives Tom 3 apples
  -> Sam.apples -= 3
  -> Tom.apples += 3
```

Acceptance:

- source-target binding tests;
- ambiguous target refused;
- no initial state refused;
- target-specific question required for commit.

### S6 — Comparison / difference frames

Add difference questions:

```text
Sam has 10 apples. Tom has 7 apples. How many more apples does Sam have than Tom?
```

Acceptance:

- direction explicit -> commit;
- direction ambiguous -> refuse;
- same-unit aggregate does not become difference by accident.

### S7 — Rate / container frames

Add structurally bound products:

```text
24 boxes with 12 erasers each
60 miles per hour for 2 hours
```

Acceptance:

- legitimate products commit;
- distractor duration with unrelated target refuses;
- protected existing product positives do not regress;
- product-of-all fallback remains until semantic rate frames cover positives.

### S8 — Temporal replay

Use ledger history to answer:

```text
before
after
initially
finally
left
now
```

Acceptance:

- prior-state questions answer only when event boundary is unambiguous;
- ambiguous temporal scope refuses;
- current prior-state refusal tests update only when the new capability is proven.

### S9 — Held worlds and DAGs

Represent multiple possible semantic worlds and quantity reuse / branch structures.

Acceptance:

- linear cases unchanged;
- unresolved multi-world ambiguity refuses;
- no DAG candidate commits without proof obligations equivalent to current grounding/completeness/target requirements.

---

## 8. Immediate next PR authorized by this ADR

Branch:

```text
feat/adr-0184-s1-semantic-state-helpers
```

Scope:

1. Add `generate/derivation/state/__init__.py`.
2. Add `generate/derivation/state/bind.py`.
3. Add `generate/derivation/state/change.py`.
4. Move proven helper logic from `accumulate.py` into those modules.
5. Keep `compose_accumulation()` unchanged externally.
6. Keep `accumulation_candidates()` unchanged externally.
7. Add tests for extracted helpers.
8. Do not touch serving.
9. Do not change runners.
10. Do not delete old reader files.

This is intentionally a behavior-equivalent refactor. It creates the seam for multi-step English reasoning without expanding capability in the same PR.

---

## 9. Explicit non-actions

Do **not** do any of the following in S1:

- no serving import;
- no `chat/**` edit;
- no `generate/math_roundtrip.py` edit;
- no runner behavior change;
- no deletion of `generate/comprehension/lifecycle.py`;
- no deletion of `generate/math_parser.py`;
- no product-of-all fallback removal;
- no transfer/comparison/rate/temporal/DAG implementation;
- no broad grammar parser;
- no pronoun resolver beyond current conservative same-referent guard.

These are future phases or separate ADRs.

---

## 10. Dead-weight policy

This ADR does not delete code immediately. It establishes deletion criteria.

### Composer-local helper deletion

After S1/S2, helper logic for subject extraction, referent continuity, polarity, cue selection, and accumulation replay should not remain private to `accumulate.py` except as thin compatibility wrappers.

### Pool prior-state guard migration

After S3, direct prior-state logic in `pool.py` should migrate into semantic target handling or become a compatibility call.

### Product-of-all fallback demotion

Only after S7 proves rate/container semantic frames protect current positives and refuse known distractors may product-of-all fallback be demoted or deleted.

### Old comprehension lifecycle

Do not delete casually. Demote or delete only after an audit proves it is inert relative to active scoring and no tests depend on it as a runtime path.

---

## 11. Acceptance criteria for this ADR moving from Proposed to Accepted

This ADR may move to Accepted when:

1. S1 lands with no behavior change and tests prove helper extraction is non-vacuous.
2. S2 lands with semantic ledger replay for accumulation and accumulation behavior remains equivalent.
3. `resolve_pooled` can source accumulation through `semantic_state_candidates()` with ADR-0182 behavior preserved.
4. Serving remains unchanged.
5. Existing wrong=0 lanes remain wrong=0.
6. Documentation identifies all old code paths that are retained, demoted, or scheduled for later deletion.

---

## 12. Final doctrine

CORE should complete English multi-step reasoning by reading into scoped semantic state, not by accumulating more arithmetic shapes.

The durable loop is:

```text
read the world stated by the text
  -> mutate scoped state under cue-licensed rules
  -> bind the question to a state/relation/time
  -> replay into arithmetic proof objects
  -> let existing verifier and pool accept or refuse
```

The first safe step is not more coverage. It is extracting the already-proven accumulation semantics into a reusable substrate so the next capability layers can compose without becoming local patches.
