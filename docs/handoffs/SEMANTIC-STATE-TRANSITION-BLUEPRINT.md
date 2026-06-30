# Semantic State Transition Blueprint

**Status:** development blueprint / handoff document  
**Branch:** `docs/semantic-state-transition-blueprint`  
**Scope:** docs only; no runtime code changes  
**Audience:** lead engineer / reviewer / future ADR author  
**Purpose:** define how to fit a scoped semantic-state-transition reader into the existing CORE math derivation lane without weakening `wrong = 0`.

---

## 0. Executive decision

CORE should not add another parser or another arithmetic composer as the next architectural move.

The next move is to promote the already-proven semantic transition behavior emerging in `generate/derivation/accumulate.py` into a small, sealed, reusable substrate:

```text
text
  -> lexeme extraction + clause segmentation
  -> semantic frames
  -> scoped entity-owned state transitions
  -> semantic world / ledger candidates
  -> GroundedDerivation replay
  -> existing self-verification / classification
  -> cross-composer pool
  -> answer or refusal
```

The system already contains the pieces, but they are spread across composer-local helpers:

- `generate/derivation/extract.py` lifts quantities and units.
- `generate/derivation/clauses.py` provides sentence-level clause segmentation and local clause results.
- `generate/derivation/accumulate.py` implements the first real state-transition reading: single-referent gain/loss accumulation.
- `generate/derivation/target.py` contains early question-target and temporal-scope guards.
- `generate/derivation/verify.py` owns the proof gate.
- `generate/derivation/pool.py` owns cross-composer disagreement and commit eligibility.
- `generate/comprehension/state.py` contains older, broader immutable reader-state types, held hypotheses, reader refusals, and canonical hashing.

The blueprint recommendation:

> Add a sealed derivation-lane semantic-state package, initially backed by accumulation only, that emits the same `GroundedDerivation` candidates the current gate already knows how to verify.

This gives CORE a real place for entity scope, question scope, temporal scope, state mutation, and later transfer/rate/comparison/DAG logic without creating composer spaghetti.

---

## 1. Why this is needed

### 1.1 The present failure mode

Current successful logic is mostly candidate arithmetic plus a strong verifier. That is good, but it is not enough. The system needs a pre-arithmetic reading step that understands:

- who owns a quantity;
- whether a quantity is an initial state, delta, scalar, rate, comparison, distractor, or target;
- whether a later clause continues the same referent or introduces a new actor;
- whether a cue licenses gain, loss, multiplication, division, comparison, or no operation;
- whether the question asks for final state, prior state, difference, total, rate, or another relation;
- whether quantities are genuinely relevant or isolated foreign distractors;
- whether the derivation is a linear chain or needs branching / reuse.

The current local composers encode some of that, but not as a shared object language.

### 1.2 The exact architectural gap

`GroundedDerivation` is intentionally small:

```text
start Quantity + ordered Step tuple
```

That is the right arithmetic proof object. It is not the right semantic reading object.

The missing layer is a semantic object language that can represent:

```text
Sam.apples = 14
Sam.apples += 9
question target = final Sam.apples
```

before replaying the arithmetic as:

```text
14 + 9 = 23
```

### 1.3 Why now

This is the right time because the repository has already proven three supporting facts:

1. `accumulate.py` shows that semantic state transitions can flip useful cases while preserving refusal-first guards.
2. `pool.py` shows that multiple readings should be pooled and arbitrated by disagreement instead of composer priority.
3. `verify.py` is strong enough to remain the final commit gate; the semantic layer can stay as candidate generation.

If we keep extending one composer at a time, the same ideas will be reimplemented repeatedly: referent binding, cue polarity, target scoping, temporal refusal, distractor classification, and eventually DAG handling. That is the path to spaghetti.

---

## 2. Non-negotiable constraints

### 2.1 Serving stays untouched

The semantic-state substrate must live in the sealed derivation/practice lane first.

Do not import it from:

- `chat/**`
- serving response generation
- runtime surface selection
- shared grounding primitives unless separately gated

The first implementation should preserve the current two-regime contract:

