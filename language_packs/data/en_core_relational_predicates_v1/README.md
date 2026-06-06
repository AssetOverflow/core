# en_core_relational_predicates_v1

Proposal-only curated English relational-predicate pack for finite-entity grounding.

This pack is intentionally compact. It is not a bulk corpus and is not mounted by
default. It contributes binary predicate surfaces only, leaving existing noun,
adverb, and adposition packs untouched.

## Scope

- Kinship predicates: `parent_of`, `child_of`, `sibling_of`, `spouse_of`
- Ordering/comparison predicates: `less_than`, `greater_than`, `equal_to`, `distinct_from`
- Spatial predicates: `left_of`, `right_of`, `inside_of`, `adjacent_to`
- Temporal predicates: `before_event`, `after_event`, `during_event`, `overlaps_event`

## Curation rules

- Deterministic lexical order: kinship, ordering/comparison, spatial, temporal.
- One row per lemma.
- Every lemma spans at least two semantic domains through `semantic_domains`.
- Surfaces are predicate-shaped to avoid collisions with prior mounted lexical
  surfaces such as `parent`, `child`, `left`, `before`, and `after`.
- `gate_engaged` is `false`; this remains pending review and runtime admission.

## Collision audit

Audited candidate lemmas against the explicitly requested packs:

- `en_core_relations_v1`
- `en_core_cognition_v1`

Additional adjacent mounted/content packs checked while drafting:

- `en_core_relations_v2`
- `en_core_spatial_v1`
- `en_core_temporal_v1`

No proposed lemma duplicates a reviewed lemma observed in those packs. The pack
therefore avoids the reverted-pack failure mode where natural-language lemmas
collided with existing mounted entries.

## Checksum

`lexicon.jsonl` SHA-256:

```text
5f3615c69e583b9e1891afd73b90786e5ec563400b24706dbbccb1b4dccef63a
```
