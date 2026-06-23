"""Tests for the local generalization benchmark cache verifier."""

from __future__ import annotations

import builtins
import json
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

from evals.generalization.cache_verifier import (
    verify_local_generalization_cache,
    GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION,
)
from evals.generalization.manifest_schema import ManifestValidationError
from scripts.benchmarks.verify_generalization_cache import main as cli_main


def write_test_manifest(
    manifests_dir: Path,
    dataset: str = "TEST",
    license: str = "TODO_VERIFY_BEFORE_CACHE",
    sha256: str = "TODO_AFTER_DOWNLOAD",
    local_cache: str = ".data/benchmarks/test/",
) -> Path:
    """Helper to write a synthetic manifest YAML file."""
    data = {
        "dataset": dataset,
        "purpose": "sealed_audit_not_training",
        "description": "Test description",
        "source": "hf://test/test",
        "license": license,
        "version": "pinned",
        "split": "test",
        "sha256": sha256,
        "local_cache": local_cache,
        "repo_policy": "manifest_only",
        "inspection_policy": "aggregate_reports_only",
        "mutation_policy": "no_direct_pack_policy_operator_mutation",
    }
    path = manifests_dir / f"{dataset.lower()}.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_metadata_only_succeeds_with_absent_cache(tmp_path: Path) -> None:
    """metadata-only succeeds with absent cache."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    write_test_manifest(manifests_dir, dataset="TEST_ABSENT")

    report = verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
    )
    assert len(report.records) == 1
    record = report.records[0]
    assert record.dataset == "TEST_ABSENT"
    assert record.exists is False
    assert record.runnable is False
    assert "CACHE_ABSENT" in record.reason_codes
    assert report.all_runnable is False


def test_require_present_refuses_absent_cache(tmp_path: Path) -> None:
    """require-present refuses absent cache."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    write_test_manifest(manifests_dir, dataset="TEST_ABSENT")

    with pytest.raises(ValueError, match="does not exist"):
        verify_local_generalization_cache(
            repo_root=repo_root, manifests_dir=manifests_dir, require_present=True
        )


def test_todo_license_makes_runnable_false(tmp_path: Path) -> None:
    """TODO license makes runnable=false."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    cache_dir = repo_root / ".data" / "benchmarks" / "test"
    cache_dir.mkdir(parents=True)

    valid_sha = "a" * 64
    write_test_manifest(
        manifests_dir,
        dataset="TEST_TODO_LICENSE",
        license="TODO_VERIFY_BEFORE_CACHE",
        sha256=valid_sha,
    )

    report = verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
    )
    record = report.records[0]
    assert record.exists is True
    assert record.license_ready is False
    assert record.checksum_ready is True
    assert record.runnable is False
    assert "LICENSE_UNRESOLVED" in record.reason_codes


def test_todo_sha256_makes_runnable_false(tmp_path: Path) -> None:
    """TODO sha256 makes runnable=false."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    cache_dir = repo_root / ".data" / "benchmarks" / "test"
    cache_dir.mkdir(parents=True)

    write_test_manifest(
        manifests_dir,
        dataset="TEST_TODO_SHA",
        license="MIT",
        sha256="TODO_AFTER_DOWNLOAD",
    )

    report = verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
    )
    record = report.records[0]
    assert record.exists is True
    assert record.license_ready is True
    assert record.checksum_ready is False
    assert record.runnable is False
    assert "CHECKSUM_UNRESOLVED" in record.reason_codes


def test_resolved_license_valid_sha_present_cache_runnable(tmp_path: Path) -> None:
    """resolved license + valid sha256 + present cache makes runnable=true."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    cache_dir = repo_root / ".data" / "benchmarks" / "test"
    cache_dir.mkdir(parents=True)

    valid_sha = "b" * 64
    write_test_manifest(
        manifests_dir,
        dataset="TEST_RUNNABLE",
        license="Apache-2.0",
        sha256=valid_sha,
    )

    report = verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=True
    )
    record = report.records[0]
    assert record.exists is True
    assert record.license_ready is True
    assert record.checksum_ready is True
    assert record.runnable is True
    assert len(record.reason_codes) == 0
    assert report.all_runnable is True


def test_local_cache_outside_benchmarks_refuses(tmp_path: Path) -> None:
    """local_cache outside .data/benchmarks refuses."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    # Write a manifest directly with invalid local_cache
    data = {
        "dataset": "BAD_CACHE",
        "purpose": "sealed_audit_not_training",
        "description": "Test description",
        "source": "hf://test/test",
        "license": "MIT",
        "version": "pinned",
        "split": "test",
        "sha256": "c" * 64,
        "local_cache": ".data/other/test/",  # outside .data/benchmarks/
        "repo_policy": "manifest_only",
        "inspection_policy": "aggregate_reports_only",
        "mutation_policy": "no_direct_pack_policy_operator_mutation",
    }
    path = manifests_dir / "bad_cache.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ManifestValidationError):
        verify_local_generalization_cache(
            repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
        )


