"""Capability reporting surfaces (Phase A-C scaffolding)."""

from .domain_contract_predicates import (
    DomainContractPredicateReport,
    PredicateResult,
    evaluate_domain_contract,
)
from .reporting import (
    CapabilityArtifactQuery,
    artifact_report,
    chain_report,
    evidence_plan_report,
    flag_report,
    ledger_report,
)
from .reviewers import (
    ALLOWED_REVIEWER_KEYS,
    ALLOWED_ROLES,
    ALLOWED_SCOPES,
    ALLOWED_TOP_LEVEL_KEYS,
    Reviewer,
    ReviewerRegistry,
    ReviewerRegistryError,
    SCHEMA_VERSION as REVIEWER_REGISTRY_SCHEMA_VERSION,
    load_reviewer_registry,
)

__all__ = [
    "ALLOWED_REVIEWER_KEYS",
    "ALLOWED_ROLES",
    "ALLOWED_SCOPES",
    "ALLOWED_TOP_LEVEL_KEYS",
    "CapabilityArtifactQuery",
    "DomainContractPredicateReport",
    "PredicateResult",
    "REVIEWER_REGISTRY_SCHEMA_VERSION",
    "Reviewer",
    "ReviewerRegistry",
    "ReviewerRegistryError",
    "artifact_report",
    "chain_report",
    "evaluate_domain_contract",
    "evidence_plan_report",
    "flag_report",
    "ledger_report",
    "load_reviewer_registry",
]
