# Scope: PropositionGraph — Epistemic Carrier for ADR-0144

**Status:** Draft / scope-only — prerequisite for ADR-0144
**Date:** 2026-05-24
**Author:** CORE agents
**Anchor:** [thesis-decoding-not-generating](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/thesis-decoding-not-generating.md) (memory)
**Related:** ADR-0142 (epistemic state taxonomy), ADR-0143 (recognition spike)
**Gated by:** Recognition spike complete (PRs #225, #224, #226 merged)

---

## Why this document exists

ADR-0142 and ADR-0143 each defer their integration work to ADR-0144, naming
the PropositionGraph as the missing carrier. The recognition spike is now
complete — `recognition/outcome.py` defines the stable output contract,
`recognition/anti_unifier.py` implements Phases 1 and 2, and 8/8 tests
pass. The carrier question can no longer be deferred.

But "PropositionGraph" is currently ambiguous: the name already exists in
the codebase with a different meaning.

---

## What "PropositionGraph" means today vs. what ADR-0144 needs

**Current `generate/graph_planner.py::PropositionGraph`** is a
*generation-side articulation planner*. It holds:

```python
GraphNode:
  node_id:       str
  subject:       str          # raw text fragment from intent classification
  predicate:     str          # intent-derived predicate label
  obj:           str          # "<pending>" until grounded from vault recall
  source_intent: IntentTag
```

Its purpose is to determine *what to say and in what order*. It drives
`plan_articulation()` → `ArticulationTarget` → `realize_semantic()`.

**What ADR-0144 needs** is a carrier that holds propositions *as they are
known* — not how they will be voiced. That carrier must:

1. Accept a `RecognitionOutcome` (from `recognition/anti_unifier.py`) as
   the epistemic content of a node.
2. Carry the `EpistemicState` that applies to this proposition at each
   pipeline stage.
3. Record provenance: which evidence spans, which recognizer, which
   verification step moved the state.
4. Allow downstream stages (verifier, vault) to transition the state and
   append provenance without mutating the original record.
5. Be serializable for replay (determinism guarantee from ADR-0143).

These two things — articulation planner and epistemic carrier — solve
different problems. Whether they should be the same object is the first
design question this scope must answer.

---

## The load-bearing question

> **What structure should carry a recognized proposition from recognition
> through the engine's subsystems (recognition → verifier → vault →
> articulation) such that:**
>
> 1. The `RecognitionOutcome` (including all feature evidence spans) is
>    preserved and accessible at every stage,
> 2. Epistemic state transitions are themselves deterministic, typed, and
>    carry provenance (what caused the transition),
> 3. The carrier is serializable to/from JSON for replay,
> 4. Cold-start turns (where recognition produces UNDETERMINED) leave the
>    existing pipeline path unchanged, and
> 5. The articulation layer can still derive what to say, either from the
>    epistemic carrier or from a parallel intent-derived graph?

---

## Three open questions

### Q1 — Carrier structure: one graph or two?

**Option A — Extend `GraphNode`**

Add `recognition_outcome: RecognitionOutcome | None` and
`epistemic_state: EpistemicState` to the existing `GraphNode`. The
generation-side graph absorbs epistemic tracking.

Pros: minimal new API surface; `CognitiveTurnResult.proposition_graph`
already exists.
Cons: mixes articulation planning (string fields: subject, predicate, obj)
with epistemic tracking (feature bundle, evidence spans, state history)
into one class. The two concerns have different mutation rules — articulation
fields are set once at planning time; epistemic state transitions on every
subsystem boundary.

**Option B — Separate `EpistemicGraph`**

A new `EpistemicNode` / `EpistemicGraph` type lives in `recognition/` or a
new `cognition/` carrier module. It carries the recognition outcome and
epistemic provenance chain. At articulation time, a connector maps
`EpistemicNode` → `GraphNode` (deriving subject/predicate/obj from the
feature bundle).

Pros: clean separation of concerns; neither class pollutes the other's
invariants; the generation-side graph keeps working as-is.
Cons: a connector must be written and tested; two graphs travel together
through the pipeline.

**Option C — Replace `GraphNode` string fields**

`GraphNode` string fields (`subject`, `predicate`, `obj`) are replaced
with feature-bundle representations. The proposition IS a feature bundle,
not a text fragment.

Pros: most thesis-aligned long-term — the engine stops carrying text
fragments as stand-ins for decoded propositions.
Cons: largest change surface; breaks every existing caller of `GraphNode`;
requires all existing tests to be updated.

