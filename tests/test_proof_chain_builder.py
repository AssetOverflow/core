"""ADR-0204 — proof-graph builder (phase 2.2, structure only).

Proves the builder in isolation before any inference rule sits on it:
1. valid proof DAGs construct cleanly;
2. the corpus cycle case (PC-CYCLE-001) refuses through the REAL builder path —
   the ADR-0203 guard firing on a real proof construction for the first time;
3. canonical_key round-trips byte-identically through rhs_canonical;
plus the admissibility-dispatch confirmation (proof operation_kinds refuse
gracefully, never misroute into the math checkers) and referential/out-of-regime
refusals inherited from the real substrate.
"""

from __future__ import annotations

import pytest

from generate.binding_graph import (
    AdmissibilityError,
    BindingGraphError,
    check_admissibility,
)
from generate.logic_canonical import LogicRegimeError, canonicalize
from generate.proof_chain import (
    PROOF_NO_UNIT,
    Proof,
    ProofError,
    ProofNode,
    build_proof_graph,
    proof_from_premises,
)


# ---------------------------------------------------------------------------
# 1. Valid proof DAGs construct cleanly
# ---------------------------------------------------------------------------


def test_valid_modus_ponens_shape_constructs() -> None:
    # PC-MP-001 desugared. The STRUCTURE builds; the modus_ponens CHECK is 2.3.
    proof = proof_from_premises(
        ("P_rains -> Q_ground_wet", "P_rains"), "Q_ground_wet", rule="modus_ponens"
    )
    pg = build_proof_graph(proof)
    assert pg.conclusion_symbol_id == "conclusion"
    assert len(pg.graph.equations) == 3
    concl = next(e for e in pg.graph.equations if e.lhs_symbol_id == "conclusion")
    assert concl.operation_kind == "modus_ponens"
    assert concl.dependencies == frozenset({"premise_0", "premise_1"})
    # Premises are equations with empty deps and operation_kind="premise".
    prem = next(e for e in pg.graph.equations if e.lhs_symbol_id == "premise_0")
    assert prem.operation_kind == "premise"
    assert prem.dependencies == frozenset()
    assert prem.unit_proof == PROOF_NO_UNIT


def test_multistep_dag_constructs() -> None:
    # n1 (premise), n2 (premise), n3 := f(n1,n2), n4 := f(n3) — strict DAG.
    proof = Proof(
        nodes=(
            ProofNode("n1", "P", (), "premise"),
            ProofNode("n2", "P -> Q", (), "premise"),
            ProofNode("n3", "Q", ("n1", "n2"), "modus_ponens"),
            ProofNode("n4", "Q | R", ("n3",), "or_intro"),
        ),
        conclusion_id="n4",
    )
    pg = build_proof_graph(proof)
    assert len(pg.graph.equations) == 4


# ---------------------------------------------------------------------------
# 2. PC-CYCLE-001 refuses through the REAL builder path
# ---------------------------------------------------------------------------


def test_corpus_cycle_refuses_through_builder() -> None:
    # PC-CYCLE-001: n1 depends_on n2, n2 depends_on n1. The 2.1 acyclicity guard
    # must fire through real proof construction — not just standalone find_cycle.
    proof = Proof(
        nodes=(
            ProofNode("n1", "P_rains", ("n2",), "modus_ponens"),
            ProofNode("n2", "Q_ground_wet", ("n1",), "modus_ponens"),
        ),
        conclusion_id="n1",
    )
    with pytest.raises(BindingGraphError) as exc:
        build_proof_graph(proof)
    assert "circular_dependency" in str(exc.value)


def test_self_dependency_refused_at_proof_model() -> None:
    # A length-1 cycle is refused early and clearly by the Proof model.
    with pytest.raises(ProofError):
        ProofNode("n1", "P", ("n1",), "modus_ponens")


def test_dangling_dependency_refuses() -> None:
    with pytest.raises(ProofError):
        Proof(nodes=(ProofNode("n1", "P", ("ghost",), "modus_ponens"),), conclusion_id="n1")


# ---------------------------------------------------------------------------
# 3. canonical_key round-trips byte-identically through rhs_canonical
# ---------------------------------------------------------------------------


def test_canonical_key_round_trips_byte_identical() -> None:
    formula = "(P -> Q) & (R | ~S)"
    proof = Proof(nodes=(ProofNode("n1", formula, (), "premise"),), conclusion_id="n1")
    eq = build_proof_graph(proof).graph.equations[0]
    assert eq.rhs_canonical == canonicalize(formula).canonical_key  # byte-identical


def test_equivalent_node_formulas_share_rhs_canonical() -> None:
    # Two nodes whose formulas are logically equivalent store identical
    # rhs_canonical — the graph can decide equivalence by string comparison
    # (the propositional twin of how the math graph uses rhs_canonical).
    proof = Proof(
        nodes=(
            ProofNode("a", "P & Q", (), "premise"),
            ProofNode("b", "Q & P", (), "premise"),
        ),
        conclusion_id="a",
    )
    eqs = {e.lhs_symbol_id: e.rhs_canonical for e in build_proof_graph(proof).graph.equations}
    assert eqs["a"] == eqs["b"]


# ---------------------------------------------------------------------------
# Admissibility-dispatch confirmation: proof operation_kinds refuse gracefully,
# never misroute into the math checkers (2.3's modus_ponens check hangs off this).
# ---------------------------------------------------------------------------


def test_proof_operation_kinds_refuse_in_admissibility_never_misroute() -> None:
    proof = proof_from_premises(("P -> Q", "P"), "Q", rule="modus_ponens")
    graph = build_proof_graph(proof).graph
    symbols = {s.symbol_id: s for s in graph.symbols}
    for eq in graph.equations:
        with pytest.raises(AdmissibilityError) as exc:
            check_admissibility(eq, symbols=symbols)
        # premise (no deps) reaches the kind dispatch -> unknown_operation;
        # modus_ponens (unitless deps) refuses at unit-resolution -> unit_unbound.
        # Either way it REFUSES and never returns a math UnitProof / misroutes.
        assert exc.value.reason in {"unknown_operation", "unit_unbound"}


# ---------------------------------------------------------------------------
# Out-of-regime formula in a node: the builder inherits the canonicalizer's
# typed refusal (honesty boundary — no silent admission of predicate logic).
# ---------------------------------------------------------------------------


def test_out_of_regime_node_formula_refuses() -> None:
    proof = Proof(
        nodes=(ProofNode("n1", "forall x. rains(x)", (), "premise"),),
        conclusion_id="n1",
    )
    with pytest.raises(LogicRegimeError):
        build_proof_graph(proof)
