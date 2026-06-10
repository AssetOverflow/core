# ADR-0184 S3–S5 — the semantic-ledger candidate-source boundary

**Date:** 2026-06-10
**Scope:** design for the boundary stack between the S2 semantic-state ledger and the
existing derivation candidate/verification system, plus the first load-bearing slice
(implemented in the accompanying PR).
**Authority unchanged:** `generate/derivation/verify.py` and `generate/derivation/pool.py`
remain the sole commit authority. Nothing in this stack may commit an answer.

## 0. Numbering reconciliation

The mission brief numbers the boundary stack S3–S5. ADR-0184 §7 already assigns
S3 = semantic target wrapper, S4 = semantic candidate source to pool, S5 = transfer
events. To avoid corrupting the repo's durable numbering, **code and tests use the
ADR's numbering**; this note carries the mapping:

| Brief | Content | ADR-0184 §7 |
|---|---|---|
| S3 | candidate-source adapter boundary (this PR) | **S4** (pool source swap) |
| S4 | replay/provenance equivalence boundary | new — proposed as **S4b** amendment |
| S5 | first narrow semantic-primary path | **S3** (semantic target) then **S5** (transfer) |

The ADR's S3 (semantic target wrapper) is *not* skipped — it is re-sequenced as a
prerequisite of the first semantic-primary path, because question/target binding is
what makes a semantic-only world safe to expose. The pool source swap (ADR S4) has no
dependency on the target wrapper: it is a byte-equivalent re-plumbing, and ADR-0184
§11.3 requires it for the ADR to move to Accepted.

## 1. The current legacy candidate path

The derivation lane (sealed; no serving import) resolves a problem like this:

```text
composers (each emits ungated GroundedDerivation candidates)
  accumulate.accumulation_candidates   — 3 readings: strict, distractor-skip, anchor-skip
  search.multiplicative_candidates     — in-clause products
  multistep.candidate_chains           — target-guided bounded search
  goal_residual.build_goal_residual    — ADR-0207 R4
        |
        v
pool.pooled_candidates  — dedup by (answer, start token, step tokens), fixed order
        |
        v
pool.resolve_pooled     — classify_derivation (complete/exempt/None) per candidate;
                          refuse on prior-state question, on zero verifying readings,
                          on disagreement, on exempt-only; commit sole complete answer
```

`compose_accumulation` separately gates the strict reading through
`select_self_verified` for the practice lane. The committed serving metric is owned by
the candidate-graph reader, a disjoint organ; nothing here touches serving.

**The parser-patch accumulation problem.** Historically each new problem shape landed
as a local composer/matcher patch (the pattern ADR-0175 warns against). ADR-0184's bet
is that capability should instead land as new *transition kinds* over the semantic
ledger plus replay rules — one reading layer, not N parser patches. For that to ever
be true, ledger output needs a single, governed entry point into the candidate pool.
That entry point is what this stack defines.

## 2. What S2 added (PR #684)

- `state/model.py` — frozen `SemanticQuantity` / `StateKey` / `StateTransition` /
  `SemanticLedger`, closed op set `{set, gain, loss}`, structural validation
  (`SemanticStateError`), unit typed `str` (`""` = unitless) to match the extractor
  and prevent a `None`-vs-`""` key-identity split.
- `state/ledger.py` — `build_accumulation_ledger`: the proven single-referent
  gain/loss reading expressed as SET + GAIN/LOSS transitions over one entity/unit key.
- `state/replay.py` — `replay_accumulation_ledger`: the ONLY bridge from ledger to
  `GroundedDerivation` (set→start, gain→add, loss→subtract, change operands inherit
  the anchor unit). Refuses non-SET start, cross-key mutation, non-gain/loss ops.
- `accumulate.py` rerouted both reading builders through build+replay.
- Proven behavior-equivalent: byte-for-byte differential over 937 GSM8K problems,
  0 differences.