```text
serving: unchanged
practice/confuser lanes: allowed to attempt, measure, and eliminate
```

### 2.2 Existing verifier remains authoritative

Do not replace `generate/derivation/verify.py`.

The semantic layer should produce candidates and refusal reasons. It should not become a second answer gate.

Commit path should remain:

```text
semantic candidate
  -> GroundedDerivation replay
  -> classify_derivation / self_verifies
  -> pool uniqueness / disagreement
  -> commit only if complete and unique
```

### 2.3 No hidden best-guessing

The semantic layer must refuse rather than infer silently when:

- referent binding is ambiguous;
- a pronoun has multiple possible antecedents;
- gain/loss polarity is ambiguous;
- a new actor appears in a single-referent chain;
- a temporal target is unsupported;
- a question target cannot be bound;
- more than one semantic world survives without eliminating evidence.

### 2.4 No grammar-template backslide

Keep ADR-0165 discipline:

- lexeme-level extraction is allowed;
- closed cue sets are allowed;
- deterministic clause/sub-clause splitting is allowed when scoped and tested;
- broad sentence-template parsing is not allowed.

This substrate should be a typed transition interpreter, not a new regex grammar parser.

### 2.5 Dead-code removal is part of the plan

Any path made obsolete by the semantic-state substrate must be marked and later removed. Do not leave parallel, inert, or duplicate readers unless explicitly retained as offline baselines.

---

## 3. Current repository map

### 3.1 `generate/derivation/extract.py`

Current role:

- lexeme-level quantity extraction;
- word numbers;
- list-unit inheritance;
- sentence-final numbers;
- unit hygiene;
- hyphen-bonded number-units;
- intentionally deferred multi-word-unit handling.

Future role:

- remains lexeme lifting only;
- should not learn semantic roles like initial state, delta, target, actor, or temporal scope;
- feeds semantic frame construction.

Keep.

### 3.2 `generate/derivation/clauses.py`

Current role:

- sentence-level splitting;
- local clause result calculation;
- local ambiguity holds/refuses.

Future role:

- remains the default deterministic clause stream;
- semantic-state package can consume `segment_clauses()`;
- local sub-clause splitting can exist in semantic-state modules only when tightly scoped and tested.

Keep, but do not overload it with semantic roles.

### 3.3 `generate/derivation/accumulate.py`

Current role:

- first real state-transition composer;
- anchor state + gain/loss changes;
- referent guard;
- polarity classification;
- cue selection;
- distractor skip / anchor skip candidates for pooling.

Future role:

- should become a thin public composer facade;
- semantic logic should move into reusable state modules;
- public functions should remain stable initially:
  - `compose_accumulation(problem_text)`
  - `accumulation_candidates(problem_text)`

Keep, but slim.

### 3.4 `generate/derivation/compose.py`

Current role:

- same-unit list-sum/comparative-scale slice;
- clause-local guard after earlier whole-problem hazards.

Future role:

- eventually should emit or consume semantic frames for list aggregation and comparative scaling;
- should not independently grow a second referent/temporal/question model.

Keep, but prevent further semantic accretion without using the shared substrate.

### 3.5 `generate/derivation/search.py` and `multistep.py`

Current role:

- multiplicative product candidates;
- target-guided bounded chain candidates;
- blunt but useful candidate sources;
- intentionally wrong=0-safe through verification and pooling.

Future role:

- remain candidate sources;
- over time, semantically grounded rate/product frames should reduce dependence on product-of-all shapes;
- do not delete until semantic replacements are measured and gated.

Keep, but expect demotion.

### 3.6 `generate/derivation/target.py`

Current role:

- question quantities;
- aggregation hints;
- asked-unit intersection;
- prior-state question guard.

Future role:

- become a lexeme-level target extractor used by semantic `QuestionTarget`;
- temporal target scope should move into the semantic-state target model.

Keep, but wrap.

### 3.7 `generate/derivation/verify.py`

Current role:

- operand grounding;
- cue grounding;
- unit consistency;
- divide-by-zero;
- completeness;
- commit eligibility classification;
- uniqueness via `select_self_verified`.

Future role:

