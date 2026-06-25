from __future__ import annotations

import ast
from pathlib import Path

from generate.problem_frame_builder import build_problem_frame

ROOT = Path(__file__).resolve().parents[1]


def _tree(path: str) -> ast.AST:
    return ast.parse((ROOT / path).read_text(), filename=path)


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names.add(node.module)
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def _defined_function_names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def test_builder_has_no_assessment_backed_proposal_imports_or_calls() -> None:
    tree = _tree("generate/problem_frame_builder.py")
    forbidden = {"make_proposal", "assess_contracts", "get_contract_family_id"}

    assert forbidden.isdisjoint(_imported_names(tree))
    assert forbidden.isdisjoint(_called_names(tree))


def test_proposal_phase_does_not_import_contracts_or_builder() -> None:
    imports = _imported_names(_tree("generate/problem_frame_proposals.py"))

    assert "generate.problem_frame_contracts" not in imports
    assert "problem_frame_contracts" not in imports
    assert "ProblemFrameBuilder" not in imports


def test_contract_phase_does_not_import_builder() -> None:
    imports = _imported_names(_tree("generate/problem_frame_contracts.py"))

    assert "generate.problem_frame_builder" not in imports
    assert "problem_frame_builder" not in imports


def test_builder_no_longer_defines_phase_helpers() -> None:
    defined = _defined_function_names(_tree("generate/problem_frame_builder.py"))

    assert not {name for name in defined if name.startswith("_extract_")}
    assert not {name for name in defined if name.endswith("_proposals")}
    assert "_quantity_kind_dispositions" not in defined
    assert "_bound_relations" not in defined
    assert "_bound_question_target" not in defined


def test_builder_smoke_shapes_remain_grounded() -> None:
    simple = build_problem_frame("Mia has 7 apples. How many apples does Mia have?")
    assert tuple(proposal.family_id for proposal in simple.proposals) == (
        "binding.quantity_entity",
    )
    assert {mention.surface.lower() for mention in simple.mentions} >= {"7", "apples"}
    assert simple.bindings

    gained = build_problem_frame("Tom gained 3 apples. How many apples did Tom gain?")
    assert "state_change.unary_delta" in {
        proposal.family_id for proposal in gained.proposals
    }
    assert gained.unary_delta_cues
    assert any(relation.relation_type == "unary_delta" for relation in gained.bound_relations)

    measurement = build_problem_frame("The tank has 3 liters. How much liquid is in the tank?")
    assert {unit.surface for unit in measurement.units} == {"liters"}
    assert any(mention.surface == "3" for mention in measurement.mentions)