After S2, the ledger exists and is exercised, but the *candidate enumeration* (which
worlds exist for a problem) still lives privately in `accumulate.py`, and `pool.py`
still imports `accumulation_candidates` — a composer-named surface, not a
semantic-state surface. There is no single place where ledger worlds become pool
candidates.

## 3. What the semantic ledger can already express / cannot yet express safely

**Can express (S2):** linear single-key histories — one entity/unit `StateKey`, a SET
anchor, ordered GAIN/LOSS deltas with licensed cues; build-time distractor-skip
(in-clause foreign-unit drop) and anchor-skip (leading non-anchorable block) readings.

**Cannot yet express safely:**

- multi-key worlds (transfer: `Sam gives Tom 3` needs two keys + a conservation law);
- question/target binding (no TARGET transition; the pool's prior-state guard is the
  only temporal scope check, and it lives outside the ledger);
- comparison/difference relations; rate/container products (op set excludes
  multiply/divide by design);
- temporal scoping (prior-state replay);
- competing worlds as first-class objects (the pool sees only flattened candidates);
- candidate provenance (a `GroundedDerivation` in the pool does not carry which
  ledger produced it).

Every one of these stays out of the candidate path until its own phase lands with
refusal-first tests.

## 4. The correct adapter boundary (brief-S3 / ADR-S4 — this PR)

One new module, `generate/derivation/state/source.py`, owns world enumeration and the
ledger→candidate conversion:

```text
accumulation_world(text, drop_isolated_foreign)   -> SemanticLedger | None
anchor_skip_world(text)                           -> SemanticLedger | None
accumulation_ledger_worlds(text)                  -> tuple[SemanticLedger, ...]
semantic_state_candidates(text)                   -> tuple[GroundedDerivation, ...]
```

`pool.py` swaps its accumulation source from `accumulate.accumulation_candidates` to
`state.source.semantic_state_candidates` (the ADR §7-S4 swap, verbatim).
`accumulate.py` keeps its public surfaces (`compose_accumulation`,
`accumulation_candidates`) as thin compatibility wrappers per ADR §10, so every
existing consumer (practice runners, tests) is untouched.

Boundary properties (each pinned by a test):

1. **Output type is inert.** The boundary emits only `GroundedDerivation` — a value
   model with no commit semantics. Acceptance/refusal happens only in verify/pool.
2. **No authority import.** Nothing under `generate/derivation/state/` imports
   `verify`, `pool`, or names `Resolution` / `select_self_verified` /
   `classify_derivation` / `self_verifies` / `resolve_pooled`. A structural AST scan
   (with a predicate self-test so it cannot be vacuous) enforces this.
3. **Fail-closed.** A world that cannot be built (`None`) or a ledger replay that
   refuses contributes *nothing* — never a placeholder or synthesized candidate.
4. **Deterministic order** — strict, distractor-skip, anchor-skip — byte-identical to
   the legacy enumeration including duplicates (pool dedup is unchanged).

