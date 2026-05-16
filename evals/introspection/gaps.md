# introspection lane — architectural findings (v1)

## v1 result

| Split | n | explain_api_present | account_nonempty | surface_match | trace_match |
|---|---|---|---|---|---|
| public/v1 | 12 | **0.0** | 0.0 | 0.0 | 0.0 |
| holdouts/v1 | 8 | **0.0** | 0.0 | 0.0 | 0.0 |

Structural zero by construction: there is no `explain` callable to
import from `core.cognition`.

## Why this is the right v1

A lane that can't run at all is worse than a lane that runs and
reports a typed zero.  The introspection lane runs today, attempts
the import, catches the failure deterministically, and emits four
sub-metrics — all zero, all explained.  The day someone lands a
`core/cognition/explain.py` module, this lane immediately starts
producing real numbers without any test infrastructure change.

## Required engineering for v2

The roadmap (`docs/capability_roadmap.md` Phase 3 work items) is
explicit:

> A new `cognition/explain.py` module may be needed for
> introspection.

Concretely, an `explain(result: CognitiveTurnResult) -> str`
function that:

1. **Reads structured state from the result** — intent tag,
   proposition graph, articulation target, vault hits, identity
   score.
2. **Composes a deterministic natural-language account** that
   re-states the trajectory in source language.  Probably leans on
   the same `realize_semantic` machinery currently used for
   articulation but inverted: surface → structured trace → surface'.
3. **Round-trip property**: feeding the account back through the
   pipeline produces an articulation whose token coverage of the
   original surface is high.  Strict trace-hash equivalence is the
   ideal but not the v1 bar — surface token overlap ≥ 0.60 is the
   v1 contract.

## Future direction (recorded here so it's not forgotten)

A working introspection API is also the substrate for **narrative
self-explanation**: the same machinery that produces "I answered X
because I retrieved Y under intent Z" is what produces an agent's
own first-person account of a turn.  Per the open scope decision in
`docs/PROGRESS.md` (Agency: responsive vs. goal-directed), this
choice should pin before introspection v2 is engineered.

## Status

v1 is structural-zero scaffolding.  Permanent regression evidence
of the missing module.
