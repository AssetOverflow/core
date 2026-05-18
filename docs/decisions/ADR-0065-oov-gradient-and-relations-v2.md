# ADR-0065 — OOV gradient + relations v2 (Plan Phase 2)

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Phase:** Plan Phase 2 (OOV cliff → gradient)
**Builds on:** ADR-0048 / ADR-0050 / ADR-0052 / ADR-0061 / ADR-0063 / ADR-0064

---

## Context

Phase 1 closed the corpus flywheel: discovery candidates aggregate
into operator-visible signals; the relations pack joined the live
runtime; cross-pack teaching corpora register and surface
deterministically.

But the **vocabulary** layer was still a cliff. When the runtime
saw a token it didn't know — `photosynthesis`, `mitochondria`,
`grandparent` — every cold-start prompt fell through to the flat
universal disclosure:

```
I don't know — insufficient grounding for that yet.
```

That surface was honest but flat. It conveyed no signal that a
*specific* vocabulary gap was hit, offered the operator no concrete
next step, and dropped the gap on the floor — no aggregation, no
queue, no path from "system saw an unknown" to "operator can act
on it".

Phase 2 converts the OOV cliff into a five-tier gradient and closes
the OOV signal into the same flywheel the chain-gap signal closed
in Phase 1.

---

## Decision

### 1. Three new surface tiers (P2.1, P2.2)

The runtime's surface composer now has five honesty tiers, ordered
by available evidence:

| Tier | grounding_source | Example surface |
|---|---|---|
| Vault | `vault` | Walk path, session-grounded |
| Reviewed corpus | `teaching` | `light reveals truth (cognition.truth).` |
| Reviewed lexicon | `pack` | `light — pack-grounded (en_core_cognition_v1): cognition.illumination; logos.core.` |
| **Partial** *(new, P2.2)* | `partial` | `Whatever 'photosynthesis' is, I can ground 'knowledge' — pack-grounded (en_core_cognition_v1): ...` |
| **OOV invitation** *(new, P2.1)* | `oov` | `I haven't learned 'photosynthesis' yet (intent: definition). Mounted lexicon packs: ... . Teach me via a reviewed PackMutationProposal.` |
| Universal disclosure | `none` | `I don't know — insufficient grounding for that yet.` |

The new tiers are *honest gradients*, not synthesized content. Every
visible token in `partial` and `oov` surfaces is either a verbatim
lexicon atom (known side), the safely-displayed user input (OOV
side), or a fixed-template instruction. **No vocabulary is invented.**
**No domain is inferred.**

### 2. New modules

- `chat/oov_surface.py` — `oov_learning_invitation_surface(token,
  intent_tag, pack_ids)`. Returns the OOV surface or `None` (caller
  routes to universal disclosure).
- `chat/partial_surface.py` — `partial_comparison_surface(a, b,
  pack_ids)`. Returns `(surface, known_side)` when exactly one of
  the two compared lemmas resolves, else `None`.
- `teaching/oov_sink.py` — `OOVCandidate` + `OOVBufferSink` +
  `OOVMonthlyFileSink`. Same on-disk shape as the discovery sink.
- `teaching/oov_gaps.py` — `aggregate_oov_gaps(root, since,
  sample_limit) → tuple[OOVGap, ...]`. Pure reader over the OOV
  sink layout.
- `teaching/oov_promotion.py` — `promote_oov_gaps(gaps, threshold,
  include_tainted, suggested_packs) → tuple[OOVPromotion, ...]`.

### 3. Runtime wiring

`chat/runtime.py:_maybe_pack_grounded_surface` was refactored so
every existing intent branch *falls through* on a `None` composer
result instead of early-returning `None`. The OOV invitation
becomes the deterministic fall-through for any clean-subject
prompt whose subject doesn't resolve in any mounted pack.

`ChatRuntime.attach_oov_sink(sink)` mirrors `attach_discovery_sink`
— the runtime emits one `OOVCandidate` JSONL line per turn whose
`grounding_source == "oov"` and is a no-op when no sink is attached.

### 4. Relations pack v2 (P2.4)

`en_core_relations_v2` — 8 pronoun + role-filler lemmas, each a
specialization of a v1 primitive:

| Lemma | Specialization of | Primary domain |
|---|---|---|
| mother | parent | `kinship.parent.female` |
| father | parent | `kinship.parent.male` |
| daughter | child | `kinship.child.female` |
| son | child | `kinship.child.male` |
| brother | sibling | `kinship.sibling.male` |
| sister | sibling | `kinship.sibling.female` |
| grandparent | ancestor (1-step) | `kinship.ascendant.transitive_1step` |
| grandchild | descendant (1-step) | `kinship.descendant.transitive_1step` |

Mounted by default. Orthogonal to v1 and cognition (no lemma
collision). Companion `relations_chains_v2` corpus seeds 7 v2-internal
reviewed chains so v2 lemmas ground via CAUSE + VERIFICATION, not
just DEFINITION/RECALL.

### 5. Two new CLI surfaces

