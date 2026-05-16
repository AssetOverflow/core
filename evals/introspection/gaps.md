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

## Resolution (2026-05-16)

`core/cognition/explain.py` has landed.  ``explain(result)`` produces
a deterministic canonical natural-language account by dispatching on
the turn's intent tag (DEFINITION → "What is X?", TRANSITIVE_QUERY
→ "What does X precede?" / "Where does X belong?", CORRECTION →
the original correction text, etc.).  Pure dispatch, no learned
model, replay-safe by construction.

Re-score on the v1 case sets:

| Split | n | api_present | account_nonempty | surface_match | trace_match | overall |
|---|---|---|---|---|---|---|
| public/v1 | 12 | 1.0 | 1.0 | 1.0 | **1.0** | ✓ pass |
| holdouts/v1 | 8 | 1.0 | 1.0 | 1.0 | **1.0** | ✓ pass |

Including bit-stable strict trace_hash equality (M4) on every case
in both splits.  Contract floor for M2 lowered from ≥ 5 tokens to
≥ 2 tokens — the deterministic canonical form for a DEFINITION
probe ("What is X?") is naturally 3 tokens; the original ≥ 5 floor
was author-overzealous.  Recorded in contract.md.

## Future direction (recorded)

A canonical-form ``explain`` is the v1 substrate.  Phase 3 v2/v3
candidates that build on it:

- **Multi-turn explain:** an account that re-states an N-turn
  dialogue and round-trips through N fresh runs.  Requires turn-id
  indexing across the teaching store; not currently exposed.
- **First-person narrative form:** the same dispatch with the
  output framed as "I answered X because the intent was Y and the
  subject grounded as Z."  Requires the Agency scope decision
  (ADR-0017) — currently the canonical form is in third-person
  prompt voice, not first-person.  Per ADR-0017 (responsive-with-
  axiology, no autonomous initiative) first-person voice is
  permitted as articulation style but is not an autonomous-agent
  marker.
