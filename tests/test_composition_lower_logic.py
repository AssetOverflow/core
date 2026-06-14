"""M1 — the composition spine's logic lowering, in isolation.

`lower_logic_chain` is the extracted (byte-identical) lowering from
`generate/determine/determine.py::_verify_subsumption`. These pin the EXACT
propositional theory it emits (so a wrong extraction is caught) and the
soundness-by-construction refusal of a mislabeled chain. The byte-PARITY of the
end-to-end determine path is covered by the unchanged determine/transitive tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.composition import LogicChainPlan, lower_logic_chain


@dataclass(frozen=True)
class _Fact:
    """Minimal duck-typed relational fact (the lowering reads only these two)."""

    relation_predicate: str
    relation_arguments: tuple[str, ...]


def test_member_chain_lowers_to_member_subset_theory() -> None:
    # "Socrates is a man" (member) ∘ "man ⊆ mortal" (subset) → member(Socrates, mortal).
    plan = LogicChainPlan(
        predicate="member",
        subject="socrates",
        target="mortal",
        member_fact=_Fact("member", ("socrates", "man")),
        subset_path=(_Fact("subset", ("man", "mortal")),),
    )
    lowered = lower_logic_chain(plan)
    assert lowered is not None
    premises, query = lowered
    # M(soc,man)=x0, S(man,mortal)=x1, sound rule (M∘S→M): (x0 & x1) -> M(soc,mortal)=x2.
    assert premises == ("x0", "x1", "(x0 & x1) -> x2")
    assert query == "x2"


def test_subset_chain_lowers_to_subset_subset_theory() -> None:
    # "a ⊆ b", "b ⊆ c" → subset(a, c) by subset ∘ subset.
    plan = LogicChainPlan(
        predicate="subset",
        subject="a",
        target="c",
        member_fact=None,
        subset_path=(_Fact("subset", ("a", "b")), _Fact("subset", ("b", "c"))),
    )
    lowered = lower_logic_chain(plan)
    assert lowered is not None
    premises, query = lowered
    # S(a,b)=x0, S(b,c)=x1, rule (S∘S→S): (x0 & x1) -> S(a,c)=x2.
    assert premises == ("x0", "x1", "(x0 & x1) -> x2")
    assert query == "x2"


def test_mislabeled_member_fact_refuses() -> None:
    # A member_fact whose predicate is not "member" must NOT be lowered (it could be
    # smuggled in as a subset edge → an unsound member∘member chain).
    plan = LogicChainPlan(
        predicate="member",
        subject="socrates",
        target="mortal",
        member_fact=_Fact("subset", ("socrates", "man")),  # wrong predicate
        subset_path=(_Fact("subset", ("man", "mortal")),),
    )
    assert lower_logic_chain(plan) is None


def test_member_fact_in_subset_path_refuses() -> None:
    # A "member" fact laundered into the subset_path must be refused.
    plan = LogicChainPlan(
        predicate="subset",
        subject="a",
        target="c",
        member_fact=None,
        subset_path=(_Fact("subset", ("a", "b")), _Fact("member", ("b", "c"))),  # member smuggled in
    )
    assert lower_logic_chain(plan) is None


def test_wrong_arity_refuses() -> None:
    plan = LogicChainPlan(
        predicate="subset",
        subject="a",
        target="c",
        member_fact=None,
        subset_path=(_Fact("subset", ("a", "b", "extra")),),  # arity 3
    )
    assert lower_logic_chain(plan) is None