- unchanged final gate;
- semantic-state layer should add preconditions, not replace this.

Keep as authoritative.

### 3.8 `generate/derivation/pool.py`

Current role:

- union candidate readings across composers;
- classify as complete/exempt/invalid;
- refuse on disagreement;
- commit only complete, unique answers.

Future role:

- should become the stable arbitration seam;
- semantic-world candidates should enter through this path.

Keep as the integration point.

### 3.9 `generate/comprehension/state.py`

Current role:

- older broad reader-state substrate;
- immutable dataclasses;
- entity/quantity/question/refusal/hypothesis types;
- canonical bytes / hashes;
- still useful as a design precedent.

Future role:

- do not wire directly into scoring yet;
- reuse discipline and possibly some types if import direction is clean;
- avoid resurrecting old all-or-nothing / ambiguous pronoun hazards.

Keep, but treat as adjacent / partially inert.

### 3.10 Potential dead weight / caution zones

The following should be reviewed for eventual retirement or demotion:

1. **Old lifecycle reader runtime assumptions**  
   The amended ADR-0174 notes that `lifecycle.py` is not the reader to promote if it admits `0/50` and remains inert relative to the scoring path. Do not build the semantic-state transition system by trying to revive that whole path wholesale.

2. **Legacy parser runtime paths**  
   If any legacy parser path remains in runtime scoring, it should be removed only after a lane-SHA and wrong=0 proof. If it is already only an offline baseline, leave it alone until the cleanup phase.

3. **Composer-local semantic helpers**  
   Helpers like referent binding, polarity classification, cue selection, temporal target guards, and foreign-distractor logic should not keep spreading across composers. Extract once.

4. **Priority-ordered composer resolution**  
   Any runner or scorer that picks the first non-`None` composer result is suspect. Pooling should be preferred wherever multiple readings are possible.

---

## 4. Target architecture

### 4.1 New package

Add:

```text
generate/derivation/state/
  __init__.py
  model.py
  frames.py
  bind.py
  change.py
  target.py
  ledger.py
  replay.py
  refusals.py
```

This package is derivation-lane scoped. It must not be imported by serving.

### 4.2 Model objects

Initial minimal model:

```python
@dataclass(frozen=True, slots=True)
class EntityMention:
    surface: str
    canonical: str
    clause_index: int
    token_index: int
    kind: str  # "proper", "pronoun", "implicit", "unknown"

@dataclass(frozen=True, slots=True)
class QuantityMention:
    value: float
    unit: str
    source_token: str
    clause_index: int
    role: str  # "state", "delta", "scalar", "rate", "target", "unknown"

@dataclass(frozen=True, slots=True)
class CueMention:
    surface: str
    cue_kind: str  # "gain", "loss", "aggregate", "multiplicative", "temporal", ...
    clause_index: int

@dataclass(frozen=True, slots=True)
class StateKey:
    entity: str
    unit: str

@dataclass(frozen=True, slots=True)
class StateTransition:
    key: StateKey
    op: str  # "set", "gain", "loss"
    quantity: QuantityMention
    cue: CueMention
    clause_index: int

@dataclass(frozen=True, slots=True)
class SemanticLedger:
    transitions: tuple[StateTransition, ...]

@dataclass(frozen=True, slots=True)
class SemanticWorld:
    ledger: SemanticLedger
    question_target: object | None
    unresolved: tuple[str, ...]
    refusal_reasons: tuple[str, ...]
```

The first version can keep some fields as closed strings rather than enums if that matches current style, but closed sets should live near the model and be tested.

### 4.3 Public surfaces

Initial public surfaces:

```python
def accumulation_world_candidates(problem_text: str) -> tuple[SemanticWorld, ...]: ...

def replay_world(world: SemanticWorld) -> GroundedDerivation | None: ...

def semantic_state_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]: ...
```

First implementation:

```text
semantic_state_candidates(problem_text) == accumulation_candidates(problem_text)
```

Behavior should be equivalent before expanding scope.

### 4.4 Integration flow

Final intended flow:

