"""Tests for ``formation.hashing`` — the content-addressing foundation."""

from __future__ import annotations

import pytest

from formation.hashing import (
    canonical_json,
    self_seal,
    sha256_of,
    verify_seal,
)


class TestCanonicalJson:
    def test_sorted_keys(self) -> None:
        assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'

    def test_tight_separators(self) -> None:
        assert canonical_json([1, 2, 3]) == b"[1,2,3]"

    def test_nested_stability(self) -> None:
        payload = {"z": [3, 2, {"y": 1, "x": 2}], "a": "hello"}
        # Same content, different construction order, must serialize identically.
        twin = {"a": "hello", "z": [3, 2, {"x": 2, "y": 1}]}
        assert canonical_json(payload) == canonical_json(twin)

    def test_utf8(self) -> None:
        assert canonical_json({"k": "wisdom λόγος"}) == '{"k":"wisdom λόγος"}'.encode()

    def test_floats_forbidden(self) -> None:
        with pytest.raises(TypeError, match="float values are forbidden"):
            canonical_json({"x": 1.5})

    def test_floats_forbidden_nested(self) -> None:
        with pytest.raises(TypeError):
            canonical_json([1, 2, [3, 4.0]])

    def test_non_string_dict_keys_forbidden(self) -> None:
        with pytest.raises(TypeError, match="dict keys must be strings"):
            canonical_json({1: "x"})


class TestSha256Of:
    def test_deterministic(self) -> None:
        payload = {"a": 1, "b": [1, 2, 3]}
        assert sha256_of(payload) == sha256_of(payload)

    def test_different_content_different_sha(self) -> None:
        assert sha256_of({"a": 1}) != sha256_of({"a": 2})

    def test_hex_64_chars(self) -> None:
        sha = sha256_of({"a": 1})
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)


class TestSelfSeal:
    def test_seal_then_verify(self) -> None:
        sealed = self_seal({"course_id": "x", "report_sha256": ""})
        assert verify_seal(sealed) is True
        assert sealed["report_sha256"] != ""

    def test_tamper_breaks_seal(self) -> None:
        sealed = self_seal({"course_id": "x", "report_sha256": ""})
        tampered = dict(sealed)
        tampered["course_id"] = "y"
        assert verify_seal(tampered) is False

    def test_blank_sha_fails_verify(self) -> None:
        assert verify_seal({"course_id": "x", "report_sha256": ""}) is False

    def test_missing_field_raises_on_seal(self) -> None:
        with pytest.raises(ValueError, match="missing required field"):
            self_seal({"course_id": "x"})

    def test_missing_field_returns_false_on_verify(self) -> None:
        assert verify_seal({"course_id": "x"}) is False
