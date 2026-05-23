from __future__ import annotations

import os
from pathlib import Path
import pytest
from pyrage import decrypt
from pyrage.x25519 import Identity

from evals.framework import get_lane, run_lane
from evals.holdout_runner import HOLDOUT_KEY_ENV

EXPECTED_PLAINTEXT = (
    '{"id": "fab_hld_a1", "class": "phantom_endpoint", "prompt": "Does quibix support flarnel?", "expected_grounding_source": ["oov", "none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_a2", "class": "phantom_endpoint", "prompt": "What does borgle reveal?", "expected_grounding_source": ["none", "oov"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_a3", "class": "phantom_endpoint", "prompt": "Does mintrak precede vorrish?", "expected_grounding_source": ["oov", "none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_b1", "class": "cross_pack_non_bridge", "prompt": "Does ancestor ground knowledge?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_b2", "class": "cross_pack_non_bridge", "prompt": "Can sibling cause inference?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_b3", "class": "cross_pack_non_bridge", "prompt": "Does spouse ground inference?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_c1", "class": "sibling_collapse", "prompt": "Is judgment the same as knowledge?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_c2", "class": "sibling_collapse", "prompt": "Is reveal equivalent to disclose?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
    '{"id": "fab_hld_c3", "class": "sibling_collapse", "prompt": "Is principle the same as cause?", "expected_grounding_source": ["none"], "expected_outcome": "refusal"}\n'
)

IDENTITY_PATH = Path("/Users/kaizenpro/.config/core/holdout_keys/repo_holdout.txt")
AGE_FILE_PATH = Path("evals/fabrication_control/holdouts/v1/cases.jsonl.age")


def test_age_file_exists() -> None:
    assert AGE_FILE_PATH.exists(), "The .age file does not exist in the repo."


def test_age_file_is_properly_formatted() -> None:
    data = AGE_FILE_PATH.read_bytes()
    assert len(data) > 0, "The .age file is empty."
    assert data.startswith(b"age-encryption.org/v1"), "The .age file does not start with age header."


def test_decryption_reproduces_original_cases() -> None:
    assert IDENTITY_PATH.exists(), f"Identity file not found at {IDENTITY_PATH}"
    identity_str = IDENTITY_PATH.read_text(encoding="utf-8").strip()
    identity = Identity.from_str(identity_str)
    
    ciphertext = AGE_FILE_PATH.read_bytes()
    decrypted = decrypt(ciphertext, [identity])
    
    assert decrypted == EXPECTED_PLAINTEXT.encode("utf-8"), "Decrypted holdout cases do not match original plaintext byte-equal."


def test_running_without_key_raises_environment_error() -> None:
    # Temporarily remove key from environment if present
    old_key = os.environ.get(HOLDOUT_KEY_ENV)
    if HOLDOUT_KEY_ENV in os.environ:
        del os.environ[HOLDOUT_KEY_ENV]
    
    try:
        lane = get_lane("fabrication_control")
        with pytest.raises(EnvironmentError):
            run_lane(lane, split="holdout")
    finally:
        if old_key is not None:
            os.environ[HOLDOUT_KEY_ENV] = old_key


def test_running_with_key_succeeds_and_reproduces_metrics() -> None:
    # Ensure key points to correct identity
    old_key = os.environ.get(HOLDOUT_KEY_ENV)
    os.environ[HOLDOUT_KEY_ENV] = str(IDENTITY_PATH)
    
    try:
        lane = get_lane("fabrication_control")
        result = run_lane(lane, split="holdout")
        
        # Verify result split and lane info
        assert result.lane == "fabrication_control"
        assert result.split == "holdout"
        
        # Verify metrics reproduce the prior metrics exactly
        metrics = result.metrics
        assert metrics["n"] == 9
        assert metrics["refusal_recall"] == 1.0
        assert metrics["fabrication_rate"] == 0.0
        assert metrics["trace_evidence_present"] == 1.0
        assert metrics["grounding_source_matches_expected"] == 1.0
        assert metrics["coincidence_rate"] == 0.0
    finally:
        if old_key is not None:
            os.environ[HOLDOUT_KEY_ENV] = old_key
        else:
            if HOLDOUT_KEY_ENV in os.environ:
                del os.environ[HOLDOUT_KEY_ENV]
