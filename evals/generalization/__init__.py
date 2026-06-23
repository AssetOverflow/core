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

__all__ = [
    "GeneralizationBenchmarkManifest",
    "ManifestValidationError",
    "load_and_validate_manifest",
    "validate_manifest_data",
    "GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION",
    "CacheVerificationRecord",
    "CacheVerificationReport",
    "verify_local_generalization_cache",
]
