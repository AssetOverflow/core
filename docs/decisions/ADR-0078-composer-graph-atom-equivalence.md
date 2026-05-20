# ADR-0078 — Composer/Graph atom equivalence telemetry

**Status:** Proposed
**Date:** 2026-05-20
**Author:** Shay
**Builds on:** [ADR-0046](./ADR-0046-forward-graph-constraint.md) (forward graph constraint), [ADR-0048](./ADR-0048-pack-grounded-cold-start.md) (pack-grounded cold-start), [ADR-0063](./ADR-0063-cross-pack-surface-resolver.md) (cross-pack resolver), [ADR-0072](./ADR-0072-register-telemetry-operator-surface.md) (register telemetry), [ADR-0073d](./ADR-0073d-anchor-lens-telemetry-cli-tour.md) (anchor-lens telemetry), [ADR-0077](./ADR-0077-substantive-register-knobs.md) (R6 layering boundary)
**Series:** C3 — composer/graph seam observability (precedes any shared-resolver enforcement)

---

## Context

ADR-0046 made the `PropositionGraph` available as a forward generation constraint: graph nodes can be converted into an `AdmissibilityRegion` before the versor walk runs.  This closes a major structural gap on the geometric generation path.

But the live runtime also has composer fast paths.  Pack-grounded, teaching-grounded, relation-confirmation, procedure, narrative, example, and discourse-planner surfaces may produce the final user-facing answer without proving that the same semantic atoms that drove the composer also appear in the graph-derived constraint space.

That is a real seam, but it must be addressed carefully.

The first instinct — parse the final English surface, extract lemmas, resolve those lemmas to vocab indices, then reject when they do not intersect the graph region — is the wrong shape for CORE:

* It introduces fuzzy surface-language extraction exactly where CORE has been avoiding fuzzy prose inference.
* It risks false rejection of currently grounded surfaces, including a cognition lane that is already pinned for groundedness.
* It checks an illegal state after construction instead of making illegal construction difficult to represent.

The stronger observation is simpler:

> Pack/teaching composers do not need to be validated by parsing their final prose.  They should expose the same atom provenance they already used to construct the surface, and the graph path should expose the atoms it resolved from its nodes.  ADR-0078 Phase 1 only observes whether those two atom sets are equivalent or divergent.

No enforcement lands in this ADR.

---

## Architectural constraint: preserve R6 axis separation

ADR-0072, ADR-0073, ADR-0074, and ADR-0077 established three deliberately separate axes:

```
truth / proposition axis
  - graph construction
  - pack / teaching atom provenance
  - trace_hash source via register_canonical_surface

register / presentation axis
  - seeded decoration
  - terse / convivial register transformations
  - must not move trace_hash or atom identity

anchor-lens / substantive substrate axis
  - may alter the proposition surface when engaged
  - may move trace_hash exactly where the substantive lens engages
  - must remain orthogonal to register variation
```

ADR-0078 governs only the first axis: composer atom provenance and graph atom provenance.  It must not collapse register and anchor-lens behavior into a single authority object.

Specifically:

* `composer_atom_set_hash` and `graph_atom_set_hash` must be invariant under register variation for the same prompt / lens / packs.
* Anchor-lens engagement may change substantive proposition behavior; tests must not falsely pin lens behavior as if it were presentation-only.
* Register decoration and R6 substantive register transforms must remain downstream of `register_canonical_surface` and must not affect atom-equivalence telemetry.

---

## Decision

Add observational telemetry for composer/graph atom equivalence.

This ADR adds no admission enforcement.  A divergent composer/graph atom report does not change the emitted surface.  The point is to determine whether a real construction bug exists and quantify its shape before any Phase 2 resolver-sharing work begins.

### New telemetry fields

Add the following fields to `TurnEvent` and `ChatResponse`, with defaults preserving compatibility for callers that do not populate them:

```
composer_graph_atom_status: str = ""
composer_atom_set_hash: str = ""
graph_atom_set_hash: str = ""
composer_graph_atom_overlap_count: int = 0
```

`chat/telemetry.py` serializes all four fields into turn JSONL.

Allowed `composer_graph_atom_status` values:

```
not_applicable
  The turn was not produced by a composer path with atom provenance.

composer_no_atoms
  A composer emitted a grounded surface, but this phase did not have
  explicit atom provenance for that composer.  This is an observation,
  not permission to infer atoms from prose.

graph_unconstrained
  The graph side had no meaningful constrained atom signal.

equivalent
  Both composer atoms and graph atoms exist, and their intersection is
  non-empty.

divergent
  Both composer atoms and graph atoms exist, the graph is constrained,
  and their intersection is empty.
```

Hashes are SHA-256 over sorted, de-duplicated atom strings.  The two hashes remain separate.  They must not be merged into a single combined hash because the divergence signal depends on asymmetry.

### Atom sources

Composer atom sources:

* Prefer existing composer candidate metadata, especially `PackSurfaceCandidate.semantic_domains`, `lemma`, and `pack_id`.
* For relation-confirmation or multi-endpoint composers, use endpoint semantic domains only when those domains are directly available from the same resolver used to construct the surface.
* For teaching/narrative/example/procedure paths that do not expose atom provenance in Phase 1, report `composer_no_atoms` rather than parsing final prose.

Graph atom source:

* Use the existing graph construction path.
* Resolve graph node named surfaces through the canonical pack resolver.
* Skip empty strings and placeholders such as `<pending>`.
* If no graph atoms resolve, report `graph_unconstrained` when the graph/region carries no usable atom signal.

### Pure helper

Add a small pure comparison helper.  The helper may live in a narrowly named module such as `generate/atom_equivalence.py` or `chat/atom_equivalence.py`.