**Recommendation candidate:** Option B. Option A mingles invariants that
have different mutation rules. Option C is the right long-term direction but
requires retiring the entire generation-side graph contract in one move —
too large a blast radius before the PropositionGraph has even been defined.
Option B lets the epistemic carrier evolve independently while the existing
articulation path continues to pass its tests. The connector is the one new
seam.

*The scope does not commit to Option B — the ADR decides.*

### Q2 — Session lifetime: per-turn or persistent?

The existing `PropositionGraph` is rebuilt every turn from intent
classification. The `_last_node_id` in `CognitiveTurnPipeline` threads a
single pointer across turns (for correction chaining), but not the full
graph.

For an epistemic carrier, the question is harder:

- **Per-turn:** Each turn derives its own epistemic carrier from the
  recognized proposition. State from prior turns is not carried forward
  in the graph. Simple; matches current session semantics.
- **Session-persistent:** The epistemic graph grows across turns.
  Propositions from earlier turns remain accessible and can be
  VERIFIED or DECODED in later turns (e.g., the engine verifies a
  proposition from turn 3 after receiving correction in turn 5).
  Required by ADR-0142's "transition history" provenance requirement in
  the full-provenance case.

Per-turn is sufficient for the ADR-0144 gate. Session-persistent is
required by ADR-0142's full provenance enforcement but is gated on the
graph having a session home (vault? session context?).

**Recommendation candidate:** Per-turn for ADR-0144; session-persistent
is post-ADR-0144 scope.

*The scope does not commit — the ADR decides.*

### Q3 — Cold-start behavior: what happens when recognition refuses?

When the recognizer returns `state=UNDETERMINED`, there is no feature
bundle to put in an epistemic node. The pipeline must still:

- Route the turn through the existing intent-classification path
- Emit a `CognitiveTurnResult` with the refusal reason accessible
- Not drop the refusal — it is teaching signal (ADR-0143 §Consequences)

Two options:
- **Empty-carrier:** The epistemic carrier exists but its node has
  `proposition=None` and `state=UNDETERMINED`. The existing pipeline
  path handles surface generation; the carrier is observability only.
- **No-carrier:** If recognition refuses, the epistemic carrier is not
  created and `CognitiveTurnResult.epistemic_graph` is `None`. The
  refusal reason is attached to `CognitiveTurnResult.refusal_reason`
  directly (which already exists).

The no-carrier option requires no new `CognitiveTurnResult` field and
is backward compatible. The empty-carrier option keeps the graph
always-present, which simplifies callers.

*The scope does not commit — the ADR decides.*

---

## Subsystem wiring (what ADR-0144 must specify)

Regardless of which option answers Q1–Q3, ADR-0144 must wire the following
path end-to-end and verify it with a determinism test:

```
text
 └─ tokenize()
     └─ recognize(recognizer, tokens)   # recognition/anti_unifier.py
         └─ RecognitionOutcome
             └─ EpistemicNode(state=EVIDENCED, bundle=..., provenance=...)
                 └─ [verifier] → state transition: EVIDENCED → VERIFIED
                     └─ [vault cross-ref] → state transition: VERIFIED → DECODED (when replay-equal)
                         └─ [connector] → GraphNode(subject, predicate, obj derived from bundle)
                             └─ plan_articulation() → ArticulationTarget
                                 └─ realize_semantic() → surface
```

Three integration points the ADR must specify:

1. **Recognition → carrier:** How `RecognitionOutcome` is wrapped into
   an epistemic node. Which field carries the `DerivedRecognizer` used
   (for replay)?
2. **Verifier → carrier:** How the verifier transitions state and appends
   provenance. What triggers verification (all EVIDENCED propositions?
   intent-filtered?)?
3. **Carrier → articulation:** How the connector derives `subject`,
   `predicate`, `obj` from a `FeatureBundle`. Feature bundle has
   `agent`, `relation`, `count`, `unit` — the articulation planner
   currently expects free-text strings. The mapping must be deterministic.

---

## Three implementation debts that become actionable here

From the ADR-0142 audit, three debts were deferred to ADR-0144:

1. **`_ratify_intent` PASSTHROUGH collapse** (`pipeline.py:390–430`).
   Three distinct cold-start conditions — `field_state is None`, `vocab
   is None`, `prompt_versor is None` — all produce the same
   `PASSTHROUGH` outcome with no way to distinguish them. Fix:
   extend `RatificationOutcome` with three distinct enum values
   (`PASSTHROUGH_NO_FIELD`, `PASSTHROUGH_NO_VOCAB`,
   `PASSTHROUGH_NO_VERSOR`). Unblocked by ADR-0144 since the wiring
   change will touch `_ratify_intent`'s callers.

