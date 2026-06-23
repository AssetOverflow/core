"""Tests for the GSM1K local cache adapter."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
import pytest

import evals.generalization.cache_verifier
from evals.generalization.adapters.gsm1k import load_gsm1k_items
from evals.generalization.cache_verifier import (
    CacheVerificationRecord,
    CacheVerificationReport,
)
from scripts.benchmarks.run_generalization_audit import main as cli_main


def write_synthetic_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_synthetic_json(path: Path, data: any) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_loads_synthetic_jsonl_records(tmp_path: Path) -> None:
    """GSM1K adapter loads synthetic JSONL records and produces stable item IDs."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Alice has 2 apples.", "answer": "2", "id": "q1"},
        {"question": "Bob has 3 apples.", "answer": "3", "id": "q2"},
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    items = load_gsm1k_items(local_cache=cache_dir, split="test")

    assert len(items) == 2
    assert items[0].dataset == "GSM1K"
    assert items[0].split == "test"
    assert items[0].item_id == "q1"
    assert items[0].prompt_ref == "gsm1k:test:q1"
    assert items[0].answer_kind == "numeric_text"

    # Verify opaque metadata
    metadata_dict = dict(items[0].metadata)
    assert "question" not in metadata_dict
    assert "prompt" not in metadata_dict
    assert "answer" not in metadata_dict
    assert "grade" not in metadata_dict
    assert "label" not in metadata_dict

    assert "question_sha256" in metadata_dict
    assert "answer_sha256" in metadata_dict
    assert "question_length" in metadata_dict
    assert metadata_dict["source_record_id"] == "q1"


def test_loads_synthetic_json_records(tmp_path: Path) -> None:
    """GSM1K adapter loads synthetic JSON array records."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Charlie has 5 coins.", "answer": "5", "id": "c1"},
        {"question": "David has 10 coins.", "answer": "10", "id": "c2"},
    ]
    write_synthetic_json(cache_dir / "test.json", records)

    items = load_gsm1k_items(local_cache=cache_dir, split="test")

    assert len(items) == 2
    assert items[0].item_id == "c1"
    assert items[1].item_id == "c2"


def test_honors_max_items(tmp_path: Path) -> None:
    """GSM1K adapter honors max_items argument."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
        {"question": "Q3", "answer": "A3"},
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    items = load_gsm1k_items(local_cache=cache_dir, split="test", max_items=2)
    assert len(items) == 2
    assert items[0].item_id == "0"
    assert items[1].item_id == "1"


def test_refuses_missing_cache_path() -> None:
    """GSM1K adapter raises FileNotFoundError if cache path is missing."""
    with pytest.raises(
        FileNotFoundError,
        match="Cache directory does not exist|Local cache path does not exist",
    ):
        load_gsm1k_items(
            local_cache=Path("non_existent_directory_1234"), split="test"
        )


def test_refuses_unsupported_split(tmp_path: Path) -> None:
    """GSM1K adapter raises FileNotFoundError if split file is not found."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    write_synthetic_jsonl(
        cache_dir / "test.jsonl", [{"question": "Q", "answer": "A"}]
    )

    with pytest.raises(
        FileNotFoundError, match="No JSON or JSONL file found for split"
    ):
        load_gsm1k_items(local_cache=cache_dir, split="train")


def test_refuses_malformed_record_missing_question(tmp_path: Path) -> None:
    """GSM1K adapter raises ValueError if a record is missing the question field."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"answer": "5", "id": "1"},  # missing question/prompt
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    with pytest.raises(ValueError, match="missing 'question' or 'prompt'"):
        load_gsm1k_items(local_cache=cache_dir, split="test")


