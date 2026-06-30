# ADR-0210 — L10 finite grounding pack and adversarial wrong=0 fixtures

Status: Proposed  
Date: 2026-06-05  
Scope: Additive pack + additive eval fixtures only  
Branch: `feat/l10-grounding-pack-evals-adr`

## Context

CORE is migrating toward an L10 runtime thread: a stateless, hyper-efficient, content-addressed execution layer. The transition must preserve CORE's existing doctrine: deterministic replay, refusal before invention, finite proof surfaces, and geometric reasoning over compiled structure rather than probabilistic guessing.

The immediate failure class is not arithmetic. It is relational grounding. A system that treats vacuous universals, unbound existentials, or contradictory premise sets as license to fabricate relational links will pass superficial natural-language tests while violating CORE's wrong=0 doctrine.

This ADR proposes an additive seed pack and an additive adversarial fixture set for the L10 transition. No existing runtime, parser, solver, loader, or pack is modified.

## Decision

Adopt `language_packs/data/l10_grounding_v1/` as the first L10-oriented grounding pack.

The pack contains finite-domain relational primitives only:

- finite entity grounding
- witness binding
- range restriction
- guarded universal
- grounded existential
- vacuous-truth refusal guard
- contradiction barrier
- no-explosion barrier
- finite-domain closure
- undecidable-refusal mapping

Every lemma is namespaced with `l10_` to avoid global lemma collisions. The pack manifest uses `oov_policy = "fail_closed"` and declares `l10_stateless = true`.

Adopt `evals/deductive_logic/fixtures/l10_adversarial.jsonl` as independent-gold adversarial cases for wrong=0 behavior. Gold labels are symbolic, not model-inferred. The fixture set explicitly covers vacuous truth, range restriction, contradictory premises, unbound existential witnesses, finite closure, and no-explosion refusal.

## Relationship to CORE-AI geometric reasoning doctrine

CORE's geometric doctrine requires that meaning be carried through stable structure and admissible transformations, not guessed associations. L10 grounding preserves that doctrine by refusing to project an ungrounded relational edge into the substrate.

For a future L10 compiler, these primitives should lower into content-addressed operators whose admissibility depends on explicit finite witnesses and guards. A universal over an empty guard may be logically vacuous, but it must not create an entity-specific rotor edge. A contradictory premise set may identify a real boundary, but it must not explode into arbitrary entailments.

## Stateless execution alignment

The pack and fixtures are L10-compatible because:

1. All rows are self-contained JSON records.
2. No row depends on mutable global state, online lookup, model inference, or hidden cache.
3. All fixture gold labels are derivable from finite premise lists.
4. The fixture format includes explicit `finite_domain`, `premises`, `query`, `gold`, and `symbolic_resolution` fields.
5. OOV behavior is fail-closed by manifest declaration.

## Wrong=0 doctrine

The expected wrong value for every fixture is `0`. Any uncertain or inconsistent proposition must resolve to `refuse`, not a guessed truth value.

This is especially load-bearing for:

- vacuous universals with no explicit witness
- existential claims without a bound witness
- range-restricted rules whose guard is not satisfied
- premise sets that derive incompatible heads
- contradictory entity facts

## Checksums

- `language_packs/data/l10_grounding_v1/lexicon.jsonl`: `829efd10d7f5fa74f1189ec6d621f2a12bc5e7a022fd7a3de436655fc8fe5603`
- `evals/deductive_logic/fixtures/l10_adversarial.jsonl`: `beda988f019b5431a3ab6e817b463a165bde719c7597f3b6a7f572107e1db123`

## Consequences

Positive:

- Establishes a clean L10 seed surface without refactoring existing code.
- Gives the wrong=0 gate concrete adversarial cases before the L10 runtime exists.
- Prevents hallucinated relation links from being treated as legitimate inference.

Negative / deferred:

- No runtime loader is added in this PR.
- No test harness is added in this PR.
- Reconciled with the existing ADR registry at merge: numbered `ADR-0210`
  (the originally requested `adr-012-l10-grounding.md` collided with the
  existing `ADR-0012-core-ingest-governance-layer.md` and did not follow the
  `ADR-NNNN` convention).

## Open reconciliation item (must resolve before the fixtures are wired)

The adversarial fixtures encode two different responses to "the query
subject is in `finite_domain` but the guard relation is unsatisfied":

- `l10-adv-003` resolves to `label: false` / `VERIFIED` (the subject is
  grounded in the same relation sort — `member(alice, team_red)` — just not
  the guarded value, so closed-world negation makes the query false).
- `l10-adv-008` resolves to `label: refuse` / `SCOPE_BOUNDARY` (the subject
  is grounded only in a *different* sort — `asset(asset_1)`, not
  `account(...)` — so the rule's range is type-incommensurate and the engine
  refuses rather than concluding false).

That distinction (same-sort negative ⇒ `false`; cross-sort/type-mismatch ⇒
`refuse`) is defensible but is not yet stated as a single decision
procedure. A future symbolic runner (verification-plan item 4) MUST encode
the discriminating principle explicitly before these labels become a live
oracle; otherwise the two cases are an inconsistent gold and would not be a
sound independent check. Until then the fixtures are an inert proposal, not
a wired wrong=0 lane.

## Verification plan

To be completed in the Claude lane or local CI after review:

1. Confirm all `lemma` values in `l10_grounding_v1/lexicon.jsonl` are globally unique across every pack.
2. Confirm the lexicon checksum matches the manifest checksum.
3. Confirm the adversarial fixture checksum matches this ADR.
4. Add a future symbolic runner that derives each fixture gold label without model inference.
5. Require wrong=0: no false positives, no hallucinated links, no ex-falso entailment.

## Non-goals

- No serving-code mutation.
- No eval-runner mutation.
- No parser mutation.
- No loader mutation.
- No new dependency.
- No empirical claim that the fixtures pass before they are run.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