Why the pool swap is in the same PR as the adapter: an adapter with no consumer is a
dead organ (the router-organ-hygiene precedent, PR #646) and a "schema-defined proof
obligation" with no executing test. The swap is what makes the boundary load-bearing,
and ADR-0184 §11.3 makes it an explicit acceptance criterion.

## 5. What verifier/pool need to see (and must keep seeing)

Unchanged tuples of `GroundedDerivation` whose operand `source_token`s, cues, and
units come from the problem text. Three properties of the current pool behavior are
load-bearing and must not drift:

- the **exempt rival readings** (distractor-skip, anchor-skip) must still be emitted —
  ADR-0182's disagreement refusals depend on them; dropping one can unmask a unique
  *wrong* commit;
- **candidate multiplicity and order** presented to pool dedup must be identical
  (order determines which derivation object a commit reports);
- **unit inheritance** (change operands take the anchor unit) must be preserved, since
  classification (complete/exempt) keys off used/unused units.

## 6. Failure modes that would create wrong=0 violations

| # | Failure mode | Defense |
|---|---|---|
| 1 | Lost exempt rival reading → disagreement disappears → unique wrong commit | byte-equivalence differential (937 problems); anchor-skip/distractor-skip presence tests |
| 2 | Reorder/dedup drift → different committed derivation object | identical enumeration order pinned by test; pool dedup untouched |
| 3 | Fabricated semantics — a candidate with no deriving ledger, or replay unfaithful to transitions | S2 replay is the only bridge; brief-S4 adds the faithfulness checker before any semantic-only world |
| 4 | Exception swallowing — structural invalidity (`SemanticStateError`) silently became "no candidate" | the boundary catches nothing; structural errors propagate loudly |
| 5 | Direct commit path from `state/` | structural no-authority-import scan (non-vacuous) |
| 6 | Unit-inheritance drift → classification flips | replay untouched; inheritance test exists in S2 suite |
| 7 | Future semantic world emits verifying-but-wrong candidates (soundness ≠ correctness) | out of scope for S3/S4 by construction (no new worlds); brief-S5 requires refusal-first acceptance + sealed gold tether before any new world enters the boundary |

## 7. Tests proving semantic candidates cannot bypass verifier/pool

- structural: no module under `state/` imports verify/pool or names any commit
  surface (AST scan + predicate self-test on a known-violating snippet);
- behavioral: a boundary candidate that fails verification (ungrounded against the
  actual problem text) never commits; rejection (no world) yields `()` and the pool
  refuses or falls through to other composers exactly as before;
- the pool's own wrong=0 obligations (disagreement refusal, exempt-only never
  commits, prior-state guard) re-run green against the swapped source;
- delegation equality: `accumulation_candidates(text) == semantic_state_candidates(text)`
  across the canonical case battery;
- 937-problem byte-for-byte differential vs `main` (local harness, reported in PR).

## 8. The S3–S5 sequence (brief numbering)

**S3 (this PR, = ADR S4).** Adapter boundary + pool source swap, byte-equivalent.
No new capability; no serving, CLAIMS, metric, or lane-pin movement.

**S4 (next, = proposed ADR S4b amendment).** Replay/provenance equivalence boundary —
the precondition for any semantic-only world:

- an internal provenance record binding each emitted candidate to the ledger that
  produced it (`(ledger, derivation)`), so a candidate cannot exist at the boundary
  without a deriving ledger;
- a structural `replay_is_faithful(ledger, derivation)` checker — steps correspond 1:1
  to transitions (set→start, gain→add, loss→subtract), values/source tokens/cues
  equal, unit-inheritance rule respected — wired into tests so an unfaithful replay
  fails loudly;
- a committed equivalence harness (legacy-twin vs boundary) so the legacy enumeration
  in `accumulate.py` can later be deleted without losing the equivalence proof.

**S5 (after S4, = ADR S3 then ADR S5).** First narrow semantic-primary path — the
first reading that exists *only* as a ledger:

1. land ADR S3 (semantic target wrapper: entity/unit/time-scope/relation binding,
   conservative, preserving the prior-state refusals) — question binding is what makes
   a multi-key world answerable;
2. then ADR S5 transfer events as the first semantic-primary world: two-key ledgers,
   replay restricted to the question-bound key, refusing ambiguous source/target, no
   initial state, or unbound questions;
3. entry only through `semantic_state_candidates`; commit only through the unchanged
   verify/pool; refusal-first acceptance tests plus sealed-lane gold tether before any
   committed metric may move (and then only via ratified PR).

If at any point a semantic world needs the verifier to change to be admissible, that
is a stop signal, not an integration task.

## 9. What is deliberately NOT in this PR

No serving/runtime edits; no CLAIMS/metric/lane-pin movement; no new readings or
capability; no parser changes; no deletion of legacy surfaces (compat wrappers stay
per ADR §10 until brief-S4's committed equivalence harness exists); no provenance
record yet (S4); no transfer/target/temporal work (S5+).
