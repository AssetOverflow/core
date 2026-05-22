from __future__ import annotations

import os
from pathlib import Path

import pytest
from pyrage import encrypt
from pyrage import x25519

from evals.holdout_runner import HOLDOUT_KEY_ENV
from evals.holdout_runner import _decrypt_holdout


@pytest.fixture()
def plaintext_cases() -> str:
    return '{"prompt":"alpha","expected":"beta"}\n'


@pytest.fixture()
def identity_pair() -> tuple[x25519.Identity, x25519.Recipient]:
    identity = x25519.Identity.generate()
    return identity, identity.to_public()


def test_round_trip_decrypt(tmp_path: Path, plaintext_cases: str, identity_pair) -> None:
    identity, recipient = identity_pair

    identity_path = tmp_path / "identity.txt"
    identity_path.write_text(str(identity))

    encrypted_path = tmp_path / "cases.jsonl.age"
    encrypted_path.write_bytes(
        encrypt(plaintext_cases.encode("utf-8"), [recipient])
    )

    os.environ[HOLDOUT_KEY_ENV] = str(identity_path)
    try:
        cases = _decrypt_holdout(encrypted_path)
    finally:
        os.environ.pop(HOLDOUT_KEY_ENV, None)

    assert len(cases) == 1
    assert cases[0]["prompt"] == "alpha"


def test_reject_wrong_identity(tmp_path: Path, plaintext_cases: str) -> None:
    good_identity = x25519.Identity.generate()
    wrong_identity = x25519.Identity.generate()

    wrong_identity_path = tmp_path / "wrong_identity.txt"
    wrong_identity_path.write_text(str(wrong_identity))

    encrypted_path = tmp_path / "cases.jsonl.age"
    encrypted_path.write_bytes(
        encrypt(
            plaintext_cases.encode("utf-8"),
            [good_identity.to_public()],
        )
    )

    os.environ[HOLDOUT_KEY_ENV] = str(wrong_identity_path)
    try:
        with pytest.raises(RuntimeError):
            _decrypt_holdout(encrypted_path)
    finally:
        os.environ.pop(HOLDOUT_KEY_ENV, None)


def test_dev_mode_plaintext_fallback(tmp_path: Path, plaintext_cases: str) -> None:
    plaintext_path = tmp_path / "cases_plaintext.jsonl"
    plaintext_path.write_text(plaintext_cases)

    encrypted_path = tmp_path / "cases.jsonl.age"

    os.environ.pop(HOLDOUT_KEY_ENV, None)
    cases = _decrypt_holdout(encrypted_path)

    assert len(cases) == 1
    assert cases[0]["expected"] == "beta"


def test_key_set_disables_plaintext_fallback(tmp_path: Path, plaintext_cases: str) -> None:
    plaintext_path = tmp_path / "cases_plaintext.jsonl"
    plaintext_path.write_text(plaintext_cases)

    missing_identity = tmp_path / "missing_identity.txt"
    encrypted_path = tmp_path / "cases.jsonl.age"

    os.environ[HOLDOUT_KEY_ENV] = str(missing_identity)
    try:
        with pytest.raises(FileNotFoundError):
            _decrypt_holdout(encrypted_path)
    finally:
        os.environ.pop(HOLDOUT_KEY_ENV, None)
