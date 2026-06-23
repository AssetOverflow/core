"""Generalization benchmark audit infrastructure."""

from __future__ import annotations

from evals.generalization.manifest_schema import (
    GeneralizationBenchmarkManifest,
    ManifestValidationError,
    load_and_validate_manifest,
    validate_manifest_data,
)
from evals.generalization.cache_verifier import (
    GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION,
    CacheVerificationRecord,
    CacheVerificationReport,
    verify_local_generalization_cache,
)
from evals.generalization.item_schema import (
    GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION,
    GeneralizationAuditItem,
    GeneralizationAuditOutcome,
    GeneralizationAuditReport,
)
from evals.generalization.audit_runner import run_generalization_audit
from evals.generalization.adapters.gsm1k import load_gsm1k_items

__all__ = [
    "GeneralizationBenchmarkManifest",
    "ManifestValidationError",
    "load_and_validate_manifest",
    "validate_manifest_data",
    "GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION",
    "CacheVerificationRecord",
    "CacheVerificationReport",
    "verify_local_generalization_cache",
    "GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION",
    "GeneralizationAuditItem",
    "GeneralizationAuditOutcome",
    "GeneralizationAuditReport",
    "run_generalization_audit",
    "load_gsm1k_items",
]
