"""MeaningGraph — Phase 2a (COMPREHEND): the neutral general-meaning interlingua.

The refusal-first, provenance-carrying structure the field-decode produces and
the domain reasoners project from. Unlike the binding-graph (ADR-0132,
quantity/equation-shaped), this carries GENERAL meaning: entities + n-ary named
relations. Every test below must MEANINGFULLY FAIL under the violation it names
(CLAUDE.md schema-defined-proof-obligation rule) — a refusal-first model is only
real if construction refuses the malformed.
"""

from __future__ import annotations

import pytest

from generate.meaning_graph.model import (
    Entity,
    MeaningGraph,
    MeaningGraphError,
    MeaningSpan,
    Relation,
)


def _span(text: str = "Alice", start: int = 0) -> MeaningSpan:
    return MeaningSpan(source_id="s1", start=start, end=start + len(text), text=text)


# --------------------------------------------------------------------------- #
# MeaningSpan — provenance, refusal-first
# --------------------------------------------------------------------------- #


def test_span_holds_halfopen_interval() -> None:
    sp = MeaningSpan(source_id="doc", start=2, end=7, text="lice ")
    assert sp.to_canonical_string() == "doc[2:7]"


def test_span_refuses_empty_end_le_start() -> None:
    with pytest.raises(MeaningGraphError):
        MeaningSpan(source_id="doc", start=5, end=5, text="x")
    with pytest.raises(MeaningGraphError):
        MeaningSpan(source_id="doc", start=5, end=4, text="x")


def test_span_refuses_empty_source_or_text() -> None:
    with pytest.raises(MeaningGraphError):
        MeaningSpan(source_id="", start=0, end=1, text="x")
    with pytest.raises(MeaningGraphError):
        MeaningSpan(source_id="doc", start=0, end=1, text="")


# --------------------------------------------------------------------------- #
# Entity — refusal-first
# --------------------------------------------------------------------------- #


def test_entity_constructs() -> None:
    e = Entity(entity_id="alice", name="Alice", span=_span())
    assert e.entity_id == "alice"
    assert e.kind is None


def test_entity_refuses_non_identifier_id() -> None:
    # entity_id must be a Python identifier so it can key relations safely.
    with pytest.raises(MeaningGraphError):
        Entity(entity_id="al ice", name="Alice", span=_span())
    with pytest.raises(MeaningGraphError):
        Entity(entity_id="", name="Alice", span=_span())


def test_entity_refuses_empty_name() -> None:
    with pytest.raises(MeaningGraphError):
        Entity(entity_id="alice", name="", span=_span())


# --------------------------------------------------------------------------- #
# Relation — n-ary named predicate, refusal-first
# --------------------------------------------------------------------------- #


def test_relation_constructs_binary() -> None:
    r = Relation(predicate="mother_of", arguments=("alice", "bob"), span=_span("is the mother of"))
    assert r.arity == 2
    assert r.negated is False


def test_relation_refuses_empty_predicate() -> None:
    with pytest.raises(MeaningGraphError):
        Relation(predicate="", arguments=("alice", "bob"), span=_span())


def test_relation_refuses_zero_arguments() -> None:
    # A relation with no arguments is not a relation.
    with pytest.raises(MeaningGraphError):
        Relation(predicate="rains", arguments=(), span=_span())


def test_relation_refuses_non_identifier_argument() -> None:
    with pytest.raises(MeaningGraphError):
        Relation(predicate="mother_of", arguments=("alice", "b ob"), span=_span())


def test_relation_carries_negation() -> None:
    r = Relation(predicate="equal_to", arguments=("a", "b"), span=_span(), negated=True)
    assert r.negated is True


# --------------------------------------------------------------------------- #
# MeaningGraph — cross-collection referential integrity
# --------------------------------------------------------------------------- #


def _alice_bob_graph() -> MeaningGraph:
    return MeaningGraph(
        entities=(
            Entity(entity_id="alice", name="Alice", span=_span("Alice", 0)),
            Entity(entity_id="bob", name="Bob", span=_span("Bob", 21)),
        ),
        relations=(
            Relation(
                predicate="mother_of",
                arguments=("alice", "bob"),
                span=_span("is the mother of", 6),
            ),
        ),
    )


def test_graph_constructs_and_is_frozen() -> None:
    g = _alice_bob_graph()
    assert len(g.entities) == 2
    assert len(g.relations) == 1
    with pytest.raises((AttributeError, Exception)):
        g.entities = ()  # type: ignore[misc]


def test_graph_refuses_duplicate_entity_id() -> None:
    with pytest.raises(MeaningGraphError):
        MeaningGraph(
            entities=(
                Entity(entity_id="alice", name="Alice", span=_span()),
                Entity(entity_id="alice", name="Alicia", span=_span()),
            ),
            relations=(),
        )


def test_graph_refuses_relation_referencing_unknown_entity() -> None:
    # The decisive integrity check: a relation argument must name a known entity.
    with pytest.raises(MeaningGraphError):
        MeaningGraph(
            entities=(Entity(entity_id="alice", name="Alice", span=_span()),),
            relations=(
                Relation(predicate="mother_of", arguments=("alice", "bob"), span=_span()),
            ),
        )


def test_graph_allows_relation_cycles() -> None:
    # Distinct from the binding-graph: general relations MAY cycle
    # ("A loves B, B loves A" is well-formed, not circular reasoning).
    g = MeaningGraph(
        entities=(
            Entity(entity_id="a", name="A", span=_span("A", 0)),
            Entity(entity_id="b", name="B", span=_span("B", 2)),
        ),
        relations=(
            Relation(predicate="loves", arguments=("a", "b"), span=_span("loves", 1)),
            Relation(predicate="loves", arguments=("b", "a"), span=_span("loves", 4)),
        ),
    )
    assert len(g.relations) == 2


# --------------------------------------------------------------------------- #
# Determinism + neutrality
# --------------------------------------------------------------------------- #


def test_canonical_string_is_deterministic_and_bites() -> None:
    a = _alice_bob_graph().to_canonical_string()
    b = _alice_bob_graph().to_canonical_string()
    assert a == b
    # A different predicate must change the canonical form (it bites).
    moved = MeaningGraph(
        entities=(
            Entity(entity_id="alice", name="Alice", span=_span("Alice", 0)),
            Entity(entity_id="bob", name="Bob", span=_span("Bob", 21)),
        ),
        relations=(
            Relation(predicate="sister_of", arguments=("alice", "bob"), span=_span("is the mother of", 6)),
        ),
    )
    assert moved.to_canonical_string() != a


def test_negation_changes_canonical_form() -> None:
    pos = Relation(predicate="equal_to", arguments=("a", "b"), span=_span())
    neg = Relation(predicate="equal_to", arguments=("a", "b"), span=_span(), negated=True)
    base = (Entity(entity_id="a", name="A", span=_span("A", 0)),
            Entity(entity_id="b", name="B", span=_span("B", 2)))
    g_pos = MeaningGraph(entities=base, relations=(pos,))
    g_neg = MeaningGraph(entities=base, relations=(neg,))
    assert g_pos.to_canonical_string() != g_neg.to_canonical_string()


def test_model_is_neutral_imports_no_algebra_or_field() -> None:
    # INV-26-style neutrality: the interlingua must not couple to the engine
    # substrate, so two independent decodings can meet there honestly.
    import ast
    import pathlib

    src = pathlib.Path("generate/meaning_graph/model.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"algebra", "field", "numpy", "evals", "core", "chat", "vault", "session"}
    assert not (imported & forbidden), f"meaning_graph.model coupled to {imported & forbidden}"
