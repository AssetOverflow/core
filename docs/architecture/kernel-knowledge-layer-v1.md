# Kernel Knowledge Layer — Architecture & Doctrine (v1)

This document defines the architecture, boundary rules, and operational doctrine for the target-state **Kernel Knowledge Layer** in CORE.

---

## 1. Purpose

The Kernel Knowledge Layer acts as a seeded, reviewed, and deterministic substrate of fundamental facts, equivalences, dimensions, physical containers, calendar systems, and hazard invariants. It provides a shared "world model" that language-processing and mathematical derivation components will consult, ensuring that common-sense relationships (such as $1 \text{ hour} = 60 \text{ minutes}$ or $\text{"half"} = 0.5$) are canonicalized consistently rather than re-engineered ad hoc inside individual derivation organs.

---

## 2. Baseline Context & Empirical Standing

As of PR-0, the current empirical results of CORE (after integration of #827) are:
- **`train_sample`:** 30 correct, 20 refused, 0 wrong (30/20/0)
- **`holdout_dev`:** 5 correct, 495 refused, 0 wrong (5/495/0)

> [!IMPORTANT]
> This PR is documentation-only (PR-0). It introduces no code, changes no serving paths, and has **zero impact** on these baseline benchmark scores.

---

## 3. Why CORE Needs This Now

As CORE has expanded its capabilities on GSM8K and similar arithmetic reasoning benchmarks, we have transitioned from simple single-step operations to complex multi-step transitive reasoning chains. However, this progress has come at the cost of duplicate local logic.

Without a central Kernel Knowledge Layer:
- Multi-step derivation organs must each write custom regexes or lookup maps for numbers like "half", "quarter", "1/2", and "50%".
- Calendar parsing (e.g., month names, day counts, and temporal splits) is repeatedly hard-coded within specific scheduling organs.
- Dimensional conversions (e.g., currency conversions, hours to days) are hand-crafted within isolated problem-solving paths.

By introducing a standardized Kernel Knowledge Layer, we decouple **lexical/factual grounding** from **derivation/problem-solving logic**.

---

## 4. What Recent GSM8K Sprints Revealed

Recent development sprints (Sprints 10 through 13) targeted high-difficulty math reasoning paths:
- **Sprint 11 (Piecewise Daily Hours):** Introduced month-length lookups and "halfway through the month" logic, which was implemented as local calendar grounding tables inside the organ.
- **Sprint 12 (Nested Partitions):** Revealed that handling phrases like "half of the kids" or "1/4 of the remaining" required specialized parsing patterns repeated across multiple files.
- **Sprint 13 (Robust Lift):** Highlighted the risk of boundary violations when resolving comparative scales ("twice as many", "half as many"). Without standardized hazard verification, organs easily make unsound inferences due to unbound base quantities or category mismatches.

These sprints proved that while CORE's geometric runtime can enforce invariants once representations are built, the *construction* of those representations relies on brittle, repetitive local logic.

---

## 5. What Already Exists in ADR-0128 (`en_numerics_v1`)

The sibling specification [ADR-0128](docs/decisions/ADR-0128-numerics-pack.md) defines `en_numerics_v1`. It contains:
- **Cardinal number words:** Zero to twenty, tens, and magnitudes.
- **Ordinal number words:** First through thirty-first, plus major anchors.
- **Fraction words & symbols:** "half", "third", "quarter", "three-quarters", and Unicode symbols (`½`, `¾`, `⅔`).
- **Multiplier words:** "double", "triple", "twice", "thrice".
- **Quantifiers:** "all", "none", "some", "each", "every", "many", "few".
- **Comparison anchors:** "more", "fewer", "less", "additional", "times".
- **Numeric format rules:** Declarative regexes matching thousand-separated, decimals, slash-fractions, mixed numbers, and percentages.

---

## 6. What Already Exists in ADR-0127 (`en_units_v1`)

[ADR-0127](docs/decisions/ADR-0127-units-pack-and-units-aware-parser.md) defines `en_units_v1`. It contains:
- **Dimensions:** Closed physical and financial dimensions (`count`, `length`, `time`, `mass`, `money`, `volume`, `wage`, `unit_price`).
- **Unit definitions:** Standard mappings for `foot`/`feet`, `hour`/`hours`, `dollar`/`dollars`, `cent`/`cents`, and entity units like `person`/`people`, `child`/`children`.
- **Conversion graphs:** Formal conversion edges between units within the same dimension (e.g., $1 \text{ dollar} = 100 \text{ cents}$).
- **Containers:** Default sizes for physical containers (`box`, `pack`, `bag`, `crate`).

---

## 7. What Must Not Be Duplicated

To prevent architectural drift and maintain a clean separation of concerns, the following functions **must not** be duplicated in derivation organs:
1. **String Normalization & Regex Scans:** Do not write custom regexes for number words, percentages, or units in local files. Use the unified parser interface.
2. **Dimension Tables:** Standard conversion coefficients (e.g., $60 \text{ minutes} = 1 \text{ hour}$) must reside in the units pack conversions, not in organ-level multiplication constants.
3. **Calendar Metrics:** Day-counts and calendar logic must be resolved strictly through the calendar pack.

---

## 8. Kernel Pack Model

Every Kernel Pack is structured as a declarative, immutable resource directory under `language_packs/data/<pack_name>_v1/` containing:
- `manifest.json`: Defines pack metadata, determinism class (`D0`), and cryptographic file checksums.
- `lexicon.jsonl`: Contains individual lexeme or concept definitions.
- `glosses.jsonl`: Human-readable descriptions explaining the exact semantic scope.
- `.mastery_report.json`: Cryptographic seals verifying disk contents.

---

## 9. Pack Boundaries

A Kernel Pack is a **passive database**. It acts as a static vocabulary and relational index:
- It **does** expose lookup functions (`lookup_*()`) and regex matching helpers (`match_*()`).
- It **does not** execute algorithms, traverse state graphs, or perform arithmetic reduction.
- It **does not** retain session state. All operations are stateless, side-effect-free, and thread-safe.

---

## 10. Provenance Model

Provenance is the system's guarantee of semantic origin. The taxonomy consists of the following explicit classes:

* `problem_text`: Literal string offsets and spans from the input narrative text.
* `derived`: Values computed during derivation steps.
* `kernel_unit`: Physical and economic unit anchors defined in `en_units_v1`.
* `kernel_calendar`: Calendar parameters derived from structured rules. Specifically, the notation `calendar_table:{month}` represents a `kernel_calendar` provenance, not a generic world fact.
* `kernel_math`: Fundamental mathematical identities and properties.
* `kernel_world_fact`: General static world facts (e.g., currency relationships or gravity constants).
* `reviewed_pack`: Checked, human-curated facts and mappings.
* `speculative`: Deductive conclusions from speculative premises (retaining speculative standing).

When a derivation organ constructs a quantity or relation, it will carry over the provenance. In-problem operands derived from narrative text must preserve their character offsets or string spans as `source_token`.

---

## 11. Hazard Model

A **Hazard** represents a semantic ambiguity, dimensional collision, or boundary violation that could lead to an incorrect inference if left unvalidated.
- When a kernel lookup retrieves an ambiguous node, it must attach a list of potential hazard IDs.
- For example, retrieving the lexeme "quarter" carries hazards: `[quarter_coin, quarter_calendar_period, quarter_school_term]`.
- The consumer (ProblemFrame or derivation organ) will check if the context disambiguates the hazard. If not, it must refuse the transaction (`refuse`).

---

## 12. Review/Proposal Model

To prevent unreviewed drift, kernel packs follow a strict proposal flow:
- Packs are compiled deterministically via offline scripts (e.g., `scripts/generate_en_numerics_v1.py`).
- Automatic runtime mutation of packs is forbidden.
- Any change to a pack must be proposed via a schema and checklist change, generating new SHA-256 hashes, and must be reviewed by codeowners prior to merging.

---

## 13. What Packs May Do

- Canonicalize varying surface forms (e.g., `half`, `0.5`, `50%`, `½`) to a single canonical ID (`scalar:1/2`) and numeric value.
- Map words to standard grammatical tags (e.g., `NOUN`, `NUM`, `ADJ`) and semantic tags.
- Declare dimensional conversion multipliers (e.g., $\text{multiplier}=100.0$ for dollars to cents).

---

## 14. What Packs May Not Do

- Decide which arithmetic operation to perform on problem operands.
- Solve equations or build target derivation networks directly.
- Infer missing problem values unless explicitly defined in a conversions graph.

---

## 15. Target-State Relationships

### Relationship to ProblemFrame
In the target state, the **ProblemFrame** represents the structured intermediate representation (IR) of the mathematical problem:
- The ProblemFrame will consume raw text, parse it using the candidate graph parser, and query the Kernel Knowledge Layer to ground actors, objects, quantities, and units.
- It will validate that dimensions match across comparison and addition operations.
- The ProblemFrame will not perform math; it will assert that the problem's relational structure is well-formed.

### Relationship to Derivation Organs
In the target state, derivation organs are specialized mathematical solvers:
- Organs **will not** parse raw surfaces directly. Instead, they will consume the structured entities and relations in the ProblemFrame.
- Organs will rely on the kernel packs to perform unit conversions or to scale values by fractional/multiplicative operators.

### Relationship to Experience Flywheel / Morphology Atlas
In the target state, the **Experience Flywheel** reviews failed or refused problems to categorize errors:
- If a problem is refused due to a missing lexical term or relation, the Flywheel will mark it with a `missing-kernel` label.
- This feeds back into the proposal queue for future kernel pack updates.
- The Flywheel **never** automatically writes to the packs; it only reports gaps.

---

## 16. Non-Goals

- Impersonating a large-scale language model by embedding encyclopedic world knowledge.
- Handling arbitrary sentence logic.
- Supporting real-time learning of user-defined facts in the core loop without human-in-the-loop review.

---

## 17. First Implementation Sequence

1. **Doctrine Alignment:** Commit this architecture and doctrine document (PR-0).
2. **ScalarEquivalence Facade over ADR-0128/en_numerics_v1:** Implement the facade layer to query numerics and fraction equivalences, unless a later ADR proves a separate pack is necessary.
3. **Organ Refactoring:** Update one target-state organ (e.g., `percent_partition.py` or `temporal_tariff.py`) to consume the new facade.
4. **Units/Dimensions Kernel:** Refactor and unify the units loader and conversions framework.

---

## 18. Kernel Pack Categories

### Category 1: scalar_equivalence
- **Scope:** Canonical fractions, multipliers, and percentages.
- **Example Nodes:** `scalar:1/2`, `scalar:3/4`, `scalar:2/1`
- **Example Surfaces:** "half", "one half", "1/2", "0.5", "50%", "double", "twice"
- **Example Relations:** `equivalence(surface, scalar_value)`
- **Allowed Inferences:** Grouping multiple spelling and symbolic representations of the same scalar scaling factor (e.g., "half" = 0.5).
- **Hazards:** `unbound_base_quantity`, `percent_change_vs_percent_of`
- **Provenance Requirements:** `reviewed_pack` (backed by `adr-0128:operator_seed`)
- **Must Not Solve:** Problem-level fraction partitions.
- **Special Case Inconsistencies:** The surface "half" corresponds to a scalar value of $0.5$. Relational comparatives such as "one-and-a-half" or "half-again" are treated as distinct $1.5$-style scalar relations, preventing conflicts during substitution.
- **First Candidate Tests:** Unification tests showing that "50%" and "half" map to the identical float/Fraction representation.

### Category 2: units_dimensions
- **Scope:** Standard units of measure and conversions.
- **Example Nodes:** `unit:dollar`, `unit:cent`, `unit:hour`, `unit:minute`, `dimension:length`
- **Example Surfaces:** "dollars", "$", "cents", "hours", "hrs", "minutes", "mins"
- **Example Relations:** `conversion_factor(unit:dollar, unit:cent, 100.0)`
- **Allowed Inferences:** Converting quantities between compatible units (e.g., $2 \text{ hours} \rightarrow 120 \text{ minutes}$).
- **Hazards:** `dimension_mismatch`, `incompatible_conversions`
- **Provenance Requirements:** `kernel_unit`
- **Must Not Solve:** Rate calculations involving non-compatible dimensions (e.g., speed = distance / time).
- **First Candidate Tests:** Round-trip unit conversion tests.

### Category 3: arithmetic_laws
- **Scope:** Common mathematical identities and algebraic patterns.
- **Example Nodes:** `identity:additive_neutral`, `law:distributive`
- **Example Surfaces:** "total", "combined", "each"
- **Example Relations:** `distributive_law(A * (B + C) = A*B + A*C)`
- **Allowed Inferences:** Exposing algebraic patterns for solvers to structure their mathematical target graph.
- **Hazards:** `operation_overflow`
- **Provenance Requirements:** `kernel_math`
- **Must Not Solve:** Solving multi-step equation systems directly.

### Category 4: comparatives
- **Scope:** Relational comparatives that describe inequalities or relative ratios.
- **Example Nodes:** `comparative:more_than`, `comparative:less_than`
- **Example Surfaces:** "fewer", "more", "additional", "older than", "younger than"
- **Example Relations:** `relation:greater_than(A, B, delta)`
- **Allowed Inferences:** Establishing logical constraints and ordering models.
- **Hazards:** `reverse_comparative_inversion_error`
- **Provenance Requirements:** `reviewed_pack` (backed by `adr-0138`)
- **Must Not Solve:** Executing comparative additions/subtractions directly without context verification.

### Category 5: part_whole
- **Scope:** Partitioning of groups and fractions of aggregates.
- **Example Nodes:** `partition:subgroup`, `partition:remainder`
- **Example Surfaces:** "rest", "remaining", "others", "girls", "boys"
- **Example Relations:** `complement(subgroup, remainder)`
- **Allowed Inferences:** Declaring candidate relation schemas (e.g., `sum(partitions) = 1.0`) and role requirements.
- **Hazards:** `unbound_whole_reference`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Multi-step fraction remainder cascades.

### Category 6: transfer_ledger
- **Scope:** Transits, gives, receives, sells, buys, and balance changes.
- **Example Nodes:** `transfer:give`, `transfer:receive`, `transfer:spend`
- **Example Surfaces:** "gave", "bought", "spent", "sold", "lost", "found"
- **Example Relations:** `balance_delta(actor, item, change_amount)`
- **Allowed Inferences:** Exposing structured transfer relations and debit/credit role templates.
- **Hazards:** `double_count_transfer`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Arithmetic inventory changes.

### Category 7: containers
- **Scope:** Storage, capacity bounds, and containment.
- **Example Nodes:** `container:box`, `container:crate`, `container:bag`
- **Example Surfaces:** "boxes", "crates", "packs", "bags"
- **Example Relations:** `contains(container, item, capacity)`
- **Allowed Inferences:** Exposing candidate relation schemas and capacity roles (e.g., `total_items = container_count * container_capacity`).
- **Hazards:** `unbound_container_size`
- **Provenance Requirements:** `kernel_unit`
- **Must Not Solve:** Box layout packing optimizations or solving totals.

### Category 8: temporal_calendar
- **Scope:** Months, weeks, calendar splits, and offsets.
- **Example Nodes:** `calendar:month:june`, `calendar:week`
- **Example Surfaces:** "June", "week", "halfway through the month"
- **Example Relations:** `day_count(calendar:month:june, 30)`
- **Allowed Inferences:** Resolving explicit calendar names and periods to day counts using `calendar_table:{month}` under the `kernel_calendar` class.
- **Hazards:** `leap_year_ambiguity`, `vague_temporal_spans`
- **Provenance Requirements:** `kernel_calendar`
- **Must Not Solve:** Multi-month schedule parsing or solving days.

### Category 9: spatial_route
- **Scope:** Linear distances, stops, and directional paths.
- **Example Nodes:** `route:distance`, `route:stop`
- **Example Surfaces:** "miles", "kilometers", "stops", "lights"
- **Example Relations:** `stops_per_distance(stops, distance)`
- **Allowed Inferences:** Exposing rate schemas along spatial routes.
- **Hazards:** `unbound_route_segments`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Arithmetic solving of rates.

### Category 10: process_frames
- **Scope:** Repeating workflows, rates, and earnings over time.
- **Example Nodes:** `process:labor`, `process:production`
- **Example Surfaces:** "earns", "makes", "works", "per day", "hourly"
- **Example Relations:** `wage_earned(hours, rate)`
- **Allowed Inferences:** Exposing production and labor relation schemas and rate roles.
- **Hazards:** `overtime_tariff_boundary_error`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Solving earnings or applying overtime equations.

### Category 11: ontology_minimal
- **Scope:** Minimal semantic hierarchy for entities to check dimensional compatibility.
- **Example Nodes:** `class:people`, `class:item`, `class:place`
- **Example Surfaces:** "students", "girls", "crayons", "classroom"
- **Example Relations:** `subclass_of(girls, students)`
- **Allowed Inferences:** Validating subclass hierarchy compatibility for addition/subtraction.
- **Hazards:** `incompatible_class_addition`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Large-scale taxonomies.

### Category 12: ambiguity_hazards
- **Scope:** Explicit registry of words carrying multiple meanings that require context constraints.
- **Example Nodes:** `hazard:quarter`, `hazard:third`
- **Example Surfaces:** "quarter", "third", "percent change"
- **Example Relations:** `has_hazard(quarter, quarter_coin)`
- **Allowed Inferences:** Flagging dangerous contexts for defensive refusal.
- **Hazards:** `unresolved_ambiguity_refusal`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Disambiguation algorithms.

### Category 13: provenance
- **Scope:** Source tracking anchors.
- **Example Nodes:** `provenance:text`, `provenance:table`
- **Example Relations:** `source_binding(operand, token_span)`
- **Allowed Inferences:** Tracking whether values are derived from narrative or are world constants.
- **Hazards:** `untracked_operand_provenance`
- **Provenance Requirements:** `reviewed_pack`
- **Must Not Solve:** Semantic parsers.