def test_refuses_malformed_record_missing_answer(tmp_path: Path) -> None:
    """GSM1K adapter raises ValueError if a record is missing the answer field."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Q?", "id": "1"},  # missing answer/grade/label
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    with pytest.raises(
        ValueError, match="missing 'answer', 'grade', or 'label'"
    ):
        load_gsm1k_items(local_cache=cache_dir, split="test")


def test_does_not_download_or_write_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GSM1K adapter does not use network or write files to disk during load."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    write_synthetic_jsonl(
        cache_dir / "test.jsonl", [{"question": "Q", "answer": "A"}]
    )

    # Intercept socket calls to block network
    def blocked_socket(*args: any, **kwargs: any) -> any:
        raise RuntimeError("Network calls are forbidden during loading!")

    monkeypatch.setattr(socket, "socket", blocked_socket)

    # Intercept write/open actions on paths that are not the test file
    orig_write_text = Path.write_text

    def blocked_write_text(self: Path, *args: any, **kwargs: any) -> any:
        if self.parent.resolve() != cache_dir.resolve():
            raise RuntimeError(
                f"Writing to disk outside test cache is forbidden: {self}"
            )
        return orig_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", blocked_write_text)

    items = load_gsm1k_items(local_cache=cache_dir, split="test")
    assert len(items) == 1


def test_repository_contains_no_committed_gsm1k_examples() -> None:
    """Check that the repository contains no committed GSM1K examples or dataset files."""
    repo_root = Path(__file__).parent.parent.parent.parent

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = result.stdout.strip().splitlines()
    except (subprocess.SubprocessError, FileNotFoundError):
        tracked_files = []
        benchmarks_dir = repo_root / ".data" / "benchmarks"
        if benchmarks_dir.exists():
            tracked_files = [
                str(p) for p in benchmarks_dir.rglob("*") if p.is_file()
            ]

    # Make sure no tracked files under .data/benchmarks/ exist except .gitkeep
    for f in tracked_files:
        if ".data/benchmarks" in f and not f.endswith(".gitkeep"):
            pytest.fail(f"Committed benchmark cache file found: {f}")

    # Check that no manifest YAML file contains actual benchmark questions/answers
    manifest_dir = repo_root / "evals" / "generalization" / "manifests"
    gsm1k_manifest = manifest_dir / "gsm1k.yaml"
    if gsm1k_manifest.exists():
        content = gsm1k_manifest.read_text(encoding="utf-8")
        assert (
            "question" not in content.lower()
        ), "GSM1K manifest contains raw question data!"
        assert (
            "answer" not in content.lower() or "grade" in content.lower()
        ), "GSM1K manifest contains raw answer data!"


def test_cli_refuses_unresolved_manifest_gates() -> None:
    """The CLI refuses to run if the manifest has unresolved license/checksum gates."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmarks/run_generalization_audit.py",
            "--dataset",
            "gsm1k",
            "--split",
            "test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "benchmark_manifest_unresolved" in result.stderr


def test_cli_local_adapter_works_with_temp_cache_and_metadata_only(
    tmp_path: Path,
) -> None:
    """The CLI run works when --metadata-only is passed with local-cache."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Alice has 2 apples.", "answer": "2", "id": "q1"},
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmarks/run_generalization_audit.py",
            "--dataset",
            "gsm1k",
            "--split",
            "test",
            "--local-cache",
            str(cache_dir),
            "--metadata-only",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["dataset"] == "GSM1K"
    assert report["n_items"] == 1
    assert report["metadata_only"] is True
    # The metadata-only path does not claim correct/wrong
    assert "correct" not in report
    assert "wrong" not in report


def test_cli_real_gsm1k_without_evaluator_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI refuses to run a full audit without an evaluator, failing with dataset_evaluator_unavailable."""
    cache_dir = tmp_path / "gsm1k_cache"
    cache_dir.mkdir()
    records = [
        {"question": "Alice has 2 apples.", "answer": "2", "id": "q1"},
    ]
    write_synthetic_jsonl(cache_dir / "test.jsonl", records)

    # Monkeypatch verify_local_generalization_cache to report resolved gates
    def mock_verify(*args: any, **kwargs: any) -> CacheVerificationReport:
        record = CacheVerificationRecord(
            dataset="GSM1K",
            manifest_path="gsm1k.yaml",
            local_cache=str(cache_dir),
            exists=True,
            license_ready=True,
            checksum_ready=True,
            runnable=True,
            reason_codes=(),
        )
        return CacheVerificationReport(
            policy_version="test.v1",
            records=(record,),
            all_runnable=True,
            reason_codes=(),
        )

    monkeypatch.setattr(
        evals.generalization.cache_verifier,
        "verify_local_generalization_cache",
        mock_verify,
    )

    # Setup sys.argv to run CLI without --metadata-only
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_generalization_audit.py",
            "--dataset",
            "gsm1k",
            "--local-cache",
            str(cache_dir),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        cli_main()
    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert "dataset_evaluator_unavailable" in captured.err
