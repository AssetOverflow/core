# Pack Unit — `en_core_relations_v1` (Kinship Starter)

**Date:** 2026-05-18
**Author:** Shay
**Pack ID:** `en_core_relations_v1`
**Lemma count:** 8 (kinship-only; deliberately tight)
**Status:** Ratified (checksum verified). **Mounted on the default runtime** as of ADR-0063 (`chat/pack_resolver.py`) — cross-pack surface composers ground kinship lemmas deterministically on the live path.

---

## Why kinship first

Per [`teaching_order.md`](../teaching_order.md) §5 — "Pick *one*
commercial domain and run the full 1→4 progression *inside* that
domain before opening a second domain. Cross-domain triples come
last and only after both domains have ratified their own internal
DAG."

Kinship is the classic starter domain for relation-curriculum work:

- Tight DAG: ~10 primitives + transitive closures over them.
- Doctrinally well-behaved: "teach `parent_of` before `grandparent_of`,
  then `ancestor_of`" maps directly to the formation pipeline's
  prerequisite gates (`ratify.py` G3 — every relation's `head` and
  `tail` must already be mastered).
- Orthogonal to the cognition pack: zero lemma overlap, zero
  semantic-domain prefix overlap. Two pack DAGs ratify in isolation.

---

## What's in v1

Eight kinship lemmas, each carrying ≥2 semantic_domains in a
deterministic taxonomy under `kinship.*`, `lineage.*`,
`biology.*`, `social.*`:

| Lemma | Primary domain | Secondary domains |
|---|---|---|
| `parent` | `kinship.ascendant.direct` | `kinship.parent`, `biology.progenitor` |
| `child` | `kinship.descendant.direct` | `kinship.child`, `biology.offspring` |
| `sibling` | `kinship.lateral.direct` | `kinship.sibling`, `social.peer` |
| `family` | `kinship.unit` | `social.group.kin`, `kinship.group` |
| `ancestor` | `kinship.ascendant.transitive` | `lineage.upward`, `kinship.elder` |
| `descendant` | `kinship.descendant.transitive` | `lineage.downward`, `kinship.successor` |
| `spouse` | `kinship.partner` | `kinship.lateral.affinal`, `social.marriage` |
| `offspring` | `kinship.descendant.direct` | `biology.progeny`, `kinship.child` |

**Note:** `person` is **not** in this pack. It lives in
`en_core_cognition_v1` (which carries it as a cognition primitive
covering "the experiencer of cognitive acts"). The orthogonality
test pins that boundary; if `person` ever drifts between the two
packs, that test fails as a deliberate signal that the domain
DAG boundary needs an ADR.

---

## What's NOT in v1 (and why)

### Pronouns + role-fillers

`mother`, `father`, `son`, `daughter`, `brother`, `sister`, `aunt`,
`uncle`, `cousin`, `grandparent`, `grandchild`, `niece`, `nephew`.

These are **specializations** of the v1 primitives — `mother`
is-a `parent` with a gender filler; `grandparent` is `parent of
parent` (a composed kinship relation). Following teaching-order
doctrine: teach the **atomic** primitives first; specializations
land in a v2 only after the v1 DAG has produced reviewed relation
chains over the primitives.

### Quantifiers + ordinals

`one`, `two`, `many`, `first`, `second`. Useful for kinship
statements ("a person has two parents") but a separate domain
(`en_core_quantification_v1`) with its own DAG. Cross-domain
triples (`one(parent)`, `two(parent)`) come after both domains
ratify internally.

### Verbs of relation

`begets`, `marries`, `descends-from`. These are predicates, not
nouns. The cognition pack carries general predicates already
(`reveals`, `grounds`, `requires`); kinship-specific predicates
will land alongside the first reviewed kinship chains (a
follow-up ADR — there is no `relations_chains_v1.jsonl` yet).

---

## Engagement (default mount as of ADR-0063)

The pack is in the default `RuntimeConfig.input_packs` as of
ADR-0063 (cross-pack surface resolver). Mounting changes the
runtime's mounted manifold (cognition+relations combination) but the
pack-grounded surface composers in `chat/pack_grounding.py` now
consult `chat/pack_resolver.py` for cross-pack lemma residency — so
kinship lemmas ground on the live path:

```
> What is a parent?
parent — pack-grounded (en_core_relations_v1): kinship.ascendant.direct;
kinship.parent; biology.progenitor. No session evidence yet.
```

For development with the pack disabled, opt out:

```python
from core.config import RuntimeConfig
from chat.runtime import ChatRuntime

# Opt-out of the default mount (development only):
defaults = RuntimeConfig().input_packs
cfg = RuntimeConfig(
    input_packs=tuple(p for p in defaults if p != "en_core_relations_v1")
)
rt = ChatRuntime(config=cfg)
```

For full production use, no override is needed — the pack is mounted by
default and the cross-pack resolver finds kinship lemmas automatically.

---

## Verification

```
tests/test_en_core_relations_v1_pack.py        6 passed
  - pack_loads_with_matching_checksum
  - all_expected_lemmas_present
  - each_lemma_carries_expected_primary_domain
  - every_lemma_has_multiple_semantic_domains
  - no_lemma_collision_with_cognition_pack
  - pack_is_not_in_default_input_packs

Lanes (regression):
  core test --suite smoke           67 passed
  core test --suite packs            6 passed
  core test --suite algebra        132 passed
```

The non-negotiable field invariant
(`versor_condition(F) < 1e-6`) is unaffected: this is pure pack
data + a contract test. No runtime code path changed.

---

## Path forward (future ADRs in priority order)

1. **Cross-pack teaching-grounded composition.** ✅ **Landed (ADR-0063).**
   `chat/pack_resolver.py` provides `resolve_lemma(lemma, pack_ids) →
   (resolving_pack_id, semantic_domains)`. Surface composers in
   `chat/pack_grounding.py` consult the resolver; kinship lemmas
   ground on the live path without a separate composer module.
   `chat/teaching_grounding.py` still references the cognition-chains
   corpus only — extending it to a relations-chains corpus is the
   natural next ADR.

2. **First kinship reviewed chains** — a
   `relations_chains_v1.jsonl` or extension of the cognition
   chains to a `domain` field. Triples like
   `(parent, verification, is_a, ancestor)`,
   `(child, verification, is_a, descendant)` form the first
   ratified kinship DAG.

3. **Pronoun + role-filler v2.** Once the v1 DAG produces
   reviewed chains, add `mother`/`father`/`son`/`daughter` as
   specializations.

4. **Cross-domain triples.** After both relations v2 AND
   cognition v1 are mature (and the
   pack-resolver / cross-pack composer exist), open the cross-
   domain frontier — e.g., `family causes belonging`,
   `parent grounds identity`.

---

## Cross-References

- [`teaching_order.md`](../teaching_order.md) — the
  prerequisite-topological doctrine that scoped this pack.
- [Curriculum: cognition saturation v2](cognition_saturation_v2.md)
  — the sibling cognition-pack saturation that produced the 21
  chains the cognition lane composes over today.
- [ADR-0027](../decisions/ADR-0027-identity-packs.md) — pack
  loading + ratification surface that this pack consumes
  unchanged.
- [ADR-0062](../decisions/ADR-0062-composed-teaching-grounded-surface.md)
  — the composed-surface ADR; the relations pack will become
  the second domain that composer composes over, once cross-pack
  composition lands.
