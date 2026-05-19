# ADR-0067 — Cross-pack teaching chains (Plan Phase 4)

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Phase:** Plan Phase 4 (multi-domain composition)
**Builds on:** ADR-0052 / ADR-0063 / ADR-0064 / ADR-0066

---

## Context

ADR-0064 introduced the cross-pack teaching corpora registry but
deliberately kept each corpus 1:1 bound to a single ratified pack.
Chains whose subject + object resolved to *different* packs were
dropped at load time. The structural rationale was sound for v1:
keep the per-pack DAGs ratified before adding cross-domain edges.

Phases 1–3 satisfied that prerequisite:
- 3 ratified content packs live on the default runtime
  (cognition v1 + relations v1/v2).
- 36 reviewed in-pack chains across three corpora.
- NARRATIVE + EXAMPLE composers in place — ready to consume
  multi-corpus chain sets.

The articulation wall now lives in the *gap between* domains. The
system has nothing to say when an operator asks:

```
> Why does family exist?
> Does identity require family?
> Does understanding require parent?
```

These prompts reference a relations-pack lemma and a cognition-pack
lemma in the same chain. No single-pack corpus can ground them; an
edge that crosses packs is required.

---

## Decision

Introduce a deliberately narrow cross-pack chain shape. Each chain
explicitly carries **two** pack-residency fields:

```json
{
  "chain_id": "cause_family_grounds_identity",
  "subject": "family",
  "intent": "cause",
  "connective": "grounds",
  "object": "identity",
  "subject_pack_id": "en_core_relations_v1",
  "object_pack_id": "en_core_cognition_v1",
  ...
}
```

The loader verifies per-chain residency: the subject must resolve in
its declared subject pack, and the object must resolve in its
declared object pack. Same-pack entries are rejected (they belong in
the in-pack corpus).

### Files

```
chat/cross_pack_grounding.py                                  NEW
teaching/cross_pack_chains/cross_pack_chains_v1.jsonl         NEW (5 chains)
chat/runtime.py                                               wired cross-pack fall-through
chat/narrative_surface.py                                     aggregates cross-pack chains
chat/example_surface.py                                       aggregates cross-pack reverse chains
tests/test_cross_pack_chains.py                               NEW (31 tests)
docs/decisions/ADR-0067-cross-pack-teaching-chains.md         NEW (this file)
```

### Surface format

```
"{X} — cross-pack-grounded ({corpus_id}: {subject_pack_id} × {object_pack_id}):
 {dX1}; {dX2}. {X} {conn} {Y} ({dY1}). No session evidence yet."
```

Both pack ids are exposed in the tag so the audit trail and operator
debugger can see *which* domains the chain crosses without parsing
the chain body.

### Resolution order

In `chat/runtime.py` for CAUSE/VERIFICATION:

1. `teaching_grounded_surface_composed` (when `composed_surface=True`)
   OR `teaching_grounded_surface` — in-pack chain index
   (`_all_chains_index` across all single-pack corpora).
2. **`cross_pack_grounded_surface` — fall-through when no in-pack
   chain resolves the `(subject, intent)`.** [ADR-0067]
3. Fall through to OOV invitation if the subject is unknown to any
   mounted pack.

The cross-pack composer is the fall-through only: when an in-pack
chain exists on the same `(subject, intent)`, the in-pack composer
wins. This preserves the cognition-lane byte-identity invariant.

### NARRATIVE and EXAMPLE aggregation

Both multi-clause composers (ADR-0066) now walk cross-pack chains
in addition to in-pack ones:

- `narrative_surface.py` calls `cross_pack_chains_for_subject(X)`
  and appends those chains into the dedup-and-sort pipeline.
- `example_surface.py` calls `cross_pack_chains_for_object(X)`
  similarly.

The corpus tag widens from `(cognition_chains_v1)` to
`(cognition_chains_v1 + cross_pack_chains_v1)` whenever any
cross-pack clause contributes. Stable lexicographic ordering — no
behaviour change on subjects with no cross-pack chains.

### Seed corpus

`teaching/cross_pack_chains/cross_pack_chains_v1.jsonl` ships with
5 hand-authored, reviewed chains:

