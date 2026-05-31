# en_core_syntax_v1

Status: implemented candidate  
Scope: foundational language substrate pack  
Pack id: `en_core_syntax_v1`

---

## Purpose

`en_core_syntax_v1` seeds the first foundation-curriculum substrate needed for later claim parsing and relation binding.

The pack does not parse sentences. It establishes the lower-level English vocabulary for speaking about syntax, claim structure, evidence binding, reference, polarity, comparison, coordination, and conditional roles.

This is the first step toward the roadmap rule:

```text
language -> relations -> quantity -> units -> logic -> evidence -> data -> algorithms -> systems -> domains
```

---

## Non-goals

This slice does not implement:

- a natural-language parser
- dependency parsing
- clause extraction
- evidence-span extraction
- claim graph construction
- GSM8K statement classification changes
- relation-binding execution
- new runtime generation behavior

Those are follow-on slices. This pack only ratifies the vocabulary substrate and makes it loadable/resolvable through existing pack infrastructure.

---

## Pack contents

The pack contains 24 reviewed noun entries:

```text
subject
predicate
agent
patient
object
modifier
clause
sentence
phrase
antecedent
consequent
referent
anaphor
qualifier
scope
polarity
coordination
conjunction
disjunction
negation
exception
comparison
attachment
evidence_span
```

Primary namespace families:

```text
syntax.*
claim.*
provenance.*
```

Each lexicon row uses provenance:

```text
foundation_syntax_v1:reviewed:2026-05-30
```

---

## Files

```text
language_packs/data/en_core_syntax_v1/manifest.json
language_packs/data/en_core_syntax_v1/lexicon.jsonl
language_packs/data/en_core_syntax_v1/glosses.jsonl
tests/test_en_core_syntax_v1_pack.py
```

The pack ships both a checksum-sealed `lexicon.jsonl` and a checksum-sealed `glosses.jsonl` companion overlay.

---

## Admission gates pinned by tests

`tests/test_en_core_syntax_v1_pack.py` verifies:

- `load_pack("en_core_syntax_v1")` succeeds;
- manifest checksum matches `lexicon.jsonl` bytes;
- manifest `glosses_checksum` matches `glosses.jsonl` bytes;
- total entry count is 24;
- POS distribution is exactly 24 `NOUN` rows;
- expected lemmas are present in the compiled manifold;
- entry ids are contiguous and zero-padded;
- every lexicon row has reviewed foundation provenance;
- every gloss lemma is resident in the same pack lexicon;
- resolver registration routes syntax lemmas to this pack;
- prior pack lemma routing remains unchanged.

---

## Resolver order

The pack is registered in `chat.pack_resolver.DEFAULT_RESOLVABLE_PACK_IDS` after the polarity pack and before relation/kinship packs:

```text
en_core_polarity_v1
en_core_syntax_v1
en_core_relations_v1
en_core_relations_v2
```

This makes syntax vocabulary available to the same deterministic first-match resolver used by existing English content packs while preserving prior high-frequency lemma ownership.

---

## Follow-on work unlocked

The next slices should use this vocabulary to implement actual relation binding:

```text
evals/language_claim_parsing
evals/language_relation_binding
tests/test_language_claim_parsing.py
tests/test_relation_binding_replay.py
```

Expected follow-on primitives:

- evidence-span extraction
- subject/predicate/argument slot binding
- modifier attachment
- conditional antecedent/consequent binding
- polarity and negation scope
- reference/anaphora target binding
- typed refusal when a required slot lacks evidence

---

## Boundary

This pack is a substrate, not a capability claim. It should not be marked as full language relation binding admission until parser/eval/runtime surfaces exist and pass their own tests.
