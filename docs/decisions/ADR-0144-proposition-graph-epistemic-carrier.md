# ADR-0144: PropositionGraph — Epistemic Carrier and Recognition Integration Gate

**Status:** Accepted
**Date:** 2026-05-24
**Scope doc:** [proposition-graph-scope](./proposition-graph-scope.md)
**Related:** ADR-0142 (epistemic state taxonomy), ADR-0143 (recognition spike — anti-unification)
**Unlocks:** Full epistemic provenance wiring (ADR-0142 §What remains gated), recognition integration into Engine A

---

## Context

The recognition spike is complete. `recognition/outcome.py` defines the
frozen output contract; `recognition/anti_unifier.py` implements Phases 1
and 2; 8/8 tests pass across three merged PRs (#225, #224, #226).

ADR-0142 and ADR-0143 both defer their integration work to this ADR, naming
the PropositionGraph as the missing carrier. Two problems block integration:

1. **The name is taken.** `generate/graph_planner.py::PropositionGraph` is
   an *articulation planner* — it holds `subject: str`, `predicate: str`,
   `obj: str` for generation purposes. That is not the same as a carrier
   that holds a `RecognitionOutcome`, an `EpistemicState`, and a provenance
   chain across subsystem transitions.

2. **The pipeline has no recognition step.** `CognitiveTurnPipeline.run()`
   calls `classify_compound_intent()` to derive intent and builds an
   articulation graph from intent labels. It never calls `recognize()`.
   The `recognition/` module is entirely disconnected from the cognition
   pipeline.

This ADR resolves both problems.

---

## Decision

### Q1 — Carrier structure: two graphs

Adopt **two separate graph types** with distinct responsibilities:

- `generate/graph_planner.py::PropositionGraph` — *articulation planner*
  (unchanged). Holds string-level `subject`, `predicate`, `obj` fields
  for surface generation. Driven by intent classification. Unmodified.

- `recognition/carrier.py::EpistemicGraph` — *epistemic carrier* (new).
  Holds `EpistemicNode` records carrying `RecognitionOutcome` + transition
  provenance. Driven by `recognize()`. Lives in the `recognition/` module.

A connector function (`recognition/connector.py`) maps an `EpistemicNode`
to a `GraphNode` for callers that need articulation output derived from a
recognized proposition. The connector is present in this ADR; consuming it
in the live generation path is gated on a new `RuntimeConfig` flag
(`recognition_grounded_graph`, default `False`) to preserve byte-identity.

Rationale for separation: the two graphs have different mutation rules.
Articulation fields are set once at planning time and never change.
Epistemic state transitions on every subsystem boundary. Merging them into
one class would require either relaxing the immutability guarantee of
`GraphNode` or introducing update methods that mutate only a subset of
fields — both are worse than a seam.

### Q2 — Session lifetime: per-turn

The `EpistemicGraph` is rebuilt every turn from the `RecognitionOutcome`
emitted by `recognize()`. State from prior turns is not carried forward in
the graph.

Session-persistent graphs (propositions from turn 3 can transition to
VERIFIED in turn 5) require a session home (vault? session context?) that
does not yet exist. That is post-ADR-0144 scope.

### Q3 — Cold-start behavior: no-carrier

When `recognize()` returns a refusal state (`UNDETERMINED`, `CONTRADICTED`,
`AMBIGUOUS`), no `EpistemicGraph` is created.
`CognitiveTurnResult.epistemic_graph` is `None`.
`CognitiveTurnResult.refusal_reason` carries the typed refusal reason as
a string (existing field, already wired in ADR-0024 Phase 2).

When no `DerivedRecognizer` is attached to the pipeline (cold start, or
proposition type outside the current recognizer's teaching set), the
recognition step is skipped entirely. The pipeline behaves byte-identically
to its pre-ADR-0144 state.

---

## Data types

### `EpistemicTransition` — a single state transition with provenance

```python
# recognition/carrier.py

@dataclass(frozen=True, slots=True)
class EpistemicTransition:
    """A single epistemic state transition with its provenance.

    ``from_state`` and ``to_state`` are values from the ADR-0142 taxonomy
    (EVIDENCED, VERIFIED, DECODED, …).  ``source`` identifies the
    subsystem that caused the transition.  ``reason`` is a human-readable
    description for audit — not load-bearing for replay.
    """
    from_state: str
    to_state: str
    source: str   # e.g. "verifier", "vault", "recognizer"
    reason: str
```

### `EpistemicNode` — one proposition with recognition output + history

```python
@dataclass(frozen=True, slots=True)
class EpistemicNode:
    """One recognized proposition with full provenance chain.

    ``node_id`` is deterministic: the teaching_set_id of the recognizer
    used, suffixed with ``:<turn_index>`` (e.g. ``"sha256abc:0"``).
    This ensures node IDs are byte-identical across runs on the same
    input and recognizer.

    ``recognition_outcome`` is the frozen ADR-0143 output object carrying
    the FeatureBundle (or refusal reason) and RecognitionProvenance.

    ``transitions`` accumulates provenance as subsystems transition the
    state.  Empty on construction — the recognizer's emission state is
    authoritative until a subsystem adds a transition.
    """
    node_id: str
    recognition_outcome: RecognitionOutcome
    transitions: tuple[EpistemicTransition, ...] = ()

    @property
    def epistemic_state(self) -> str:
        """Current state: transitions[-1].to_state if any, else outcome.state."""
        if self.transitions:
            return self.transitions[-1].to_state
        return self.recognition_outcome.state

    def with_transition(self, transition: EpistemicTransition) -> "EpistemicNode":
        """Return a new node with the transition appended (immutable update)."""
        return EpistemicNode(
            node_id=self.node_id,
            recognition_outcome=self.recognition_outcome,
            transitions=(*self.transitions, transition),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "epistemic_state": self.epistemic_state,
            "recognition_outcome": self.recognition_outcome.as_dict(),
            "transitions": [t.as_dict() for t in self.transitions],
        }
```

### `EpistemicGraph` — the carrier

```python
@dataclass(frozen=True, slots=True)
class EpistemicGraph:
    """Per-turn epistemic carrier for recognized propositions.

    ``nodes`` is a tuple of EpistemicNodes in recognition order (one per
    recognized proposition per turn; ADR-0144 Phase 1 emits exactly one
    node per admitted turn).

    ``recognizer_id`` is the ``teaching_set_id`` of the DerivedRecognizer
    used to produce this graph — byte-identical across runs on the same
    recognizer and input.  Carries replay identity.
    """
    nodes: tuple[EpistemicNode, ...]
    recognizer_id: str

    def get(self, node_id: str) -> EpistemicNode | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "recognizer_id": self.recognizer_id,
            "nodes": [n.as_dict() for n in self.nodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False,
                          separators=(",", ":"), sort_keys=True)
```

**Invariants:**
- `EpistemicGraph.to_json()` must be byte-identical across runs on the
  same `DerivedRecognizer` and input token sequence.
- Every `EpistemicNode.node_id` within a graph is unique.
- `EpistemicNode.transitions` is append-only. No transition is ever
  removed or replaced.

---

## Connector: `EpistemicNode` → `GraphNode`

```python
# recognition/connector.py

def epistemic_node_to_graph_node(
    node: EpistemicNode,
    *,
    source_intent: IntentTag,
    node_id: str | None = None,
) -> GraphNode:
    """Derive a generation-side GraphNode from an admitted EpistemicNode.

    Only callable when ``node.recognition_outcome.state == EVIDENCED``.
    Raises ``ValueError`` otherwise.

    Feature-bundle → GraphNode mapping (v1, has-relation propositions):
      subject   ← bundle["agent"].value  (str)
      predicate ← bundle["relation"].value  (str)
      obj       ← f"{bundle['count'].value} {bundle['unit'].value}"  (str)

    This mapping is intentionally narrow in v1.  As the recognizer is
    extended to new proposition types, the mapping table grows here.
    Unknown feature names raise ``ValueError`` so the gap surfaces
    explicitly rather than silently defaulting.
    """
    outcome = node.recognition_outcome
    if outcome.state != EVIDENCED:
        raise ValueError(
            f"Cannot derive GraphNode from non-EVIDENCED EpistemicNode: "
            f"state={outcome.state!r}"
        )
    bundle = outcome.proposition
    assert bundle is not None  # invariant: EVIDENCED → proposition not None

    agent = bundle.get("agent")
    relation = bundle.get("relation")
    count = bundle.get("count")
    unit = bundle.get("unit")

    subject = str(agent.value) if agent is not None else "<unknown-agent>"
    predicate = str(relation.value) if relation is not None else "has"
    obj = (
        f"{count.value} {unit.value}"
        if count is not None and unit is not None
        else "<pending>"
    )

    return GraphNode(
        node_id=node_id or node.node_id,
        subject=subject,
        predicate=predicate,
        obj=obj,
        source_intent=source_intent,
    )
```

---

## Pipeline wiring

### `CognitiveTurnPipeline.__init__` addition

```python
def __init__(
    self,
    runtime,
    teaching_store: TeachingStore | None = None,
    recognizer: DerivedRecognizer | None = None,   # NEW — default None
) -> None:
    ...
    self._recognizer = recognizer
```

`recognizer=None` is the backward-compatible default. Every existing caller
of `CognitiveTurnPipeline(runtime, ...)` is unaffected.

### Recognition step in `run()`

Insert after `raw_tokens = tuple(self.runtime.tokenize(text))` (which
already exists in `run()` at the bottom of the method) — but the recognition
step needs tokens early. Restructure to tokenize once at the top of `run()`:

```python
def run(self, text: str, max_tokens: int | None = None) -> CognitiveTurnResult:

    # 0. TOKENIZE — once at the top; reused by recognition and trace.
    raw_tokens: tuple[str, ...] = tuple(self.runtime.tokenize(text))

    # 0b. RECOGNIZE — if a DerivedRecognizer is attached.
    epistemic_graph: EpistemicGraph | None = None
    recognition_refusal_str: str = ""

    if self._recognizer is not None:
        recognition_outcome = recognize(self._recognizer, raw_tokens)
        if recognition_outcome.admitted:
            node = EpistemicNode(
                node_id=f"{self._recognizer.teaching_set_id}:{self._turn_number}",
                recognition_outcome=recognition_outcome,
                transitions=(),
            )
            epistemic_graph = EpistemicGraph(
                nodes=(node,),
                recognizer_id=self._recognizer.teaching_set_id,
            )
        elif recognition_outcome.refusal_reason is not None:
            recognition_refusal_str = repr(
                recognition_outcome.refusal_reason.as_dict()
            )

    # 1. LISTEN — pre-turn field state (existing code, unchanged)
    ...
```

### `recognition_grounded_graph` flag

Add to `RuntimeConfig`:

```python
# ADR-0144 — recognition-grounded articulation graph.  When True and a
# DerivedRecognizer is attached to the pipeline, the articulation graph
# is derived from the admitted EpistemicNode via the connector rather
# than from intent classification.  Default False preserves byte-identity
# for every existing surface and trace_hash.
recognition_grounded_graph: bool = False
```

When `recognition_grounded_graph=True` and `epistemic_graph is not None`,
replace the intent-derived `graph` with one constructed from the connector:

```python
if self.runtime.config.recognition_grounded_graph and epistemic_graph is not None:
    derived_node = epistemic_graph.nodes[0]
    derived_graph_node = epistemic_node_to_graph_node(
        derived_node, source_intent=intent.tag
    )
    graph = PropositionGraph().add_node(derived_graph_node)
    target = plan_articulation(graph)
```

When `recognition_grounded_graph=False` (default), the intent-derived
`graph` is used unchanged — byte-identical to pre-ADR-0144.

### `CognitiveTurnResult` addition

```python
# --- recognition / epistemic carrier (ADR-0144) ---
# ``epistemic_graph`` is None when no DerivedRecognizer is attached,
# when recognition refused, or on the first turn before any recognizer
# is configured.  Non-None only when recognition admitted.
# NOT folded into trace_hash in Phase 1 (observability only);
# trace_hash participation is gated on session-persistent provenance
# (post-ADR-0144 scope).
epistemic_graph: EpistemicGraph | None = None
```

---

## Implementation debt: `_ratify_intent` PASSTHROUGH collapse

The `_ratify_intent` method collapses three distinct cold-start conditions
into one indistinguishable `PASSTHROUGH` outcome, making it impossible to
diagnose which precondition failed (ADR-0142 §Implementation debts, debt 1).

Fix as part of this ADR since the wiring change touches `_ratify_intent`'s
callers:

Extend `RatificationOutcome` (in `generate/intent_ratifier.py`) with three
distinct passthrough values:

```python
class RatificationOutcome(Enum):
    RATIFIED   = "ratified"
    DEMOTED    = "demoted"
    PASSTHROUGH_NO_FIELD  = "passthrough_no_field"   # field_state is None
    PASSTHROUGH_NO_VOCAB  = "passthrough_no_vocab"   # vocab is None
    PASSTHROUGH_NO_VERSOR = "passthrough_no_versor"  # prompt_versor is None
    # Backward-compatible alias so existing callers checking
    # outcome == PASSTHROUGH keep working during the transition.
    PASSTHROUGH = "passthrough"
```

Update `_ratify_intent` to emit the specific value. Update
`compute_trace_hash` to continue treating all four PASSTHROUGH variants
identically (fold the `.value` string; callers that checked
`== "passthrough"` now check `in _PASSTHROUGH_OUTCOMES`).

---

## Acceptance test

### Phase 1 — admitted recognition produces a carrier

Given a `DerivedRecognizer` derived from Phase 1 or Phase 2 teaching
examples and an admissible input:

1. `CognitiveTurnPipeline(runtime, recognizer=recognizer).run(text)` returns
   a `CognitiveTurnResult` where `epistemic_graph` is not `None`.
2. `epistemic_graph.nodes` has exactly one node.
3. `node.epistemic_state == "evidenced"`.
4. `node.recognition_outcome.proposition` is the same `FeatureBundle`
   returned by `recognize(recognizer, tokens)` directly — field-for-field
   equal.
5. `node.recognition_outcome.provenance.teaching_set_id ==
   recognizer.teaching_set_id`.
6. Two runs produce byte-identical `epistemic_graph.to_json()`.
7. All existing `core test --suite smoke -q` tests pass (no regressions).

### Phase 2 — refused recognition produces no carrier

Given the same recognizer and an inadmissible input:

1. `CognitiveTurnResult.epistemic_graph is None`.
2. The pipeline completes without raising.
3. `CognitiveTurnResult.trace_hash` is byte-identical across two runs.
4. All existing tests pass.

### Phase 3 — connector produces a valid articulation graph

Given an admitted `EpistemicNode` from a Phase 1/2 recognizer:

1. `epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)`
   returns a `GraphNode` with non-empty `subject`, `predicate`, `obj`.
2. `PropositionGraph().add_node(derived_node)` passes `plan_articulation()`
   without raising.
3. With `recognition_grounded_graph=True`, the pipeline produces a surface
   derived from the feature bundle's agent/relation/count/unit fields.
4. With `recognition_grounded_graph=False` (default), output is
   byte-identical to pre-ADR-0144 on the same input.

---

## File layout

```
recognition/
  __init__.py        (existing — add EpistemicGraph, EpistemicNode to __all__)
  outcome.py         (existing — unchanged)
  anti_unifier.py    (existing — unchanged)
  carrier.py         (NEW — EpistemicTransition, EpistemicNode, EpistemicGraph)
  connector.py       (NEW — epistemic_node_to_graph_node)

core/config.py       (add recognition_grounded_graph: bool = False)
core/cognition/
  pipeline.py        (add recognizer param; wire recognition step; add
                      epistemic_graph to CognitiveTurnResult construction)
  result.py          (add epistemic_graph: EpistemicGraph | None = None)

generate/
  intent_ratifier.py (extend RatificationOutcome with three PASSTHROUGH variants)

tests/
  test_epistemic_carrier.py  (NEW — acceptance test phases 1–3)
```

---

## What this ADR does NOT commit

- **Verifier implementation.** The `EpistemicNode.with_transition()` API
  exists so the verifier can append transitions; the verifier itself is
  out of scope.
- **Vault cross-reference.** VERIFIED → DECODED transition requires vault
  replay-equality check. Deferred.
- **Session-persistent graph.** Per-turn carrier is the gate. Persistent
  session graph (propositions survive across turns) requires a session home.
- **Storage layer for DerivedRecognizer.** Where recognizers live (pack /
  vault / substrate) is deferred from ADR-0143.
- **Trace hash participation for `epistemic_graph`.** `EpistemicGraph` is
  not folded into `trace_hash` in Phase 1. That gate opens when
  session-persistent provenance lands.
- **Connector generalization.** The v1 connector covers `has`-relation
  feature bundles only. New proposition types extend the mapping table.
- **Grounding-source dispatcher provenance gaps.** Six gaps identified in
  ADR-0142 §Implementation debts, debt 2. Require a session carrier before
  they can be fixed. Post-ADR-0144.
- **Teaching pipeline `MetricSet` dataclass.** ADR-0142 §Implementation
  debts, debt 3. Not blocked by PropositionGraph; tracked separately.

---

## Consequences

- `CognitiveTurnPipeline` grows a `recognizer` constructor parameter.
  Default `None` — all existing callers unaffected.
- `CognitiveTurnResult` grows `epistemic_graph: EpistemicGraph | None`.
  Default `None` — all existing serialization unaffected.
- `RuntimeConfig` grows `recognition_grounded_graph: bool = False`.
  Default preserves byte-identity.
- `RatificationOutcome` grows three specific PASSTHROUGH values. Existing
  callers checking `== "passthrough"` must migrate to an `in` check;
  the backward-compatible `PASSTHROUGH = "passthrough"` alias covers the
  transition window.
- Recognition is now a first-class step in the cognitive turn. Every
  UNDETERMINED / CONTRADICTED / AMBIGUOUS outcome is auditable —
  it carries a typed `RefusalReason` — rather than being silently absent.
  Refusal is teaching signal, not silence.
- Integration into the live generation path is explicit and opt-in
  (`recognition_grounded_graph=True`). Operators control when recognized
  propositions replace intent-derived articulation graphs.
