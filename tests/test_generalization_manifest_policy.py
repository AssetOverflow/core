"""Tests to enforce generalization benchmark manifest policy constraints."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
import pytest

from evals.generalization.manifest_schema import (
    load_and_validate_manifest,
    ManifestValidationError,
    validate_manifest_data,
)

MANIFESTS_DIR = Path(__file__).parent.parent / "evals" / "generalization" / "manifests"


def test_all_manifests_valid() -> None:
    """Ensure all committed generalization manifests parse and satisfy policy checks."""
    manifest_files = list(MANIFESTS_DIR.glob("*.yaml"))
    assert len(manifest_files) > 0, "No manifests found in generalization/manifests/"

    for path in manifest_files:
        try:
            load_and_validate_manifest(path)
        except ManifestValidationError as exc:
            pytest.fail(f"Manifest {path.name} failed policy validation: {exc}")


def test_no_sealed_slice_in_comments() -> None:
    """Ensure no manifest comments contain the words 'sealed slice' to respect holdout rules."""
    manifest_files = list(MANIFESTS_DIR.glob("*.yaml"))
    for path in manifest_files:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            comment_idx = line.find("#")
            if comment_idx != -1:
                comment_text = line[comment_idx:]
                if "sealed slice" in comment_text.lower():
                    pytest.fail(
                        f"Manifest {path.name} contains forbidden comment text "
                        f"'sealed slice': {line!r}"
                    )


def test_manifest_validation_failures() -> None:
    """Test validation errors for invalid data cases."""
    base_valid = {
        "dataset": "TEST",
        "purpose": "sealed_audit_not_training",
        "description": "Test description",
        "source": "hf://test/test",
        "license": "TODO_VERIFY_BEFORE_CACHE",
        "version": "pinned",
        "split": "test",
        "sha256": "TODO_AFTER_DOWNLOAD",
        "local_cache": ".data/benchmarks/test/",
        "repo_policy": "manifest_only",
        "inspection_policy": "aggregate_reports_only",
        "mutation_policy": "no_direct_pack_policy_operator_mutation",
    }

    # Wrong purpose
    bad_purpose = base_valid.copy()
    bad_purpose["purpose"] = "training"
    with pytest.raises(ManifestValidationError, match="purpose"):
        validate_manifest_data(bad_purpose)

    # Missing field
    missing_field = base_valid.copy()
    del missing_field["dataset"]
    with pytest.raises(ManifestValidationError, match="Missing required fields"):
        validate_manifest_data(missing_field)

    # Extra field
    extra_field = base_valid.copy()
    extra_field["extra_key"] = "forbidden"
    with pytest.raises(ManifestValidationError, match="Unknown fields found"):
        validate_manifest_data(extra_field)

    # Invalid local_cache path structure
    bad_cache = base_valid.copy()
    bad_cache["local_cache"] = ".data/benchmarks/test"  # missing ending slash
    with pytest.raises(ManifestValidationError, match="end with '/'"):
        validate_manifest_data(bad_cache)

    # Invalid sha256
    bad_sha = base_valid.copy()
    bad_sha["sha256"] = "not-a-sha256"
    with pytest.raises(ManifestValidationError, match="sha256"):
        validate_manifest_data(bad_sha)

    # Vague license string
    bad_lic = base_valid.copy()
    bad_lic["license"] = "Typically Apache 2.0"
    with pytest.raises(
        ManifestValidationError, match="contains non-permitted vague/vibe word"
    ):
        validate_manifest_data(bad_lic)

    # License TODO mismatch
    bad_lic_todo = base_valid.copy()
    bad_lic_todo["license"] = "TODO verify"
    with pytest.raises(
        ManifestValidationError,
        match="license.*must be exactly 'TODO_VERIFY_BEFORE_CACHE'",
    ):
        validate_manifest_data(bad_lic_todo)

    # Smoke fixture with TODO license
    bad_smoke = base_valid.copy()
    bad_smoke["license"] = "TODO_VERIFY_BEFORE_CACHE"
    bad_smoke["smoke_fixture"] = "evals/generalization/smoke/test.jsonl"
    with pytest.raises(
        ManifestValidationError, match="has smoke_fixture.*but license is still"
    ):
        validate_manifest_data(bad_smoke)


def test_repo_leak_guard() -> None:
    """Ensure no files under .data/benchmarks/ are tracked in Git except .gitkeep."""
    repo_root = Path(__file__).parent.parent
    try:
        result = subprocess.run(
            ["git", "ls-files", ".data/benchmarks/"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback if git is not available in the test environment (e.g. sandbox limits)
        benchmarks_dir = repo_root / ".data" / "benchmarks"
        if benchmarks_dir.exists():
            tracked_files = [
                str(p.relative_to(repo_root))
                for p in benchmarks_dir.rglob("*")
                if p.is_file() and p.name != ".gitkeep"
            ]
            assert not tracked_files, (
                f"Found untracked/local benchmark files: {tracked_files}"
            )
        return

    tracked_files = result.stdout.strip().splitlines()
    # Normalize path separators
    tracked_files = [f.replace(os.sep, "/") for f in tracked_files]

    forbidden_files = [
        f
        for f in tracked_files
        if not f.endswith(".data/benchmarks/.gitkeep")
        and f != ".data/benchmarks/.gitkeep"
    ]
    assert not forbidden_files, (
        f"Committed files under .data/benchmarks/ detected: {forbidden_files}"
    )
