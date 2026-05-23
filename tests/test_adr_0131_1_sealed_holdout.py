"""ADR-0131.1.S — Sealed holdout tests for symbolic equivalence v1.

Pins:
1. Sealed holdout file exists and is age-formatted.
2. Decryption fails (raises EnvironmentError) if CORE_SEALED_KEY is unset or points to a non-existent file.
3. Decryption yields valid JSONL cases matching the schema.
4. The sealed runner passes its exit criterion (wrong == 0, correct_rate >= 0.95).
5. The holdout cases are strictly disjoint from the public cases (no duplicate case_id or expression pairs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from evals.math_symbolic_equivalence.v1.sealed_runner import (
    build_report,
    decrypt_cases,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEALED_PATH = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "sealed_holdout.age"
_PUBLIC_CASES_PATH = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "cases.jsonl"


def _decrypt_or_skip() -> list[dict]:
    """Helper to decrypt cases or skip if key is missing."""
    key = os.environ.get("CORE_SEALED_KEY")
    if not key:
        pytest.skip("CORE_SEALED_KEY not set; skipping decryption test")
    key_path = Path(key)
    if not key_path.exists():
        pytest.skip(f"CORE_SEALED_KEY path {key_path} does not exist; skipping decryption test")
    try:
        return decrypt_cases(_SEALED_PATH)
    except Exception as exc:
        pytest.fail(f"Decryption failed: {exc}")


class TestSealedFileExists:
    def test_sealed_file_present(self) -> None:
        assert _SEALED_PATH.exists(), f"missing sealed file: {_SEALED_PATH}"
        assert _SEALED_PATH.is_file()
        assert _SEALED_PATH.stat().st_size > 0

    def test_sealed_file_is_age_formatted(self) -> None:
        head = _SEALED_PATH.read_bytes()[:64]
        assert head.startswith(b"age-encryption.org/"), (
            f"sealed file does not look age-formatted; head={head!r}"
        )


class TestDecryptionGated:
    def test_decryption_refuses_without_key(self) -> None:
        old_key = os.environ.get("CORE_SEALED_KEY")
        if "CORE_SEALED_KEY" in os.environ:
            del os.environ["CORE_SEALED_KEY"]
        
        try:
            with pytest.raises(EnvironmentError) as excinfo:
                decrypt_cases(_SEALED_PATH)
            assert "CORE_SEALED_KEY environment variable is not set" in str(excinfo.value)
        finally:
            if old_key is not None:
                os.environ["CORE_SEALED_KEY"] = old_key

    def test_decryption_refuses_with_invalid_key_path(self) -> None:
        old_key = os.environ.get("CORE_SEALED_KEY")
        os.environ["CORE_SEALED_KEY"] = "/nonexistent/path/to/key.txt"
        
        try:
            with pytest.raises(EnvironmentError) as excinfo:
                decrypt_cases(_SEALED_PATH)
            assert "CORE_SEALED_KEY file path does not exist" in str(excinfo.value)
        finally:
            if old_key is not None:
                os.environ["CORE_SEALED_KEY"] = old_key


class TestSealedFileContent:
    def test_decrypt_produces_valid_schema(self) -> None:
        cases = _decrypt_or_skip()
        assert len(cases) >= 10, f"expected at least 10 holdout cases, got {len(cases)}"
        
        for c in cases:
            assert "case_id" in c
            assert c["case_id"].startswith("sym-eq-v1-hld-")
            assert "expression_a" in c
            assert isinstance(c["expression_a"], str) and c["expression_a"]
            assert "expression_b" in c
            assert isinstance(c["expression_b"], str) and c["expression_b"]
            assert "expected" in c
            assert c["expected"] in ("equivalent", "not_equivalent", "refused")
            assert "category" in c
            assert isinstance(c["category"], str) and c["category"]
            assert "provenance" in c
            assert "adr-0131.1" in c["provenance"]

    def test_disjointness_from_public_cases(self) -> None:
        sealed_cases = _decrypt_or_skip()
        
        # Load public cases
        public_cases = []
        with _PUBLIC_CASES_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    public_cases.append(json.loads(line))
        
        public_ids = {c["case_id"] for c in public_cases}
        public_pairs = {
            (c["expression_a"].strip(), c["expression_b"].strip())
            for c in public_cases
        }
        
        for c in sealed_cases:
            assert c["case_id"] not in public_ids, (
                f"Duplicate case_id {c['case_id']} found in sealed holdout"
            )
            pair = (c["expression_a"].strip(), c["expression_b"].strip())
            reverse_pair = (c["expression_b"].strip(), c["expression_a"].strip())
            assert pair not in public_pairs and reverse_pair not in public_pairs, (
                f"Duplicate expression pair {pair} found in sealed holdout"
            )


class TestSealedRunnerGate:
    def test_runner_passes_exit_criterion(self) -> None:
        cases = _decrypt_or_skip()
        report = build_report(cases)
        assert report["exit_criterion"]["passed"], (
            f"Sealed holdout runner failed: correct_rate={report['correct_rate']}, "
            f"wrong={report['counts']['wrong']}"
        )
        assert report["counts"]["wrong"] == 0, "Sealed holdout must have wrong == 0"
        assert report["correct_rate"] >= 0.95, "Sealed holdout correct rate must be >= 0.95"