def test_path_traversal_local_cache_refuses(tmp_path: Path) -> None:
    """path traversal local_cache refuses."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    # Write a manifest with path traversal escaping via ..
    data = {
        "dataset": "TRAVERSAL",
        "purpose": "sealed_audit_not_training",
        "description": "Test description",
        "source": "hf://test/test",
        "license": "MIT",
        "version": "pinned",
        "split": "test",
        "sha256": "c" * 64,
        "local_cache": ".data/benchmarks/../other/",  # path traversal
        "repo_policy": "manifest_only",
        "inspection_policy": "aggregate_reports_only",
        "mutation_policy": "no_direct_pack_policy_operator_mutation",
    }
    path = manifests_dir / "traversal.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="Path traversal detected"):
        verify_local_generalization_cache(
            repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
        )


def test_cli_rejects_download_flags(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI rejects --download / --fetch / --pull."""
    for flag in ("--download", "--fetch", "--pull"):
        monkeypatch.setattr(sys, "argv", ["verify_generalization_cache.py", flag])
        with pytest.raises(SystemExit) as excinfo:
            cli_main()
        assert excinfo.value.code != 0
        captured = capsys.readouterr()
        assert "not supported" in captured.err


def test_json_output_deterministic(tmp_path: Path) -> None:
    """JSON output is deterministic."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    write_test_manifest(manifests_dir, dataset="B_DATASET")
    write_test_manifest(manifests_dir, dataset="A_DATASET")

    report = verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
    )

    from dataclasses import asdict

    json1 = json.dumps(asdict(report), indent=2, sort_keys=True)
    json2 = json.dumps(asdict(report), indent=2, sort_keys=True)
    assert json1 == json2

    # Verify sorting by filename (dataset key) is deterministic
    records = report.records
    assert records[0].dataset == "A_DATASET"
    assert records[1].dataset == "B_DATASET"


def test_does_not_open_example_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verification does not open/read example files inside the cache."""
    repo_root = tmp_path
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (repo_root / ".data" / "benchmarks").mkdir(parents=True)

    cache_dir = repo_root / ".data" / "benchmarks" / "test"
    cache_dir.mkdir(parents=True)
    sentinel_file = cache_dir / "example.jsonl"
    sentinel_file.write_text("dummy content", encoding="utf-8")

    write_test_manifest(manifests_dir, dataset="TEST_SENTINEL")

    read_paths: list[Path] = []

    # Spy on Path read methods
    orig_read_text = Path.read_text

    def mock_read_text(self: Path, *args: any, **kwargs: any) -> str:
        read_paths.append(self)
        return orig_read_text(self, *args, **kwargs)

    orig_read_bytes = Path.read_bytes

    def mock_read_bytes(self: Path, *args: any, **kwargs: any) -> bytes:
        read_paths.append(self)
        return orig_read_bytes(self, *args, **kwargs)

    orig_open = Path.open

    def mock_open(self: Path, *args: any, **kwargs: any) -> any:
        read_paths.append(self)
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)
    monkeypatch.setattr(Path, "open", mock_open)

    # Patch builtin open
    orig_builtin_open = builtins.open

    def mock_builtin_open(file: any, *args: any, **kwargs: any) -> any:
        if isinstance(file, (str, Path)):
            read_paths.append(Path(file))
        return orig_builtin_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_builtin_open)

    verify_local_generalization_cache(
        repo_root=repo_root, manifests_dir=manifests_dir, require_present=False
    )

    # Ensure no read path resides inside the cache directory
    for p in read_paths:
        resolved_p = p.resolve()
        assert not resolved_p.is_relative_to(
            cache_dir.resolve()
        ), f"Read file inside cache: {resolved_p}"


def test_cli_subprocess_metadata_only_json() -> None:
    """Run CLI in metadata-only and json mode via subprocess against actual manifests."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmarks/verify_generalization_cache.py",
            "--metadata-only",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["policy_version"] == GENERALIZATION_CACHE_VERIFIER_POLICY_VERSION
    assert isinstance(report["records"], list)
    assert len(report["records"]) > 0
