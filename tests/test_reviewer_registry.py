"""Unit tests for the Reviewer Registry v1 loader (ADR-0092)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.capability.reviewers import (
    ReviewerRegistry,
    ReviewerRegistryError,
    SCHEMA_VERSION,
    load_reviewer_registry,
)


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "reviewers.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def _valid_primary_yaml() -> str:
    return """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack", "proposal", "chain", "eval"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""


def _valid_domain_yaml() -> str:
    return """\
schema_version: 1
reviewers:
  - reviewer_id: math-reviewer
    display_name: "Math Domain Reviewer"
    role: domain
    domains: ["mathematics_logic"]
    review_scope: ["pack", "chain"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""


class TestPositiveLoad:
    def test_loads_primary_reviewer(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _valid_primary_yaml())
        registry = load_reviewer_registry(path)
        assert isinstance(registry, ReviewerRegistry)
        assert registry.schema_version == SCHEMA_VERSION
        assert len(registry.reviewers) == 1
        reviewer = registry.reviewers[0]
        assert reviewer.reviewer_id == "shay-j"
        assert reviewer.role == "primary"
        assert reviewer.domains == ("*",)
        assert reviewer.review_scope == ("pack", "proposal", "chain", "eval")

    def test_loads_domain_reviewer(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _valid_domain_yaml())
        registry = load_reviewer_registry(path)
        assert registry.reviewers[0].role == "domain"
        assert registry.reviewers[0].domains == ("mathematics_logic",)

    def test_registry_is_frozen(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _valid_primary_yaml())
        registry = load_reviewer_registry(path)
        with pytest.raises((AttributeError, TypeError)):
            registry.reviewers = ()  # type: ignore[misc]

    def test_reviewer_is_frozen(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _valid_primary_yaml())
        registry = load_reviewer_registry(path)
        with pytest.raises((AttributeError, TypeError)):
            registry.reviewers[0].role = "domain"  # type: ignore[misc]


class TestResolution:
    def test_resolve_known_reviewer(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_primary_yaml()))
        reviewer = registry.resolve("shay-j")
        assert reviewer is not None
        assert reviewer.reviewer_id == "shay-j"

    def test_resolve_unknown_reviewer(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_primary_yaml()))
        assert registry.resolve("ghost") is None

    def test_can_review_primary_covers_any_domain(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_primary_yaml()))
        assert registry.can_review("shay-j", domain_id="mathematics_logic", scope="pack")
        assert registry.can_review("shay-j", domain_id="physics", scope="proposal")

    def test_can_review_domain_only_covers_declared(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_domain_yaml()))
        assert registry.can_review("math-reviewer", domain_id="mathematics_logic", scope="pack")
        assert not registry.can_review("math-reviewer", domain_id="physics", scope="pack")

    def test_can_review_respects_scope(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_domain_yaml()))
        assert registry.can_review("math-reviewer", domain_id="mathematics_logic", scope="chain")
        assert not registry.can_review(
            "math-reviewer", domain_id="mathematics_logic", scope="proposal"
        )

    def test_can_review_unknown_reviewer_returns_false(self, tmp_path: Path) -> None:
        registry = load_reviewer_registry(_write_yaml(tmp_path, _valid_primary_yaml()))
        assert not registry.can_review("ghost", domain_id="mathematics_logic", scope="pack")


class TestNegativeSchema:
    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ReviewerRegistryError, match="not found"):
            load_reviewer_registry(tmp_path / "absent.yaml")

    def test_wrong_schema_version(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, "schema_version: 2\nreviewers: []\n")
        with pytest.raises(ReviewerRegistryError, match="schema_version"):
            load_reviewer_registry(path)

    def test_missing_schema_version(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, "reviewers: []\n")
        with pytest.raises(ReviewerRegistryError, match="schema_version"):
            load_reviewer_registry(path)

    def test_unknown_top_level_key(self, tmp_path: Path) -> None:
        path = _write_yaml(
            tmp_path,
            "schema_version: 1\nreviewers: []\nextra_field: nope\n",
        )
        with pytest.raises(ReviewerRegistryError, match="unknown top-level"):
            load_reviewer_registry(path)

    def test_reviewers_must_be_list(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, "schema_version: 1\nreviewers: {}\n")
        with pytest.raises(ReviewerRegistryError, match="must be a list"):
            load_reviewer_registry(path)

    def test_unknown_reviewer_field(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
    secret_powers: ["unlimited"]
"""
        with pytest.raises(ReviewerRegistryError, match="unknown fields"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_missing_required_field(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack"]
"""
        with pytest.raises(ReviewerRegistryError, match="missing required fields"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_invalid_role(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: emperor
    domains: ["*"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="invalid role"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_domain_reviewer_cannot_claim_wildcard(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: math-reviewer
    display_name: "Math Reviewer"
    role: domain
    domains: ["*"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="wildcard"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_primary_reviewer_must_claim_wildcard(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["mathematics_logic"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="wildcard"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_unknown_review_scope_value(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack", "deploy"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="unknown review_scope"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_empty_review_scope(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: []
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="empty 'review_scope'"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_duplicate_reviewer_id(self, tmp_path: Path) -> None:
        yaml = """\
schema_version: 1
reviewers:
  - reviewer_id: shay-j
    display_name: "Joshua Shay"
    role: primary
    domains: ["*"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
  - reviewer_id: shay-j
    display_name: "Imposter"
    role: primary
    domains: ["*"]
    review_scope: ["pack"]
    provenance: "adr-0092:bootstrap:2026-05-21"
"""
        with pytest.raises(ReviewerRegistryError, match="duplicate reviewer_id"):
            load_reviewer_registry(_write_yaml(tmp_path, yaml))

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, "schema_version: 1\nreviewers: [\n")
        with pytest.raises(ReviewerRegistryError, match="YAML parse error"):
            load_reviewer_registry(path)


class TestProductionRegistry:
    """Verify the in-tree docs/reviewers.yaml passes ADR-0092 v1 schema."""

    def test_production_registry_loads(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        registry = load_reviewer_registry(repo_root / "docs" / "reviewers.yaml")
        assert registry.schema_version == SCHEMA_VERSION
        assert len(registry.reviewers) >= 1
        ids = [r.reviewer_id for r in registry.reviewers]
        assert "shay-j" in ids

    def test_production_bootstrap_reviewer_is_primary(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        registry = load_reviewer_registry(repo_root / "docs" / "reviewers.yaml")
        shay = registry.resolve("shay-j")
        assert shay is not None
        assert shay.role == "primary"
        assert shay.domains == ("*",)
        assert shay.provenance.startswith("adr-0092:bootstrap:")