```text
resolve_pooled(problem_text)
  -> pooled_candidates(problem_text)
      -> semantic_state_candidates(problem_text)
      -> multiplicative_candidates(problem_text)
      -> candidate_chains(problem_text)
  -> classify_derivation(...)
  -> disagreement / commit eligibility
```

Initially, `pool.py` can keep calling `accumulation_candidates`; later swap to `semantic_state_candidates` after equivalence tests pass.

---

## 5. Implementation phases

## Phase S0 — ADR / blueprint ratification

### Goal

Convert this blueprint into an ADR or ADR-scope document before code begins.

### Why

This touches several ADR lines:

- ADR-0174 held-hypothesis comprehension;
- ADR-0178 compositional structure;
- ADR-0182 pooling;
- ADR-0165 regex scope;
- ADR-0176/0177 derivation search and cue precision.

A small ADR prevents future code from treating this as another local composer tweak.

### Deliverable

Suggested file:

```text
docs/decisions/ADR-0183-scoped-semantic-state-transitions.md
```

If ADR numbering is already occupied, use the next available number.

### Acceptance

- ADR explicitly says serving remains untouched.
- ADR explicitly says semantic worlds replay to `GroundedDerivation` and use existing gates.
- ADR explicitly identifies `accumulate.py` as the first migration target.
- ADR explicitly forbids reviving the old lifecycle reader as a scoring path without a separate proof.

---

## Phase S1 — Extract proven helpers without behavior change

### Where

From:

```text
generate/derivation/accumulate.py
```

To:

```text
generate/derivation/state/bind.py
generate/derivation/state/change.py
```

### What moves

Move / rename:

```text
_subject_token -> leading_subject_token
_same_referent -> continues_anchor_referent
_polarity -> classify_change_polarity
_cue -> select_change_cue
```

### Why

These helpers are no longer accumulation-specific. They are the beginning of semantic reading.

### How

- Copy behavior exactly.
- Preserve ordering and cue selection.
- Preserve tests.
- Add direct unit tests for the new helper names.
- Keep `accumulate.py` public behavior unchanged.

### Acceptance

- `tests/test_adr_0178_gb3b1_accumulation.py` unchanged and green.
- `tests/test_adr_0182_pool.py` unchanged and green.
- No new imports from serving.
- No change to practice counts unless explicitly measured as byte-identical.

### Dead-weight check

If any old helper remains in `accumulate.py` after extraction, it should be a thin import alias or deleted.

---

## Phase S2 — Add minimal semantic ledger for accumulation

### Where

New files:

```text
generate/derivation/state/model.py
generate/derivation/state/ledger.py
generate/derivation/state/replay.py
```

### What

Represent accumulation as:

```text
SET_STATE(entity, unit, value)
GAIN(entity, unit, value)
LOSS(entity, unit, value)
```

### Why

This is the first true transition layer. It decouples semantic reading from arithmetic replay.

### How

Internal flow for accumulation:

```text
problem_text
  -> quantity-bearing clauses
  -> anchor state transition
  -> change transitions
  -> SemanticLedger
  -> GroundedDerivation replay
  -> existing select_self_verified / classify_derivation
```

`compose_accumulation()` should still return `Resolution | None`.

`accumulation_candidates()` should still return `tuple[GroundedDerivation, ...]`.

### Acceptance

- Clean gain/loss fixtures still resolve.
- New actor still refuses.
- No-change-cue still refuses.
- Multi-change in one clause still refuses.
- Anchor must still be single quantity for strict accumulation.
- Distractor-skip and anchor-skip candidates still classify as expected under pooling.

### Dead-weight check

After this phase, direct manual construction of accumulation `GroundedDerivation` inside `accumulate.py` should be minimal or gone. Replay should own that.

---

## Phase S3 — Add semantic question target wrapper

### Where

New file:

```text
generate/derivation/state/target.py
```

Existing file remains:

```text
generate/derivation/target.py
```

### What

Wrap existing `Target` with semantic target fields:

```text
entity: optional
unit: optional
time_scope: final | prior | unknown
relation: count | difference | aggregate | unknown
```

First implementation can be conservative:

