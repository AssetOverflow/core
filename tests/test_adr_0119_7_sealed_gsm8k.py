"""ADR-0119.7 — sealed GSM8K test set invariants.

Pins four load-bearing invariants:

1. **Sealed file exists.** ``evals/gsm8k_math/holdouts/v1/cases.jsonl.age``
   is on disk and age-formatted.

2. **No plaintext leaks.** No other plaintext-form holdout file
   (``cases.jsonl``, ``cases_plaintext.jsonl``, etc.) exists alongside
   the sealed file. The seal is one-way per ADR-0119.7's discipline.

3. **Sealed file is on the expected key.** Decrypting with the recipe
   identity registered under ADR-0119.1 succeeds; the plaintext parses
   to JSONL with the documented schema.

4. **Sealed file runs through the lane runner with `wrong == 0`.**
   Even on real GSM8K data, the runner produces zero misparses. CORE
   refuses what it can't grammar-handle; ADR-0114a Obligation #4
   discipline is preserved against an external corpus.

Skip behavior: tests that need to decrypt require the CORE_HOLDOUT_KEY
env var pointing at the age identity. They are skipped (not failed)
when the key is absent — matches ADR-0105's dev-mode discipline.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOLDOUT_DIR = _REPO_ROOT / "evals" / "gsm8k_math" / "holdouts" / "v1"
_SEALED_PATH = _HOLDOUT_DIR / "cases.jsonl.age"


def _decrypt_or_skip() -> bytes:
    """Decrypt the sealed file using CORE_HOLDOUT_KEY, or skip the test."""
    key_path_str = os.environ.get("CORE_HOLDOUT_KEY")
    if not key_path_str:
        pytest.skip(
            "CORE_HOLDOUT_KEY not set; cannot decrypt sealed holdout. "
            "This matches ADR-0105 dev-mode discipline — set the env "
            "var only at release events."
        )
    try:
        import pyrage
        from pyrage.x25519 import Identity
    except ImportError:
        pytest.skip("pyrage not installed")
    key_path = Path(key_path_str)
    if not key_path.exists():
        pytest.skip(f"CORE_HOLDOUT_KEY={key_path} does not exist")
    identity = Identity.from_str(key_path.read_text(encoding="utf-8").strip())
    return pyrage.decrypt(_SEALED_PATH.read_bytes(), [identity])


class TestSealedFileExists:
    def test_sealed_file_present(self) -> None:
        assert _SEALED_PATH.exists()
        assert _SEALED_PATH.is_file()
        assert _SEALED_PATH.stat().st_size > 0

    def test_sealed_file_is_age_formatted(self) -> None:
        # age files start with "age-encryption.org/" magic header
        head = _SEALED_PATH.read_bytes()[:64]
        assert head.startswith(b"age-encryption.org/"), (
            f"sealed file does not look age-formatted; head={head!r}"
        )


class TestNoPlaintextLeaks:
    def test_no_plaintext_companions(self) -> None:
        """Per ADR-0119.7 seal discipline: only the .age file is on disk."""
        forbidden_names = (
            "cases.jsonl",
            "cases_plaintext.jsonl",
            "cases-train.jsonl",
        )
        for name in forbidden_names:
            path = _HOLDOUT_DIR / name
            if path.exists():
                # Size 0 placeholders are tolerable only if non-empty cases
                # are guaranteed sealed. Default: refuse any sibling file.
                pytest.fail(
                    f"plaintext companion file {path} exists alongside "
                    f"the sealed holdout; remove it or never commit it"
                )


class TestSealedFileDecryptsCleanly:
    def test_decrypt_produces_jsonl(self) -> None:
        plaintext = _decrypt_or_skip()
        lines = plaintext.decode("utf-8").splitlines()
        cases = [json.loads(line) for line in lines if line.strip()]
        assert len(cases) >= 1000, (
            f"sealed file decrypts to {len(cases)} cases; "
            f"expected ≥ 1000 (GSM8K test has 1319)"
        )

    def test_every_case_has_documented_schema(self) -> None:
        plaintext = _decrypt_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        for case in cases[:20]:  # sample to keep test fast
            assert "id" in case
            assert case["id"].startswith("gsm8k-test-")
            assert "problem" in case
            assert isinstance(case["problem"], str) and case["problem"]
            assert "expected_answer" in case
            assert isinstance(case["expected_answer"], (int, float))
            assert "expected_unit" in case
            # ADR-0119.7 schema: empty unit signals "no unit-level check"
            assert case["expected_unit"] == ""


class TestSealedRunnerWrongZero:
    """ADR-0114a Obligation #4 holds against real GSM8K."""

    def test_runner_against_sealed_test_produces_zero_wrong(self) -> None:
        from evals.gsm8k_math.runner import run_lane

        plaintext = _decrypt_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        report = run_lane(cases)
        assert report.metrics["wrong"] == 0, (
            f"runner produced {report.metrics['wrong']} wrong outcomes on "
            f"the sealed GSM8K test; CORE silently confabulated"
        )
        assert report.metrics["wrong_count_is_zero"] is True
        # correct + refused == total (accounting completeness, ADR-0119.3)
        assert (
            report.metrics["correct"] + report.metrics["refused"]
            == report.metrics["cases_total"]
        )