2. **Chat runtime grounding-source dispatcher** (`runtime.py:831–1012`).
   Six provenance gaps: the dispatcher does not record which grounding
   sources were attempted or why each fell through. Once the
   PropositionGraph is the carrier, the dispatcher can attach a dispatch
   trace to the graph node instead of losing it. Blocked until the node
   exists.

3. **Teaching pipeline `watched-metrics` tuple** (`replay.py`). Should
   be a named, versioned `MetricSet` dataclass. Survives future metric
   additions without breaking trace byte-identity. Not directly
   dependent on ADR-0144 but the ADR's determinism gate is the right
   moment to fix it.

---

## What the smallest provable test looks like

**Phase 1 — recognition feeds the carrier (no verifier, no vault):**

Given a Phase 1 or Phase 2 `DerivedRecognizer` and an admissible input:

1. `recognize(recognizer, tokens)` returns `RecognitionOutcome(state=EVIDENCED, ...)`
2. The carrier wraps it as an `EpistemicNode` with `state=EVIDENCED`
3. The connector derives a `GraphNode` from the feature bundle
4. `plan_articulation(graph_with_derived_node)` returns a valid `ArticulationTarget`
5. `CognitiveTurnResult` carries the epistemic node (or graph) with the
   original `RecognitionProvenance` intact
6. Two runs produce byte-identical `CognitiveTurnResult` records

**Phase 2 — refused input does not break the pipeline:**

Given an inadmissible input:

1. `recognize(recognizer, tokens)` returns `RecognitionOutcome(state=UNDETERMINED, ...)`
2. The pipeline routes through the existing intent-classification path
3. `CognitiveTurnResult.refusal_reason` carries the typed `ShapeRefusal`
4. `trace_hash` is byte-identical across two runs

---

## What this scope does NOT commit

- **Option selection for Q1–Q3.** The ADR decides.
- **Storage layer for derived recognizers.** Deferred from ADR-0143 —
  where recognizers live (pack / vault / substrate) is still open.
- **Full session-persistent provenance.** Per-turn carrier is the
  ADR-0144 gate; session persistence is post-ADR-0144.
- **Verifier implementation.** ADR-0144 wires the integration point;
  it does not implement the verifier.
- **Lens-conditional recognition.** How anchor lenses interact with
  derived recognizers is deferred (named in ADR-0143 §What this ADR
  does NOT commit).
- **`EpistemicNode` serialization format.** Defined by the ADR, not
  this scope.

---

## Risks

- **Connector complexity.** Mapping a `FeatureBundle` to `GraphNode`
  string fields (`subject`, `predicate`, `obj`) is straightforward for
  Phase 1/2 examples but may not generalize cleanly to all future
  proposition types. The ADR must either commit to a general mapping
  rule or scope the first connector narrowly to the `has`-relation
  feature bundles that exist today.

- **Trace hash breakage.** Every change to the fields folded into
  `compute_trace_hash()` breaks byte-identity for all prior turns. The
  ADR must specify which new fields (if any) are folded in, and whether
  they are gated on non-emptiness (as `refusal_reason` is) to preserve
  pre-ADR-0144 hashes.

- **`_ratify_intent` PASSTHROUGH** fires on every cold-start turn. If
  ADR-0144 wires recognition before intent ratification, the cold-start
  path must handle the case where the recognizer itself is not yet
  derived — i.e., there is no `DerivedRecognizer` for this proposition
  type yet. The engine must refuse cleanly, not fail.

- **`main` is Codex's checked-out branch.** Branch deletion via
  `--delete-branch` on any PR may fail. Use `gh pr merge --squash`
  without `--delete-branch`.

---

## Summary

The load-bearing question for ADR-0144 is what structure carries a
recognized proposition through the engine — from `RecognitionOutcome`
through verifier and vault to articulation — while preserving all evidence
spans and epistemic state provenance.

Three design questions are open:
1. One graph (extend `GraphNode`) or two (separate `EpistemicGraph`)?
2. Per-turn carrier or session-persistent?
3. Empty-carrier or no-carrier on recognition refusal?

The scope recommends two-graph and per-turn as the lower-blast-radius
options for the first integration gate, but the ADR decides.

Minimum deliverable for ADR-0144 acceptance: one recognized proposition
travels from `recognize()` through the carrier to a `CognitiveTurnResult`
with the original `RecognitionProvenance` intact, verified byte-identical
across two runs.