- detect prior-state question using existing `asks_prior_state()`;
- detect final/net questions only when safe;
- leave entity binding as unknown unless the question clearly names the anchor entity;
- refuse unsupported prior targets before replay.

### Why

Temporal and question-scope logic should not live in `pool.py` or in individual composers forever.

### How

Initially:

```text
resolve_pooled() prior-state guard
  -> semantic target refuses prior-state worlds before candidate replay
```

Keep old `asks_prior_state()` as a compatibility helper until all callers migrate.

### Acceptance

- Prior-state minimal pair still refuses:
  - “How much did Lisa have before lunch?” refuses.
- Forward/net twin still resolves:
  - “How much money does Lisa have left?” resolves.
- Body narrative “before” does not trip prior-state refusal.
- “used to make” false positive stays guarded.

### Dead-weight check

Once all prior-state checks route through semantic target, remove direct prior-state guard from `pool.py` or reduce it to a compatibility call.

---

## Phase S4 — Introduce `semantic_state_candidates()` and pool integration

### Where

New public surface:

```text
generate/derivation/state/__init__.py
```

Modified:

```text
generate/derivation/pool.py
generate/derivation/__init__.py
```

### What

Add:

```python
def semantic_state_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]:
    ...
```

Initial implementation delegates to accumulation-backed worlds.

Then change pool ordering from:

```text
accumulation_candidates, multiplicative_candidates, candidate_chains
```

to:

```text
semantic_state_candidates, multiplicative_candidates, candidate_chains
```

### Why

`pool.py` should not need to know every semantic composer. It should ask for semantic-state readings as one candidate source.

### How

Perform this only after equivalence tests prove the candidate set is unchanged for existing fixtures.

### Acceptance

- `pooled_candidates()` de-duplicates as before.
- All ADR-0182 pool tests remain green.
- Clean accumulation still commits.
- Distractor cases still refuse through disagreement.
- Exempt-only still never commits.

### Dead-weight check

Once `pool.py` calls `semantic_state_candidates`, direct import of `accumulation_candidates` from `pool.py` should be removed.

---

## Phase S5 — Add transfer events

### Where

```text
generate/derivation/state/transfer.py
```

or inside:

```text
generate/derivation/state/change.py
```

if small.

### What

Support:

```text
Sam gives Tom 3 apples.
```

as:

```text
Sam.apples -= 3
Tom.apples += 3
```

### Why

Transfer is the first multi-entity state transition. It should be implemented only after entity-owned ledgers exist.

### How

Rules:

- require source entity;
- require target entity;
- require grounded quantity;
- require unit;
- require transfer cue;
- refuse if source/target ambiguous;
- refuse if question target does not identify which resulting state is requested.

### Acceptance

Tests:

```text
Sam has 10 apples. Sam gives Tom 3 apples. How many apples does Sam have? -> 7
Tom has 2 apples. Sam gives Tom 3 apples. How many apples does Tom have? -> 5
Sam gives Tom 3 apples. How many apples does Sam have? -> refuse, no initial state
Sam gives Tom 3 apples. How many apples total? -> refuse until aggregate target exists
```

### Dead-weight check

Do not patch transfer into `accumulate.py`. If transfer needs new helpers, they belong in the semantic-state package.

---

## Phase S6 — Add comparison / difference frames

### Where

```text
generate/derivation/state/compare.py
```

### What

Support safe cases:

```text
Sam has 10 apples. Tom has 7 apples. How many more apples does Sam have than Tom?
```

as:

```text
difference(Sam.apples, Tom.apples) = 10 - 7
```

### Why

Difference questions require target relation binding, not just state replay.

### How

Rules:

- both entity states must be known;
- units must match;
- question must request difference / “more than” / “less than”;
- relation direction must be explicit;
- ambiguous direction refuses.

### Acceptance

- `Sam more than Tom` resolves `Sam - Tom`.
- `Tom fewer than Sam` resolves `Sam - Tom` only if direction is unambiguous.
- Unknown relation direction refuses.
- Same-unit aggregate question does not accidentally become difference.

---

## Phase S7 — Add rate / container frames

### Where

```text
generate/derivation/state/rate.py
```

