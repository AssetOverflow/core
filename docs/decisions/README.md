# Architecture Decision Records (ADRs)

This directory records every significant architectural decision made in the design
and implementation of CORE. Each record is **immutable once written** — if a
decision is superseded, a new ADR is created that references and replaces it.
Old ADRs are never deleted or edited.

## Format

```
docs/decisions/ADR-NNNN-short-title.md   ← formal architectural decisions
docs/decisions/SESSION-YYYY-MM-DD.md     ← timestamped working session logs
```

ADRs record *decisions*. Session logs record *the reasoning process*, open
questions, and implementation details discovered during active development.
Both are permanent record.

## ADR Template

```markdown
# ADR-NNNN: Title

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Superseded by ADR-XXXX  
**Deciders:** [names/handles]

## Context
What situation or problem prompted this decision.

## Decision
What was decided, precisely.

## Rationale
Why this and not the alternatives. Which axiom(s) it serves.

## Consequences
What becomes easier. What becomes harder. What is now forbidden.

## Alternatives Considered
What was explicitly rejected and why.
```

## Index

| ADR | Title | Date | Status |
|-----|-------|------|--------|
| [ADR-0001](ADR-0001-vocab-layer-invariants.md) | VocabManifold Versor Invariant | 2026-05-12 | Accepted |
| [ADR-0002](ADR-0002-ingest-layer-design.md) | Ingest Layer Architecture | 2026-05-12 | Accepted |
| [ADR-0003](ADR-0003-coordinate-system-dissolution.md) | Coordinate System Dissolution | 2026-05-12 | Accepted |
| [ADR-0004](ADR-0004-rotor-as-operator-not-property.md) | Rotor as Operator, Not Vocabulary Property | 2026-05-12 | Accepted |