```
core teaching oov-gaps [--top N] [--since YYYY-MM] [--root PATH]
core teaching oov-queue [--threshold N] [--include-tainted]
```

Same shape as `core teaching gaps` / `core teaching queue` from
Phase 1 — operators get a consistent workflow whether the signal is
a chain gap or a lexicon gap.

---

## Operator workflow (closed loop, both axes)

```
operator → core chat
         ← cold turn
           - lemma resolves + chain exists  → teaching surface
           - lemma resolves, no chain       → discovery sink + universal/teaching tier
           - lemma OOV                      → OOV invitation surface + OOV sink
           - one lemma OOV in comparison    → partial surface

operator → core teaching gaps      # chain-gap aggregation
operator → core teaching queue     # chain-gap auto-promotion
operator → core teaching oov-gaps  # vocabulary-gap aggregation
operator → core teaching oov-queue # vocabulary-gap auto-promotion

operator → for chain gaps:        core teaching propose <path>
operator → for vocab gaps:        author PackMutationProposal (ADR-0027 path)
operator →                       core teaching review <id> --accept
```

Two independent signal streams, identical structural shape, both
feed the same reviewed mutation path.

---

## Trust boundaries

- **No content synthesis.** OOV surface names the unknown token
  verbatim (safe-displayed); partial surface composes known-side
  atoms verbatim. Neither composer invents vocabulary or guesses
  domain.
- **Sink emission is opt-in.** Without `attach_oov_sink`, the OOV
  surface still fires (P2.1 is unconditional), but nothing is
  persisted. Identical to the pre-Phase-2 path when no sink is
  attached.
- **Auto-promotion never mutates a pack.** `OOVPromotion` is an
  operator-visible signal; the only path to a real pack change is
  the existing reviewed `PackMutationProposal` (ADR-0027).
- **Suggested packs are mounted-pack list.** The promotion does
  NOT recommend a single destination — domain inference is out of
  scope (would require a stochastic classifier).

---

## Files changed

```
chat/oov_surface.py                              NEW (~125 lines)
chat/partial_surface.py                          NEW (~105 lines)
chat/pack_resolver.py                            relations_v2 added to defaults
chat/runtime.py                                  fall-through refactor + attach_oov_sink + emission
chat/teaching_grounding.py                       relations_chains_v2 registered
core/cli.py                                      oov-gaps + oov-queue subcommands
core/config.py                                   relations_v2 in input_packs defaults
language_packs/data/en_core_relations_v2/        NEW pack (8 lemmas + manifest)
teaching/oov_sink.py                             NEW (~150 lines)
teaching/oov_gaps.py                             NEW (~165 lines)
teaching/oov_promotion.py                        NEW (~120 lines)
teaching/relations_chains_v2/                    NEW corpus (7 reviewed chains)
tests/test_oov_surface.py                        NEW (22 tests)
tests/test_partial_surface.py                    NEW (16 tests)
tests/test_oov_pipeline.py                       NEW (24 tests)
tests/test_en_core_relations_v2_pack.py          NEW (10 tests)
docs/decisions/ADR-0065-oov-gradient-and-relations-v2.md  NEW (this file)
```

---

## Verification

```
tests/test_oov_surface.py                          22 passed
tests/test_partial_surface.py                      16 passed
tests/test_oov_pipeline.py                         24 passed
tests/test_en_core_relations_v2_pack.py            10 passed

Curated lanes (all green):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed

Cognition eval (byte-identical to pre-ADR baseline):
  public:  intent 100% / surface 100% / term 91.7% / closure 100%
  holdout: intent 100% / surface 100% / term 83.3% / closure 100%

Live verification:
  > What is photosynthesis?
    [oov] I haven't learned 'photosynthesis' yet (intent: definition). ...
  > Compare knowledge and photosynthesis.
    [partial] Whatever 'photosynthesis' is, I can ground 'knowledge' ...
  > What is mother?
    [pack] mother — pack-grounded (en_core_relations_v2): kinship.parent.female; ...
  > Why does mother exist?
    [teaching] mother — teaching-grounded (relations_chains_v2): mother precedes daughter ...
```

The non-negotiable field invariant `versor_condition(F) < 1e-6` is
unaffected.

---

## Future ADRs unlocked

- **ADR-0066 — Multi-lemma CAUSE/VERIFICATION partial grounding.**
  Today the partial tier engages only on COMPARISON. CAUSE and
  VERIFICATION carry a single subject; once the intent classifier
  grows multi-lemma extraction (e.g. "Why does photosynthesis
  produce energy?" → CAUSE + subject=photosynthesis + secondary
  object-side hint=energy), partial-grounding extends to those
  intents too.
- **Phase 3 — turn-level composition.** Anaphora / NARRATIVE /
  EXAMPLE intents. Requires Phase 1+2 corpus density first.
- **Domain classifier for OOV promotion suggestions.** Today the
  OOV queue lists every mounted pack. A small deterministic
  domain heuristic (token affix matches a pack's primary domain
  prefix?) could narrow the suggestion — only if it stays
  deterministic and the operator can override.
