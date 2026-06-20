# Foundational Family Specification: Quantity-Entity Binding

Status: Proposed (gating specification)
Related ADRs: ADR-0223, ADR-0224
Domains: Arithmetic/Quantitative, Physical Science, Charts/Tables/Data, Social Studies
Summary:
This family defines the structural binding of a quantified scalar value to the semantic entity, object, or category it measures. Quantity-entity binding is the foundational prerequisite for all relational reasoning: before a rate, partition, comparison, or state change can be computed, the quantities themselves must be unambiguously anchored to their semantic referents.

Surface / chunk patterns:
- `<number> <noun>` (e.g., "5 apples", "12 grams")
- `<number> of the <noun>` (e.g., "three of the boxes")
- `<noun>: <number>` (e.g., "Population: 50,000", "Red group: 12")
- `<number> <unit> of <material>` (e.g., "5 kg of iron")

Semantic neighborhood:
- `quantified_group`
- `measured_property`
- `category_cardinality`
- `resource_population`

Construction signatures:
```text
Signature: quantity_entity_binding
Future adapter: quantity_entity_adapter
Relation Type: quantity_entity
```

Required roles:
- `quantity`: The GroundedMention pointing to a ScalarCandidate representing the numerical value (including fractions, percents, or integers).
- `entity`: The GroundedMention pointing to the noun, noun phrase, or category that the quantity measures.

Optional roles:
- `unit`: The GroundedMention pointing to the measurement unit (e.g., "meters", "dollars"), if the quantity is dimensional.

Hazards / confusers:
- `PF-EN-002 quantity_entity_unbound`: A quantity appears adjacent to another quantity modifier rather than a noun (e.g., "3 more").
- `PF-LX-004 span_collision`: Numeric homophones or compound words leading to overlapping/competing scalar candidate spans (e.g., "one half-hour" -> "one", "one half", "half-hour").
- `PF-EN-005 role_alias_collision`: Same surface denotes different subgroups or objects (e.g., "5 red apples and 3 green ones" where "ones" is an alias for "apples").
- `PF-HZ-005 conflict_auto_resolved`: Confused reference mapping when multiple entities of the same category are mentioned in close proximity.

ProblemFrame / domain-frame representation:
```python
# Typed bindings and relations representing quantity-entity alignment
from dataclasses import dataclass

@dataclass(frozen=True)
class GroundedMention:
    mention_id: str
    surface: str
    start: int
    end: int
    fact_id: str | None = None  # Links to GroundedScalar, GroundedUnit, etc.

@dataclass(frozen=True)
class MentionBinding:
    binding_id: str
    binding_type: str  # "quantity_entity" | "quantity_unit"
    source_mention_id: str  # GroundedMention.mention_id of quantity
    target_mention_id: str  # GroundedMention.mention_id of entity/unit
```

ContractAssessment readiness criteria:
A candidate quantity-entity binding reaches `RUNNABLE` status if and only if:
1. The quantity mention is successfully grounded to a parsed `GroundedScalar` with exact numeric fraction values (`PF-LX-001` resolved).
2. The entity mention is successfully resolved to a valid noun phrase or category within the sentence span (`PF-EN-001` resolved).
3. No active overlap or span collisions exist (`PF-LX-004` resolved).
4. No unresolved hazard category is active (e.g., `quantity_entity_unbound` checks pass).

Verification style:
- Invariance under lexical substitution (e.g., substituting "apples" with "oranges" must result in identical binding topology, modulo spans).
- Confuser rejection (e.g., "3 more than 5" must bind "5" to its entity and flag "3" as comparative, refusing generic binding for "3").

Refusal conditions:
- Presence of unresolved ambiguous referents (e.g., "them" or "ones" in "there are 5 apples and 3 of them" when multiple candidate entities are active and ungrounded).
- Multi-scalar overlap collisions that cannot be deterministically ordered.

Cross-domain evidence:
1. **Physical Science (Measurement):**
   - *Example:* "A block of iron has a mass of 12 grams."
   - *Bindings:*
     ```python
     GroundedMention(mention_id="m-qty", surface="12", start=34, end=36, fact_id="scalar-0001")
     GroundedMention(mention_id="m-unit", surface="grams", start=37, end=42, fact_id="unit-0001")
     GroundedMention(mention_id="m-entity", surface="iron", start=10, end=14, fact_id="entity-0001")
     
     MentionBinding(binding_id="b-qty-ent", binding_type="quantity_entity", source_mention_id="m-qty", target_mention_id="m-entity")
     MentionBinding(binding_id="b-qty-unit", binding_type="quantity_unit", source_mention_id="m-qty", target_mention_id="m-unit")
     ```
2. **Charts/Tables (Category Counts):**
   - *Example:* "The bar graph shows: Apples: 15, Bananas: 8."
   - *Bindings:*
     ```python
     GroundedMention(mention_id="m-qty-1", surface="15", start=32, end=34, fact_id="scalar-0001")
     GroundedMention(mention_id="m-ent-1", surface="Apples", start=24, end=30, fact_id="entity-0001")
     GroundedMention(mention_id="m-qty-2", surface="8", start=46, end=47, fact_id="scalar-0002")
     GroundedMention(mention_id="m-ent-2", surface="Bananas", start=36, end=43, fact_id="entity-0002")
     
     MentionBinding(binding_id="b-qty-ent-1", binding_type="quantity_entity", source_mention_id="m-qty-1", target_mention_id="m-ent-1")
     MentionBinding(binding_id="b-qty-ent-2", binding_type="quantity_entity", source_mention_id="m-qty-2", target_mention_id="m-ent-2")
     ```
3. **Social Studies (Demographics):**
   - *Example:* "The town of Shelbyville has a population of 50,000 residents."
   - *Bindings:*
     ```python
     GroundedMention(mention_id="m-qty", surface="50,000", start=47, end=53, fact_id="scalar-0001")
     GroundedMention(mention_id="m-ent-town", surface="Shelbyville", start=12, end=23, fact_id="entity-0001")
     GroundedMention(mention_id="m-ent-pop", surface="residents", start=54, end=63, fact_id="entity-0002")
     
     MentionBinding(binding_id="b-qty-ent", binding_type="quantity_entity", source_mention_id="m-qty", target_mention_id="m-ent-pop")
     ```
4. **Arithmetic / GSM-style Pressure Lane:**
   - *Example:* "Joan has 5 marbles. She gives 3 marbles to Todd."
   - *Bindings:*
     ```python
     GroundedMention(mention_id="m-qty-1", surface="5", start=9, end=10, fact_id="scalar-0001")
     GroundedMention(mention_id="m-ent-1", surface="marbles", start=11, end=18, fact_id="entity-0001")
     GroundedMention(mention_id="m-qty-2", surface="3", start=31, end=32, fact_id="scalar-0002")
     GroundedMention(mention_id="m-ent-2", surface="marbles", start=33, end=40, fact_id="entity-0001")
     
     MentionBinding(binding_id="b-qty-ent-1", binding_type="quantity_entity", source_mention_id="m-qty-1", target_mention_id="m-ent-1")
     MentionBinding(binding_id="b-qty-ent-2", binding_type="quantity_entity", source_mention_id="m-qty-2", target_mention_id="m-ent-2")
     ```

Serving status: Not implemented / not serving.
Current state relies on ad-hoc regex heuristic extraction within local parsers. Assessment-backed proposal traces for selected math constructions exist in diagnostics, but general CGA/substrate retrieval does not yet support this family.

Implementation authorization:
**NOT AUTHORIZED.** This is a constitutional specification file only. Implementation requires a separate, evidence-backed implementation plan and PR.