### What

Support safe product structures:

```text
24 boxes, 12 erasers each -> 24 * 12 erasers
60 miles per hour for 2 hours -> 60 * 2 miles
```

### Why

This is how CORE should eventually distinguish legitimate multiplicative binders from distractor products.

### How

Rules:

- rate must bind two dimensions;
- container count must bind to rate denominator;
- output unit must be rate numerator;
- unrelated foreign state quantities must not be consumed;
- ambiguous “for” adjuncts should remain candidates only if structurally bound.

### Acceptance

- Legitimate rate/container products commit.
- Distractor duration with unrelated target refuses via disagreement or lack of binding.
- Existing correct product cases do not regress.
- Product-of-all fallback remains until semantic rate coverage is measured sufficient.

---

## Phase S8 — Add temporal target replay

### Where

```text
generate/derivation/state/time.py
```

### What

Support:

```text
before
initially
originally
at first
after
now
left
finally
```

as target scope over ledger history.

### Why

Current forward composers compute final/net state. Prior-state questions are correctly refused. The semantic ledger makes prior-state replay possible.

### How

Ledger replay must support:

```text
state at transition index N
state before event E
state after event E
final state
initial state
```

### Acceptance

- “How much did Lisa have before lunch?” returns the pre-spend value only when the event boundary is unambiguous.
- “How much does Lisa have left?” returns final/net state.
- Ambiguous temporal target refuses.

---

## Phase S9 — Held semantic worlds and DAGs

### Where

```text
generate/derivation/state/world.py
generate/derivation/state/dag.py
```

### What

Represent more than one possible semantic world, and eventually derivations where quantities are reused across branches.

### Why

Some GSM8K problems cannot be represented as one left-fold chain. They require branch/reuse structures.

### How

Only after earlier layers are stable:

```text
SemanticWorld candidates
  -> eliminate by constraints
  -> if one survives, replay
  -> if multiple survive and disagree, refuse
  -> if no linear replay possible, emit DAG candidate behind a new gate
```

### Acceptance

- Existing left-fold cases unchanged.
- DAG cases remain sealed until verifier supports them.
- No DAG candidate can commit without a completeness/grounding/target proof equivalent to current `GroundedDerivation` requirements.

---

## 6. Testing strategy

### 6.1 Unit tests

Add tests under:

```text
tests/test_semantic_state_*.py
```

or ADR-numbered tests once an ADR exists.

Required categories:

- model validation;
- referent binding;
- cue polarity;
- semantic ledger construction;
- replay to `GroundedDerivation`;
- prior-state refusal;
- pool equivalence;
- deterministic replay.

### 6.2 Regression tests

Do not weaken existing tests:

- `tests/test_adr_0178_gb3b1_accumulation.py`
- `tests/test_adr_0182_pool.py`
- `tests/test_adr_0175_phase3b_mult_search.py`
- `tests/test_adr_0177_cp2a_training.py`

### 6.3 Lane tests

Every implementation PR must state whether it affects:

- serving;
- sealed practice;
- confuser probe;
- train_sample;
- cue precision reports.

Default for early phases:

```text
serving: unchanged
practice: equivalent until new semantic capability phase
confuser: equivalent until pool candidate source changes
```

### 6.4 Determinism tests

Every semantic object must either:

- be frozen and directly comparable, or
- expose canonical bytes / canonical hash.

Avoid unordered set iteration in emitted outputs. Sets may be used only for boolean membership or cardinality checks, never output ordering.

---

## 7. Documentation strategy

### 7.1 ADR sequence

Suggested:

1. `ADR-0183` — scoped semantic-state transitions.
2. `ADR-0183.S1` — accumulation extraction/refactor into semantic-state substrate.
3. `ADR-0183.S2` — semantic target wrapper.
4. `ADR-0183.S3` — transfer events.
5. `ADR-0183.S4` — comparison/difference frames.
6. `ADR-0183.S5` — rate/container frames.
7. `ADR-0183.S6` — temporal replay.
8. `ADR-0183.S7` — semantic-world hypotheses / DAGs.

### 7.2 Required ADR language

