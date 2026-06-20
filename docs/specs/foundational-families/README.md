# Foundational Substrate Family Specifications

This directory contains the controlled foundational family specifications for the K–8 cognitive substrate, as mandated by **ADR-0224**.

## Core Principles

1. **Gate for Implementation Slices**
   A complete and approved family specification document in this directory is a strict constitutional requirement *before* any implementation slice for that family is authorized. These specifications act as architectural gating artifacts, not runtime behavior.

2. **Extension of ADR-0223 Doctrine**
   All future family design and implementation must strictly adhere to the canonical rule defined in **ADR-0223**:
   > Closeness proposes; bindings ground; contracts determine.

   - **Semantic closeness proposes:** Lexical/CGA neighborhood scans identify candidate affordances.
   - **Exact bindings ground:** Span-grounded bindings map values to roles.
   - **Organ-specific contracts determine:** Contract assessments verify completeness, topology, and absence of hazards before admitting a candidate.

3. **Benchmarks as Diagnostic Lanes Only**
   Benchmarks, such as GSM8K, are valuable diagnostic pressure lanes to identify gaps, verify behavior, and test morphology. They **never** define the substrate. The substrate is defined by minimal, reusable constructional affordances across elementary and middle school subjects.

## Directory Structure

- [TEMPLATE.md](TEMPLATE.md): The mandatory section structure every family specification must populate.
- [quantity-entity-binding.md](quantity-entity-binding.md): Specification for the quantity-entity binding family.
- [state-change.md](state-change.md): Specification for the state-change family.
