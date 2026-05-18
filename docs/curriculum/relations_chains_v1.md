# Curriculum Unit — `relations_chains_v1` (Kinship Seed)

**Date:** 2026-05-18
**Author:** Shay
**Corpus ID:** `relations_chains_v1`
**Pack binding:** `en_core_relations_v1` (1:1, pack-internal only)
**Chain count:** 7
**Status:** Ratified — initial reviewed seed for the kinship domain.

---

## Why this unit

The `en_core_relations_v1` kinship pack was mounted by default in
ADR-0063, but the live teaching-grounded path had no reviewed chains
for any kinship lemma. Every cold-start CAUSE/VERIFICATION on a
kinship prompt fell through to the universal disclosure even though
the lemmas were known.

ADR-0064 closed that gap architecturally (cross-pack teaching corpora
registered, surface composers consult the aggregated index). This
unit closes it operationally — seven hand-authored chains that
exercise every formation gate end-to-end against a fresh corpus.

Per [`teaching_order.md`](../teaching_order.md) §5 — "Pick *one*
commercial domain and run the full 1→4 progression *inside* that
domain before opening a second domain. Cross-domain triples come
last and only after both domains have ratified their own internal
DAG." Every chain in v1 is therefore **strictly pack-internal** to
`en_core_relations_v1`. Cross-domain triples (e.g. `family grounds
identity` with `identity` from cognition) are deliberately deferred.

---

## The seven chains

| Chain ID | Subject | Intent | Connective | Object |
|---|---|---|---|---|
| `cause_parent_precedes_child` | parent | cause | precedes | child |
| `cause_child_follows_parent` | child | cause | follows | parent |
| `cause_ancestor_precedes_descendant` | ancestor | cause | precedes | descendant |
| `cause_descendant_follows_ancestor` | descendant | cause | follows | ancestor |
| `cause_family_grounds_parent` | family | cause | grounds | parent |
| `verification_child_requires_parent` | child | verification | requires | parent |
| `verification_descendant_requires_ancestor` | descendant | verification | requires | ancestor |

Pack-residency: every subject ∈ `en_core_relations_v1`, every
object ∈ `en_core_relations_v1`. Zero cognition-pack atoms.

Predicate residency: every connective (`precedes`, `follows`,
`grounds`, `requires`) already exists in
`generate.semantic_templates._PREDICATE_HUMANIZE`. No new
predicates introduced in this seed.

---

## Coverage

Five of the eight ratified relations lemmas (`parent`, `child`,
`ancestor`, `descendant`, `family`) receive at least one chain.
Three lemmas (`sibling`, `spouse`, `offspring`) are intentionally
deferred to a future curriculum unit — they need lateral / affinal /
descendant-direct chains that compose more naturally once the v1
ancestor-descendant axis is in place.

---

## Live verification

```
$ core chat
> Why does parent exist?
parent — teaching-grounded (relations_chains_v1):
kinship.ascendant.direct; kinship.parent. parent precedes child
(kinship.descendant.direct). No session evidence yet.
grounding_source = teaching

> Does child require parent?
child — teaching-grounded (relations_chains_v1):
kinship.descendant.direct; kinship.child. child requires parent
(kinship.ascendant.direct). No session evidence yet.
grounding_source = teaching
```

Every kinship CAUSE/VERIFICATION prompt covered by the seed now
emits a deterministic teaching-grounded surface tagged with the
resolving corpus id (`relations_chains_v1`), not the cognition tag.

---

## Provenance

Every line carries:

```
"provenance": "adr-0064:reviewed:2026-05-18:relations_seed_v1"
```

This is the **direct-append seed pattern** — the same shape used
when the cognition corpus was originally seeded pre-ADR-0055
(provenance `adr-0052:reviewed:...`, `adr-0053:reviewed:...`).
The propose/replay/accept pipeline is for *additions* once a
corpus has chains to baseline against; for an empty-corpus seed,
the replay gate has no baseline and direct append is the
correct surface.

Future chains added to `relations_chains_v1` must go through the
propose/replay/accept pipeline. The seed is the only direct-write.

---

## Eval impact

The cognition lane is **byte-identical** — cognition lemmas resolve
to the cognition corpus first and the orthogonal-pack invariant
prevents any (subject, intent) collision. Public/holdout splits
remain at:

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

Relations-domain coverage opens on the live path but is not yet
measured by a dedicated eval lane. A `relations` lane is the
natural follow-up.

---

## Path forward

1. **`relations` eval lane.** Mirror the cognition lane harness with
   relations-domain prompts. Use the seven chains as ground truth.
2. **`sibling`/`spouse`/`offspring` chains** — extend the seed to
   cover the remaining ratified lemmas.
3. **Pronoun + role-filler v2** — `mother`/`father`/`son`/`daughter`
   chains as specializations of v1's primitives.
4. **Cross-domain triples** — only after the relations corpus is
   internally saturated. Then `family grounds identity`,
   `parent informs experience`, etc.

---

## Cross-References

- [ADR-0064](../decisions/ADR-0064-cross-pack-teaching-chains.md) —
  the architectural unlock that made this seed possible.
- [Pack: `en_core_relations_v1`](relations_pack_v1.md) — the lexicon
  this corpus is bound to.
- [`teaching_order.md`](../teaching_order.md) §5 — the
  prerequisite-topological doctrine.
- [Cognition saturation v2](cognition_saturation_v2.md) — the
  sibling cognition curriculum unit.