Each ADR must include:

- why this is not a regex grammar template;
- how it preserves wrong=0;
- which composer-local logic it replaces;
- which tests fail if the guard is removed;
- what remains out of scope;
- dead-code/deprecation notes.

---

## 8. Dead weight / cleanup plan

### 8.1 Composer-local semantic helpers

After Phase S1/S2, the following should not remain as private accumulation-only concepts:

- subject-token extraction;
- same-referent check;
- change polarity;
- cue selection;
- anchor-state construction;
- state-change replay.

They should live in semantic-state modules.

### 8.2 Direct prior-state guard in pool

`pool.py` currently performs a prior-state guard because forward composers cannot compute prior target scope. Once semantic targets own temporal scope, this guard should move out of `pool.py`.

### 8.3 Old broad comprehension lifecycle

Do not delete casually. But do not treat it as the active path to promote unless a separate audit proves it has become load-bearing.

Potential future state:

```text
generate/comprehension/state.py       keep / share types / canonical hashing
generate/comprehension/lifecycle.py   retire or demote if still inert
generate/math_parser.py               baseline only, eventual delete after gate
generate/math_candidate_graph.py      thin dispatcher / eventual simplification
```

### 8.4 Product-of-all fallback

Do not delete early. It still protects known product cases. But semantic rate/container frames should eventually reduce reliance on blunt product-of-all candidate generation.

Retirement condition:

- semantic rate/container frames cover protected positives;
- confuser probe remains wrong=0;
- train_sample protected correct cases do not regress;
- cue precision report confirms better candidate readings.

---

## 9. Risks and mitigations

### Risk 1 — resurrecting old pronoun hazards

Mitigation:

- do not use gender-blind most-recent antecedent as a resolver;
- new actor or multiple possible actors should refuse;
- same-referent continuation must be tested with minimal pairs.

### Risk 2 — semantic layer bypasses verifier

Mitigation:

- semantic worlds emit `GroundedDerivation`;
- verifier remains authoritative;
- no semantic world commits directly.

### Risk 3 — hidden composer priority

Mitigation:

- pool candidates across composers;
- refuse on disagreement;
- do not choose first non-`None` where multiple readings exist.

### Risk 4 — grammar-template creep

Mitigation:

- closed lexeme sets only;
- scoped clause splitting only;
- every multi-token cue must be documented as a cue phrase, not a sentence template;
- no broad natural-language parse regexes.

### Risk 5 — line-count growth without payoff

Mitigation:

- every semantic-state phase must identify what it makes obsolete;
- refactor phases must be behavior-equivalent;
- capability phases must show either correct-count increase or wrong-count decrease/refusal improvement.

---

## 10. Recommended immediate next PR

Branch:

```text
feat/adr-0183-semantic-state-accumulation-substrate
```

Scope:

1. Add ADR-0183.
2. Add `generate/derivation/state/__init__.py`.
3. Add `generate/derivation/state/bind.py`.
4. Add `generate/derivation/state/change.py`.
5. Move proven helper logic from `accumulate.py` into those modules.
6. Keep `compose_accumulation()` and `accumulation_candidates()` behavior unchanged.
7. Add tests for extracted helpers.
8. Do not touch serving.
9. Do not change runners.
10. Do not delete old reader files yet.

Acceptance:

```text
existing accumulation tests pass
existing pool tests pass
no serving imports
no behavior change
new helper tests prove referent/polarity guards are non-vacuous
```

---

## 11. Final doctrine

CORE should read word problems as scoped semantic state, not as number bags.

The correct internal progression is:

```text
lexemes
  -> frames
  -> entity-bound state transitions
  -> question-targeted ledger replay
  -> arithmetic proof object
  -> existing verifier
  -> pooled uniqueness/disagreement
```

`accumulate.py` is the proof that this works. `pool.py` is the proof that competing readings should be arbitrated by disagreement. `verify.py` is the proof that wrong=0 can remain the floor.

The next engineering task is to stop letting those ideas remain composer-local and promote them into a clean semantic-state substrate before transfer, comparison, rate, temporal, and DAG logic arrive.
