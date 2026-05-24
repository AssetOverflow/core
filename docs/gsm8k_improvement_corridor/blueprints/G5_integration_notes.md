# G.5 Integration Notes

## Current landing state

The first G.5 implementation landings are substrate-only:

- `TargetBinding` graph primitive
- aggregate-target extraction helper

Neither changes solver semantics yet.

## Why staged integration matters

The existing architecture already preserves:

```text
admitted_wrong == 0
```

Unsafe integration risks:

- silently broadening total-across semantics;
- changing solver assumptions for `Unknown(entity=None)`;
- accidental entity-scope inflation;
- ambiguity acceptance.

The staged posture keeps the corridor fail-closed.

## Planned integration sequence

### Step 1

Attach optional `target_binding` metadata to graphs.

Constraint:

- graph behavior unchanged when target_binding absent.

### Step 2

Allow solver read-only inspection of target_binding.

Constraint:

- no semantic override of Unknown yet.

### Step 3

Enable aggregate traversal only when:

- provenance path explicit;
- unit scopes identical;
- branch entity universe deterministic.

### Step 4

Introduce curated aggregate-binding lane.

### Step 5

Measure GSM8K question-layer refusal reduction.

## Explicit anti-goals

- no fuzzy semantic aggregation;
- no inferred entity groups;
- no hidden probabilistic fallback;
- no automatic discourse expansion.