| chain_id                                  | direction               |
|---|---|
| `cause_family_grounds_identity`           | relations → cognition   |
| `cause_parent_grounds_understanding`      | relations → cognition   |
| `cause_family_supports_memory`            | relations → cognition   |
| `verification_identity_requires_family`   | cognition → relations   |
| `verification_understanding_requires_parent` | cognition → relations |

All connectives are whitelisted in
`generate.semantic_templates._PREDICATE_HUMANIZE`.

---

## Consequences

### Capability unlocked

| Prompt | Pre-ADR-0067 | Post-ADR-0067 |
|---|---|---|
| `"Does identity require family?"` | OOV invitation | `identity requires family` (cross-pack) |
| `"Does understanding require parent?"` | OOV invitation | `understanding requires parent` (cross-pack) |
| `"Tell me about family"` | 1 clause (in-pack) | 3 clauses (in-pack + 2 cross-pack) |
| `"Give me an example of memory"` | 1 example | 2 examples (in-pack `recall` + cross-pack `family supports`) |

### Live verification

```
> Does identity require family?
  [teaching] identity — cross-pack-grounded
  (cross_pack_chains_v1: en_core_cognition_v1 × en_core_relations_v1):
  cognition.identity; identity.stable. identity requires family
  (kinship.unit). No session evidence yet.

> Tell me about family.
  [teaching] family — narrative-grounded
  (cross_pack_chains_v1 + relations_chains_v1): kinship.unit;
  social.group.kin. family grounds identity (cognition.identity);
  family grounds parent (kinship.ascendant.direct); family supports
  memory (cognition.memory). No session evidence yet.

> Give me an example of memory.
  [teaching] memory — example-grounded
  (cognition_chains_v1 + cross_pack_chains_v1): cognition.memory.
  Example: family supports memory; recall reveals memory. No session
  evidence yet.
```

### Cognition lane — byte-identical

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

The cross-pack composer fires only as a fall-through. All cognition-
lane prompts (which exercise in-pack chains) follow the unchanged
path.

---

## Trust boundaries

- **Strict per-chain pack residency.** A chain declares
  `subject_pack_id` and `object_pack_id` explicitly; the loader
  verifies each lemma against its named pack. Skewed entries drop
  silently with no surface impact.
- **Anti-leakage: cross-pack chains must actually cross packs.**
  Entries where `subject_pack_id == object_pack_id` are rejected as
  corpus-misfilings.
- **No prose generation.** Every visible non-template token in the
  surface is a lemma, a pack `semantic_domains` atom, or a
  whitelisted connective from `humanize_predicate`.
- **No new mutation surface.** ADR-0027 / ADR-0057 doctrine
  preserved: corpus appends go through `accept_proposal` (or
  `supersede_chain`) and nowhere else. This module is read-only.
- **In-pack precedence.** Cross-pack chains never override an
  in-pack chain on the same `(subject, intent)` — the cognition-
  lane byte-identity invariant depends on this.
- **Supersession honoured.** Cross-pack chains support
  `superseded_by` (ADR-0055 Phase A) — retired entries drop from the
  active view, history preserved on disk.

---

## Verification

```
tests/test_cross_pack_chains.py                              31 passed
Curated lanes (all green):
  smoke 67 / cognition 121 / teaching 17 / packs 6 / runtime 19
Cognition eval byte-identical (public + holdout).
Full lane: 2096 passed, 2 skipped, 0 failed.
```

---

## Future ADRs unlocked

- **Cross-pack supersede CLI.** Today `core teaching supersede` is
  in-pack only. A cross-pack supersede needs to validate the new
  chain's residency against the *same* `(subject_pack_id,
  object_pack_id)` pair as the retired chain.
- **Cross-pack proposals via `core teaching propose`.** Today
  proposals target the in-pack corpus only. Extending to cross-pack
  needs the proposal schema to carry both pack ids and the replay-
  equivalence gate to handle multi-corpus surface diffs.
- **Cross-pack composed surface (ADR-0062 generalisation).** Chain-
  of-chains across packs (e.g. `family grounds identity, which
  grounds knowledge`) would compose a relations seed → cognition
  intermediate → cognition tail. Needs the composer to dispatch on
  per-chain `object_pack_id` for follow-up lookup.
- **Three-pack chains.** Today cross-pack is binary
  (`subject_pack × object_pack`). N-ary chains crossing 3+ packs
  would need a different schema; out of scope until a third
  content-bearing pack ratifies.