The helper should expose a shape equivalent to:

```
@dataclass(frozen=True, slots=True)
class AtomEquivalence:
    status: str
    composer_atom_set_hash: str
    graph_atom_set_hash: str
    overlap_count: int
```

and one pure comparator equivalent to:

```
compare_atom_sets(
    *,
    composer_atoms: tuple[str, ...],
    graph_atoms: tuple[str, ...],
    graph_unconstrained: bool,
    applicable: bool,
) -> AtomEquivalence
```

This helper must not inspect final rendered surfaces.

---

## Non-goals / forbidden changes

ADR-0078 Phase 1 explicitly forbids:

* No `GraphAuthority` dataclass or framework object.
* No new runtime config flag.
* No runtime rejection path.
* No admission enforcement.
* No mutation of `surface`, `pre_decoration_surface`, `register_canonical_surface`, `grounding_source`, or `trace_hash` behavior.
* No discourse-planner coupling.
* No final prose parser such as `extract_candidate_surface_lemmas`, `surface_lemma`, or `parse_surface_atoms`.
* No Phase 2 shared-resolver refactor.
* No combined atom hash replacing the separate composer and graph hashes.
* No register hash instrumentation beyond the four fields above.

If a composer does not expose explicit atom provenance, Phase 1 reports `composer_no_atoms`.

---

## Required tests

Add focused tests in a file such as:

```
tests/test_composer_graph_atom_equivalence.py
```

Required coverage:

### 1. Pack definition equivalence

A normal pack-grounded prompt such as `What is truth?` should produce a pack-grounded surface and non-empty composer atom telemetry.  If graph atoms resolve for the prompt, the status must be `equivalent`, both hashes non-empty, and overlap count positive.  If the graph is deliberately unconstrained, the status must be `graph_unconstrained` rather than `divergent`.

### 2. Corrupt graph divergence is observable, not rejected

A pure helper/unit test must feed mismatched atom sets, for example:

```
composer_atoms = ("logos.aletheia.verity",)
graph_atoms = ("logos.unrelated.test_atom",)
graph_unconstrained = False
applicable = True
```

Expected:

```
status == "divergent"
overlap_count == 0
composer_atom_set_hash != graph_atom_set_hash
```

No surface emission should be involved in this unit test.  This is the falsification test proving the telemetry would catch a real divergence.

### 3. Register invariance

For the same prompt and same anchor-lens setting, vary registers across at least:

```
default_neutral_v1
terse_v1
convivial_v1
```

Expected:

* `composer_atom_set_hash` identical.
* `graph_atom_set_hash` identical.
* `composer_graph_atom_status` identical.
* R6 trace-hash invariance preserved.
* User-facing surfaces may vary.

### 4. Anchor-lens compatibility

Run at least one engaged anchor-lens case.  The telemetry must compute cleanly and preserve existing glyph-leak and tour invariants.  Tests must not force anchor-lens behavior to mimic register invariance; lens engagement is a substantive axis and may move proposition/trace where already allowed by ADR-0073d / ADR-0074.

### 5. No final surface lemma extractor

Add a guard test or static check ensuring the implementation did not introduce helpers named like:

```
extract_candidate_surface_lemmas
surface_lemma
parse_surface_atoms
```

The stronger version may scan the new helper module to ensure it does not accept `surface` / `ChatResponse.surface` as the atom source.

---

## Validation commands

Minimum implementation validation:

```
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run pytest -q \
  tests/test_graph_constraint.py \
  tests/test_pack_grounding.py \
  tests/test_register_tour_demo.py \
  tests/test_anchor_lens_tour_demo.py \
  tests/test_orthogonality_tour_demo.py \
  tests/test_realizer_guard_holdout.py \
  tests/test_composer_graph_atom_equivalence.py
```

Cognition regression:

```
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run --with-editable . core eval cognition
```

Useful tour checks:

```
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run --with-editable . core demo register-tour --json

CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run --with-editable . core demo anchor-lens-tour --json

CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run --with-editable . core demo orthogonality-tour --json
```

---

## Acceptance gates

ADR-0078 Phase 1 is acceptable when:

* New telemetry fields exist on `TurnEvent` and `ChatResponse`.
* New telemetry fields serialize through `chat/telemetry.py`.
* Atom comparison is pure and unit-tested.
* Pack-grounded composer paths expose existing atom provenance without parsing final prose.
* A corrupt atom-set test produces `divergent` without affecting surface emission.
* Register variation leaves atom hashes/status stable and preserves R6 trace-hash invariance.
* Anchor-lens compatibility tests remain green without falsely treating lenses as registers.
* No user-facing surface changes.
* No new config flag.
* No enforcement or rejection path.
* Cognition eval remains green.

---

## Consequences

### Positive

* Makes the composer/graph seam observable before enforcement.
* Preserves R6 layering discipline and register/anchor orthogonality.
* Avoids fuzzy final-surface NLP extraction.
* Creates data to decide whether Phase 2 is needed.
* Gives future resolver-sharing work a measured bug shape instead of a design hunch.

### Negative / costs

* Adds telemetry fields that downstream JSON consumers may need to ignore or adopt.
* Does not immediately prevent divergent composer/graph construction if such divergence exists.
* Some grounded paths may initially report `composer_no_atoms`; that is an honest instrumentation gap to close later, not a Phase 1 failure.

### Deferred follow-up

Only if Phase 1 telemetry shows real divergence, a later ADR may share resolver construction between graph builder and composer so inadmissible composer output becomes structurally difficult to construct.

That later ADR is explicitly not part of ADR-0078 Phase 1.
