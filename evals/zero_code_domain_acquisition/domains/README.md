# Domain Authoring Kits

Three surprise domains for testing CORE's extensibility contract. Each domain provides a complete pack-only authoring kit.

## Kit Structure

Each domain directory contains:

- `vocabulary.jsonl` — Lexicon entries (nouns, verbs, predicates) in pack format
- `relations.txt` — List of domain-specific relation predicates (one per line)
- `axioms.jsonl` — Ground-truth propositions defining the domain (subject/predicate/object triples)
- `teaching_examples.jsonl` — ~20 reviewed teaching events for the teaching loop
- `prompts_dev.jsonl` — ~10 dev articulation prompts (PropositionGraph → surface)

## Domains

### D1: Kinship Relations
Relations between people: parent/child, sibling, spouse, ancestor/descendant, relative.

Core predicate: `is_parent_of`, `is_child_of`, `is_sibling_of`, `is_spouse_of`, etc.

### D2: Calendar Relations
Temporal ordering: weekdays, months, seasons, containment relationships.

Core predicates: `precedes`, `follows`, `occurs_in`, `contains`.

### D3: Color Taxonomy
Color properties and relationships: warmth, brightness, similarity, opposition, containment.

Core predicates: `is_warmer_than`, `is_cooler_than`, `is_lighter_than`, `is_darker_than`, `is_opposite_of`, etc.

## Usage Protocol

To test domain acquisition:

1. Load the domain's `vocabulary.jsonl` into a new language pack
2. Register the domain's relations in the relation manifest
3. Seed the vault with the `axioms.jsonl` (optional; tests "cold start" if omitted)
4. Apply `teaching_examples.jsonl` through the teaching loop
5. Run `prompts_dev.jsonl` through the realizer and score against acceptance criteria

## Success Criteria

Each domain must independently achieve:
- >=80% accuracy on dev prompts (no engineering required)
- >=75% accuracy on holdout prompts (no engineering required)

An empty engineering gap log at completion means CORE's extensibility contract is solid.
