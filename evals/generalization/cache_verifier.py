"""Verifier for local generalization benchmark cache directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from evals.generalization.manifest_schema import (
    load_and_validate_manifest,
    ManifestValidationError,
)

GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION = "generalization_cache_verifier.v1"


@dataclass(frozen=True, slots=True)
class CacheVerificationRecord:
    """Readiness and verification details for a single generalization benchmark cache."""

    dataset: str
    manifest_path: str
    local_cache: str
    exists: bool
    license_ready: bool
    checksum_ready: bool
    runnable: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CacheVerificationReport:
    """Aggregated cache verification report across all manifests."""

    policy_version: str
    records: tuple[CacheVerificationRecord, ...]
    all_runnable: bool
    reason_codes: tuple[str, ...]


def verify_local_generalization_cache(
    repo_root: Path,
    manifests_dir: Path,
    require_present: bool = False,
) -> CacheVerificationReport:
    """Verify all generalization benchmark manifests and local cache directory readiness.

    Args:
        repo_root: Path to the root of the git repository.
        manifests_dir: Path to the directory containing YAML manifests.
        require_present: If True, raises ValueError if any local cache directory is missing.

    Returns:
        A CacheVerificationReport containing verification records for all manifests.
    """
    if not manifests_dir.exists() or not manifests_dir.is_dir():
        raise ValueError(f"Manifests directory does not exist: {manifests_dir}")

    manifest_files = sorted(manifests_dir.glob("*.yaml"))
    records: list[CacheVerificationRecord] = []

    benchmarks_dir = (repo_root / ".data/benchmarks").resolve()

    for path in manifest_files:
        manifest = load_and_validate_manifest(path)
        local_cache = manifest.local_cache

        # Check path traversal and escaping
        # resolved cache directory path must lie strictly within .data/benchmarks/
        cache_path = (repo_root / local_cache).resolve()
        try:
            cache_path.relative_to(benchmarks_dir)
        except ValueError as exc:
            raise ManifestValidationError(
                f"Path traversal detected: local_cache {local_cache!r} in {path.name} "
                f"resolves outside .data/benchmarks/ ({cache_path})"
            ) from exc

        # Check directory existence (no files inside should be read/opened)
        exists = cache_path.is_dir()

        if require_present and not exists:
            raise ValueError(
                f"Cache directory for dataset {manifest.dataset} does not exist: {cache_path}"
            )

        license_ready = manifest.license != "TODO_VERIFY_BEFORE_CACHE"
        checksum_ready = manifest.sha256 != "TODO_AFTER_DOWNLOAD"
        runnable = license_ready and checksum_ready and exists

        reason_codes_list: list[str] = []
        if not exists:
            reason_codes_list.append("CACHE_ABSENT")
        if not license_ready:
            reason_codes_list.append("LICENSE_UNRESOLVED")
        if not checksum_ready:
            reason_codes_list.append("CHECKSUM_UNRESOLVED")

        try:
            rel_manifest_path = str(path.relative_to(repo_root))
        except ValueError:
            rel_manifest_path = str(path)

        records.append(
            CacheVerificationRecord(
                dataset=manifest.dataset,
                manifest_path=rel_manifest_path,
                local_cache=local_cache,
                exists=exists,
                license_ready=license_ready,
                checksum_ready=checksum_ready,
                runnable=runnable,
                reason_codes=tuple(reason_codes_list),
            )
        )

    all_runnable = all(r.runnable for r in records)

    report_reasons = set()
    for r in records:
        report_reasons.update(r.reason_codes)

    return CacheVerificationReport(
        policy_version=GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION,
        records=tuple(records),
        all_runnable=all_runnable,
        reason_codes=tuple(sorted(report_reasons)),
    )
