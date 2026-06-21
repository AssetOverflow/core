from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import generate.foundational_families as foundational_families
from generate.foundational_families import (
    FoundationalFamilySpec,
    get_foundational_family,
    get_foundational_family_by_relation_type,
    iter_foundational_families,
    require_foundational_family,
)


EXPECTED_FAMILY_IDS = (
    "binding.quantity_entity",
    "state_change.transition",
)


def test_registry_contains_only_the_two_approved_specs_in_deterministic_order() -> None:
    families = iter_foundational_families()

    assert isinstance(families, tuple)
    assert tuple(family.family_id for family in families) == EXPECTED_FAMILY_IDS
    assert tuple(family.family_id for family in iter_foundational_families()) == (
        EXPECTED_FAMILY_IDS
    )


def test_public_family_accessors() -> None:
    quantity = get_foundational_family("binding.quantity_entity")
    state_change = require_foundational_family("state_change.transition")

    assert quantity is not None
    assert quantity.family_id == "binding.quantity_entity"
    assert state_change.family_id == "state_change.transition"
    assert get_foundational_family("missing.family") is None

    with pytest.raises(KeyError, match="missing.family"):
        require_foundational_family("missing.family")


def test_lookup_by_primary_relation_type() -> None:
    quantity = get_foundational_family_by_relation_type("quantity_entity")
    state_change = get_foundational_family_by_relation_type("state_change")

    assert quantity is get_foundational_family("binding.quantity_entity")
    assert state_change is get_foundational_family("state_change.transition")
    assert get_foundational_family_by_relation_type("missing_relation") is None


def test_registry_keys_are_unique() -> None:
    families = iter_foundational_families()
    family_ids = tuple(family.family_id for family in families)
    relation_types = tuple(family.primary_relation_type for family in families)

    assert len(family_ids) == len(set(family_ids))
    assert len(relation_types) == len(set(relation_types))


def test_specs_are_frozen_and_explicitly_not_authorized() -> None:
    for family in iter_foundational_families():
        assert isinstance(family, FoundationalFamilySpec)
        assert family.serving_allowed is False
        assert family.implementation_authorized is False
        assert "not serving" in family.serving_status.lower()

        with pytest.raises(FrozenInstanceError):
            family.display_name = "mutated"  # type: ignore[misc]


def test_required_adr_0224_fields_are_populated() -> None:
    required_fields = (
        "family_id",
        "display_name",
        "status",
        "related_adrs",
        "domains",
        "summary",
        "surface_chunk_patterns",
        "semantic_neighborhood",
        "construction_signatures",
        "required_roles",
        "optional_roles",
        "hazards_confusers",
        "frame_representation",
        "contract_readiness_criteria",
        "verification_style",
        "refusal_conditions",
        "cross_domain_evidence",
        "current_state",
        "target_state",
        "serving_status",
        "primary_relation_type",
        "future_adapter",
    )

    for family in iter_foundational_families():
        assert all(getattr(family, field) for field in required_fields)
        assert "ADR-0224" in family.related_adrs
        assert family.hazards_confusers
        assert family.refusal_conditions
        assert family.current_state != family.target_state


def test_each_family_has_at_least_two_non_math_evidence_examples() -> None:
    math_domains = {
        "arithmetic",
        "arithmetic_quantitative",
        "arithmetic_proportional",
        "mathematics",
    }

    for family in iter_foundational_families():
        non_math_evidence = tuple(
            evidence
            for evidence in family.cross_domain_evidence
            if evidence.domain not in math_domains
        )
        assert len(non_math_evidence) >= 2
        assert all(evidence.example for evidence in non_math_evidence)
        assert all(evidence.expected_roles for evidence in non_math_evidence)


def test_registry_module_has_no_markdown_or_filesystem_loading_surface() -> None:
    source_path = Path(foundational_families.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "pathlib" not in imported_modules | imported_from_modules
    assert "markdown" not in imported_modules | imported_from_modules
    assert "open" not in called_names
    assert not ({"read_text", "read_bytes"} & called_attributes)
