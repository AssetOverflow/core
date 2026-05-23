# Bounded Grammar Specification (v1)

This specification defines the deterministic subset of English grammar recognized by the math expert parser (`generate/math_parser.py`) for the composite math-expert gate (ADR-0131).

Word problems outside this bounded grammar are cleanly refused at the parser level (or downstream at the binding-admissibility level). Within this grammar, the end-to-end pipeline achieves 100% correctness.

---

## 1. Terminology

- `<Entity>`: A title-cased proper noun (e.g. `Sam`, `Alice`, `Sarah`) or a definite-article collective (e.g. `the boys`, `the girls`).
- `<Number>`: A numeric digit sequence (e.g. `5`, `12`, `0.50`) or a supported word-form integer (e.g. `one` through `twelve`).
- `<Unit>`: A lowercase noun denoting count or dimension (e.g. `apples`, `marbles`, `dollars`, `feet`, `seconds`). Any unit used must either be registered in `en_units_v1` or be part of the allowed generic count nouns set.
- `<Place>`: A title-cased proper noun or word group denoting a location (e.g. `the box`, `the basket`).

---

## 2. Sentence Templates

### A. Initial Possession (Introducing state)

1. **Active Entity Possession**
   - **Template**: `<Entity> has <Number> <Unit>.`
   - **Example**: `Sam has 5 apples.`
   - **Graph Mapping**: Adds `entity` to `entities`, appends `InitialPossession(entity, Quantity(value, unit))` to `initial_state`.

2. **Implicit-Subject / Location Possession**
   - **Template**: `There are <Number> <Unit> [in <Place>].`
   - **Example**: `There are 12 candies in the box.`
   - **Graph Mapping**: If `in <Place>` is present, `place` is the entity; otherwise, `unit` is the entity. Appends `InitialPossession(entity, Quantity(value, unit))` to `initial_state`.

---

### B. State-Mutating Operations (Story sequence)

1. **Add (Buy/Get/Find/Earn)**
   - **Template**: `<Entity> buys <Number> <Unit>.` / `<Entity> gets <Number> <Unit>.` / `<Entity> finds <Number> <Unit>.` / `<Entity> earns <Number> <Unit>.`
   - **Example**: `Sam buys 3 apples.`
   - **Graph Mapping**: Appends `Operation(actor, kind="add", operand=Quantity(value, unit))` to `operations`.

2. **Subtract (Eat/Lose/Sell/Donate/Use/Spend)**
   - **Template**: `<Entity> eats <Number> <Unit>.` / `<Entity> loses <Number> <Unit>.` / `<Entity> sells <Number> <Unit>.` / `<Entity> donates <Number> <Unit>.` / `<Entity> uses <Number> <Unit>.` / `<Entity> spends <Number> <Unit>.`
   - **Example**: `Sam eats 2 apples.`
   - **Graph Mapping**: Appends `Operation(actor, kind="subtract", operand=Quantity(value, unit))` to `operations`.

3. **Transfer (Give/Send)**
   - **Template**: `<Entity1> gives <Number> <Unit> to <Entity2>.` / `<Entity1> sends <Number> <Unit> to <Entity2>.`
   - **Example**: `Anna gives 3 marbles to Ben.`
   - **Graph Mapping**: Appends `Operation(actor=Entity1, kind="transfer", operand=Quantity(value, unit), target=Entity2)` to `operations`.

4. **Multiply (Double/Triple)**
   - **Template**: `<Entity> doubles his/her/their <Unit>.` / `<Entity> triples them.`
   - **Example**: `Rina doubles her ribbons.`
   - **Graph Mapping**: Appends `Operation(actor, kind="multiply", operand=Quantity(value, unit))` with factor 2 or 3 to `operations`.

5. **Divide (Split)**
   - **Template**: `<Entity> splits them evenly into <Number> groups [and keeps one group].`
   - **Example**: `Ruth splits them evenly into 6 groups and keeps one group.`
   - **Graph Mapping**: Appends `Operation(actor, kind="divide", operand=Quantity(groups, unit))` to `operations`.

---

### C. Rate and Comparisons

1. **Rate Declaration**
   - **Template**: `Each <Unit> costs $<Number>.` / `An <Unit> costs $<Number>.` / `<Unit> cost $<Number> each.`
   - **Example**: `Each apple costs $2.`
   - **Graph Mapping**: Registers `Rate(value, numerator_unit="dollars", denominator_unit=unit)` in the parser state.

2. **Additive Comparison**
   - **Template**: `<Entity1> has <Number> more/fewer <Unit> than <Entity2>.`
   - **Example**: `Alice has 3 more apples than Bob.`
   - **Graph Mapping**: Appends `Operation(actor=Entity1, kind="compare_additive", operand=Comparison(reference_actor=Entity2, delta=Quantity(value, unit), factor=None, direction="more"/"fewer"))` to `operations`.

3. **Multiplicative Comparison**
   - **Template**: `<Entity1> has <Number> times as many <Unit> as <Entity2>.` / `<Entity1> has twice/half as many <Unit> as <Entity2>.`
   - **Example**: `Alice has 3 times as many apples as Bob.`
   - **Graph Mapping**: Appends `Operation(actor=Entity1, kind="compare_multiplicative", operand=Comparison(reference_actor=Entity2, delta=None, factor=factor, direction="times"/"fraction"))` to `operations`.

---

### D. Questions (Target of query)

1. **Single Entity Question**
   - **Template**: `How many <Unit> does <Entity> have [now|left|in total]?`
   - **Example**: `How many apples does Sam have now?`
   - **Graph Mapping**: Sets `unknown` to `Unknown(entity, unit)`.

2. **Total-Across Question**
   - **Template**: `How many <Unit> do they have [in total|altogether]?`
   - **Example**: `How many apples do they have in total?`
   - **Graph Mapping**: Sets `unknown` to `Unknown(entity=None, unit)`.

3. **Rate Aggregate Question**
   - **Template**: `How much does <Entity> spend/pay/earn?`
   - **Example**: `How much does Sarah spend?`
   - **Graph Mapping**: Appends `Operation(actor=Entity, kind="apply_rate", operand=Rate)` and sets `unknown` to `Unknown(entity, unit="dollars")`.
