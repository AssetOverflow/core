"""Schema and validation policies for generalization benchmark manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional
import yaml


@dataclass(frozen=True)
class GeneralizationBenchmarkManifest:
    """Represents a validated generalization benchmark manifest."""

    dataset: str
    purpose: str
    description: str
    source: str
    license: str
    version: str
    split: str
    sha256: str
    local_cache: str
    repo_policy: str
    inspection_policy: str
    mutation_policy: str
    smoke_fixture: Optional[str] = None
    notes: Optional[str] = None
    hf_config: Optional[str] = None


class ManifestValidationError(Exception):
    """Raised when a manifest violates schema or policy constraints."""


REQUIRED_FIELDS = {
    "dataset",
    "purpose",
    "description",
    "source",
    "license",
    "version",
    "split",
    "sha256",
    "local_cache",
    "repo_policy",
    "inspection_policy",
    "mutation_policy",
}

ALLOWED_FIELDS = REQUIRED_FIELDS | {"smoke_fixture", "notes", "hf_config"}

SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
VIBE_LICENSE_WORDS = {"typically", "probably", "confirm;", "likely", "check"}


def validate_manifest_data(data: Mapping[str, Any]) -> GeneralizationBenchmarkManifest:
    """Validate a loaded manifest dictionary against policy constraints."""
    if not isinstance(data, Mapping):
        raise ManifestValidationError("Manifest root must be a mapping.")

    # 1. Field existence checks
    missing_fields = REQUIRED_FIELDS - set(data.keys())
    if missing_fields:
        raise ManifestValidationError(
            f"Missing required fields: {sorted(missing_fields)}"
        )

    extra_fields = set(data.keys()) - ALLOWED_FIELDS
    if extra_fields:
        raise ManifestValidationError(f"Unknown fields found: {sorted(extra_fields)}")

    # 2. Extract and check types
    dataset = data["dataset"]
    purpose = data["purpose"]
    description = data["description"]
    source = data["source"]
    lic = data["license"]
    version = data["version"]
    split = data["split"]
    sha256 = data["sha256"]
    local_cache = data["local_cache"]
    repo_policy = data["repo_policy"]
    inspection_policy = data["inspection_policy"]
    mutation_policy = data["mutation_policy"]
    smoke_fixture = data.get("smoke_fixture")
    notes = data.get("notes")
    hf_config = data.get("hf_config")

    # Type validation
    for name, val in [
        ("dataset", dataset),
        ("purpose", purpose),
        ("description", description),
        ("source", source),
        ("license", lic),
        ("version", version),
        ("split", split),
        ("sha256", sha256),
        ("local_cache", local_cache),
        ("repo_policy", repo_policy),
        ("inspection_policy", inspection_policy),
        ("mutation_policy", mutation_policy),
    ]:
        if not isinstance(val, str):
            raise ManifestValidationError(f"Field '{name}' must be a string.")

    if smoke_fixture is not None and not isinstance(smoke_fixture, str):
        raise ManifestValidationError("Field 'smoke_fixture' must be null or a string.")
    if notes is not None and not isinstance(notes, str):
        raise ManifestValidationError("Field 'notes' must be null or a string.")
    if hf_config is not None and not isinstance(hf_config, str):
        raise ManifestValidationError("Field 'hf_config' must be null or a string.")

    # 3. Policy constraint validation
    if purpose != "sealed_audit_not_training":
        raise ManifestValidationError(
            f"Field 'purpose' must be 'sealed_audit_not_training'; got {purpose!r}"
        )

    if repo_policy != "manifest_only":
        raise ManifestValidationError(
            f"Field 'repo_policy' must be 'manifest_only'; got {repo_policy!r}"
        )

    if inspection_policy != "aggregate_reports_only":
        raise ManifestValidationError(
            f"Field 'inspection_policy' must be 'aggregate_reports_only'; got {inspection_policy!r}"
        )

    if mutation_policy != "no_direct_pack_policy_operator_mutation":
        raise ManifestValidationError(
            f"Field 'mutation_policy' must be 'no_direct_pack_policy_operator_mutation'; got {mutation_policy!r}"
        )

    if not local_cache.startswith(".data/benchmarks/"):
        raise ManifestValidationError(
            f"Field 'local_cache' must start with '.data/benchmarks/'; got {local_cache!r}"
        )
    if not local_cache.endswith("/"):
        raise ManifestValidationError(
            f"Field 'local_cache' must end with '/' to denote a directory path; got {local_cache!r}"
        )

    # sha256 checks
    if sha256 != "TODO_AFTER_DOWNLOAD" and not SHA256_RE.match(sha256):
        raise ManifestValidationError(
            f"Field 'sha256' must be 'TODO_AFTER_DOWNLOAD' or a valid 64-char hex SHA256; got {sha256!r}"
        )

    # license checks
    lic_lower = lic.lower()
    if "todo" in lic_lower and lic != "TODO_VERIFY_BEFORE_CACHE":
        raise ManifestValidationError(
            f"Field 'license' containing 'TODO' must be exactly 'TODO_VERIFY_BEFORE_CACHE'; got {lic!r}"
        )

    for word in VIBE_LICENSE_WORDS:
        if word in lic_lower:
            raise ManifestValidationError(
                f"Field 'license' contains non-permitted vague/vibe word '{word}': {lic!r}"
            )

    # smoke_fixture checks
    if smoke_fixture is not None:
        if lic == "TODO_VERIFY_BEFORE_CACHE":
            raise ManifestValidationError(
                f"Dataset has smoke_fixture {smoke_fixture!r} but license is still 'TODO_VERIFY_BEFORE_CACHE'"
            )

    return GeneralizationBenchmarkManifest(
        dataset=dataset,
        purpose=purpose,
        description=description,
        source=source,
        license=lic,
        version=version,
        split=split,
        sha256=sha256,
        local_cache=local_cache,
        repo_policy=repo_policy,
        inspection_policy=inspection_policy,
        mutation_policy=mutation_policy,
        smoke_fixture=smoke_fixture,
        notes=notes,
        hf_config=hf_config,
    )


def load_and_validate_manifest(path: Path) -> GeneralizationBenchmarkManifest:
    """Load a manifest from a YAML file and validate it."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestValidationError(
            f"Failed to read manifest file at {path}: {exc}"
        ) from exc

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ManifestValidationError(
            f"YAML parse error in manifest at {path}: {exc}"
        ) from exc

    try:
        return validate_manifest_data(data)
    except ManifestValidationError as exc:
        raise ManifestValidationError(
            f"Validation error in manifest {path.name}: {exc}"
        ) from exc
